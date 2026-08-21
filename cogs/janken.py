import secrets

import discord
from discord import app_commands


HANDS = {
    "rock": ("✊", "グー"),
    "scissors": ("✌️", "チョキ"),
    "paper": ("✋", "パー"),
}
WINNING_PAIRS = {("rock", "scissors"), ("scissors", "paper"), ("paper", "rock")}


class JankenView(discord.ui.View):
    def __init__(self, player_id: int):
        super().__init__(timeout=60)
        self.player_id = player_id
        self.finished = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.player_id:
            await interaction.response.send_message(
                "このじゃんけんには参加できません。", ephemeral=True
            )
            return False
        if self.finished:
            await interaction.response.send_message("このじゃんけんは終了しています。", ephemeral=True)
            return False
        return True

    async def choose(self, interaction: discord.Interaction, hand: str) -> None:
        self.finished = True
        bot_hand = secrets.choice(tuple(HANDS))
        if hand == bot_hand:
            result = "🤝 引き分け！"
            color = discord.Color.light_grey()
        elif (hand, bot_hand) in WINNING_PAIRS:
            result = "🎉 あなたの勝ち！"
            color = discord.Color.green()
        else:
            result = "😢 Botの勝ち！"
            color = discord.Color.red()

        for child in self.children:
            child.disabled = True
        user_emoji, user_label = HANDS[hand]
        bot_emoji, bot_label = HANDS[bot_hand]
        embed = discord.Embed(title="✊ じゃんけん結果", color=color)
        embed.add_field(name="あなた", value=f"{user_emoji} {user_label}", inline=True)
        embed.add_field(name="Bot", value=f"{bot_emoji} {bot_label}", inline=True)
        embed.add_field(name="結果", value=result, inline=False)
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="グー", emoji="✊", style=discord.ButtonStyle.primary)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.choose(interaction, "rock")

    @discord.ui.button(label="チョキ", emoji="✌️", style=discord.ButtonStyle.primary)
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.choose(interaction, "scissors")

    @discord.ui.button(label="パー", emoji="✋", style=discord.ButtonStyle.primary)
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.choose(interaction, "paper")


def setup(bot) -> None:
    @bot.tree.command(name="janken", description="Botとじゃんけんをします")
    async def janken(interaction: discord.Interaction):
        embed = discord.Embed(
            title="✊ じゃんけん",
            description="出す手を選んでください。",
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(
            embed=embed, view=JankenView(interaction.user.id)
        )
