import unittest

from fox_river_valley import cmd, new_game
from tests.test_commands import parse_state


class AlphaDayLoopTests(unittest.TestCase):
    def test_player_can_complete_one_playable_day(self):
        new_game("12071008")
        fish_state = parse_state(cmd("fish"))
        self.assertGreaterEqual(fish_state["inventory"].get("fish", 0), 1)

        eat_state = parse_state(cmd("eat fish"))
        self.assertEqual(eat_state["inventory"].get("fish", 0), 0)
        self.assertGreater(eat_state["hunger"], fish_state["hunger"])

        moved = parse_state(cmd("move north"))
        self.assertEqual(moved["terrain"], "forest")

        gathered = parse_state(cmd("gather"))
        self.assertGreaterEqual(gathered["inventory"].get("fiber", 0), 1)

        chopped = parse_state(cmd("chop"))
        self.assertGreater(chopped["inventory"].get("wood", 0), gathered["inventory"].get("wood", 0))

        mined = parse_state(cmd("mine"))
        self.assertGreater(mined["inventory"].get("stone", 0), chopped["inventory"].get("stone", 0))

        rested = parse_state(cmd("rest"))
        self.assertGreaterEqual(rested["energy"], mined["energy"])

        shelter_output = cmd("build simple_shelter")
        shelter = parse_state(shelter_output)
        self.assertTrue(shelter["shelter"])

        sleep_output = cmd("sleep")
        woke = parse_state(sleep_output)
        self.assertIn("醒来", sleep_output)
        self.assertEqual(woke["day"], 2)
        self.assertEqual(woke["time"], "morning")
        self.assertTrue(woke["shelter"])

        journal = cmd("journal")
        self.assertIn("第一条鱼", journal)
        self.assertIn("simple_shelter", journal)
        self.assertIn("醒来", journal)

    def test_sleep_without_shelter_fails_without_advancing_time(self):
        new_game("12071008")
        before = parse_state(cmd("status"))
        output = cmd("sleep")
        after = parse_state(output)
        self.assertIn("庇护所", output)
        self.assertEqual(after["day"], before["day"])
        self.assertEqual(after["time"], before["time"])
