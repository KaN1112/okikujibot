from __future__ import annotations

import asyncio
import logging
import os

import discord

from games.werewolf.game import GamePhase, WerewolfGame
from games.werewolf.roles import ROLE_DESCRIPTION, ROLE_EMOJI, Role
from games.werewolf.views import LobbyView, NightTargetView, VoteView


log = logging.getLogger(__name__)
DISCUSSION_TIME = int(os.getenv("WEREWOLF_DISCUSSION_TIME", "180"))
NIGHT_TIME = int(os.getenv("WEREWOLF_NIGHT_TIME", "60"))
VOTE_TIME = int(os.getenv("WEREWOLF_VOTE_TIME", "60"))


class WerewolfManager:
    def __init__(self):
        self.sessions: dict[tuple[int, int], WerewolfSession] = {}

    def remove(self, key: tuple[int, int]) -> None:
        self.sessions.pop(key, None)


class WerewolfSession:
    def __init__(self, manager: WerewolfManager, interaction: discord.Interaction):
        self.manager = manager
        self.game = WerewolfGame(interaction.guild_id, interaction.channel_id, interaction.user.id)
        self.channel = interaction.channel
        self.message: discord.InteractionMessage | discord.Message | None = None
        self.view = LobbyView(self)
        self.task: asyncio.Task | None = None
        self.action_event = asyncio.Event()
        self.starting = False
        self.night_time = NIGHT_TIME
        self.vote_time = VOTE_TIME
        self.game.add_player(interaction.user.id, interaction.user.display_name)

    def lobby_embed(self) -> discord.Embed:
        names = "\n".join(f"・{p.display_name}" for p in self.game.players.values()) or "なし"
        embed = discord.Embed(
            title="🐺 人狼ゲーム",
            description="参加者を募集中です。",
            color=discord.Color.dark_red(),
        )
        embed.add_field(name="参加人数", value=f"{len(self.game.players)}人", inline=False)
        embed.add_field(name="参加者", value=names, inline=False)
        embed.set_footer(text="4～12人で開始できます。ロビーは15分で終了します。")
        return embed

    async def refresh_lobby(self, interaction: discord.Interaction, notice: str) -> None:
        await interaction.response.edit_message(embed=self.lobby_embed(), view=self.view)
        await interaction.followup.send(notice, ephemeral=True)

    async def join(self, interaction: discord.Interaction) -> None:
        if self.starting:
            await interaction.response.send_message("ゲームを開始処理中です。", ephemeral=True)
        elif interaction.user.bot:
            await interaction.response.send_message("Botは参加できません。", ephemeral=True)
        elif interaction.user.id in self.game.players:
            await interaction.response.send_message("すでに参加しています。", ephemeral=True)
        elif len(self.game.players) >= 12:
            await interaction.response.send_message("参加人数は最大12人です。", ephemeral=True)
        else:
            self.game.add_player(interaction.user.id, interaction.user.display_name)
            await self.refresh_lobby(interaction, "参加しました。")

    async def leave(self, interaction: discord.Interaction) -> None:
        if self.starting:
            await interaction.response.send_message("ゲームを開始処理中です。", ephemeral=True)
            return
        if interaction.user.id not in self.game.players:
            await interaction.response.send_message("このロビーに参加していません。", ephemeral=True)
            return
        self.game.remove_player(interaction.user.id)
        await self.refresh_lobby(interaction, "退出しました。")

    async def start(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.game.host_id:
            await interaction.response.send_message("ゲーム開始はロビー作成者のみ行えます。", ephemeral=True)
            return
        if len(self.game.players) < 4:
            await interaction.response.send_message("ゲーム開始には4人以上必要です。", ephemeral=True)
            return
        if self.starting:
            await interaction.response.send_message("ゲームを開始処理中です。", ephemeral=True)
            return
        self.starting = True
        await interaction.response.defer(ephemeral=True, thinking=True)

        failed = []
        users = {}
        for player in self.game.players.values():
            user = interaction.guild.get_member(player.user_id)
            if user is None:
                failed.append(player.display_name)
                continue
            users[player.user_id] = user
            try:
                await user.send("🐺 人狼ゲームのDM疎通確認です。まもなく役職をお送りします。")
            except (discord.Forbidden, discord.HTTPException):
                failed.append(player.display_name)
        if failed:
            await interaction.followup.send(
                f"{', '.join(failed)} さんにDMを送信できませんでした。DiscordのDM設定を確認してください。",
                ephemeral=True,
            )
            self.starting = False
            return

        self.game.assign_roles()
        for player in self.game.players.values():
            role = player.role
            embed = discord.Embed(title="🐺 人狼ゲーム", color=discord.Color.dark_red())
            embed.add_field(
                name="あなたの役職",
                value=f"{ROLE_EMOJI[role]} **{role.value}**\n\n{ROLE_DESCRIPTION[role]}",
                inline=False,
            )
            if role == Role.WEREWOLF:
                allies = [p.display_name for p in self.game.players_with_role(Role.WEREWOLF, alive_only=False) if p.user_id != player.user_id]
                if allies:
                    embed.add_field(name="仲間の人狼", value="\n".join(allies), inline=False)
            try:
                await users[player.user_id].send(embed=embed)
            except (discord.Forbidden, discord.HTTPException):
                await interaction.followup.send(
                    f"{player.display_name} さんへの役職DM送信に失敗したため開始を中止しました。",
                    ephemeral=True,
                )
                self.starting = False
                return

        for child in self.view.children:
            child.disabled = True
        await self.message.edit(
            embed=discord.Embed(
                title="🐺 人狼ゲーム開始",
                description="役職をDMで配布しました。夜になります。",
                color=discord.Color.dark_red(),
            ),
            view=self.view,
        )
        await interaction.followup.send("ゲームを開始しました。", ephemeral=True)
        self.view.stop()
        self.task = asyncio.create_task(self.run(), name=f"werewolf-{self.game.key}")

    async def cancel(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.game.host_id:
            await interaction.response.send_message("キャンセルはロビー作成者のみ行えます。", ephemeral=True)
            return
        if self.starting:
            await interaction.response.send_message("ゲームを開始処理中です。", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=discord.Embed(title="🐺 人狼ゲーム", description="ロビーをキャンセルしました。"),
            view=None,
        )
        self.view.stop()
        self.manager.remove(self.game.key)

    async def expire_lobby(self) -> None:
        if self.game.phase == GamePhase.LOBBY:
            self.manager.remove(self.game.key)
            if self.message:
                try:
                    await self.message.edit(content="ロビーは時間切れになりました。", embed=None, view=None)
                except discord.HTTPException:
                    pass

    def night_action_changed(self) -> None:
        required = sum(1 for p in self.game.alive_players() if p.role != Role.VILLAGER)
        submitted = len(self.game.wolf_votes) + len(self.game.seer_targets) + len(self.game.guard_targets)
        if submitted >= required:
            self.action_event.set()

    def vote_changed(self) -> None:
        if len(self.game.votes) >= len(self.game.alive_players()):
            self.action_event.set()

    async def wait_event(self, timeout: int) -> None:
        self.action_event.clear()
        try:
            await asyncio.wait_for(self.action_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass

    async def run(self) -> None:
        try:
            while True:
                self.game.begin_night()
                await self.channel.send(
                    embed=discord.Embed(
                        title=f"🌙 {self.game.day}日目の夜",
                        description=f"能力者は{self.night_time}秒以内にDMで対象を選択してください。",
                        color=discord.Color.dark_blue(),
                    )
                )
                await self.send_night_actions()
                await self.wait_event(self.night_time)
                victim_id = self.game.resolve_night()
                if victim_id is None:
                    description = "昨晩の犠牲者はいませんでした。"
                else:
                    victim = self.game.players[victim_id]
                    description = f"昨晩、**{victim.display_name}** さんが襲撃されました。\n役職は「{victim.role.value}」でした。"
                await self.channel.send(
                    embed=discord.Embed(title="☀️ 朝になりました", description=description, color=discord.Color.gold())
                )
                if await self.finish_if_winner():
                    return

                self.game.phase = GamePhase.DISCUSSION
                await self.channel.send(
                    embed=discord.Embed(
                        title="💬 議論フェーズ",
                        description=f"{DISCUSSION_TIME}秒後に投票を開始します。",
                        color=discord.Color.blurple(),
                    )
                )
                await asyncio.sleep(DISCUSSION_TIME)

                self.game.phase = GamePhase.VOTING
                self.game.votes.clear()
                await self.channel.send(
                    embed=discord.Embed(
                        title="🗳️ 投票フェーズ",
                        description=f"生存者へDMを送りました。{self.vote_time}秒以内に投票してください。",
                        color=discord.Color.blurple(),
                    )
                )
                await self.send_vote_views()
                await self.wait_event(self.vote_time)
                executed_id, tied = self.game.resolve_vote()
                if tied:
                    description = "同票になりました。今回は処刑なしです。"
                elif executed_id is None:
                    description = "有効な投票がなかったため、処刑なしです。"
                else:
                    executed = self.game.players[executed_id]
                    description = f"**{executed.display_name}** さんが処刑されました。\n役職は「{executed.role.value}」でした。"
                await self.channel.send(
                    embed=discord.Embed(title="⚖️ 投票結果", description=description, color=discord.Color.dark_grey())
                )
                if await self.finish_if_winner():
                    return
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Werewolf session failed: %s", self.game.key)
            try:
                await self.channel.send("ゲーム進行中にエラーが発生したため、このゲームを終了しました。")
            except discord.HTTPException:
                pass
        finally:
            self.manager.remove(self.game.key)

    async def send_night_actions(self) -> None:
        for player in self.game.alive_players():
            if player.role == Role.VILLAGER:
                continue
            member = self.channel.guild.get_member(player.user_id)
            if not member:
                continue
            try:
                await member.send(
                    f"{self.game.day}日目の夜です。対象を選択してください。",
                    view=NightTargetView(self, player.user_id, player.role),
                )
            except (discord.Forbidden, discord.HTTPException):
                log.warning("Night DM failed for %s", player.user_id)

    async def send_vote_views(self) -> None:
        for player in self.game.alive_players():
            member = self.channel.guild.get_member(player.user_id)
            if not member:
                continue
            try:
                await member.send(
                    "追放するプレイヤーを選択してください。",
                    view=VoteView(self, player.user_id),
                )
            except (discord.Forbidden, discord.HTTPException):
                log.warning("Vote DM failed for %s", player.user_id)

    async def finish_if_winner(self) -> bool:
        winner = self.game.winner()
        if winner is None:
            return False
        self.game.phase = GamePhase.ENDED
        title = "🏆 市民陣営の勝利！" if winner == "villagers" else "🏆 人狼陣営の勝利！"
        survivors = "\n".join(p.display_name for p in self.game.alive_players()) or "なし"
        roles = "\n".join(f"{p.display_name}：{p.role.value}" for p in self.game.players.values())
        embed = discord.Embed(title=title, color=discord.Color.gold())
        embed.add_field(name="生存者", value=survivors, inline=False)
        embed.add_field(name="役職一覧", value=roles, inline=False)
        await self.channel.send(embed=embed)
        return True

    async def member_left(self, member_id: int) -> None:
        player = self.game.players.get(member_id)
        if not player:
            return
        if self.game.phase == GamePhase.LOBBY:
            self.game.remove_player(member_id)
            if self.message:
                await self.message.edit(embed=self.lobby_embed(), view=self.view)
        elif player.alive:
            player.alive = False
            await self.channel.send(f"{player.display_name} さんがサーバーを退出したため死亡扱いになりました。")


def setup(bot) -> None:
    manager = WerewolfManager()
    bot.werewolf_manager = manager

    @bot.tree.command(name="werewolf", description="人狼ゲームのロビーを作成します")
    async def werewolf(interaction: discord.Interaction):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message("サーバーのチャンネル内で使用してください。", ephemeral=True)
            return
        key = interaction.guild_id, interaction.channel_id
        if key in manager.sessions:
            await interaction.response.send_message(
                "このチャンネルではすでに人狼ゲームが進行しています。", ephemeral=True
            )
            return
        session = WerewolfSession(manager, interaction)
        manager.sessions[key] = session
        await interaction.response.send_message(embed=session.lobby_embed(), view=session.view)
        session.message = await interaction.original_response()

    @bot.listen("on_member_remove")
    async def werewolf_member_remove(member: discord.Member):
        sessions = [s for (guild_id, _), s in manager.sessions.items() if guild_id == member.guild.id]
        for session in sessions:
            try:
                await session.member_left(member.id)
            except discord.HTTPException:
                log.warning("Failed to process member removal", exc_info=True)

    @bot.listen("on_raw_message_delete")
    async def werewolf_message_delete(payload: discord.RawMessageDeleteEvent):
        for session in list(manager.sessions.values()):
            if session.message and session.message.id == payload.message_id:
                if session.task:
                    session.task.cancel()
                manager.remove(session.game.key)
