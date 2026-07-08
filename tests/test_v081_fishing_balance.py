import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


FISH_SPECIES = {"fish", "silver_fish", "rain_carp", "dusk_eel", "river_crab"}
FINDING_ITEMS = {"drift_bottle", "old_boot", "map_fragment", "old_coin", "cracked_tile", "small_charm"}


def body_lines(output: str) -> str:
    return "\n".join(line for line in output.splitlines() if not line.startswith("STATE "))


class V081FishingBalanceTests(unittest.TestCase):
    def mutate_save(self, updates: dict) -> None:
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(saved.get(key), dict):
                saved[key].update(value)
            else:
                saved[key] = value
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")

    def fish_total(self, state: dict) -> int:
        return sum(state["inventory"].get(item, 0) for item in FISH_SPECIES)

    def catch_total(self, state: dict) -> int:
        return sum(state["inventory"].get(item, 0) for item in FISH_SPECIES | {"drift_bottle", "old_boot"})

    def test_fish_command_returns_limited_catch(self):
        new_game("12071008", companion_name="Yaya")

        state = parse_state(cmd("fish"))

        self.assertEqual(self.fish_total(state), 1)
        self.assertLessEqual(self.catch_total(state), 2)

    def test_fishing_rod_can_bonus_but_not_overloot(self):
        saw_bonus = False
        for index in range(80):
            new_game(f"rod-balance-{index}", companion_name="Yaya")
            self.mutate_save({"inventory": {"fishing_rod": 1}})

            state = parse_state(cmd("fish"))
            fish_total = self.fish_total(state)

            self.assertLessEqual(fish_total, 2)
            self.assertLessEqual(self.catch_total(state), 3)
            if fish_total == 2:
                saw_bonus = True

        self.assertTrue(saw_bonus, "expected at least one seeded fishing_rod bonus catch")

    def test_fish_log_excludes_non_fish_items(self):
        new_game("12071008", companion_name="Yaya")
        self.mutate_save({"fish_log": {"fish": 1, "old_boot": 1, "drift_bottle": 1}})

        output = cmd("fish log")

        self.assertIn("fish log", output)
        self.assertIn("fish x1", output)
        self.assertNotIn("old_boot", output)
        self.assertNotIn("drift_bottle", output)

    def test_findings_records_bottle_boot_fragments(self):
        saw_bottle = False
        saw_boot = False
        for index in range(120):
            new_game(f"finding-seed-{index}", companion_name="Yaya")
            state = parse_state(cmd("fish"))
            output = body_lines(cmd("findings"))
            self.assertIn("findings", output)
            if state["inventory"].get("drift_bottle", 0):
                self.assertIn("drift_bottle", output)
                saw_bottle = True
            if state["inventory"].get("old_boot", 0):
                self.assertIn("old_boot", output)
                saw_boot = True
            if saw_bottle and saw_boot:
                break

        self.assertTrue(saw_bottle, "expected at least one seeded drift_bottle finding")
        self.assertTrue(saw_boot, "expected at least one seeded old_boot finding")

        new_game("12071008", companion_name="Yaya")
        self.mutate_save({"inventory": {"map_fragment": 2}})
        cmd("move north")
        cmd("move west")
        cmd("move west")
        cmd("explore ruins")

        findings = body_lines(cmd("findings"))

        self.assertIn("map_fragment", findings)

    def test_rain_fishing_bonus_still_deterministic(self):
        def run() -> dict:
            new_game("seed-1", companion_name="Yaya")
            return parse_state(cmd("fish"))

        first = run()
        second = run()

        self.assertEqual(first["weather"], "rain")
        self.assertEqual(first["inventory"], second["inventory"])
        self.assertIn("rain_carp", first["inventory"])
        self.assertLessEqual(self.fish_total(first), 2)

    def test_same_seed_same_commands_same_fishing_balance(self):
        sequence = ["fish", "fish log", "findings", "open drift_bottle", "findings"]

        def run():
            state = parse_state(new_game("12071008", companion_name="Yaya"))
            outputs = []
            for command in sequence:
                output = cmd(command)
                outputs.append(output)
                state = parse_state(output)
            return state["inventory"], outputs

        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main()
