import asyncio
import json
import os
import secrets
import time
from collections import defaultdict, deque
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import discord
from flask import Flask, jsonify, redirect, render_template, request, session, url_for


DISCORD_API = "https://discord.com/api/v10"
MESSAGE_LIMIT = 2000
DESTINATION_LIMIT = 10
SEND_TIMEOUT = 15
RATE_LIMIT_COUNT = 5
RATE_LIMIT_WINDOW = 60


class AnnouncementHistory:
    def __init__(self, filename=None):
        self.filename = Path(filename) if filename else None
        self._lock = Lock()
        self.last_error = None
        self._items = self._load()

    @property
    def persistent(self):
        return self.filename is not None and self.last_error is None

    def _load(self):
        if not self.filename or not self.filename.exists():
            return []
        try:
            with self.filename.open("r", encoding="utf-8") as file:
                value = json.load(file)
                return value if isinstance(value, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def add(self, item):
        with self._lock:
            self._items.insert(0, item)
            self._items = self._items[:200]
            if not self.filename:
                return
            try:
                self.filename.parent.mkdir(parents=True, exist_ok=True)
                temporary = self.filename.with_suffix(self.filename.suffix + ".tmp")
                with temporary.open("w", encoding="utf-8") as file:
                    json.dump(self._items, file, ensure_ascii=False, indent=2)
                os.replace(temporary, self.filename)
                self.last_error = None
            except OSError as error:
                self.last_error = str(error)

    def all(self):
        with self._lock:
            return list(self._items)


def create_web_app(bot, owner_id, config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY"),
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=3600,
    )
    if config:
        app.config.update(config)

    configured_admins = {
        value.strip()
        for value in os.getenv("ADMIN_DISCORD_IDS", "").split(",")
        if value.strip().isdigit()
    }
    allowed_admins = {str(owner_id), *configured_admins}
    history = AnnouncementHistory(os.getenv("ANNOUNCEMENT_HISTORY_FILE"))
    attempts = defaultdict(deque)
    attempts_lock = Lock()

    def configuration_error():
        required = {
            "DISCORD_CLIENT_ID": os.getenv("DISCORD_CLIENT_ID"),
            "DISCORD_CLIENT_SECRET": os.getenv("DISCORD_CLIENT_SECRET"),
            "DISCORD_REDIRECT_URI": os.getenv("DISCORD_REDIRECT_URI"),
            "FLASK_SECRET_KEY": app.config.get("SECRET_KEY"),
        }
        missing = [name for name, value in required.items() if not value]
        return missing

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user_id = str(session.get("user", {}).get("id", ""))
            if not user_id:
                return redirect(url_for("login"))
            if user_id not in allowed_admins:
                session.clear()
                return render_template("error.html", message="この管理画面を利用する権限がありません。"), 403
            return view(*args, **kwargs)

        return wrapped

    def csrf_token():
        if not app.config.get("SECRET_KEY"):
            return ""
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return session["csrf_token"]

    def valid_csrf():
        supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        return bool(supplied and secrets.compare_digest(supplied, session.get("csrf_token", "")))

    def discord_request(path, method="GET", data=None, token=None):
        body = urlencode(data).encode() if data is not None else None
        headers = {"User-Agent": "okikujibot-admin/1.0"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request_object = Request(f"{DISCORD_API}{path}", data=body, headers=headers, method=method)
        try:
            with urlopen(request_object, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise RuntimeError(f"Discord認証APIがエラーを返しました ({error.code})") from error
        except (URLError, TimeoutError) as error:
            raise RuntimeError("Discord認証APIに接続できませんでした") from error

    def run_on_bot(coroutine):
        if not bot.is_ready() or bot.loop.is_closed():
            coroutine.close()
            raise RuntimeError("Botの準備が完了していません。しばらく待ってから再試行してください。")
        future = asyncio.run_coroutine_threadsafe(coroutine, bot.loop)
        try:
            return future.result(timeout=SEND_TIMEOUT)
        except FutureTimeoutError as error:
            future.cancel()
            raise RuntimeError("Discord処理がタイムアウトしました。") from error

    async def guild_list():
        return [
            {
                "id": str(guild.id),
                "name": guild.name,
                "icon": guild.icon.url if guild.icon else None,
            }
            for guild in bot.guilds
        ]

    async def channel_list(guild_id):
        guild = bot.get_guild(guild_id)
        if guild is None:
            raise ValueError("指定されたサーバーにBotが参加していません。")
        member = guild.me
        channels = []
        for channel in guild.text_channels:
            permissions = channel.permissions_for(member)
            if permissions.view_channel and permissions.send_messages:
                channels.append(
                    {
                        "id": str(channel.id),
                        "name": channel.name,
                        "can_mention_everyone": permissions.mention_everyone,
                    }
                )
        roles = [
            {"id": str(role.id), "name": role.name, "mentionable": role.mentionable}
            for role in guild.roles
            if not role.is_default() and not role.managed
        ]
        users = [
            {"id": str(member.id), "name": member.display_name}
            for member in guild.members
            if not member.bot
        ]
        return {"guild": {"id": str(guild.id), "name": guild.name}, "channels": channels, "roles": roles, "users": users}

    def prepare_announcement(guild_id, channel_id, content, mention_options):
        guild = bot.get_guild(guild_id)
        if guild is None:
            raise ValueError("指定されたサーバーにBotが参加していません。")
        channel = guild.get_channel(channel_id)
        if channel is None or not isinstance(channel, discord.TextChannel):
            raise ValueError("指定されたテキストチャンネルは利用できません。")
        permissions = channel.permissions_for(guild.me)
        if not permissions.view_channel or not permissions.send_messages:
            raise PermissionError("Botにチャンネルの閲覧・送信権限がありません。")

        everyone = bool(mention_options.get("everyone"))
        role_ids = {str(value) for value in mention_options.get("roles", [])}
        user_ids = {str(value) for value in mention_options.get("users", [])}
        roles = [role for role in guild.roles if str(role.id) in role_ids]
        users = [member for member in guild.members if str(member.id) in user_ids]
        if len(roles) != len(role_ids) or len(users) != len(user_ids):
            raise ValueError("無効なメンション対象が含まれています。")
        if everyone and not permissions.mention_everyone:
            raise PermissionError("BotにEveryone/Hereを通知する権限がありません。")
        if any(not role.mentionable for role in roles) and not permissions.mention_everyone:
            raise PermissionError("Botが通知できないロールが選択されています。")
        if any(f"<@&{role.id}>" not in content for role in roles):
            raise ValueError("選択したロールのメンションが本文にありません。")
        if any(
            f"<@{member.id}>" not in content and f"<@!{member.id}>" not in content
            for member in users
        ):
            raise ValueError("選択したユーザーのメンションが本文にありません。")
        if everyone and "@everyone" not in content and "@here" not in content:
            raise ValueError("Everyone/Hereメンションが本文にありません。")

        allowed_mentions = discord.AllowedMentions(
            everyone=everyone,
            roles=roles,
            users=users,
            replied_user=False,
        )
        return guild, channel, allowed_mentions

    async def send_announcements(destinations, content):
        prepared = []
        for destination in destinations:
            try:
                guild_id = int(destination.get("guild_id"))
                channel_id = int(destination.get("channel_id"))
            except (TypeError, ValueError) as error:
                raise ValueError("送信先が不正です。") from error
            mentions = destination.get("mentions")
            if not isinstance(mentions, dict):
                mentions = {}
            guild, channel, allowed_mentions = prepare_announcement(
                guild_id, channel_id, content, mentions
            )
            prepared.append((destination, guild, channel, allowed_mentions))

        results = []
        for destination, guild, channel, allowed_mentions in prepared:
            try:
                message = await channel.send(content, allowed_mentions=allowed_mentions)
                results.append(
                    {
                        "ok": True,
                        "guild_id": str(guild.id),
                        "guild_name": guild.name,
                        "channel_id": str(channel.id),
                        "channel_name": channel.name,
                        "message_id": str(message.id),
                    }
                )
            except discord.DiscordException as error:
                results.append(
                    {
                        "ok": False,
                        "guild_id": str(guild.id),
                        "guild_name": guild.name,
                        "channel_id": str(channel.id),
                        "channel_name": channel.name,
                        "error": str(error),
                    }
                )
        return results

    def rate_limited(user_id):
        now = time.monotonic()
        with attempts_lock:
            queue = attempts[user_id]
            while queue and now - queue[0] >= RATE_LIMIT_WINDOW:
                queue.popleft()
            if len(queue) >= RATE_LIMIT_COUNT:
                return True
            queue.append(now)
            return False

    def history_item(payload, destination, result, error=None, message_id=None):
        return {
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "sender_id": str(session["user"]["id"]),
            "guild_id": str(destination.get("guild_id", "")),
            "guild_name": result.get("guild_name", "") if result else "",
            "channel_id": str(destination.get("channel_id", "")),
            "channel_name": result.get("channel_name", "") if result else "",
            "content": str(payload.get("content", "")),
            "result": "成功" if not error else "失敗",
            "message_id": message_id,
            "error": error,
        }

    @app.context_processor
    def template_values():
        return {"csrf_token": csrf_token, "current_user": session.get("user")}

    @app.get("/admin")
    def home():
        if session.get("user"):
            return redirect(url_for("dashboard"))
        return render_template("login.html", missing_config=configuration_error())

    @app.get("/")
    @app.get("/health")
    def health():
        return "Bot Online"

    @app.get("/login")
    def login():
        missing = configuration_error()
        if missing:
            return render_template("error.html", message=f"環境変数が未設定です: {', '.join(missing)}"), 503
        state = secrets.token_urlsafe(32)
        session.clear()
        session["oauth_state"] = state
        query = urlencode(
            {
                "client_id": os.environ["DISCORD_CLIENT_ID"],
                "redirect_uri": os.environ["DISCORD_REDIRECT_URI"],
                "response_type": "code",
                "scope": "identify",
                "state": state,
                "prompt": "none",
            }
        )
        return redirect(f"https://discord.com/oauth2/authorize?{query}")

    @app.get("/oauth/callback")
    def oauth_callback():
        state = session.pop("oauth_state", "")
        received_state = request.args.get("state", "")
        if not state or not secrets.compare_digest(state, received_state):
            return render_template("error.html", message="OAuth stateの検証に失敗しました。"), 400
        code = request.args.get("code")
        if not code:
            return render_template("error.html", message="Discord認証がキャンセルされました。"), 400
        try:
            token_data = discord_request(
                "/oauth2/token",
                method="POST",
                data={
                    "client_id": os.environ["DISCORD_CLIENT_ID"],
                    "client_secret": os.environ["DISCORD_CLIENT_SECRET"],
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": os.environ["DISCORD_REDIRECT_URI"],
                },
            )
            user = discord_request("/users/@me", token=token_data["access_token"])
        except (KeyError, RuntimeError) as error:
            return render_template("error.html", message=str(error)), 502
        if str(user.get("id", "")) not in allowed_admins:
            session.clear()
            return render_template("error.html", message="このDiscordアカウントには管理権限がありません。"), 403
        session.clear()
        session.permanent = True
        session["user"] = {
            "id": str(user["id"]),
            "username": user.get("global_name") or user.get("username", "Discord User"),
            "avatar": user.get("avatar"),
        }
        csrf_token()
        return redirect(url_for("dashboard"))

    @app.post("/logout")
    @admin_required
    def logout():
        if not valid_csrf():
            return render_template("error.html", message="CSRF検証に失敗しました。"), 403
        session.clear()
        return redirect(url_for("home"))

    @app.get("/dashboard")
    @admin_required
    def dashboard():
        return render_template("dashboard.html", persistent_history=history.persistent)

    @app.get("/announcements/new")
    @admin_required
    def announcement_form():
        return render_template("announcement.html", message_limit=MESSAGE_LIMIT)

    @app.get("/history")
    @admin_required
    def announcement_history():
        return render_template("history.html", items=history.all(), persistent_history=history.persistent)

    @app.get("/api/guilds")
    @admin_required
    def api_guilds():
        try:
            return jsonify({"guilds": run_on_bot(guild_list())})
        except RuntimeError as error:
            return jsonify({"error": str(error)}), 503

    @app.get("/api/guilds/<int:guild_id>/channels")
    @admin_required
    def api_channels(guild_id):
        try:
            return jsonify(run_on_bot(channel_list(guild_id)))
        except ValueError as error:
            return jsonify({"error": str(error)}), 404
        except RuntimeError as error:
            return jsonify({"error": str(error)}), 503

    @app.post("/api/send-token")
    @admin_required
    def api_send_token():
        if not valid_csrf():
            return jsonify({"error": "CSRF検証に失敗しました。"}), 403
        token = secrets.token_urlsafe(24)
        session["send_token"] = token
        return jsonify({"send_token": token})

    @app.post("/api/announcements")
    @admin_required
    def api_send_announcement():
        if not valid_csrf():
            return jsonify({"error": "CSRF検証に失敗しました。"}), 403
        payload = request.get_json(silent=True) or {}
        supplied_token = str(payload.get("send_token", ""))
        expected_token = str(session.pop("send_token", ""))
        if not supplied_token or not expected_token or not secrets.compare_digest(supplied_token, expected_token):
            return jsonify({"error": "送信確認トークンが無効です。再度確認してください。"}), 409
        user_id = str(session["user"]["id"])
        if rate_limited(user_id):
            return jsonify({"error": "送信回数が上限に達しました。1分後に再試行してください。"}), 429
        content = payload.get("content")
        if not isinstance(content, str) or not content.strip():
            return jsonify({"error": "メッセージを入力してください。"}), 400
        if len(content) > MESSAGE_LIMIT:
            return jsonify({"error": f"メッセージは{MESSAGE_LIMIT}文字以内にしてください。"}), 400
        destinations = payload.get("destinations")
        if not isinstance(destinations, list):
            destinations = [
                {
                    "guild_id": payload.get("guild_id"),
                    "channel_id": payload.get("channel_id"),
                    "mentions": payload.get("mentions", {}),
                }
            ]
        if not destinations or len(destinations) > DESTINATION_LIMIT:
            return jsonify({"error": f"送信先は1〜{DESTINATION_LIMIT}件で指定してください。"}), 400
        destination_keys = {
            (str(item.get("guild_id", "")), str(item.get("channel_id", "")))
            for item in destinations
            if isinstance(item, dict)
        }
        if len(destination_keys) != len(destinations):
            return jsonify({"error": "重複または不正な送信先が含まれています。"}), 400
        try:
            results = run_on_bot(send_announcements(destinations, content))
            for destination, result in zip(destinations, results):
                history.add(
                    history_item(
                        payload,
                        destination,
                        result,
                        error=result.get("error"),
                        message_id=result.get("message_id"),
                    )
                )
            success_count = sum(result["ok"] for result in results)
            status = 200 if success_count == len(results) else 207
            return jsonify(
                {
                    "ok": success_count == len(results),
                    "success_count": success_count,
                    "failure_count": len(results) - success_count,
                    "results": results,
                }
            ), status
        except (ValueError, PermissionError, RuntimeError, discord.DiscordException) as error:
            for destination in destinations:
                history.add(history_item(payload, destination, {}, error=str(error)))
            status = 403 if isinstance(error, PermissionError) else 400
            if isinstance(error, (RuntimeError, discord.DiscordException)):
                status = 503
            return jsonify({"error": str(error)}), status

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", message="ページが見つかりません。"), 404

    @app.errorhandler(500)
    def server_error(_error):
        return render_template("error.html", message="管理画面でエラーが発生しました。"), 500

    return app
