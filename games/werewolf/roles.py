from enum import Enum


class Role(str, Enum):
    VILLAGER = "市民"
    WEREWOLF = "人狼"
    SEER = "占い師"
    KNIGHT = "騎士"


ROLE_EMOJI = {
    Role.VILLAGER: "👤",
    Role.WEREWOLF: "🐺",
    Role.SEER: "🔮",
    Role.KNIGHT: "🛡️",
}

ROLE_DESCRIPTION = {
    Role.VILLAGER: "能力はありません。議論と投票で人狼を見つけてください。",
    Role.WEREWOLF: "毎晩、生存者を1名襲撃できます。",
    Role.SEER: "毎晩、生存者を1名占うことができます。",
    Role.KNIGHT: "毎晩、自分以外の生存者を1名護衛できます。",
}

# プレイヤー数ごとの構成。値の合計は必ずキーと一致させます。
ROLE_COMPOSITIONS = {
    4: {Role.WEREWOLF: 1, Role.SEER: 1, Role.VILLAGER: 2},
    5: {Role.WEREWOLF: 1, Role.SEER: 1, Role.KNIGHT: 1, Role.VILLAGER: 2},
    6: {Role.WEREWOLF: 1, Role.SEER: 1, Role.KNIGHT: 1, Role.VILLAGER: 3},
    7: {Role.WEREWOLF: 2, Role.SEER: 1, Role.KNIGHT: 1, Role.VILLAGER: 3},
    8: {Role.WEREWOLF: 2, Role.SEER: 1, Role.KNIGHT: 1, Role.VILLAGER: 4},
    9: {Role.WEREWOLF: 2, Role.SEER: 1, Role.KNIGHT: 1, Role.VILLAGER: 5},
    10: {Role.WEREWOLF: 2, Role.SEER: 1, Role.KNIGHT: 1, Role.VILLAGER: 6},
    11: {Role.WEREWOLF: 3, Role.SEER: 1, Role.KNIGHT: 1, Role.VILLAGER: 6},
    12: {Role.WEREWOLF: 3, Role.SEER: 1, Role.KNIGHT: 1, Role.VILLAGER: 7},
}


def roles_for_player_count(count: int) -> list[Role]:
    composition = ROLE_COMPOSITIONS[count]
    return [role for role, amount in composition.items() for _ in range(amount)]
