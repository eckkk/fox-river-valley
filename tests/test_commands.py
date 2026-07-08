import json
import unittest

from fox_river_valley import cmd, new_game


def parse_state(output: str) -> dict:
    lines = output.strip().splitlines()
    state_lines = [line for line in lines if line.startswith("STATE ")]
    assert len(state_lines) == 1, output
    assert lines[-1].startswith("STATE "), output
    return json.loads(lines[-1][6:])


class CommandContractTests(unittest.TestCase):
    def test_new_game_returns_state_line(self):
        output = new_game("12071008")
        state = parse_state(output)
        self.assertEqual(state["day"], 1)
        self.assertEqual(state["time"], "morning")
        self.assertEqual(state["pos"], [12, 12])
        self.assertEqual(state["known_tiles"], 1)
        self.assertFalse(state["shelter"])

    def test_unknown_command_returns_state_without_time_change(self):
        new_game("12071008")
        before = parse_state(cmd("status"))
        output = cmd("dance")
        after = parse_state(output)
        self.assertIn("听不懂", output)
        self.assertEqual(after["time"], before["time"])
        self.assertEqual(after["pos"], before["pos"])
        self.assertEqual(after["inventory"], before["inventory"])


class MinimalLoopTests(unittest.TestCase):
    def test_minimal_loop_changes_state(self):
        new_game("12071008")
        self.assertIn("河谷", cmd("look"))
        self.assertIn("@", cmd("map"))
        moved = parse_state(cmd("move north"))
        self.assertEqual(moved["pos"], [12, 11])
        gathered = parse_state(cmd("gather"))
        self.assertGreaterEqual(gathered["inventory"].get("wood", 0), 1)
        crafted = parse_state(cmd("craft stick"))
        self.assertGreaterEqual(crafted["inventory"].get("stick", 0), 1)
        built_output = cmd("build campfire")
        built = parse_state(built_output)
        self.assertTrue(built["campfire"])
        journal = cmd("journal")
        self.assertIn("campfire", journal)
        parse_state(journal)

    def test_goal_is_recorded_without_task_system(self):
        new_game("12071008")
        state = parse_state(cmd("goal build riverside_bench for Yaya"))
        self.assertEqual(state["goal"], "build riverside_bench for Yaya")
        self.assertIn("riverside_bench", cmd("journal"))
