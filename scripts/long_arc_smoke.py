from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH


def _parse_state(output: str) -> dict[str, Any]:
    lines = output.strip().splitlines()
    state_lines = [line for line in lines if line.startswith("STATE ")]
    if len(state_lines) != 1:
        raise AssertionError(output)
    return json.loads(state_lines[0][6:])


def _mutate_save(mutator) -> dict[str, Any]:
    cmd("save")
    saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
    mutator(saved)
    DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    cmd("load")
    return saved


def _base_checkpoint(saved: dict[str, Any], *, builds: list[str] | None = None) -> None:
    saved["pos"] = [12, 12]
    saved["base_pos"] = [12, 12]
    saved["shelter_pos"] = [12, 12]
    saved["home_level"] = saved.get("home_level") or "shelter"
    saved["builds"] = {"12,12": builds or ["simple_shelter"]}


def _relationship_checkpoint(saved: dict[str, Any], *, stage: str = "trusted_family", bond: int = 12) -> None:
    buddy = saved["companion"]
    buddy["security"] = 7
    buddy["comfort"] = 6
    buddy["trust"] = 8
    buddy["mood"] = 7
    buddy["relationship"]["stage"] = stage
    buddy["relationship"]["bond"] = bond
    buddy["relationship"]["milestones"] = [
        {"id": "first_home", "label": "第一个家", "day": 1, "time": "morning"},
        {"id": "first_window_table", "label": "第一张窗边桌", "day": 1, "time": "evening"},
        {"id": "stage_shared_home", "label": "关系阶段：shared_home", "day": 2, "time": "morning"},
    ]


def run_long_arc_smoke() -> dict[str, Any]:
    segments: dict[str, str] = {}

    new_game("12071008", difficulty="normal", companion_name="Yaya", companion_profile="silas_yaya")
    _mutate_save(lambda saved: saved.update({"inventory": {"wood": 4, "fiber": 1, "stone": 3, "stick": 2}}))
    shelter = cmd("build simple_shelter")
    campfire = cmd("build campfire")
    segments["day_one_home"] = shelter + "\n" + campfire

    _mutate_save(
        lambda saved: (
            _base_checkpoint(saved, builds=["simple_shelter", "campfire", "workbench"]),
            saved.update({"inventory": {"hoe": 1, "flower_seed": 1, "watering_can": 1}}),
        )
    )
    garden_plot = cmd("build garden_plot")
    plant = cmd("plant flower_seed")

    def make_foxbell_ready(saved: dict[str, Any]) -> None:
        plot = saved["garden"]["plots"][0]
        plot.update(
            {
                "crop": "flower",
                "seed": "flower_seed",
                "variety": "foxbell",
                "color": "warm apricot / cream edge",
                "growth": 2,
                "watered_days": 2,
                "growth_days": 2,
                "ready": True,
            }
        )
        saved.setdefault("flower_log", {}).setdefault("foxbell", {})["planted"] = 1

    _mutate_save(make_foxbell_ready)
    harvest = cmd("harvest")
    segments["garden"] = garden_plot + "\n" + plant + "\n" + harvest

    _mutate_save(
        lambda saved: (
            _base_checkpoint(saved, builds=["simple_shelter", "campfire", "workbench", "storage_box"]),
            saved.update({"inventory": {"plank": 4, "river_clay": 1, "weathered_wood": 1}}),
        )
    )
    segments["home_upgrade"] = cmd("upgrade home to little_cabin")

    _mutate_save(
        lambda saved: (
            _base_checkpoint(saved, builds=["simple_shelter", "campfire", "window_table"]),
            saved.update({"home_name": "Little Fox Cabin", "inventory": {"foxbell": 1, "warm_meal": 1}}),
            _relationship_checkpoint(saved, stage="trusted_family", bond=12),
        )
    )
    promise = cmd("propose with foxbell")
    ceremony = cmd("hold ceremony")
    segments["commitment"] = promise + "\n" + ceremony

    _mutate_save(
        lambda saved: (
            _base_checkpoint(
                saved,
                builds=[
                    "simple_shelter",
                    "workbench",
                    "storage_box",
                    "window_table",
                    "hearth",
                    "family_bed",
                    "flower_pot",
                ],
            ),
            saved.update(
                {
                    "home_name": "Little Fox Cabin",
                    "home_level": "warm_cabin",
                    "home_comfort": 6,
                    "home_security": 6,
                    "home_decor": {"flower_pot": "foxbell", "hearth": True},
                    "inventory": {"warm_meal": 1},
                    "storage": {},
                }
            ),
            saved["companion"].update({"family_species": "silicon_fox"}),
            saved["companion"]["companion_profile"].update({"family_species": "silicon_fox"}),
            _relationship_checkpoint(saved, stage="married_family", bond=14),
        )
    )
    wish = cmd("wish for kits")
    sleeps = [cmd("sleep"), cmd("sleep"), cmd("sleep")]
    check = cmd("check kits")
    segments["kit"] = wish + "\n" + "\n".join(sleeps) + "\n" + check

    ok = all(
        needle in segments[name]
        for name, needle in {
            "day_one_home": "campfire",
            "garden": "foxbell",
            "home_upgrade": "little_cabin",
            "commitment": "married_family",
            "kit": "arrived",
        }.items()
    )
    return {"ok": ok, "segments": segments, "final_state": _parse_state(check)}


if __name__ == "__main__":
    print(json.dumps(run_long_arc_smoke(), ensure_ascii=False, indent=2))
