import unittest
from pathlib import Path


class V173ObserverLauncherRobustnessTests(unittest.TestCase):
    def test_start_bat_delegates_to_powershell_launcher(self):
        text = Path("Start_Fox_River_Valley.bat").read_text(encoding="utf-8")

        self.assertIn("scripts\\start_observer.ps1", text)
        self.assertNotIn("python scripts\\run_observer_server.py", text)

    def test_powershell_launcher_finds_bundled_python_and_avoids_windowsapps_alias(self):
        text = Path("scripts/start_observer.ps1").read_text(encoding="utf-8")

        self.assertIn("codex-primary-runtime", text)
        self.assertIn("WindowsApps", text)
        self.assertIn("Test-Python", text)
        self.assertIn("run_observer_server.py", text)

    def test_powershell_launcher_waits_for_port_before_opening_browser(self):
        text = Path("scripts/start_observer.ps1").read_text(encoding="utf-8")

        self.assertIn("Wait-ObserverReady", text)
        self.assertIn("Test-NetConnection", text)
        self.assertIn("Start-Process $Url", text)

    def test_readme_mentions_one_click_python_fallback(self):
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("如果双击后浏览器显示 ERR_CONNECTION_REFUSED", readme)
        self.assertIn("launcher 会自动寻找可用 Python", readme)


if __name__ == "__main__":
    unittest.main()
