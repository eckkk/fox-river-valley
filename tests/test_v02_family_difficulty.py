import json
import unittest
from pathlib import Path

from fox_river_valley import cmd, new_game
from tests.test_commands import parse_state


class V02FamilyDifficultyTests(unittest.TestCase):
    def add_inventory(self, items: dict[str, int]) -> None:
        cmd("save")
        path = Path("saves/fox_river_valley.save.json")
        saved = json.loads(path.read_text(encoding="utf-8"))
        saved["inventory"].update(items)
        path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")

    def test_inventory_returns_single_state_and_no_time_advance(self):
        new_game("12071008")
        before = parse_state(cmd("status"))
        output = cmd("inventory")
        after = parse_state(output)
        self.assertIn("背包", output)
        self.assertEqual(after["time"], before["time"])
        self.assertEqual(after["day"], before["day"])
        self.assertEqual(output.strip().splitlines()[-1][:6], "STATE ")

    def test_tools_consume_resources_and_improve_actions(self):
        new_game("12071008")
        cmd("move north")
        gathered = parse_state(cmd("gather"))
        baseline_before_wood = gathered["inventory"].get("wood", 0)
        baseline_chop = parse_state(cmd("chop"))
        baseline_delta = baseline_chop["inventory"].get("wood", 0) - baseline_before_wood

        new_game("12071008")
        cmd("move north")
        cmd("gather")
        self.add_inventory({"wood": 4, "fiber": 1, "plank": 2, "stick": 2})
        cmd("build simple_shelter")
        cmd("build workbench")
        self.add_inventory({"stick": 1, "stone": 2, "cord": 1})
        axe_state = parse_state(cmd("craft stone_axe"))
        self.assertEqual(axe_state["inventory"].get("stone_axe"), 1)
        axe_before_wood = axe_state["inventory"].get("wood", 0)
        axe_chop = parse_state(cmd("chop"))
        axe_delta = axe_chop["inventory"].get("wood", 0) - axe_before_wood
        self.assertGreater(axe_delta, baseline_delta)

        self.add_inventory({"stick": 2, "stone": 3, "cord": 1})
        pick_state = parse_state(cmd("craft stone_pickaxe"))
        self.assertEqual(pick_state["inventory"].get("stone_pickaxe"), 1)
        mined = parse_state(cmd("mine"))
        self.assertGreaterEqual(mined["inventory"].get("iron_ore", 0), 1)

        self.add_inventory({"stick": 2, "cord": 2})
        rod_state = parse_state(cmd("craft fishing_rod"))
        self.assertEqual(rod_state["inventory"].get("fishing_rod"), 1)
        cmd("move south")
        rod_fish = parse_state(cmd("fish"))
        fish_species = {"fish", "silver_fish", "rain_carp", "dusk_eel", "river_crab"}
        fish_total = sum(rod_fish["inventory"].get(item, 0) for item in fish_species)
        self.assertGreaterEqual(fish_total, 2)
        self.assertLessEqual(fish_total, 2)

    def test_cozy_builds_persist_in_builds_here_and_journal(self):
        new_game("12071008", companion_name="Yaya")
        cmd("move north")
        cmd("gather")
        cmd("chop")
        cmd("chop")
        cmd("chop")
        cmd("build simple_shelter")
        self.add_inventory({"plank": 6, "stick": 4})
        cmd("build storage_box")
        cmd("build workbench")
        table = parse_state(cmd("build window_table"))
        self.assertIn("storage_box", table["builds_here"])
        self.assertIn("window_table", table["builds_here"])
        cmd("move south")
        self.add_inventory({"plank": 2, "stick": 1})
        bench = parse_state(cmd("build riverside_bench"))
        self.assertIn("riverside_bench", bench["builds_here"])
        journal = cmd("journal")
        self.assertIn("riverside_bench", journal)
        self.assertIn("窗边书桌", journal)
        self.assertIn("Yaya", journal)

    def test_difficulty_is_saved_loaded_and_changes_resource_behavior(self):
        normal_output = new_game("12071008", difficulty="normal")
        normal_state = parse_state(normal_output)
        self.assertEqual(normal_state["difficulty"], "normal")
        cmd("move north")
        cmd("gather")
        normal_chop = parse_state(cmd("chop"))

        hard_output = new_game("12071008", difficulty="hard")
        hard_state = parse_state(hard_output)
        self.assertEqual(hard_state["difficulty"], "hard")
        cmd("move north")
        cmd("gather")
        hard_chop = parse_state(cmd("chop"))
        self.assertLessEqual(
            hard_chop["inventory"].get("wood", 0),
            normal_chop["inventory"].get("wood", 0),
        )
        self.assertLessEqual(hard_chop["energy"], normal_chop["energy"])
        cmd("save")
        raw = json.loads(Path("saves/fox_river_valley.save.json").read_text(encoding="utf-8"))
        self.assertEqual(raw["difficulty"], "hard")
        new_game("other", difficulty="casual")
        loaded = parse_state(cmd("load"))
        self.assertEqual(loaded["difficulty"], "hard")

    def test_difficulty_changes_sleep_hunger_decay(self):
        new_game("12071008", difficulty="normal")
        cmd("move north")
        cmd("gather")
        cmd("chop")
        cmd("chop")
        cmd("build simple_shelter")
        normal_woke = parse_state(cmd("sleep"))

        new_game("12071008", difficulty="hard")
        cmd("move north")
        cmd("gather")
        cmd("chop")
        cmd("chop")
        cmd("build simple_shelter")
        hard_woke = parse_state(cmd("sleep"))

        self.assertLess(hard_woke["hunger"], normal_woke["hunger"])

    def test_invalid_difficulty_fails_safely(self):
        with self.assertRaises(ValueError):
            new_game("12071008", difficulty="nightmare")
        fresh = parse_state(new_game("12071008"))
        self.assertEqual(fresh["difficulty"], "normal")

    def test_family_mode_creates_companion_state(self):
        output = new_game("12071008", companion_name="Yaya")
        state = parse_state(output)
        self.assertEqual(state["mode"], "family")
        self.assertEqual(state["companion"]["name"], "Yaya")
        self.assertEqual(state["companion"]["location"], "with_player")
        self.assertIn("你不是一个人醒来的", cmd("journal"))

    def test_share_food_changes_companion_and_inventory(self):
        new_game("12071008", companion_name="Yaya")
        fish_state = parse_state(cmd("fish"))
        shared = parse_state(cmd("share fish"))
        self.assertLess(shared["inventory"].get("fish", 0), fish_state["inventory"].get("fish", 0))
        self.assertGreater(shared["companion"]["hunger"], fish_state["companion"]["hunger"])
        self.assertIn("第一次分享食物", cmd("journal"))

        cmd("gather")
        berries_before = parse_state(cmd("inventory"))
        shared_berries = parse_state(cmd("share berries"))
        self.assertLessEqual(
            shared_berries["inventory"].get("berries", 0),
            berries_before["inventory"].get("berries", 0),
        )

    def test_talk_companion_changes_mood_or_trust(self):
        new_game("12071008", companion_name="Yaya")
        before = parse_state(cmd("check companion"))
        after = parse_state(cmd("talk companion"))
        self.assertGreaterEqual(after["companion"]["mood"], before["companion"]["mood"])
        self.assertGreaterEqual(after["companion"]["trust"], before["companion"]["trust"])

    def test_window_table_affects_companion_and_journal(self):
        new_game("12071008", companion_name="Yaya")
        cmd("move north")
        cmd("gather")
        cmd("chop")
        cmd("chop")
        cmd("build simple_shelter")
        self.add_inventory({"plank": 4, "stick": 4})
        cmd("build workbench")
        before = parse_state(cmd("check companion"))
        after = parse_state(cmd("build window_table"))
        self.assertGreaterEqual(after["companion"]["mood"], before["companion"]["mood"])
        self.assertGreaterEqual(after["companion"]["trust"], before["companion"]["trust"])
        journal = cmd("journal")
        self.assertIn("window_table", journal)
        self.assertIn("Yaya", journal)

    def test_regular_actions_do_not_start_next_day_before_sleep(self):
        new_game("12071008", companion_name="Yaya")
        cmd("fish")
        cmd("share fish")
        cmd("move north")
        cmd("gather")
        cmd("chop")
        self.add_inventory({"stick": 1, "stone": 2, "cord": 1})
        self.add_inventory({"wood": 4, "fiber": 1, "plank": 2, "stick": 2})
        cmd("build simple_shelter")
        cmd("build workbench")
        cmd("craft stone_axe")
        cmd("chop")
        self.add_inventory({"plank": 2, "stick": 2})
        table = parse_state(cmd("build window_table"))
        self.assertEqual(table["day"], 1)
        self.assertEqual(table["time"], "night")
        woke = parse_state(cmd("sleep"))
        self.assertEqual(woke["day"], 2)
        self.assertEqual(woke["time"], "morning")
        self.assertIn("Yaya", cmd("journal"))

    def test_save_load_preserves_v02_state(self):
        new_game("12071008", difficulty="casual", companion_name="Yaya")
        cmd("fish")
        cmd("share fish")
        cmd("move north")
        cmd("gather")
        self.add_inventory({"wood": 4, "fiber": 1, "plank": 2, "stick": 2})
        cmd("build simple_shelter")
        cmd("build workbench")
        self.add_inventory({"stick": 1, "stone": 2, "cord": 1})
        cmd("craft stone_axe")
        cmd("chop")
        self.add_inventory({"plank": 2, "stick": 2})
        cmd("build window_table")
        before = parse_state(cmd("save"))
        new_game("other", difficulty="hard")
        after = parse_state(cmd("load"))
        self.assertEqual(after["difficulty"], "casual")
        self.assertEqual(after["mode"], "family")
        self.assertEqual(after["companion"]["name"], "Yaya")
        self.assertEqual(after["inventory"], before["inventory"])
        self.assertIn("window_table", after["builds_here"])

    def test_same_seed_difficulty_and_commands_are_deterministic(self):
        def run_sequence():
            new_game("12071008", difficulty="normal", companion_name="Yaya")
            cmd("fish")
            cmd("share fish")
            cmd("move north")
            cmd("gather")
            self.add_inventory({"wood": 4, "fiber": 1, "plank": 2, "stick": 2})
            cmd("build simple_shelter")
            cmd("build workbench")
            self.add_inventory({"stick": 1, "stone": 2, "cord": 1})
            cmd("craft stone_axe")
            cmd("chop")
            self.add_inventory({"plank": 2, "stick": 2})
            cmd("build window_table")
            return parse_state(cmd("talk companion"))

        first = run_sequence()
        second = run_sequence()
        self.assertEqual(first["inventory"], second["inventory"])
        self.assertEqual(first["companion"], second["companion"])
        self.assertEqual(first["difficulty"], second["difficulty"])
