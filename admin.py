from discord import app_commands
import discord

OWNER_ID = 958943157800800307

FORTUNES = [
    "超大吉 🔱",
    "大吉 🎉",
    "中吉 🙂",
    "小吉 😌",
    "吉 👍",
    "末吉 🤔",
    "凶 😢",
    "大凶 💀",
    "超大凶 💔☠"
]


class AdminState:

    def __init__(self):
        self.selected_user = None
        self.mode = "once"


state = AdminState()


def is_owner(interaction: discord.Interaction):

    return interaction.user.id == OWNER_ID


def make_embed():

    embed = discord.Embed(
        title="🎴 おみくじ管理",
        color=discord.Color.red()
    )

    if state.selected_user:

        embed.add_field(
            name="対象ユーザー",
            value=state.selected_user.mention,
            inline=False
        )

    else:

        embed.add_field(
            name="対象ユーザー",
            value="未選択",
            inline=False
        )

    embed.add_field(
        name="設定",
        value="次回のみ" if state.mode == "once" else "固定",
        inline=False
    )

    return embed
