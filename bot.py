import discord
from discord.ext import commands
import random
import time
import json
import os
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

omikuji_data = {
    "大吉 🎉": "今日は最強！何やっても成功するかも",
    "中吉 🙂": "いい感じの日、油断しなければOK",
    "小吉 😌": "平和に過ごせる日",
    "吉 👍": "安定した運勢！コツコツいこう",
    "末吉 🤔": "あと一歩で運気アップ",
    "凶 😢": "ちょっと慎重にいこう",
    "大凶 💀": "今日は無理せず休むのが吉"
}

COOLDOWN = 3600
FILE_NAME = "cooldown.json"

def load_data():
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(FILE_NAME, "w") as f:
        json.dump(data, f)

last_used = load_data()

@bot.event
async def on_ready():
    print(f"ログインした: {bot.user}")

@bot.command()
async def omikuji(ctx):
    user_id = str(ctx.author.id)
    now = time.time()

    if user_id in last_used:
        elapsed = now - last_used[user_id]
        remaining = COOLDOWN - elapsed

        if remaining > 0:
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            await ctx.send(
                f"{ctx.author.mention} あと {minutes}分 {seconds}秒 ⏳"
            )
            return

    result = random.choice(list(omikuji_data.keys()))
    message = omikuji_data[result]

    last_used[user_id] = now
    save_data(last_used)

    embed = discord.Embed(
        title="🎴 おみくじ結果",
        description=f"**{result}**",
        color=discord.Color.gold()
    )

    embed.add_field(name="一言", value=message, inline=False)
    embed.set_footer(text=f"{ctx.author} の運勢")
    embed.set_thumbnail(url=ctx.author.avatar.url)

    await ctx.send(embed=embed)

bot.run(TOKEN)
