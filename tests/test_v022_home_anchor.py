import unittest

from fox_river_valley import cmd, new_game
from tests.test_commands import parse_state


class V022HomeAnchorTests(unittest.TestCase):
    def build_home(self):
        new_game("12071008", companion_name="Yaya")
        cmd("move north")
        cmd("gather")
        cmd("chop")
        cmd("chop")
        return parse_state(cmd("build simple_shelter"))

    def test_build_shelter_sets_base_pos(self):
        state = self.build_home()
        self.assertEqual(state["base_pos"], state["pos"])
        self.assertEqual(state["shelter_pos"], state["pos"])
        self.assertIn("第一个家", cmd("journal"))

    def test_sleep_requires_being_at_base(self):
        self.build_home()
        moved = parse_state(cmd("move south"))
        output = cmd("sleep")
        after = parse_state(output)
        self.assertIn("家在别处。你得先回到 shelter 才能安心睡下。", output)
        self.assertEqual(after["day"], moved["day"])
        self.assertEqual(after["time"], moved["time"])
        self.assertEqual(after["pos"], moved["pos"])

    def test_return_home_moves_to_base(self):
        home = self.build_home()
        cmd("move south")
        returned = parse_state(cmd("return home"))
        self.assertEqual(returned["pos"], home["base_pos"])
        self.assertIn("base_pos", returned)

    def test_return_home_without_shelter_fails(self):
        new_game("12071008")
        before = parse_state(cmd("status"))
        output = cmd("return home")
        after = parse_state(output)
        self.assertIn("还没有家", output)
        self.assertEqual(after["day"], before["day"])
        self.assertEqual(after["time"], before["time"])
        self.assertEqual(after["pos"], before["pos"])

    def test_window_table_requires_base_tile(self):
        self.build_home()
        cmd("move south")
        before = parse_state(cmd("status"))
        output = cmd("build window_table")
        after = parse_state(output)
        self.assertIn("得先回到 shelter", output)
        self.assertNotIn("window_table", after["builds_here"])
        self.assertEqual(after["time"], before["time"])
        returned = parse_state(cmd("return home"))
        self.assertEqual(returned["pos"], returned["base_pos"])
        cmd("craft plank")
        cmd("craft stick")
        cmd("build workbench")
        cmd("craft plank")
        cmd("craft stick")
        built = parse_state(cmd("build window_table"))
        self.assertIn("window_table", built["builds_here"])

    def test_storage_box_requires_base_tile(self):
        self.build_home()
        cmd("move south")
        before = parse_state(cmd("status"))
        output = cmd("build storage_box")
        after = parse_state(output)
        self.assertIn("得先回到 shelter", output)
        self.assertNotIn("storage_box", after["builds_here"])
        self.assertEqual(after["inventory"], before["inventory"])
        self.assertEqual(after["time"], before["time"])

    def test_save_load_preserves_base_pos(self):
        state = self.build_home()
        cmd("save")
        new_game("other")
        loaded = parse_state(cmd("load"))
        self.assertEqual(loaded["base_pos"], state["base_pos"])
        self.assertEqual(loaded["shelter_pos"], state["shelter_pos"])

    def test_state_includes_base_pos(self):
        new_state = parse_state(new_game("12071008"))
        self.assertIn("base_pos", new_state)
        self.assertIn("shelter_pos", new_state)
        self.assertIsNone(new_state["base_pos"])
        self.assertIsNone(new_state["shelter_pos"])
        home = self.build_home()
        self.assertEqual(home["base_pos"], [12, 11])
        self.assertEqual(home["shelter_pos"], [12, 11])


if __name__ == "__main__":
    unittest.main()
