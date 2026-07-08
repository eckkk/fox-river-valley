import json
import unittest
from pathlib import Path

from fox_river_valley import cmd, new_game
from tests.test_commands import parse_state


class SaveLoadTests(unittest.TestCase):
    def test_save_and_load_restore_minimal_loop_state(self):
        new_game("12071008")
        cmd("move north")
        cmd("gather")
        cmd("craft stick")
        built = parse_state(cmd("build campfire"))
        save_output = cmd("save")
        self.assertIn("已保存", save_output)
        save_path = Path("saves/fox_river_valley.save.json")
        self.assertTrue(save_path.exists())
        raw = json.loads(save_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["seed"], "12071008")
        new_game("other")
        loaded = parse_state(cmd("load"))
        self.assertEqual(loaded["pos"], built["pos"])
        self.assertEqual(loaded["inventory"], built["inventory"])
        self.assertTrue(loaded["campfire"])
