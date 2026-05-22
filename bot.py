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

# -----------------------------
# おみくじデータ
# -----------------------------
omikuji_data = {
    "超大吉 🔱": "まじでお前今日最強よ。わいも毒舌コメントできないわ",

    "大吉 🎉": [
        "今日のお前、奇跡的に輝いてるな。年イチのバグ発生やん",
        "運が良すぎて逆に怖いわ。明日から反動くるぞ",
        "今日だけは主人公補正入ってるっぽいな。調子乗るなよ？",
        "なんか今日のお前、普通にいい感じやん。素直に褒めとくわ"
    ],

    "中吉 🙂": [
        "まあまあ良い日。お前にしては上出来やん",
        "油断しなければ事故らん…はず。知らんけど",
        "そこそこ良い感じ。お前の人生で“そこそこ”は奇跡レベル",
        "今日は落ち着いてていい日になりそうやな。安心していけ"
    ],

    "小吉 😌": [
        "平和な日。お前が何も起こせるタイプじゃないからな",
        "特に何も起きん。いつも通りの地味な日や",
        "静かに過ごせる日。お前の存在感と同じで薄い",
        "ゆっくりできる日やで。たまにはこういうのも悪くないやろ"
    ],

    "吉 👍": [
        "安定してるっていうか、代わり映えしないだけやな",
        "コツコツいけ？お前にスピード感なんて元からないやろ",
        "まあ悪くない。良くもない。お前らしい中途半端さ",
        "安定してて良い日やと思うで。無理せずいこ"
    ],

    "末吉 🤔": [
        "微妙すぎて草。お前の人生の縮図やん",
        "なんとも言えん運勢。お前の性格みたいに曖昧",
        "可もなく不可もなく…いや、ちょい不可寄りやな",
        "まあ悪いわけじゃないし、気楽にいけばなんとかなるで"
    ],

    "凶 😢": [
        "慎重にいけ。お前の判断力は基本バグってるからな",
        "今日はやらかす未来が見える。気をつけとけよ",
        "運悪いな。まあお前なら慣れてるやろ",
        "ちょっと注意すれば普通に乗り切れるで。落ち込むな"
    ],

    "大凶 💀": [
        "終わってる。今日のお前は歩く災害。外出るな",
        "運勢ゴミ。逆にここまで悪いと才能感じるわ",
        "今日の不運、もはや芸術。世界が敵やな",
        "まあ…逆にここから上がるだけやし、ある意味チャンスやで"
    ],

    "超大凶 💔☠": "今日はマジでずっと寝てたほうがいい。言葉がでないわ"
}

# -----------------------------
# 出現確率（重み）
# -----------------------------
weights = [
    1,   # 超大吉
    10,  # 大吉
    20,  # 中吉
    20,  # 小吉
    20,  # 吉
    15,  # 末吉
    10,  # 凶
    5,   # 大凶
    1    # 超大凶
]

# -----------------------------
# クールダウン設定
# -----------------------------
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

# -----------------------------
# Bot 起動
# -----------------------------
@bot.event
async def on_ready():
    print(f"ログインした: {bot.user}")

# -----------------------------
# おみくじコマンド
# -----------------------------
@bot.command()
async def omikuji(ctx):
    user_id = str(ctx.author.id)
    now = time.time()

    # クールダウンチェック
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

    # 運勢を重み付きで抽選
    results = list(omikuji_data.keys())
    result = random.choices(results, weights=weights, k=1)[0]

    # 一言メッセージを抽選（リスト or 文字列）
    value = omikuji_data[result]
    if isinstance(value, list):
        message = random.choice(value)
    else:
        message = value

    # クールダウン更新
    last_used[user_id] = now
    save_data(last_used)

    # Embed 作成
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

# -----------------------------
# Bot 実行
# -----------------------------
bot.run(TOKEN)
