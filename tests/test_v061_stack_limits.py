import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


class V061StackLimitTests(unittest.TestCase):
    def add_inventory(self, items: dict[str, int]) -> None:
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        saved["inventory"].update(items)
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")

    def set_storage(self, items: dict[str, int]) -> None:
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        saved["storage"] = dict(items)
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")

    def saved_state(self) -> dict:
        cmd("save")
        return json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))

    def build_storage_base(self) -> None:
        new_game("12071008", difficulty="normal", companion_name="Yaya")
        cmd("move north")
        self.add_inventory({"wood": 4, "fiber": 1, "plank": 2})
        cmd("build simple_shelter")
        cmd("build storage_box")

    def test_inventory_item_stack_cap_999(self):
        new_game("12071008", difficulty="normal")
        cmd("move north")
        self.add_inventory({"wood": 998})

        output = cmd("chop")
        state = parse_state(output)

        self.assertEqual(state["inventory"].get("wood"), 999)
        self.assertIn("某些物品已经接近叠加上限", output)

    def test_storage_item_stack_cap_999(self):
        self.build_storage_base()
        self.set_storage({"wood": 998})
        self.add_inventory({"wood": 1})

        state = parse_state(cmd("deposit wood 1"))

        self.assertNotIn("wood", state["inventory"])
        self.assertIn("wood x999", cmd("storage"))

    def test_craft_fails_if_output_would_exceed_stack(self):
        new_game("12071008", difficulty="normal")
        self.add_inventory({"branch": 1, "stick": 998})
        before = parse_state(cmd("status"))

        output = cmd("craft stick")
        after = parse_state(output)

        self.assertIn("叠加上限", output)
        self.assertEqual(after["inventory"].get("branch"), 1)
        self.assertEqual(after["inventory"].get("stick"), 998)
        self.assertEqual(after["time"], before["time"])

    def test_deposit_fails_if_storage_stack_full(self):
        self.build_storage_base()
        self.set_storage({"wood": 999})
        self.add_inventory({"wood": 1})
        before = parse_state(cmd("status"))

        output = cmd("deposit wood 1")
        after = parse_state(output)

        self.assertIn("叠加上限", output)
        self.assertEqual(after["inventory"].get("wood"), 1)
        self.assertEqual(after["time"], before["time"])
        self.assertIn("wood x999", cmd("storage"))

    def test_withdraw_fails_if_inventory_stack_full(self):
        self.build_storage_base()
        self.set_storage({"stone": 1})
        self.add_inventory({"stone": 999})
        before = parse_state(cmd("status"))

        output = cmd("withdraw stone 1")
        after = parse_state(output)

        self.assertIn("叠加上限", output)
        self.assertEqual(after["inventory"].get("stone"), 999)
        self.assertEqual(after["time"], before["time"])
        self.assertIn("stone x1", cmd("storage"))

    def test_gather_clamps_to_stack_limit(self):
        new_game("12071008", difficulty="normal")
        cmd("move north")
        self.add_inventory({"wood": 998, "branch": 999})

        output = cmd("gather")
        state = parse_state(output)

        self.assertEqual(state["inventory"].get("wood"), 999)
        self.assertEqual(state["inventory"].get("branch"), 999)
        self.assertIn("某些物品已经接近叠加上限", output)
        self.assertEqual(state["time"], "midday")

    def test_load_clamps_legacy_overstack(self):
        new_game("12071008", difficulty="normal")
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        saved["inventory"] = {"wood": 1200}
        saved["storage"] = {"stone": 1001}
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")

        loaded = parse_state(cmd("load"))
        cmd("save")
        raw = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))

        self.assertEqual(loaded["inventory"].get("wood"), 999)
        self.assertEqual(raw["storage"].get("stone"), 999)

    def test_failed_stack_overflow_does_not_mutate(self):
        new_game("12071008", difficulty="normal")
        self.add_inventory({"wood": 2, "plank": 998})
        before = parse_state(cmd("status"))

        output = cmd("craft plank")
        after = parse_state(output)

        self.assertIn("叠加上限", output)
        self.assertEqual(after["inventory"], before["inventory"])
        self.assertEqual(after["time"], before["time"])

    def test_save_load_preserves_stack_limit(self):
        self.build_storage_base()
        self.add_inventory({"wood": 999})
        self.set_storage({"branch": 999})
        before = self.saved_state()
        new_game("other")

        loaded = parse_state(cmd("load"))
        after = self.saved_state()

        self.assertEqual(loaded["inventory"].get("wood"), 999)
        self.assertEqual(after["storage"].get("branch"), 999)
        self.assertEqual(before["storage"], after["storage"])


if __name__ == "__main__":
    unittest.main()
