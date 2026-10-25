from concurrent.futures import Future
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import web_admin


class FakePermissions:
    view_channel = True
    send_messages = True
    mention_everyone = True


class FakeRole:
    def __init__(self, role_id, name, mentionable=True, default=False):
        self.id = role_id
        self.name = name
        self.mentionable = mentionable
        self.managed = False
        self._default = default

    def is_default(self):
        return self._default


class FakeMember:
    def __init__(self, user_id, name, bot=False):
        self.id = user_id
        self.display_name = name
        self.bot = bot


class FakeChannel:
    def __init__(self, channel_id=20, name="announcements"):
        self.id = channel_id
        self.name = name
        self.sent = []

    def permissions_for(self, _member):
        return FakePermissions()

    async def send(self, content, allowed_mentions):
        self.sent.append((content, allowed_mentions))
        return SimpleNamespace(id=999)


class FakeGuild:
    def __init__(self):
        self.id = 10
        self.name = "Test Guild"
        self.icon = None
        self.me = FakeMember(1, "Bot", bot=True)
        self.channel = FakeChannel()
        self.text_channels = [self.channel]
        self.roles = [FakeRole(10, "everyone", default=True), FakeRole(30, "News")]
        self.members = [self.me, FakeMember(40, "Admin")]

    def get_channel(self, channel_id):
        return self.channel if channel_id == self.channel.id else None


class FakeBot:
    def __init__(self):
        self.guild = FakeGuild()
        self.guilds = [self.guild]
        self.loop = SimpleNamespace(is_closed=lambda: False)

    def is_ready(self):
        return True

    def get_guild(self, guild_id):
        return self.guild if guild_id == self.guild.id else None

    def close(self):
        pass


def run_coroutine_immediately(coroutine, _loop):
    future = Future()
    try:
        coroutine.send(None)
        future.set_exception(RuntimeError("Test coroutine unexpectedly suspended"))
    except StopIteration as result:
        future.set_result(result.value)
    except Exception as error:
        future.set_exception(error)
    return future


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


class WebAdminTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(dir=os.getcwd())
        self.environment = patch.dict(
            os.environ,
            {
                "DISCORD_CLIENT_ID": "client",
                "DISCORD_CLIENT_SECRET": "secret",
                "DISCORD_REDIRECT_URI": "https://example.test/oauth/callback",
                "FLASK_SECRET_KEY": "test-secret",
                "ANNOUNCEMENT_HISTORY_FILE": os.path.join(self.tempdir.name, "history.json"),
            },
            clear=False,
        )
        self.environment.start()
        self.bot = FakeBot()
        self.text_channel_patch = patch.object(web_admin.discord, "TextChannel", FakeChannel)
        self.text_channel_patch.start()
        self.coroutine_patch = patch.object(
            web_admin.asyncio,
            "run_coroutine_threadsafe",
            side_effect=run_coroutine_immediately,
        )
        self.coroutine_patch.start()
        self.app = web_admin.create_web_app(
            self.bot,
            123,
            {"TESTING": True, "SESSION_COOKIE_SECURE": False},
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.bot.close()
        self.coroutine_patch.stop()
        self.text_channel_patch.stop()
        self.environment.stop()
        self.tempdir.cleanup()

    def login(self):
        with self.client.session_transaction() as session:
            session["user"] = {"id": "123", "username": "Owner"}
            session["csrf_token"] = "csrf"

    def send_token(self):
        response = self.client.post("/api/send-token", headers={"X-CSRF-Token": "csrf"})
        return response.get_json()["send_token"]

    def test_health_and_unauthenticated_access(self):
        self.assertEqual(self.client.get("/").data, b"Bot Online")
        self.assertEqual(self.client.get("/health").data, b"Bot Online")
        self.assertEqual(self.client.get("/dashboard").status_code, 302)
        self.assertIn("/login", self.client.get("/dashboard").location)

    def test_owner_can_access_dashboard_and_guilds(self):
        self.login()
        self.assertEqual(self.client.get("/dashboard").status_code, 200)
        response = self.client.get("/api/guilds")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["guilds"][0]["id"], "10")

    def test_channels_reject_unknown_guild(self):
        self.login()
        self.assertEqual(self.client.get("/api/guilds/999/channels").status_code, 404)
        response = self.client.get("/api/guilds/10/channels")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["channels"][0]["id"], "20")

    def test_csrf_is_required(self):
        self.login()
        self.assertEqual(self.client.post("/api/send-token").status_code, 403)
        self.assertEqual(
            self.client.post("/api/announcements", json={"content": "test"}).status_code,
            403,
        )

    def test_send_and_duplicate_prevention(self):
        self.login()
        token = self.send_token()
        payload = {
            "guild_id": "10",
            "channel_id": "20",
            "content": "Hello <@&30> <@40>",
            "send_token": token,
            "mentions": {"everyone": False, "roles": ["30"], "users": ["40"]},
        }
        response = self.client.post(
            "/api/announcements",
            json=payload,
            headers={"X-CSRF-Token": "csrf"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["message_id"], "999")
        self.assertEqual(len(self.bot.guild.channel.sent), 1)
        duplicate = self.client.post(
            "/api/announcements",
            json=payload,
            headers={"X-CSRF-Token": "csrf"},
        )
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(len(self.bot.guild.channel.sent), 1)
        self.assertTrue(os.path.exists(os.environ["ANNOUNCEMENT_HISTORY_FILE"]))

    def test_selected_mention_must_exist_in_content(self):
        self.login()
        payload = {
            "guild_id": "10",
            "channel_id": "20",
            "content": "Hello",
            "send_token": self.send_token(),
            "mentions": {"everyone": False, "roles": ["30"], "users": []},
        }
        response = self.client.post(
            "/api/announcements",
            json=payload,
            headers={"X-CSRF-Token": "csrf"},
        )
        self.assertEqual(response.status_code, 400)

    def test_oauth_state_and_owner_check(self):
        with self.client.session_transaction() as session:
            session["oauth_state"] = "expected"
        self.assertEqual(self.client.get("/oauth/callback?state=wrong&code=x").status_code, 400)

        with self.client.session_transaction() as session:
            session["oauth_state"] = "expected"
        responses = [FakeResponse({"access_token": "token"}), FakeResponse({"id": "456"})]
        with patch.object(web_admin, "urlopen", side_effect=responses):
            response = self.client.get("/oauth/callback?state=expected&code=x")
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
