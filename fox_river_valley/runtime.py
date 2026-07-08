from __future__ import annotations

import os
from pathlib import Path

RUNTIME_ENV_VAR = "FRV_HOME"
OBSERVER_ENV_VAR = "FRV_OBSERVER"
PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
DEFAULT_SERVER_URL = "http://127.0.0.1:8765/observer.html"


def _looks_like_project_root(path: Path) -> bool:
    return (path / "fox_river_valley").is_dir() and (path / "README.md").is_file()


def runtime_root() -> Path:
    env_home = os.environ.get(RUNTIME_ENV_VAR)
    if env_home:
        return Path(env_home).expanduser().resolve()
    if _looks_like_project_root(REPO_ROOT):
        return REPO_ROOT.resolve()
    return (Path.home() / ".fox_river_valley").resolve()


def save_path() -> Path:
    return runtime_root() / "saves" / "fox_river_valley.save.json"


def manual_save_path() -> Path:
    return runtime_root() / "saves" / "fox_river_valley.manual.save.json"


def observer_enabled() -> bool:
    value = os.environ.get(OBSERVER_ENV_VAR)
    if value is None:
        return True
    return value.strip().lower() not in {"0", "false", "no", "off", "text_only"}


def observer_dir() -> Path:
    return runtime_root() / "observer"


def observer_paths() -> dict[str, Path]:
    directory = observer_dir()
    return {
        "dir": directory,
        "state": directory / "observer_state.json",
        "html": directory / "observer.html",
    }


def runtime_status_lines() -> list[str]:
    paths = observer_paths()
    return [
        f"Runtime root: {runtime_root()}",
        f"Save path: {save_path()}",
        f"Observer HTML: {paths['html']}",
        f"Observer state: {paths['state']}",
    ]
