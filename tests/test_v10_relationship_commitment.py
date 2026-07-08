import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley import data
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


class V10RelationshipCommitmentTests(unittest.TestCase):
    def mutate_save(self, mutator) -> dict:
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        mutator(saved)
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")
        return saved

    def add_inventory(self, items: dict[str, int]) -> None:
        def mutate(saved: dict) -> None:
            saved.setdefault("inventory", {}).update(items)

        self.mutate_save(mutate)

    def prepare_ready_home(
        self,
        *,
        companion_profile: str = "default",
        token: str = "old_coin",
        extra_inventory: dict[str, int] | None = None,
    ) -> None:
        new_game("12071008", difficulty="normal", companion_name="Yaya", companion_profile=companion_profile)

        def mutate(saved: dict) -> None:
            saved["pos"] = [12, 12]
            saved["base_pos"] = [12, 12]
            saved["shelter_pos"] = [12, 12]
            saved["home_name"] = "Little Fox Cabin"
            saved["builds"] = {"12,12": ["simple_shelter", "campfire", "window_table"]}
            inventory = {token: 1}
            if extra_inventory:
                inventory.update(extra_inventory)
            saved["inventory"] = inventory
            buddy = saved["companion"]
            buddy["trust"] = 7
            buddy["comfort"] = 4
            buddy["security"] = 6
            buddy["mood"] = 6
            buddy["relationship"]["stage"] = "shared_home"
            buddy["relationship"]["bond"] = 10
            buddy["relationship"]["milestones"] = [
                {"id": "first_home", "label": "第一个家", "day": 1, "time": "morning"},
                {"id": "stage_shared_home", "label": "关系阶段：shared_home", "day": 1, "time": "morning"},
            ]

        self.mutate_save(mutate)

    def test_item_tags_include_commitment_tokens(self):
        commitment_tokens = {
            "foxbell",
            "river_forget_me_not",
            "hearth_marigold",
            "moon_violet",
            "crafted_charm",
            "old_coin",
        }

        self.assertTrue(hasattr(data, "ITEM_TAGS"))
        self.assertTrue(hasattr(data, "COMMITMENT_TOKEN_ITEMS"))
        self.assertTrue(commitment_tokens.issubset(data.COMMITMENT_TOKEN_ITEMS))
        for item in commitment_tokens:
            self.assertIn("commitment_token", data.ITEM_TAGS[item])
        self.assertIn("flower", data.ITEM_TAGS["foxbell"])
        self.assertIn("food", data.ITEM_TAGS["warm_meal"])
        self.assertIn("finding", data.ITEM_TAGS["old_coin"])

    def test_default_profile_accepts_any_commitment_token(self):
        self.prepare_ready_home(token="old_coin")

        output = cmd("propose with old_coin")
        state = parse_state(output)

        self.assertIn("SCENE: Promise", output)
        self.assertEqual(state["relationship"]["stage"], "promised_family")
        self.assertEqual(state["relationship"]["commitment"], "promised")

    def test_silas_yaya_profile_prefers_foxbell(self):
        new_game("12071008", companion_name="Yaya", companion_profile="silas_yaya")

        output = cmd("debug companion")

        self.assertIn("companion_profile: silas_yaya", output)
        self.assertIn("preferred_commitment_tokens: foxbell", output)
        self.assertIn("favorite_flower: foxbell", output)
        self.assertIn("family_species: silicon_fox", output)
        self.assertIn("hidden_breed: curly_brace_fox", output)

    def test_propose_requires_relationship_conditions(self):
        new_game("12071008", companion_name="Yaya")
        self.add_inventory({"foxbell": 1})
        before = parse_state(cmd("status"))

        output = cmd("propose with foxbell")
        after = parse_state(output)

        self.assertIn("缺少条件", output)
        self.assertIn("relationship stage at least shared_home", output)
        self.assertIn("bond >= 10", output)
        self.assertIn("trust >= 7", output)
        self.assertIn("comfort >= 4", output)
        self.assertIn("security >= 6", output)
        self.assertIn("home_name", output)
        self.assertIn("shelter/base", output)
        self.assertEqual(after["time"], before["time"])
        self.assertEqual(after["inventory"].get("foxbell"), 1)

    def test_propose_with_non_token_fails(self):
        self.prepare_ready_home(token="dew_daisy")
        before = parse_state(cmd("status"))

        output = cmd("propose with dew_daisy")
        after = parse_state(output)

        self.assertIn("不是 commitment_token", output)
        self.assertEqual(after["time"], before["time"])
        self.assertEqual(after["inventory"].get("dew_daisy"), 1)
        self.assertEqual(after["relationship"]["stage"], "shared_home")

    def test_successful_propose_consumes_item_and_sets_promised_family(self):
        self.prepare_ready_home(token="river_forget_me_not")

        output = cmd("propose with river_forget_me_not")
        state = parse_state(output)

        self.assertNotIn("river_forget_me_not", state["inventory"])
        self.assertEqual(state["relationship"], {"stage": "promised_family", "bond": 10, "commitment": "promised"})
        self.assertIn("first_promise", cmd("debug companion"))
        self.assertIn("家庭承诺", cmd("journal"))

    def test_preferred_token_gives_bonus(self):
        self.prepare_ready_home(companion_profile="silas_yaya", token="foxbell")

        state = parse_state(cmd("propose with foxbell"))

        self.assertEqual(state["companion"]["mood"], 7)
        self.assertEqual(state["companion"]["trust"], 8)
        self.assertEqual(state["companion"]["comfort"], 5)

    def test_hold_ceremony_requires_promised_family(self):
        self.prepare_ready_home(token="foxbell", extra_inventory={"warm_meal": 1})
        before = parse_state(cmd("status"))

        output = cmd("hold ceremony")
        after = parse_state(output)

        self.assertIn("需要先进入 promised_family", output)
        self.assertEqual(after["time"], before["time"])
        self.assertEqual(after["relationship"]["stage"], "shared_home")

    def test_hold_ceremony_sets_married_family(self):
        self.prepare_ready_home(token="old_coin", extra_inventory={"warm_meal": 1})
        cmd("propose with old_coin")

        output = cmd("hold ceremony")
        state = parse_state(output)

        self.assertIn("SCENE: Ceremony", output)
        self.assertIn("关系阶段更新：married_family", output)
        self.assertEqual(state["relationship"]["stage"], "married_family")
        self.assertEqual(state["relationship"]["bond"], 12)
        self.assertEqual(state["relationship"]["commitment"], "married")
        self.assertIn("first_ceremony", cmd("debug companion"))

    def test_cutscene_is_direct_and_contains_state_change(self):
        self.prepare_ready_home(companion_profile="silas_yaya", token="foxbell")

        output = cmd("propose with foxbell")
        lines = output.strip().splitlines()

        self.assertEqual(lines[0], "SCENE: Promise")
        self.assertIn("你拿出 foxbell，向 Yaya 提出家庭承诺。", output)
        self.assertIn("Yaya 接受了。", output)
        self.assertIn("关系阶段更新：promised_family", output)
        self.assertIn("新增里程碑：first_promise", output)
        self.assertIn("可尝试：relationship、hold ceremony、journal", output)
        self.assertEqual(sum(1 for line in lines if line.startswith("STATE ")), 1)
        self.assertTrue(lines[-1].startswith("STATE "))

    def test_save_load_preserves_commitment_stage_profile_species(self):
        self.prepare_ready_home(companion_profile="silas_yaya", token="foxbell", extra_inventory={"warm_meal": 1})
        cmd("propose with foxbell")
        cmd("hold ceremony")
        cmd("save")

        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(saved["companion"]["relationship"]["stage"], "married_family")
        self.assertEqual(saved["companion"]["companion_profile"]["id"], "silas_yaya")
        self.assertEqual(saved["companion"]["family_species"], "silicon_fox")

        new_game("other")
        loaded = parse_state(cmd("load"))
        debug = cmd("debug companion")

        self.assertEqual(loaded["relationship"]["stage"], "married_family")
        self.assertEqual(loaded["relationship"]["commitment"], "married")
        self.assertIn("companion_profile: silas_yaya", debug)
        self.assertIn("family_species: silicon_fox", debug)

    def test_solo_mode_cannot_propose(self):
        new_game("12071008")
        self.add_inventory({"old_coin": 1})
        before = parse_state(cmd("status"))

        output = cmd("propose with old_coin")
        after = parse_state(output)

        self.assertIn("solo mode", output)
        self.assertEqual(after["time"], before["time"])
        self.assertNotIn("relationship", after)
        self.assertEqual(after["inventory"].get("old_coin"), 1)

    def test_same_seed_same_commands_same_commitment_state(self):
        def run_sequence() -> dict:
            self.prepare_ready_home(token="old_coin", extra_inventory={"warm_meal": 1})
            cmd("propose with old_coin")
            state = parse_state(cmd("commit family"))
            return {
                "relationship": state["relationship"],
                "home_name": state["home_name"],
                "inventory": state["inventory"],
            }

        self.assertEqual(run_sequence(), run_sequence())


if __name__ == "__main__":
    unittest.main()
