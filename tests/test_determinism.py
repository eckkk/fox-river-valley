import unittest

from fox_river_valley import cmd, new_game
from tests.test_commands import parse_state


class DeterminismTests(unittest.TestCase):
    def test_same_seed_and_commands_reproduce_key_state(self):
        new_game("12071008")
        cmd("move north")
        cmd("gather")
        final_a = parse_state(cmd("craft stick"))

        new_game("12071008")
        cmd("move north")
        cmd("gather")
        final_b = parse_state(cmd("craft stick"))

        self.assertEqual(final_a["pos"], final_b["pos"])
        self.assertEqual(final_a["inventory"], final_b["inventory"])
        self.assertEqual(final_a["time"], final_b["time"])
