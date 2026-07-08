import json
from typing import Any

from . import calendar as calendar_rules
from .companion import refresh_inner_state
from .family import compact_family, kit_readiness_status
from .farming import garden_plot_count, ready_crop_count
from .relationship import compact_relationship, ensure_home_fields
from .survival import night_pressure
from .world import describe_tile, nearby_terrains, terrain_at

COMPACT_COMPANION_KEYS = (
    "name",
    "hunger",
    "warmth",
    "mood",
    "trust",
    "energy",
    "security",
    "comfort",
    "thought",
    "wish",
    "location",
    "location_mode",
    "pos",
)


def compact_companion(buddy: dict[str, Any]) -> dict[str, Any]:
    return {key: buddy[key] for key in COMPACT_COMPANION_KEYS if key in buddy}


def state_summary(state: dict[str, Any]) -> dict[str, Any]:
    refresh_inner_state(state)
    ensure_home_fields(state)
    calendar = calendar_rules.ensure_calendar(state)
    builds = state.get("builds", {})
    current_key = f"{state['pos'][0]},{state['pos'][1]}"
    current_builds = builds.get(current_key, [])
    all_builds = [item for items in builds.values() for item in items]
    summary = {
        "day": state["day"],
        "year": calendar["year"],
        "season": calendar["season"],
        "day_of_season": calendar["day_of_season"],
        "time": state["time_slot"],
        "weather": state["weather"],
        "difficulty": state.get("difficulty", "normal"),
        "death_mode": state.get("death_mode", "cozy"),
        "game_over": bool(state.get("game_over", False)),
        "mode": state.get("mode", "solo"),
        "pos": state["pos"],
        "terrain": terrain_at(state["seed"], state["pos"]),
        "hp": state["hp"],
        "hunger": state["hunger"],
        "energy": state["energy"],
        "inventory": {
            key: value
            for key, value in sorted(state["inventory"].items())
            if value > 0
        },
        "known_tiles": len(state["discovered"]),
        "shelter": "simple_shelter" in all_builds,
        "base_pos": state.get("base_pos"),
        "shelter_pos": state.get("shelter_pos"),
        "home_name": state.get("home_name"),
        "home_level": state.get("home_level"),
        "home_comfort": state.get("home_comfort", 0),
        "home_security": state.get("home_security", 0),
        "kit_readiness": kit_readiness_status(state),
        "family": compact_family(state),
        "campfire": "campfire" in all_builds,
        "builds_here": current_builds,
        "garden_plots": garden_plot_count(state),
        "ready_crops": ready_crop_count(state),
        "goal": state.get("goal"),
        "night_pressure": night_pressure(state),
        "nearby": nearby_terrains(state["seed"], state["pos"]),
    }
    if state.get("companion"):
        summary["companion"] = compact_companion(state["companion"])
        rel = compact_relationship(state)
        if rel:
            summary["relationship"] = rel
    return summary


def render(lines: list[str], state: dict[str, Any]) -> str:
    clean_lines = [line for line in lines if line]
    compact = json.dumps(state_summary(state), ensure_ascii=False, separators=(",", ":"))
    return "\n".join([*clean_lines, f"STATE {compact}"])


def place_line(state: dict[str, Any]) -> str:
    return f"你在狐狸河谷的{describe_tile(state['seed'], state['pos'])}上。"
