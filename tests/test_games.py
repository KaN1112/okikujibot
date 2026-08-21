import unittest

from cogs.dice import roll_dice
from games.werewolf.game import GamePhase, WerewolfGame
from games.werewolf.roles import ROLE_COMPOSITIONS, Role, roles_for_player_count


class DiceTests(unittest.TestCase):
    def test_roll_bounds_and_count(self):
        rolls = roll_dice(6, 20)
        self.assertEqual(len(rolls), 20)
        self.assertTrue(all(1 <= roll <= 6 for roll in rolls))


class RoleTests(unittest.TestCase):
    def test_all_compositions_match_player_count(self):
        for count, composition in ROLE_COMPOSITIONS.items():
            self.assertEqual(sum(composition.values()), count)
            self.assertEqual(len(roles_for_player_count(count)), count)


class WerewolfGameTests(unittest.TestCase):
    def make_game(self):
        game = WerewolfGame(1, 2, 1)
        for user_id in range(1, 6):
            game.add_player(user_id, f"User{user_id}")
        game.players[1].role = Role.WEREWOLF
        game.players[2].role = Role.SEER
        game.players[3].role = Role.KNIGHT
        game.players[4].role = Role.VILLAGER
        game.players[5].role = Role.VILLAGER
        return game

    def test_duplicate_join_is_rejected(self):
        game = WerewolfGame(1, 2, 1)
        self.assertTrue(game.add_player(1, "one"))
        self.assertFalse(game.add_player(1, "one"))

    def test_guard_prevents_attack(self):
        game = self.make_game()
        game.begin_night()
        self.assertTrue(game.choose_night_target(1, 4)[0])
        self.assertTrue(game.choose_night_target(3, 4)[0])
        self.assertIsNone(game.resolve_night())
        self.assertTrue(game.players[4].alive)

    def test_seer_result_and_duplicate_action(self):
        game = self.make_game()
        game.begin_night()
        self.assertEqual(game.choose_night_target(2, 1), (True, "人狼"))
        self.assertEqual(game.choose_night_target(2, 4), (False, None))

    def test_tied_vote_executes_nobody(self):
        game = self.make_game()
        game.phase = GamePhase.VOTING
        game.cast_vote(1, 2)
        game.cast_vote(2, 1)
        self.assertEqual(game.resolve_vote(), (None, True))

    def test_winner_conditions(self):
        game = self.make_game()
        game.players[1].alive = False
        self.assertEqual(game.winner(), "villagers")
        game = self.make_game()
        game.players[2].alive = False
        game.players[3].alive = False
        game.players[4].alive = False
        self.assertEqual(game.winner(), "werewolves")


if __name__ == "__main__":
    unittest.main()
