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
    "超大吉 🔱": "まじでお前今日最強よ。わいも毒舌コメントできないわ",
    "大吉 🎉": "今日のお前、奇跡的に輝いてるな。年イチのバグ発生って感じ",
    "中吉 🙂": "まあまあ良い日。調子乗らなきゃ事故らんやろ、多分な",
    "小吉 😌": "平和？そりゃそうだろ、お前が何も起こせるタイプじゃないし",
    "吉 👍": "安定してるっていうか…代わり映えしない人生って感じ",
    "末吉 🤔": "微妙すぎて逆に笑う。お前の人生の縮図みたいで草",
    "凶 😢": "今日は慎重にしとけ。お前の判断力、基本的に信用ならんし",
    "大凶 💀": "終わってる。今日のお前は歩く災害。外出るな、世界のために",
    "超大凶💔☠": "今日はマジでずっと寝てたほうがいい。言葉がでないわ"
}

# 出現確率（バランス型）
weights = [
    5, #超大吉
    10, # 大吉
    20, # 中吉
    20, # 小吉
    20, # 吉
    15, # 末吉
    10, # 凶
    5,  # 大凶
    2 　#超大凶
]

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

    results = list(omikuji_data.keys())
    result = random.choices(results, weights=weights, k=1)[0]
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

    if ctx.author.avatar:
        embed.set_thumbnail(url=ctx.author.avatar.url)

    await ctx.send(embed=embed)

bot.run(TOKEN)
