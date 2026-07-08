import inspect
import json
import unittest
from pathlib import Path

from fox_river_valley import cmd, new_game
from fox_river_valley import observer
from tests.test_commands import parse_state


OBSERVER_STATE = Path("observer/observer_state.json")
OBSERVER_HTML = Path("observer/observer.html")
OBSERVER_SERVER = Path("scripts/run_observer_server.py")


class V171ObserverLiveRefreshTests(unittest.TestCase):
    def read_state(self) -> dict:
        self.assertTrue(OBSERVER_STATE.exists())
        return json.loads(OBSERVER_STATE.read_text(encoding="utf-8"))

    def test_observer_state_has_turn_id(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")

        state = self.read_state()

        self.assertIsInstance(state["turn_id"], int)
        self.assertEqual(state["turn_id"], 1)
        self.assertIn("last_updated", state)
        self.assertIn("T", state["last_updated"])
        self.assertEqual(state["last_command"], "new_game")

    def test_turn_id_increments_after_cmd(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")
        first = self.read_state()["turn_id"]

        cmd("look")
        second = self.read_state()["turn_id"]
        cmd("options")
        third = self.read_state()["turn_id"]

        self.assertEqual(second, first + 1)
        self.assertEqual(third, second + 1)

    def test_observer_html_contains_polling_script(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")

        html = OBSERVER_HTML.read_text(encoding="utf-8")

        self.assertIn('fetch("./observer_state.json?ts=" + Date.now())', html)
        self.assertIn("setInterval", html)
        self.assertIn("turn_id", html)
        self.assertIn("Observer is not connected", html)
        self.assertIn("python scripts/run_observer_server.py", html)
        self.assertIn("file://", html)

    def test_observer_server_script_exists(self):
        source = OBSERVER_SERVER.read_text(encoding="utf-8")

        self.assertIn("http.server", source)
        self.assertIn("8765", source)
        self.assertIn("observer", source)
        self.assertIn("http://127.0.0.1:8765/observer.html", source)

    def test_observer_command_mentions_html_state_and_server(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")
        before = parse_state(cmd("status"))

        output = cmd("observer")
        after = parse_state(output)

        self.assertIn("observer.html", output)
        self.assertIn("observer_state.json", output)
        self.assertIn("http://127.0.0.1:8765/observer.html", output)
        self.assertIn("scripts/run_observer_server.py", output)
        self.assertEqual(after["time"], before["time"])

    def test_observer_state_atomic_write(self):
        source = inspect.getsource(observer.write_json_atomic)

        self.assertIn("observer_state.tmp.json", source)
        self.assertIn(".replace(", source)
        new_game("12071008", difficulty="normal", companion_name="Yaya")
        self.assertTrue(OBSERVER_STATE.exists())
        self.assertFalse(Path("observer/observer_state.tmp.json").exists())

    def test_observer_state_does_not_include_hidden_tables(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")

        encoded = json.dumps(self.read_state(), ensure_ascii=False)

        for forbidden in (
            "DIFFICULTY_PROFILES",
            "BUILD_COSTS",
            "CRAFT_RECIPES",
            "PROCESS_RECIPES",
            "FLOWER_VARIETIES",
            "HIDDEN_MATERIAL",
            "probability",
            "rare_conditions",
        ):
            self.assertNotIn(forbidden, encoded)


if __name__ == "__main__":
    unittest.main()
