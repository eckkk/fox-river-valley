from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from . import calendar as calendar_rules
from .data import DIFFICULTY_PROFILES, FINDING_ITEMS, FISH_SPECIES_ITEMS, FLOWER_VARIETY_ITEMS, ITEM_STACK_LIMIT, START_POS
from .family import create_empty_family, ensure_family_state
from .relationship import build_companion_profile, ensure_home_fields, new_relationship, normalize_companion_profile, normalize_milestones
from .runtime import save_path
from .survival import ensure_survival_fields, weather_for_day
from .world import tile_key

DEFAULT_SAVE_PATH = save_path()
DEATH_MODES = {"cozy", "survival", "ai_playtest"}


def ensure_garden_state(state: dict[str, Any]) -> dict[str, Any]:
    garden = state.setdefault("garden", {})
    garden.setdefault("plots", [])
    garden.setdefault("next_id", 1)
    return garden


def ensure_flower_log_state(state: dict[str, Any]) -> dict[str, Any]:
    log = state.setdefault("flower_log", {})
    for variety in FLOWER_VARIETY_ITEMS:
        entry = log.setdefault(variety, {})
        if not isinstance(entry, dict):
            entry = {}
            log[variety] = entry
        entry["planted"] = max(0, int(entry.get("planted", 0)))
        entry["harvested"] = max(0, int(entry.get("harvested", 0)))
        entry["best_quality"] = str(entry.get("best_quality", "none"))
        rare = entry.get("rare_yields_found", [])
        if not isinstance(rare, list):
            rare = []
        entry["rare_yields_found"] = sorted({str(item) for item in rare})
        if entry["harvested"] > entry["planted"]:
            entry["planted"] = entry["harvested"]
    for key in list(log):
        if key not in FLOWER_VARIETY_ITEMS:
            log.pop(key, None)
    return log


def ensure_crop_log_state(state: dict[str, Any]) -> dict[str, Any]:
    log = state.setdefault("crop_log", {})
    if not isinstance(log, dict):
        log = {}
        state["crop_log"] = log
    for crop, raw in list(log.items()):
        if not isinstance(raw, dict):
            log.pop(crop, None)
            continue
        raw["planted"] = max(0, int(raw.get("planted", 0)))
        raw["harvested"] = max(0, int(raw.get("harvested", 0)))
        raw["best_quality"] = str(raw.get("best_quality", "none"))
        rare = raw.get("rare_yields_found", [])
        if not isinstance(rare, list):
            rare = []
        raw["rare_yields_found"] = sorted({str(item) for item in rare})
        if raw["harvested"] > raw["planted"]:
            raw["planted"] = raw["harvested"]
    return log


def ensure_memory_dates_state(state: dict[str, Any]) -> dict[str, Any]:
    dates = state.setdefault("memory_dates", {})
    if not isinstance(dates, dict):
        dates = {}
        state["memory_dates"] = dates
    valid_keys = {"first_home_day", "first_foxbell_day", "first_promise_day", "first_ceremony_day"}
    for key in list(dates):
        if key not in valid_keys or not isinstance(dates[key], dict):
            dates.pop(key, None)
            continue
        total_day = max(1, int(dates[key].get("total_day") or 1))
        normalized = calendar_rules.date_from_total_day(total_day)
        dates[key] = {
            "year": int(dates[key].get("year") or normalized["year"]),
            "season": dates[key].get("season") or normalized["season"],
            "day_of_season": int(dates[key].get("day_of_season") or normalized["day_of_season"]),
            "total_day": total_day,
        }
    return dates


def clamp_item_stacks(items: dict[str, Any] | None) -> dict[str, int]:
    clamped: dict[str, int] = {}
    for item, amount in (items or {}).items():
        try:
            count = int(amount)
        except (TypeError, ValueError):
            continue
        if count > 0:
            clamped[item] = min(count, ITEM_STACK_LIMIT)
    return clamped


def stack_space(items: dict[str, int], item: str) -> int:
    current = int(items.get(item, 0))
    return max(0, ITEM_STACK_LIMIT - current)


def can_add_item_stack(items: dict[str, int], item: str, amount: int) -> bool:
    return int(amount) <= stack_space(items, item)


def add_item_stack(items: dict[str, int], item: str, amount: int) -> int:
    requested = max(0, int(amount))
    added = min(requested, stack_space(items, item))
    if added:
        items[item] = int(items.get(item, 0)) + added
    return added


def create_companion(
    name: str,
    companion_profile: str = "default",
    family_species: str | None = None,
) -> dict[str, Any]:
    profile = build_companion_profile(companion_profile, family_species)
    return {
        "name": name,
        "hunger": 6,
        "warmth": 5,
        "mood": 6,
        "trust": 5,
        "energy": 5,
        "security": 5,
        "comfort": 0,
        "thought": "她看着还没有家的草地，像在等你决定第一件事。",
        "wish": "build simple_shelter",
        "profile": {
            "likes_window_table": True,
            "likes_riverside_bench": True,
            "likes_warm_meal": True,
            "dislikes_cave_at_night": True,
            "comfort_priority": "medium",
        },
        "companion_profile": profile,
        "family_species": profile.get("family_species"),
        "relationship": new_relationship(),
        "location": "with_player",
        "location_mode": "with_player",
        "pos": list(START_POS),
    }


def create_state(
    seed: int | str | None = None,
    difficulty: str = "normal",
    companion_name: str | None = None,
    companion_profile: str = "default",
    family_species: str | None = None,
    death_mode: str = "cozy",
) -> dict[str, Any]:
    if difficulty not in DIFFICULTY_PROFILES:
        raise ValueError(f"invalid difficulty: {difficulty}")
    if death_mode not in DEATH_MODES:
        raise ValueError(f"invalid death_mode: {death_mode}")
    seed_text = "default" if seed is None else str(seed)
    start_key = tile_key(START_POS)
    journal = [
        {
            "day": 1,
            "time": "morning",
            "text": "你在狐狸河谷醒来，草叶上还挂着雾。",
            "system": True,
        }
    ]
    companion = create_companion(companion_name, companion_profile, family_species) if companion_name else None
    calendar = calendar_rules.date_from_total_day(1)
    if companion:
        journal.append(
            {
                "day": 1,
                "time": "morning",
                "text": "你不是一个人醒来的。",
                "system": True,
            }
        )
    return {
        "version": "1.5",
        "seed": seed_text,
        "difficulty": difficulty,
        "death_mode": death_mode,
        "game_over": False,
        "zero_hunger_days": 0,
        "consecutive_sleep_count": 0,
        "mode": "family" if companion else "solo",
        "companion": companion,
        "rng_counter": 0,
        "day": 1,
        "calendar": calendar,
        "time_slot": "morning",
        "weather": weather_for_day(seed_text, 1),
        "pos": list(START_POS),
        "hp": 10,
        "hunger": 6,
        "energy": 6,
        "inventory": {},
        "storage": {},
        "food_age": {},
        "fish_log": {},
        "findings_log": {},
        "flower_log": {},
        "crop_log": {},
        "garden": {"plots": [], "next_id": 1},
        "night_pressure": "none",
        "discovered": [start_key],
        "builds": {},
        "base_pos": None,
        "shelter_pos": None,
        "home_name": None,
        "home_level": None,
        "home_comfort": 0,
        "home_security": 0,
        "home_decor": {},
        "family": create_empty_family(),
        "journal": journal,
        "memory_dates": {},
        "goal": None,
        "flags": {},
    }


def clone_state(state: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(state)


def discover(state: dict[str, Any], pos: list[int]) -> None:
    key = tile_key(pos)
    if key not in state["discovered"]:
        state["discovered"].append(key)


def add_journal(state: dict[str, Any], text: str, system: bool = True) -> None:
    for entry in state.setdefault("journal", []):
        if entry.get("day") == state["day"] and entry.get("text") == text:
            return
    state["journal"].append(
        {
            "day": state["day"],
            "time": state["time_slot"],
            "text": text,
            "system": system,
        }
    )


def save_state(state: dict[str, Any], path: Path | None = None) -> None:
    path = Path(path) if path is not None else save_path()
    state["inventory"] = clamp_item_stacks(state.get("inventory"))
    state["storage"] = clamp_item_stacks(state.get("storage"))
    state["fish_log"] = {
        item: count
        for item, count in clamp_item_stacks(state.get("fish_log", {})).items()
        if item in FISH_SPECIES_ITEMS
    }
    state["findings_log"] = {
        item: count
        for item, count in clamp_item_stacks(state.get("findings_log", {})).items()
        if item in FINDING_ITEMS
    }
    ensure_garden_state(state)
    ensure_flower_log_state(state)
    ensure_crop_log_state(state)
    calendar_rules.ensure_calendar(state)
    ensure_memory_dates_state(state)
    ensure_home_fields(state)
    ensure_family_state(state)
    ensure_survival_fields(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state(path: Path | None = None) -> dict[str, Any]:
    path = Path(path) if path is not None else save_path()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return migrate_state(loaded)


def migrate_state(state: dict[str, Any]) -> dict[str, Any]:
    state.setdefault("version", "0.1")
    state["version"] = "1.5"
    state.setdefault("difficulty", "normal")
    if state["difficulty"] not in DIFFICULTY_PROFILES:
        state["difficulty"] = "normal"
    state.setdefault("death_mode", "cozy")
    if state["death_mode"] not in DEATH_MODES:
        state["death_mode"] = "cozy"
    state.setdefault("game_over", False)
    state.setdefault("zero_hunger_days", 0)
    state.setdefault("consecutive_sleep_count", 0)
    state.setdefault("companion", None)
    state.setdefault("mode", "family" if state.get("companion") else "solo")
    state.setdefault("rng_counter", 0)
    calendar_rules.ensure_calendar(state)
    state.setdefault("inventory", {})
    state.setdefault("storage", {})
    state["inventory"] = clamp_item_stacks(state.get("inventory"))
    state["storage"] = clamp_item_stacks(state.get("storage"))
    legacy_fish_log = clamp_item_stacks(state.get("fish_log", {}))
    state["fish_log"] = {item: count for item, count in legacy_fish_log.items() if item in FISH_SPECIES_ITEMS}
    findings_log = clamp_item_stacks(state.get("findings_log", {}))
    for item, count in legacy_fish_log.items():
        if item in FINDING_ITEMS:
            findings_log[item] = findings_log.get(item, 0) + count
    state["findings_log"] = {item: count for item, count in findings_log.items() if item in FINDING_ITEMS}
    ensure_flower_log_state(state)
    ensure_crop_log_state(state)
    ensure_memory_dates_state(state)
    garden = ensure_garden_state(state)
    cleaned_plots = []
    next_id = 1
    for raw_plot in garden.get("plots", []):
        try:
            plot_id = int(raw_plot.get("id", next_id))
        except (TypeError, ValueError):
            plot_id = next_id
        pos = raw_plot.get("pos")
        if not isinstance(pos, list) or len(pos) != 2:
            pos = list(state.get("base_pos") or state.get("pos", START_POS))
        crop = raw_plot.get("crop")
        if crop not in {None, "berries", "herb", "flower"}:
            crop = None
        seed = raw_plot.get("seed")
        if seed not in {None, "berry_seed", "herb_seed", "flower_seed"}:
            seed = None
        variety = raw_plot.get("variety")
        if variety not in FLOWER_VARIETY_ITEMS:
            variety = None
        color = raw_plot.get("color")
        if variety is None:
            color = None
        growth = max(0, int(raw_plot.get("growth", 0)))
        ready = bool(raw_plot.get("ready", False)) or (crop is not None and growth >= 2)
        cleaned_plots.append(
            {
                "id": plot_id,
                "pos": [int(pos[0]), int(pos[1])],
                "crop": crop,
                "seed": seed,
                "variety": variety,
                "color": color,
                "growth": growth,
                "watered_today": bool(raw_plot.get("watered_today", False)),
                "watered_days": max(0, int(raw_plot.get("watered_days", 0))),
                "growth_days": max(0, int(raw_plot.get("growth_days", growth))),
                "planted_day": raw_plot.get("planted_day"),
                "ready": ready,
            }
        )
        next_id = max(next_id, plot_id + 1)
    garden["plots"] = cleaned_plots
    garden["next_id"] = max(next_id, int(garden.get("next_id", next_id)))
    ensure_survival_fields(state)
    state.setdefault("discovered", [tile_key(state.get("pos", START_POS))])
    state.setdefault("builds", {})
    state.setdefault("base_pos", None)
    state.setdefault("shelter_pos", None)
    state.setdefault("home_name", None)
    state.setdefault("home_level", None)
    state.setdefault("home_comfort", 0)
    state.setdefault("home_security", 0)
    state.setdefault("home_decor", {})
    ensure_family_state(state)
    if state["base_pos"] is None:
        for key, builds in state["builds"].items():
            if "simple_shelter" in builds:
                x_text, y_text = key.split(",", 1)
                state["base_pos"] = [int(x_text), int(y_text)]
                break
    if state["shelter_pos"] is None and state["base_pos"] is not None:
        state["shelter_pos"] = list(state["base_pos"])
    ensure_home_fields(state)
    if state.get("companion"):
        state["companion"].setdefault("security", 5)
        state["companion"].setdefault("comfort", 0)
        state["companion"].setdefault("thought", "她看着还没有家的草地，像在等你决定第一件事。")
        state["companion"].setdefault("wish", "build simple_shelter")
        profile = {
            "likes_window_table": True,
            "likes_riverside_bench": True,
            "likes_warm_meal": True,
            "dislikes_cave_at_night": True,
            "comfort_priority": "medium",
        }
        profile.update(state["companion"].get("profile", {}))
        state["companion"]["profile"] = profile
        family_species = state["companion"].get("family_species")
        companion_profile = normalize_companion_profile(
            state["companion"].get("companion_profile", "default"),
            family_species,
        )
        state["companion"]["companion_profile"] = companion_profile
        state["companion"]["family_species"] = companion_profile.get("family_species")
        relationship = new_relationship()
        relationship.update(state["companion"].get("relationship", {}))
        care_today = {
            "shared_food": False,
            "talked": False,
            "sat_together": False,
            "comforted": False,
            "warm_meal": False,
        }
        care_today.update(relationship.get("care_today", {}))
        relationship["care_today"] = care_today
        relationship["milestones"] = normalize_milestones(relationship.get("milestones", []))
        relationship.setdefault("next_stage_hint", None)
        relationship["bond"] = max(0, min(20, int(relationship.get("bond", 0))))
        if relationship.get("stage") not in {
            "new_arrival",
            "surviving_together",
            "shared_home",
            "trusted_family",
            "promised_family",
            "married_family",
        }:
            relationship["stage"] = "new_arrival"
        state["companion"]["relationship"] = relationship
        location = state["companion"].get("location_mode") or state["companion"].get("location") or "with_player"
        if location not in {"with_player", "at_home", "unavailable"}:
            location = "with_player"
        state["companion"]["location_mode"] = location
        state["companion"]["location"] = location
        pos = state["companion"].get("pos")
        if not isinstance(pos, list) or len(pos) != 2:
            pos = state.get("base_pos") if location == "at_home" and state.get("base_pos") else state.get("pos", START_POS)
        state["companion"]["pos"] = [int(pos[0]), int(pos[1])]
    state.setdefault("journal", [])
    state.setdefault("goal", None)
    state.setdefault("flags", {})
    return state
