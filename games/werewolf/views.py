from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from .roles import Role

if TYPE_CHECKING:
    from cogs.werewolf import WerewolfSession


class LobbyView(discord.ui.View):
    def __init__(self, session: "WerewolfSession"):
        super().__init__(timeout=900)
        self.session = session

    @discord.ui.button(label="参加する", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.session.join(interaction)

    @discord.ui.button(label="退出する", style=discord.ButtonStyle.secondary)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.session.leave(interaction)

    @discord.ui.button(label="ゲーム開始", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.session.start(interaction)

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.session.cancel(interaction)

    async def on_timeout(self):
        await self.session.expire_lobby()


class NightTargetSelect(discord.ui.Select):
    def __init__(self, session: "WerewolfSession", actor_id: int, role: Role):
        self.session = session
        self.actor_id = actor_id
        self.role = role
        actor = session.game.players[actor_id]
        options = []
        for player in session.game.alive_players():
            if player.user_id == actor_id:
                continue
            if role == Role.WEREWOLF and player.role == Role.WEREWOLF:
                continue
            options.append(discord.SelectOption(label=player.display_name, value=str(player.user_id)))
        super().__init__(placeholder="対象を選択してください", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.actor_id:
            await interaction.response.send_message("この操作はあなた用ではありません。")
            return
        accepted, result = self.session.game.choose_night_target(
            self.actor_id, int(self.values[0])
        )
        if not accepted:
            await interaction.response.send_message("すでに選択済みか、選択できない対象です。")
            return
        self.disabled = True
        target = self.session.game.players[int(self.values[0])]
        message = f"{target.display_name} さんを選択しました。"
        if result is not None:
            message += f"\n占い結果: **{target.display_name} さんは「{result}」**。"
        await interaction.response.edit_message(content=message, view=self.view)
        self.view.stop()
        self.session.night_action_changed()


class NightTargetView(discord.ui.View):
    def __init__(self, session: "WerewolfSession", actor_id: int, role: Role):
        super().__init__(timeout=session.night_time)
        self.add_item(NightTargetSelect(session, actor_id, role))


class VoteSelect(discord.ui.Select):
    def __init__(self, session: "WerewolfSession", voter_id: int):
        self.session = session
        self.voter_id = voter_id
        options = [
            discord.SelectOption(label=player.display_name, value=str(player.user_id))
            for player in session.game.alive_players()
            if player.user_id != voter_id
        ]
        super().__init__(placeholder="追放するプレイヤーを選択してください", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.voter_id:
            await interaction.response.send_message("この投票はあなた用ではありません。")
            return
        target_id = int(self.values[0])
        if not self.session.game.cast_vote(self.voter_id, target_id):
            await interaction.response.send_message("すでに投票済みか、投票できない対象です。")
            return
        self.disabled = True
        target = self.session.game.players[target_id]
        await interaction.response.edit_message(
            content=f"{target.display_name} さんに投票しました。", view=self.view
        )
        self.view.stop()
        self.session.vote_changed()


class VoteView(discord.ui.View):
    def __init__(self, session: "WerewolfSession", voter_id: int):
        super().__init__(timeout=session.vote_time)
        self.add_item(VoteSelect(session, voter_id))
