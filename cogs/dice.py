import secrets

import discord
from discord import app_commands


def roll_dice(sides: int, count: int) -> list[int]:
    return [secrets.randbelow(sides) + 1 for _ in range(count)]


def setup(bot) -> None:
    @bot.tree.command(name="dice", description="ダイスを振ります")
    @app_commands.describe(sides="ダイスの面数（2～1000）", count="振る個数（1～20）")
    @app_commands.rename(sides="面数", count="個数")
    async def dice(interaction: discord.Interaction, sides: int = 6, count: int = 1):
        if not 2 <= sides <= 1000:
            await interaction.response.send_message(
                "面数は2～1000の範囲で指定してください。", ephemeral=True
            )
            return
        if not 1 <= count <= 20:
            await interaction.response.send_message(
                "個数は1～20の範囲で指定してください。", ephemeral=True
            )
            return

        rolls = roll_dice(sides, count)
        embed = discord.Embed(
            title="🎲 ダイス",
            description=f"{sides}面ダイス × {count}",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="結果", value=" / ".join(map(str, rolls)), inline=False)
        if count > 1:
            embed.add_field(name="合計", value=str(sum(rolls)), inline=False)
        await interaction.response.send_message(embed=embed)
