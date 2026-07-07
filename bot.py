import json
import os
import random
import time
from threading import Thread

import discord
from discord.ext import commands
from flask import Flask


app = Flask(__name__)


@app.route("/")
def home():
    return "Bot Online"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


Thread(target=run_web, daemon=True).start()

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = 958943157800800307
GUILD_ID = os.getenv("DISCORD_GUILD_ID")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

omikuji_data = {
    "超大吉": "今日は最強。やること全部うまくいくかも。",
    "大吉": [
        "運気はかなり良い感じ。思い切って動いてみよう。",
        "うれしい偶然がありそうな日。",
        "周りから助けてもらいやすい日。感謝を忘れずに。"
    ],
    "中吉": [
        "安定して良い日。焦らず進めば大丈夫。",
        "小さなチャンスを拾える日。",
        "いつもより少しだけ前向きに動けそう。"
    ],
    "小吉": [
        "穏やかな日。無理せずいこう。",
        "小さな幸せを見つけやすい日。",
        "休憩を入れると流れが良くなりそう。"
    ],
    "吉": [
        "普通に良い日。いつもの調子で大丈夫。",
        "落ち着いていけば良い方向に進みそう。",
        "堅実な選択が吉。"
    ],
    "末吉": [
        "少しずつ良くなる日。急がなくてOK。",
        "今は準備のタイミング。あとで効いてくる。",
        "控えめに動くと安定しそう。"
    ],
    "凶": [
        "今日は慎重に。確認を増やすと回避できそう。",
        "無理は禁物。休む判断も大事。",
        "焦るとミスしやすい日。ゆっくりいこう。"
    ],
    "大凶": [
        "今日は守りの日。大きな決断は明日に回してもよさそう。",
        "まずは深呼吸。落ち着けばちゃんと抜けられる。",
        "トラブルの芽は早めに摘んでおこう。"
    ],
    "超大凶": "今日はかなり慎重に。寝て回復するのも立派な作戦。"
}

weights = [1, 10, 20, 20, 20, 15, 10, 5, 1]

COOLDOWN = 3600
MESSAGE_COOLDOWN = 10
COOLDOWN_FILE = "cooldown.json"
FORCE_FILE = "force_result.json"

message_cooldown = {}


def load_json(filename):
    if not os.path.exists(filename):
        return {}

    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


last_used = load_json(COOLDOWN_FILE)
force_result = load_json(FORCE_FILE)


def set_force_result(user_id, result, mode):
    force_result[str(user_id)] = {
        "result": result,
        "mode": mode
    }
    save_json(FORCE_FILE, force_result)


def clear_force_result(user_id):
    user_id = str(user_id)
    if user_id in force_result:
        del force_result[user_id]
        save_json(FORCE_FILE, force_result)


def consume_force_result(user_id):
    user_id = str(user_id)
    data = force_result.get(user_id)
    if not data:
        return None

    result = data.get("result")
    is_once = data.get("mode") == "once" or data.get("permanent") is False
    if is_once:
        del force_result[user_id]
        save_json(FORCE_FILE, force_result)

    return result


def get_omikuji_message(result):
    value = omikuji_data[result]
    return random.choice(value) if isinstance(value, list) else value


@bot.event
async def on_ready():
    print("===== BOT READY =====", flush=True)

    if GUILD_ID:
        guild = discord.Object(id=int(GUILD_ID))
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"サーバー同期したコマンド数: {len(synced)}", flush=True)
    else:
        synced = await bot.tree.sync()
        print(f"グローバル同期したコマンド数: {len(synced)}", flush=True)

    print(f"同期したコマンド数: {len(synced)}", flush=True)
    print("同期したコマンド:", ", ".join(command.name for command in synced), flush=True)

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="おみくじを引くには /omikuji"
        )
    )

    print(f"ログインした: {bot.user}", flush=True)


@bot.tree.command(name="omikuji", description="おみくじを引きます")
async def omikuji(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    now = time.time()

    if user_id in last_used:
        elapsed = now - last_used[user_id]
        remaining = COOLDOWN - elapsed

        if remaining > 0:
            last_msg = message_cooldown.get(user_id, 0)

            if now - last_msg >= MESSAGE_COOLDOWN:
                minutes = int(remaining // 60)
                seconds = int(remaining % 60)
                await interaction.response.send_message(
                    f"{interaction.user.mention} あと {minutes}分{seconds}秒 待ってね。",
                    ephemeral=True
                )
                message_cooldown[user_id] = now
            else:
                await interaction.response.send_message(
                    "まだクールタイム中です。",
                    ephemeral=True
                )
            return

    forced_result = consume_force_result(user_id)
    if forced_result in omikuji_data:
        result = forced_result
    else:
        results = list(omikuji_data.keys())
        result = random.choices(results, weights=weights, k=1)[0]

    last_used[user_id] = now
    save_json(COOLDOWN_FILE, last_used)

    embed = discord.Embed(
        title="おみくじ結果",
        description=f"**{result}**",
        color=discord.Color.gold()
    )
    embed.add_field(name="ひとこと", value=get_omikuji_message(result), inline=False)
    embed.set_footer(text=f"{interaction.user} の運勢")

    if interaction.user.avatar:
        embed.set_thumbnail(url=interaction.user.avatar.url)

    await interaction.response.send_message(embed=embed)


class OmikujiAdminPanel(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.target_user = None
        self.fortune = None
        self.mode = "once"
        self.add_item(OmikujiTargetUserSelect())
        self.add_item(OmikujiFortuneSelect())
        self.add_item(OmikujiModeSelect())

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "この管理パネルは実行した管理者だけが操作できます。",
                ephemeral=True
            )
            return False
        return True

    def make_embed(self):
        embed = discord.Embed(
            title="おみくじ管理パネル",
            description="対象ユーザー、運勢、適用方法を選んで保存してください。",
            color=discord.Color.red()
        )
        embed.add_field(
            name="対象ユーザー",
            value=self.target_user.mention if self.target_user else "未選択",
            inline=False
        )
        embed.add_field(
            name="運勢",
            value=self.fortune if self.fortune else "未選択",
            inline=False
        )
        embed.add_field(
            name="適用方法",
            value="次回のみ" if self.mode == "once" else "固定",
            inline=False
        )
        return embed

    async def refresh(self, interaction):
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="保存", style=discord.ButtonStyle.green)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.target_user or not self.fortune:
            await interaction.response.send_message(
                "対象ユーザーと運勢を両方選んでから保存してください。",
                ephemeral=True
            )
            return

        set_force_result(self.target_user.id, self.fortune, self.mode)
        mode_label = "次回のみ" if self.mode == "once" else "固定"
        await interaction.response.send_message(
            f"{self.target_user.mention} の運勢を「{self.fortune}」に設定しました。適用方法: {mode_label}",
            ephemeral=True
        )

    @discord.ui.button(label="解除", style=discord.ButtonStyle.gray)
    async def clear_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.target_user:
            await interaction.response.send_message(
                "解除する対象ユーザーを選んでください。",
                ephemeral=True
            )
            return

        clear_force_result(self.target_user.id)
        await interaction.response.send_message(
            f"{self.target_user.mention} の固定/次回のみ設定を解除しました。",
            ephemeral=True
        )


class OmikujiTargetUserSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="対象ユーザーを選択", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        self.view.target_user = self.values[0]
        await self.view.refresh(interaction)


class OmikujiFortuneSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=result, value=result)
            for result in omikuji_data.keys()
        ]
        super().__init__(
            placeholder="運勢を選択",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.fortune = self.values[0]
        await self.view.refresh(interaction)


class OmikujiModeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="次回のみ",
                value="once",
                description="対象ユーザーが次に /omikuji を引いた1回だけ適用します。"
            ),
            discord.SelectOption(
                label="固定",
                value="fixed",
                description="解除するまで毎回この運勢にします。"
            )
        ]
        super().__init__(
            placeholder="固定 / 次回のみを選択",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.mode = self.values[0]
        await self.view.refresh(interaction)


@bot.tree.command(
    name="omikuji_admin",
    description="おみくじの結果をユーザーごとに管理します"
)
async def omikuji_admin(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "このコマンドは管理者だけが使えます。",
            ephemeral=True
        )
        return

    view = OmikujiAdminPanel(interaction.user.id)
    await interaction.response.send_message(
        embed=view.make_embed(),
        view=view,
        ephemeral=True
    )


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN が設定されていません。")

bot.run(TOKEN)
