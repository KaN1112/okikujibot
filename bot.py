import json
import os
import random
import time
from threading import Thread

import discord
from discord.ext import commands
from web_admin import create_web_app


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = 958943157800800307
GUILD_ID = os.getenv("DISCORD_GUILD_ID")

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
app = create_web_app(bot, OWNER_ID)

omikuji_data = {
    "神吉 👑": {
        "weight": 1,
        "messages": "は！？！？神引ききたあああ！！お前今日何者だよwww 運営さんこいつチート使ってます！！！",
    },
    "虹吉 🌈": {
        "weight": 5,
        "messages": "おおお虹色演出きたーー！！今日は何か奇跡が起こるかもな！！知らんけどwww",
    },
    "超大吉 🔱": {
        "weight": 10,
        "messages": "うぉ！持ってるなぁ！？今日は主人公確定！！その運分けてくれwww",
    },
    "覚醒吉 ⚡": {
        "weight": 20,
        "messages": "覚醒モード突入ーー！！今日のお前、いつもの3倍くらい強そうwww まあ気のせいかもしれんけど！！",
    },
    "大吉 🎉": {
        "weight": 100,
        "messages": [
            "おいおい今日のお前どうした！？運気バグってんぞwww",
            "え、強すぎん？？今日のお前なら何やっても許されそうwww",
            "はい勝ち組確定ーー！！今日だけはお前を認めてやるよ！！",
            "お前今日めっちゃツイてるやん！！さては運営と寝たな？www",
            "今日は神引き確定演出！！その勢いで宝くじでも買っとけwww",
        ],
    },
    "中吉 🙂": {
        "weight": 150,
        "messages": [
            "おっ！悪くないやん！！今日はちょっと調子乗ってもいいぞwww",
            "なかなかいい運勢じゃねぇか！お前にしては上出来すぎるwww",
            "今日はそこそこ勝ち組！！まあ大吉には負けてるけどなwww",
            "おっ、いい感じ！！今日のお前はいつもの1.5倍くらい強そうwww",
            "やるやん！！今日は何かいいこと起こるかもな！！知らんけど！！",
        ],
    },
    "小吉 😌": {
        "weight": 150,
        "messages": [
            "おっ、ちっちゃい幸せゲット！！まあ何もないよりマシだろwww",
            "今日は平和そうだな！！お前が余計なことしなければなwww",
            "小さい吉だけど喜んどけ！！お前には十分すぎるだろwww",
            "まあまあまあ！！悪くないって！！たぶん！！知らんけどwww",
            "今日は地味にいい日！！お前の存在感くらい地味だけどなwww",
        ],
    },
    "吉 👍": {
        "weight": 200,
        "messages": [
            "はい普通ーー！！リアクションに困る運勢引いてて草www",
            "お前らしい無難な結果だな！！まあ平和が一番だろwww",
            "吉かぁ！！なんかコメントしづらい結果出すなよwww",
            "今日は普通に過ごせそう！！ただし調子乗ったら知らんwww",
            "おっ吉じゃん！！良くも悪くもない！！以上！！解散！！",
        ],
    },
    "末吉 🤔": {
        "weight": 150,
        "messages": [
            "うわ微妙ーー！！喜んでいいのか分からんやつwww",
            "お前の運勢、絶妙にコメントしづらくて草www",
            "末吉かよ！！もうちょっと頑張れよ運勢www",
            "まあ凶じゃないだけマシ！！ポジティブにいこうぜwww",
            "はい微妙賞受賞ーー！！なんとも言えねぇなこれwww",
        ],
    },
    "迷吉 🤡": {
        "weight": 50,
        "messages": "なんだこの運勢！？！？運営も意味わかってません！！とりあえずおめでとうwww",
    },
    "凶 😢": {
        "weight": 100,
        "messages": [
            "あっ……ドンマイwww 今日は変なことしない方がいいぞ！！",
            "はい黄色信号ーー！！今日のお前は慎重に行動しろよwww",
            "おっと凶引いちゃったか！！まあ人生そんな日もあるってwww",
            "今日は運に見放されてて草！！自力でなんとかしろwww",
            "あーあ！！今日は何やっても裏目に出そうだなwww",
        ],
    },
    "虚無 🌀": {
        "weight": 30,
        "messages": "……え？運勢どこ行った？？お前の運、存在ごと消えてて草www",
    },
    "大凶 💀": {
        "weight": 30,
        "messages": [
            "はい大事故ーー！！今日のお前、運勢に嫌われすぎだろwww",
            "うわあああ！！大凶引くとか逆に才能あるだろお前www",
            "おいおいマジかよ！！今日のお前にだけは近づきたくねぇwww",
            "終了のお知らせ！！今日の運勢、完全に息してませんwww",
            "はい詰みーー！！もうここまで来たら笑うしかねぇなwww",
        ],
    },
    "超大凶 💔☠": {
        "weight": 3,
        "messages": "はい終了ーーー！！今日は大人しくしとけｗｗｗ 逆にここまで来たら伝説だろ！！今日はもう寝ろ！！解散！！！！",
    },
    "奈落 ☠️": {
        "weight": 1,
        "messages": "おい待て待て待て！！！超大凶の下が存在したのかよwww もうお前が伝説だわ！！！",
    },
}

COOLDOWN = 3600
MESSAGE_COOLDOWN = 10
COOLDOWN_FILE = "cooldown.json"
FORCE_FILE = "force_result.json"
message_cooldown = {}


def load_json(filename):
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


last_used = load_json(COOLDOWN_FILE)
force_result = load_json(FORCE_FILE)


def set_force_result(user_id, result, mode):
    force_result[str(user_id)] = {"result": result, "mode": mode}
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
    value = omikuji_data[result]["messages"]
    return random.choice(value) if isinstance(value, list) else value


@bot.event
async def on_ready():
    print("===== BOT READY =====", flush=True)
    if not getattr(bot, "_commands_synced", False):
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"サーバー同期したコマンド数: {len(synced)}", flush=True)
        else:
            synced = await bot.tree.sync()
            print(f"グローバル同期したコマンド数: {len(synced)}", flush=True)
        bot._commands_synced = True
        print("同期したコマンド:", ", ".join(c.name for c in synced), flush=True)

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="/omikuji | /janken | /dice | /werewolf",
        )
    )
    print(f"ログインした: {bot.user}", flush=True)


@bot.tree.command(name="omikuji", description="おみくじを引きます")
async def omikuji(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    now = time.time()
    if user_id in last_used:
        remaining = COOLDOWN - (now - last_used[user_id])
        if remaining > 0:
            last_msg = message_cooldown.get(user_id, 0)
            if now - last_msg >= MESSAGE_COOLDOWN:
                minutes, seconds = int(remaining // 60), int(remaining % 60)
                message = f"{interaction.user.mention} あと {minutes}分{seconds}秒 待ってね。"
                message_cooldown[user_id] = now
            else:
                message = "まだクールタイム中です。"
            await interaction.response.send_message(message, ephemeral=True)
            return

    forced_result = consume_force_result(user_id)
    if forced_result in omikuji_data:
        result = forced_result
    else:
        result = random.choices(
            list(omikuji_data),
            weights=[data["weight"] for data in omikuji_data.values()],
            k=1,
        )[0]
    last_used[user_id] = now
    save_json(COOLDOWN_FILE, last_used)

    embed = discord.Embed(
        title="おみくじ結果", description=f"**{result}**", color=discord.Color.gold()
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

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "この管理パネルは実行した管理者だけが操作できます。", ephemeral=True
            )
            return False
        return True

    def make_embed(self):
        embed = discord.Embed(
            title="おみくじ管理パネル",
            description="対象ユーザー、運勢、適用方法を選んで保存してください。",
            color=discord.Color.red(),
        )
        embed.add_field(
            name="対象ユーザー",
            value=self.target_user.mention if self.target_user else "未選択",
            inline=False,
        )
        embed.add_field(name="運勢", value=self.fortune or "未選択", inline=False)
        embed.add_field(
            name="適用方法", value="次回のみ" if self.mode == "once" else "固定", inline=False
        )
        return embed

    async def refresh(self, interaction):
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="保存", style=discord.ButtonStyle.green)
    async def save_button(self, interaction, button):
        if not self.target_user or not self.fortune:
            await interaction.response.send_message(
                "対象ユーザーと運勢を両方選んでから保存してください。", ephemeral=True
            )
            return
        set_force_result(self.target_user.id, self.fortune, self.mode)
        label = "次回のみ" if self.mode == "once" else "固定"
        await interaction.response.send_message(
            f"{self.target_user.mention} の運勢を「{self.fortune}」に設定しました。適用方法: {label}",
            ephemeral=True,
        )

    @discord.ui.button(label="解除", style=discord.ButtonStyle.gray)
    async def clear_button(self, interaction, button):
        if not self.target_user:
            await interaction.response.send_message("解除する対象ユーザーを選んでください。", ephemeral=True)
            return
        clear_force_result(self.target_user.id)
        await interaction.response.send_message(
            f"{self.target_user.mention} の固定/次回のみ設定を解除しました。", ephemeral=True
        )


class OmikujiTargetUserSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="対象ユーザーを選択", min_values=1, max_values=1)

    async def callback(self, interaction):
        self.view.target_user = self.values[0]
        await self.view.refresh(interaction)


class OmikujiFortuneSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="運勢を選択",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=result, value=result) for result in omikuji_data],
        )

    async def callback(self, interaction):
        self.view.fortune = self.values[0]
        await self.view.refresh(interaction)


class OmikujiModeSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="固定 / 次回のみを選択",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="次回のみ", value="once", description="次の1回だけ適用します。"),
                discord.SelectOption(label="固定", value="fixed", description="解除するまで適用します。"),
            ],
        )

    async def callback(self, interaction):
        self.view.mode = self.values[0]
        await self.view.refresh(interaction)


@bot.tree.command(name="omikuji_admin", description="管理パネル")
async def omikuji_admin(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("このコマンドは管理者だけが使えます。", ephemeral=True)
        return
    view = OmikujiAdminPanel(interaction.user.id)
    await interaction.response.send_message(embed=view.make_embed(), view=view, ephemeral=True)


from cogs.dice import setup as setup_dice
from cogs.janken import setup as setup_janken
from cogs.werewolf import setup as setup_werewolf

setup_janken(bot)
setup_dice(bot)
setup_werewolf(bot)


def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN が設定されていません。")
    Thread(target=run_web, daemon=True).start()
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
