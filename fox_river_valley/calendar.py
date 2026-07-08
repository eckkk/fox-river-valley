from __future__ import annotations

from typing import Any

from .rng import deterministic_int

DAYS_PER_SEASON = 28
SEASONS = ("spring", "summer", "autumn", "winter")
DAYS_PER_YEAR = DAYS_PER_SEASON * len(SEASONS)

SEASON_WEATHER_WEIGHTS = {
    "spring": ("clear", "cloudy", "rain", "fog", "cold_wind"),
    "summer": ("clear", "clear", "clear", "cloudy", "rain"),
    "autumn": ("cloudy", "fog", "cold_wind", "fog", "clear"),
    "winter": ("cold_wind", "cold_wind", "cloudy", "cold_wind", "fog"),
}

SEASON_HINTS = {
    "spring": "spring：花种、草药种和河边 reed 更容易成为今天的线索。",
    "summer": "summer：浆果、草药和水边材料更充足。",
    "autumn": "autumn：落枝、mushroom 和 seed_pod 开始出现。",
    "winter": "winter：作物不会死，但生长会慢；branch 和 stone 更可靠。",
}


def date_from_total_day(total_day: int) -> dict[str, int | str]:
    day = max(1, int(total_day))
    zero_based = day - 1
    year = zero_based // DAYS_PER_YEAR + 1
    within_year = zero_based % DAYS_PER_YEAR
    season_index = within_year // DAYS_PER_SEASON
    day_of_season = within_year % DAYS_PER_SEASON + 1
    return {
        "season": SEASONS[season_index],
        "day_of_season": day_of_season,
        "year": year,
        "total_day": day,
    }


def season_title(season: str) -> str:
    return season[:1].upper() + season[1:]


def ensure_calendar(state: dict[str, Any]) -> dict[str, Any]:
    total_day = int(state.get("day", state.get("calendar", {}).get("total_day", 1)))
    calendar = date_from_total_day(total_day)
    state["day"] = int(calendar["total_day"])
    state["calendar"] = calendar
    return calendar


def advance_day(state: dict[str, Any]) -> dict[str, Any]:
    state["day"] = int(state.get("day", 1)) + 1
    return ensure_calendar(state)


def season(state: dict[str, Any]) -> str:
    return str(ensure_calendar(state)["season"])


def _uncapped_weather_for_total_day(seed: str, total_day: int) -> str:
    calendar = date_from_total_day(total_day)
    season_name = str(calendar["season"])
    weights = SEASON_WEATHER_WEIGHTS[season_name]
    index = deterministic_int(str(seed), int(total_day), "weather", len(weights))
    return weights[index]


def weather_for_total_day(seed: str, total_day: int) -> str:
    day = int(total_day)
    candidate = _uncapped_weather_for_total_day(seed, day)
    block_start = ((day - 1) // 8) * 8 + 1
    block_end = block_start + 7
    block_has_fog = any(_uncapped_weather_for_total_day(seed, check_day) == "fog" for check_day in range(block_start, block_end + 1))
    if not block_has_fog and day == block_end:
        return "fog"
    return candidate


def memory_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    calendar = ensure_calendar(state)
    return {
        "year": calendar["year"],
        "season": calendar["season"],
        "day_of_season": calendar["day_of_season"],
        "total_day": calendar["total_day"],
    }


def record_memory_date(state: dict[str, Any], key: str) -> bool:
    dates = state.setdefault("memory_dates", {})
    if dates.get(key):
        return False
    dates[key] = memory_snapshot(state)
    return True


def calendar_lines(state: dict[str, Any]) -> list[str]:
    calendar = ensure_calendar(state)
    season_name = str(calendar["season"])
    return [
        f"Year {calendar['year']} {season_title(season_name)} Day {calendar['day_of_season']}",
        f"total day: {calendar['total_day']}",
        f"weather: {state.get('weather', weather_for_total_day(str(state.get('seed', 'default')), int(calendar['total_day'])))}",
        f"today hint: {SEASON_HINTS[season_name]}",
    ]
