from __future__ import annotations

import secrets
from collections import Counter
from dataclasses import dataclass
from enum import Enum

from .roles import Role, roles_for_player_count


class GamePhase(str, Enum):
    LOBBY = "lobby"
    NIGHT = "night"
    DISCUSSION = "discussion"
    VOTING = "voting"
    ENDED = "ended"


@dataclass
class Player:
    user_id: int
    display_name: str
    role: Role | None = None
    alive: bool = True


class WerewolfGame:
    def __init__(self, guild_id: int, channel_id: int, host_id: int):
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.host_id = host_id
        self.phase = GamePhase.LOBBY
        self.day = 0
        self.players: dict[int, Player] = {}
        self.wolf_votes: dict[int, int] = {}
        self.seer_targets: dict[int, int] = {}
        self.guard_targets: dict[int, int] = {}
        self.votes: dict[int, int] = {}

    @property
    def key(self) -> tuple[int, int]:
        return self.guild_id, self.channel_id

    def add_player(self, user_id: int, display_name: str) -> bool:
        if self.phase != GamePhase.LOBBY or user_id in self.players or len(self.players) >= 12:
            return False
        self.players[user_id] = Player(user_id, display_name)
        return True

    def remove_player(self, user_id: int) -> bool:
        if self.phase != GamePhase.LOBBY or user_id not in self.players:
            return False
        del self.players[user_id]
        return True

    def assign_roles(self) -> None:
        roles = roles_for_player_count(len(self.players))
        secrets.SystemRandom().shuffle(roles)
        for player, role in zip(self.players.values(), roles):
            player.role = role

    def alive_players(self) -> list[Player]:
        return [player for player in self.players.values() if player.alive]

    def players_with_role(self, role: Role, *, alive_only: bool = True) -> list[Player]:
        players = self.alive_players() if alive_only else list(self.players.values())
        return [player for player in players if player.role == role]

    def begin_night(self) -> None:
        self.day += 1
        self.phase = GamePhase.NIGHT
        self.wolf_votes.clear()
        self.seer_targets.clear()
        self.guard_targets.clear()

    def choose_night_target(self, actor_id: int, target_id: int) -> tuple[bool, str | None]:
        actor, target = self.players.get(actor_id), self.players.get(target_id)
        if self.phase != GamePhase.NIGHT or not actor or not target or not actor.alive or not target.alive:
            return False, None
        if actor.role == Role.WEREWOLF:
            if target.role == Role.WEREWOLF or actor_id in self.wolf_votes:
                return False, None
            self.wolf_votes[actor_id] = target_id
            return True, None
        if actor.role == Role.SEER:
            if actor_id == target_id or actor_id in self.seer_targets:
                return False, None
            self.seer_targets[actor_id] = target_id
            result = "人狼" if target.role == Role.WEREWOLF else "人狼ではありません"
            return True, result
        if actor.role == Role.KNIGHT:
            if actor_id == target_id or actor_id in self.guard_targets:
                return False, None
            self.guard_targets[actor_id] = target_id
            return True, None
        return False, None

    def resolve_night(self) -> int | None:
        if not self.wolf_votes:
            return None
        counts = Counter(self.wolf_votes.values())
        top = max(counts.values())
        candidates = [target for target, votes in counts.items() if votes == top]
        victim_id = secrets.choice(candidates)
        if victim_id in self.guard_targets.values():
            return None
        self.players[victim_id].alive = False
        return victim_id

    def cast_vote(self, voter_id: int, target_id: int) -> bool:
        voter, target = self.players.get(voter_id), self.players.get(target_id)
        if (
            self.phase != GamePhase.VOTING
            or not voter
            or not target
            or not voter.alive
            or not target.alive
            or voter_id == target_id
            or voter_id in self.votes
        ):
            return False
        self.votes[voter_id] = target_id
        return True

    def resolve_vote(self) -> tuple[int | None, bool]:
        if not self.votes:
            return None, False
        counts = Counter(self.votes.values())
        top = max(counts.values())
        candidates = [target for target, votes in counts.items() if votes == top]
        if len(candidates) != 1:
            return None, True
        executed = candidates[0]
        self.players[executed].alive = False
        return executed, False

    def winner(self) -> str | None:
        alive_wolves = len(self.players_with_role(Role.WEREWOLF))
        alive_others = len(self.alive_players()) - alive_wolves
        if alive_wolves == 0:
            return "villagers"
        if alive_wolves >= alive_others:
            return "werewolves"
        return None
