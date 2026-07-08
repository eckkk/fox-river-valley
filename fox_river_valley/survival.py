from __future__ import annotations

from typing import Any

from . import calendar as calendar_rules
from .data import ITEM_STACK_LIMIT
from .rng import deterministic_int

WEATHER_TYPES = ("clear", "cloudy", "rain", "fog", "cold_wind")

WEATHER_LINES = {
    "clear": "天气 clear：光线稳定，今天适合走远一点。",
    "cloudy": "天气 cloudy：云层压低，河谷安静但不难行动。",
    "rain": "天气 rain：wood/fiber 采集略慢，fish 更容易靠近水面；夜里没有火会更冷。",
    "fog": "天气 fog：雾压在草叶上，look 和 map 的线索会更朦胧。",
    "cold_wind": "天气 cold_wind：夜里冷意更明显，campfire 或 hearth 会很有用。",
}

PERISHABLE_DAYS = {
    "fish": 2,
    "silver_fish": 2,
    "rain_carp": 2,
    "dusk_eel": 2,
    "river_crab": 2,
    "cooked_fish": 3,
    "berries": 3,
    "warm_meal": 2,
    "herb": 5,
}

SPOILAGE_RESULTS = {
    "fish": "stale_fish",
    "silver_fish": "stale_fish",
    "rain_carp": "stale_fish",
    "dusk_eel": "stale_fish",
    "river_crab": "stale_food",
    "cooked_fish": "stale_food",
    "berries": "spoiled_berries",
    "warm_meal": "stale_food",
    "herb": "dried_herb",
}

STALE_ITEMS = {"stale_fish", "stale_food", "spoiled_berries"}
BENIGN_AGING_RESULTS = {"dried_herb"}


def weather_for_day(seed: str, day: int) -> str:
    return calendar_rules.weather_for_total_day(str(seed), int(day))


def _positive_count(container: dict[str, int], item: str) -> int:
    return max(0, int(container.get(item, 0)))


def _total_count(state: dict[str, Any], item: str) -> int:
    return _positive_count(state.get("inventory", {}), item) + _positive_count(state.get("storage", {}), item)


def _add_count(container: dict[str, int], item: str, count: int) -> None:
    if count <= 0:
        return
    container[item] = min(ITEM_STACK_LIMIT, _positive_count(container, item) + count)


def _remove_count(container: dict[str, int], item: str, count: int) -> int:
    available = _positive_count(container, item)
    removed = min(available, count)
    if removed:
        remaining = available - removed
        if remaining:
            container[item] = remaining
        else:
            container.pop(item, None)
    return removed


def sync_food_age(state: dict[str, Any]) -> None:
    age = state.setdefault("food_age", {})
    for item in list(age):
        if item not in PERISHABLE_DAYS or _total_count(state, item) <= 0:
            age.pop(item, None)
    for item in PERISHABLE_DAYS:
        if _total_count(state, item) > 0:
            age[item] = max(0, int(age.get(item, 0)))


def ensure_survival_fields(state: dict[str, Any]) -> None:
    calendar_rules.ensure_calendar(state)
    state.setdefault("weather", weather_for_day(str(state.get("seed", "default")), int(state.get("day", 1))))
    state.setdefault("food_age", {})
    state.setdefault("night_pressure", "none")
    sync_food_age(state)


def note_food_added(state: dict[str, Any], item: str) -> None:
    if item in PERISHABLE_DAYS:
        state.setdefault("food_age", {})[item] = 0


def note_food_removed(state: dict[str, Any], item: str) -> None:
    if item in PERISHABLE_DAYS:
        sync_food_age(state)


def advance_food_morning(state: dict[str, Any]) -> list[dict[str, Any]]:
    sync_food_age(state)
    spoiled: list[dict[str, Any]] = []
    age = state.setdefault("food_age", {})
    for item in list(age):
        age[item] = int(age[item]) + 1
        limit = PERISHABLE_DAYS[item]
        if age[item] < limit:
            continue
        result = SPOILAGE_RESULTS.get(item)
        if not result:
            continue
        inventory_count = _remove_count(state.setdefault("inventory", {}), item, _positive_count(state.get("inventory", {}), item))
        storage_count = _remove_count(state.setdefault("storage", {}), item, _positive_count(state.get("storage", {}), item))
        total = inventory_count + storage_count
        if total <= 0:
            age.pop(item, None)
            continue
        _add_count(state["inventory"], result, inventory_count)
        _add_count(state["storage"], result, storage_count)
        age.pop(item, None)
        spoiled.append({"item": item, "result": result, "count": total})
    sync_food_age(state)
    return spoiled


def food_lines(state: dict[str, Any]) -> list[str]:
    sync_food_age(state)
    lines = ["食物新鲜度："]
    found = False
    for item in sorted(PERISHABLE_DAYS):
        count = _total_count(state, item)
        if count <= 0:
            continue
        found = True
        age = state["food_age"].get(item, 0)
        lines.append(f"- {item} x{count}: age {age}/{PERISHABLE_DAYS[item]}")
    stale = {
        item: _total_count(state, item)
        for item in sorted(STALE_ITEMS)
        if _total_count(state, item) > 0
    }
    for item, count in stale.items():
        found = True
        lines.append(f"- {item} x{count}: 已不新鲜，建议 discard")
    if not found:
        lines.append("- 没有易腐食物。")
    return lines


def weather_lines(state: dict[str, Any]) -> list[str]:
    weather = state.get("weather", "clear")
    return [
        WEATHER_LINES.get(weather, f"天气 {weather}：河谷暂时没有特殊变化。"),
        f"night pressure: {night_pressure(state)}",
    ]


def base_builds(state: dict[str, Any]) -> list[str]:
    base_pos = state.get("base_pos")
    if base_pos is None:
        return []
    key = f"{base_pos[0]},{base_pos[1]}"
    return state.get("builds", {}).get(key, [])


def at_base(state: dict[str, Any]) -> bool:
    return state.get("base_pos") is not None and list(state.get("pos", [])) == list(state["base_pos"])


def warmth_protection(state: dict[str, Any]) -> str:
    builds = base_builds(state)
    if "hearth" in builds:
        return "hearth"
    if "campfire" in builds:
        return "campfire"
    return "none"


def night_pressure(state: dict[str, Any]) -> str:
    if state.get("time_slot") != "night":
        return "none"
    if not at_base(state):
        return "high"
    weather = state.get("weather", "clear")
    protection = warmth_protection(state)
    if weather == "cold_wind" and protection == "none":
        return "high"
    if weather == "rain" and protection == "none":
        return "mild"
    if weather in {"rain", "cold_wind"} and protection == "campfire":
        return "mild"
    return "none"


def sleep_warmth_loss(state: dict[str, Any], weather: str | None = None) -> int:
    actual_weather = weather or state.get("weather", "clear")
    protection = warmth_protection(state)
    if protection == "hearth":
        return 0
    if protection == "campfire":
        return 1 if actual_weather in {"rain", "cold_wind"} else 0
    return 2 if actual_weather in {"rain", "cold_wind"} else 1


def wait_warmth_loss(state: dict[str, Any]) -> int:
    if state.get("time_slot") != "night":
        return 0
    if at_base(state) and warmth_protection(state) == "hearth":
        return 0
    if state.get("weather") == "cold_wind":
        return 2 if warmth_protection(state) == "none" else 1
    if state.get("weather") == "rain":
        return 1 if warmth_protection(state) == "none" else 0
    return 1 if not at_base(state) else 0


def adjust_gather_amount(state: dict[str, Any], item: str, amount: int) -> int:
    if state.get("weather") == "rain" and item in {"wood", "fiber"}:
        return max(1, amount - 1)
    return amount


def fish_bonus(state: dict[str, Any]) -> int:
    return 1 if state.get("weather") == "rain" else 0


def has_stale_food(state: dict[str, Any]) -> bool:
    return any(_total_count(state, item) > 0 for item in STALE_ITEMS)
