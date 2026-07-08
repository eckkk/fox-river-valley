from __future__ import annotations

from typing import Any

from . import calendar as calendar_rules
from .data import FLOWER_VARIETY_ITEMS, item_counts_text, item_label, normalize_item_id
from .rng import deterministic_int
from .state import add_item_stack, add_journal
from .survival import note_food_added
from .world import nearby_terrains

FLOWER_VARIETIES = {
    "foxbell": {
        "label": "小狐铃花",
        "color": "warm apricot / cream edge",
        "journal": "门口亮起几朵小狐铃花，像把家轻轻点了一下。",
    },
    "dew_daisy": {
        "label": "晨露雏菊",
        "color": "white petals / yellow heart",
        "journal": "第一簇晨露雏菊在家旁边开了，白瓣上像还挂着清晨。",
    },
    "river_forget_me_not": {
        "label": "河雾勿忘我",
        "color": "pale blue / mist violet",
        "journal": "河雾勿忘我在风里轻轻点头，像把水声留在了家旁边。",
    },
    "hearth_marigold": {
        "label": "炉火金盏",
        "color": "orange gold / deep gold",
        "journal": "炉火金盏在屋边亮起来，颜色像一小圈留下来的火。",
    },
    "moon_violet": {
        "label": "月影堇",
        "color": "pale violet / silver gray edge",
        "journal": "第一朵月影堇开得很安静，像把夜色折在了花边上。",
    },
}

FLOWER_VARIETY_ORDER = tuple(FLOWER_VARIETIES)

QUALITY_ORDER = ("none", "normal", "good", "perfect")

CROP_PREFERRED_SEASONS = {
    "foxbell": {"spring", "autumn"},
    "dew_daisy": {"spring", "summer"},
    "river_forget_me_not": {"spring"},
    "hearth_marigold": {"summer", "autumn"},
    "moon_violet": {"autumn", "winter"},
    "berries": {"summer"},
    "herb": {"spring", "summer", "autumn"},
}

RARE_YIELDS = {
    "foxbell": "foxbell_dye_material",
    "dew_daisy": "dew_petal",
    "river_forget_me_not": "river_blue_petal",
    "hearth_marigold": "hearth_gold_petal",
    "moon_violet": "moon_violet_pigment",
}

SEED_TO_CROP = {
    "berry_seed": "berries",
    "herb_seed": "herb",
    "flower_seed": "flower",
}

CROP_TO_SEED = {
    "berries": "berry_seed",
    "herb": "herb_seed",
    "flower": "flower_seed",
}

FOOD_CROPS = {"berries", "herb"}
GROWTH_READY_AT = 2
MAX_PLOTS_PER_TILE = 3


def ensure_garden(state: dict[str, Any]) -> dict[str, Any]:
    garden = state.setdefault("garden", {})
    garden.setdefault("plots", [])
    garden.setdefault("next_id", 1)
    return garden


def plots(state: dict[str, Any]) -> list[dict[str, Any]]:
    return ensure_garden(state)["plots"]


def garden_plot_count(state: dict[str, Any]) -> int:
    return len(plots(state))


def ready_crop_count(state: dict[str, Any]) -> int:
    return sum(1 for plot in plots(state) if plot.get("ready"))


def has_garden_plot(state: dict[str, Any]) -> bool:
    return garden_plot_count(state) > 0


def has_flower_crop(state: dict[str, Any]) -> bool:
    inventory = state.get("inventory", {})
    return (
        any(plot.get("crop") == "flower" or plot.get("variety") in FLOWER_VARIETY_ITEMS for plot in plots(state))
        or inventory.get("flower", 0) > 0
        or any(inventory.get(item, 0) > 0 for item in FLOWER_VARIETY_ITEMS)
    )


def has_flower_variety(state: dict[str, Any], variety: str) -> bool:
    if variety not in FLOWER_VARIETY_ITEMS:
        return False
    return any(plot.get("variety") == variety for plot in plots(state)) or state.get("inventory", {}).get(variety, 0) > 0


def has_food_seed(state: dict[str, Any]) -> bool:
    inventory = state.get("inventory", {})
    return inventory.get("berry_seed", 0) > 0 or inventory.get("herb_seed", 0) > 0


def _same_pos(left: list[int], right: list[int]) -> bool:
    return list(left) == list(right)


def _near_base(state: dict[str, Any]) -> bool:
    base_pos = state.get("base_pos")
    if not base_pos:
        return False
    x, y = state["pos"]
    bx, by = base_pos
    return max(abs(x - bx), abs(y - by)) <= 1


def _plots_here(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [plot for plot in plots(state) if _same_pos(plot.get("pos", []), state["pos"])]


def can_build_plot(state: dict[str, Any]) -> tuple[bool, str | None]:
    if state.get("base_pos") is None:
        return False, "还没有家，小菜地（garden_plot）需要建在 base 旁边。"
    if not _near_base(state):
        return False, "小菜地（garden_plot）必须建在 base tile 或 base 附近一格。"
    if state.get("inventory", {}).get("hoe", 0) <= 0:
        return False, "需要 hoe 才能开垦小菜地（garden_plot）。"
    if len(_plots_here(state)) >= MAX_PLOTS_PER_TILE:
        return False, "这个 tile 的小菜地（garden_plot）已经够多了。"
    return True, None


def build_plot(state: dict[str, Any]) -> tuple[list[str], bool]:
    ok, error = can_build_plot(state)
    if not ok:
        return ([error or "现在不能建小菜地（garden_plot）。"], False)
    garden = ensure_garden(state)
    plot_id = int(garden.get("next_id", 1))
    garden["next_id"] = plot_id + 1
    garden["plots"].append(
        {
            "id": plot_id,
            "pos": list(state["pos"]),
            "crop": None,
            "seed": None,
            "variety": None,
            "color": None,
            "growth": 0,
            "watered_today": False,
            "watered_days": 0,
            "growth_days": 0,
            "planted_day": None,
            "ready": False,
        }
    )
    if not state["flags"].get("first_garden_plot"):
        state["flags"]["first_garden_plot"] = True
        add_journal(state, "你在家旁边开出第一块小菜地，土翻开时带着一点湿气。")
    return (["你用 hoe 翻开家旁边的土，整理出一块小小的菜地。", "建造完成：小菜地（garden_plot）"], True)


def _empty_plot_here(state: dict[str, Any]) -> dict[str, Any] | None:
    for plot in _plots_here(state):
        if plot.get("crop") is None:
            return plot
    return None


def ensure_flower_log(state: dict[str, Any]) -> dict[str, dict[str, int]]:
    log = state.setdefault("flower_log", {})
    for variety in FLOWER_VARIETY_ORDER:
        entry = log.setdefault(variety, {})
        entry["planted"] = int(entry.get("planted", 0))
        entry["harvested"] = int(entry.get("harvested", 0))
        entry["best_quality"] = str(entry.get("best_quality", "none"))
        rare = entry.get("rare_yields_found", [])
        if not isinstance(rare, list):
            rare = []
        entry["rare_yields_found"] = sorted({str(item) for item in rare})
        if entry["harvested"] > entry["planted"]:
            entry["planted"] = entry["harvested"]
    return log


def ensure_crop_log(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    log = state.setdefault("crop_log", {})
    if not isinstance(log, dict):
        log = {}
        state["crop_log"] = log
    return log


def _quality_rank(quality: str) -> int:
    try:
        return QUALITY_ORDER.index(quality)
    except ValueError:
        return 0


def _record_crop_log(
    state: dict[str, Any],
    crop: str,
    key: str,
    quality: str = "none",
    rare_yields: list[str] | None = None,
) -> None:
    if key not in {"planted", "harvested"}:
        return
    entry = ensure_crop_log(state).setdefault(
        crop,
        {"planted": 0, "harvested": 0, "best_quality": "none", "rare_yields_found": []},
    )
    entry[key] = int(entry.get(key, 0)) + 1
    if int(entry.get("harvested", 0)) > int(entry.get("planted", 0)):
        entry["planted"] = int(entry.get("harvested", 0))
    if _quality_rank(quality) > _quality_rank(str(entry.get("best_quality", "none"))):
        entry["best_quality"] = quality
    found = set(entry.get("rare_yields_found", []))
    found.update(rare_yields or [])
    entry["rare_yields_found"] = sorted(found)


def record_flower(
    state: dict[str, Any],
    variety: str,
    key: str,
    quality: str = "none",
    rare_yields: list[str] | None = None,
) -> None:
    if variety not in FLOWER_VARIETIES or key not in {"planted", "harvested"}:
        return
    log = ensure_flower_log(state)
    log[variety][key] = int(log[variety].get(key, 0)) + 1
    if int(log[variety].get("harvested", 0)) > int(log[variety].get("planted", 0)):
        log[variety]["planted"] = int(log[variety].get("harvested", 0))
    if _quality_rank(quality) > _quality_rank(str(log[variety].get("best_quality", "none"))):
        log[variety]["best_quality"] = quality
    found = set(log[variety].get("rare_yields_found", []))
    found.update(rare_yields or [])
    log[variety]["rare_yields_found"] = sorted(found)
    _record_crop_log(state, variety, key, quality, rare_yields)


def flower_log_lines(state: dict[str, Any]) -> list[str]:
    log = ensure_flower_log(state)
    seen = [
        (variety, entry)
        for variety, entry in log.items()
        if int(entry.get("planted", 0)) > 0 or int(entry.get("harvested", 0)) > 0
    ]
    if not seen:
        return ["flower log: empty"]
    lines = ["flower log:"]
    for variety, entry in sorted(seen):
        details = FLOWER_VARIETIES[variety]
        rare = entry.get("rare_yields_found", [])
        rare_text = ", ".join(rare) if rare else "none"
        lines.append(
            f"- {variety} ({details['label']}): planted {entry.get('planted', 0)}, harvested {entry.get('harvested', 0)}, best_quality {entry.get('best_quality', 'none')}, rare_yields_found {rare_text}, color {details['color']}"
        )
    return lines


def crop_log_lines(state: dict[str, Any]) -> list[str]:
    log = ensure_crop_log(state)
    seen = [(crop, entry) for crop, entry in log.items() if int(entry.get("planted", 0)) or int(entry.get("harvested", 0))]
    if not seen:
        return ["crop log: empty"]
    lines = ["crop log:"]
    for crop, entry in sorted(seen):
        rare = entry.get("rare_yields_found", [])
        rare_text = ", ".join(rare) if rare else "none"
        lines.append(
            f"- {crop}: planted {entry.get('planted', 0)}, harvested {entry.get('harvested', 0)}, best_quality {entry.get('best_quality', 'none')}, rare_yields_found {rare_text}"
        )
    return lines


def choose_flower_variety(state: dict[str, Any], plot: dict[str, Any]) -> str:
    index = deterministic_int(str(state["seed"]), int(plot["id"]), "flower:variety:v1", len(FLOWER_VARIETY_ORDER))
    return FLOWER_VARIETY_ORDER[index]


def plant_seed(state: dict[str, Any], seed: str) -> tuple[list[str], bool, str | None]:
    seed = normalize_item_id(seed)
    if seed not in SEED_TO_CROP:
        return ([f"{item_label(seed)} 现在还不能种。"], False, None)
    if state["inventory"].get(seed, 0) <= 0:
        return ([f"背包里没有 {item_label(seed)}。"], False, None)
    plot = _empty_plot_here(state)
    if plot is None:
        return (["这里没有空的小菜地（garden_plot）。"], False, None)
    crop = SEED_TO_CROP[seed]
    variety = choose_flower_variety(state, plot) if seed == "flower_seed" else None
    color = FLOWER_VARIETIES[variety]["color"] if variety else None
    state["inventory"][seed] -= 1
    if state["inventory"][seed] <= 0:
        state["inventory"].pop(seed, None)
    plot.update(
        {
            "crop": crop,
            "seed": seed,
            "variety": variety,
            "color": color,
            "growth": 0,
            "watered_today": state.get("weather") == "rain",
            "watered_days": 1 if state.get("weather") == "rain" else 0,
            "growth_days": 0,
            "planted_day": state["day"],
            "ready": False,
        }
    )
    if variety:
        record_flower(state, variety, "planted")
        variety_flag = f"first_plant_flower:{variety}"
        if not state["flags"].get(variety_flag):
            state["flags"][variety_flag] = True
            add_journal(state, f"你第一次种下 {variety}（{FLOWER_VARIETIES[variety]['label']}）。")
    else:
        _record_crop_log(state, crop, "planted")
    if not state["flags"].get("first_plant"):
        state["flags"]["first_plant"] = True
        add_journal(state, f"你第一次把 {item_label(seed, include_id=False)} 种进小菜地。")
    planted_name = variety or crop
    return ([f"你把 {item_label(seed)} 按进松开的土里。", f"种下：{item_label(planted_name)}"], True, planted_name)


def water_crops(state: dict[str, Any]) -> tuple[list[str], bool]:
    if state["inventory"].get("watering_can", 0) <= 0:
        return (["需要 watering_can 才能给作物浇水。"], False)
    planted = [plot for plot in plots(state) if plot.get("crop") and not plot.get("ready")]
    if not planted:
        return (["现在没有需要浇水的作物。"], False)
    for plot in planted:
        plot["watered_today"] = True
        plot["watered_days"] = max(1, int(plot.get("watered_days", 0)))
    return ([f"你给 {len(planted)} 块小菜地浇过水，土色慢慢深了一点。"], True)


def advance_garden_morning(state: dict[str, Any], previous_weather: str) -> list[str]:
    grown = 0
    slowed = 0
    rain_watered = previous_weather == "rain"
    winter_slow = calendar_rules.season(state) == "winter"
    for plot in plots(state):
        if not plot.get("crop") or plot.get("ready"):
            plot["watered_today"] = False
            continue
        if plot.get("watered_today") or rain_watered:
            plot["watered_days"] = int(plot.get("watered_days", 0)) + 1
            if winter_slow and not rain_watered:
                slowed += 1
                plot["watered_today"] = False
                continue
            plot["growth"] = int(plot.get("growth", 0)) + 1
            plot["growth_days"] = int(plot.get("growth_days", 0)) + 1
            grown += 1
            if plot["growth"] >= GROWTH_READY_AT:
                plot["ready"] = True
        plot["watered_today"] = False
    if rain_watered and grown and not state["flags"].get("first_rain_watered_crops"):
        state["flags"]["first_rain_watered_crops"] = True
        add_journal(state, "第一场雨替小菜地浇过水，清晨的土闻起来很新。")
    lines = [f"garden growth +1: {grown} plot(s)"] if grown else []
    if slowed:
        lines.append(f"winter growth slowed: {slowed} plot(s)")
    return lines


def crop_identity(plot: dict[str, Any]) -> str:
    crop = str(plot.get("crop"))
    if crop == "flower" and plot.get("variety"):
        return str(plot["variety"])
    return crop


def season_fit(state: dict[str, Any], crop: str) -> str:
    season_name = calendar_rules.season(state)
    preferred = CROP_PREFERRED_SEASONS.get(crop, set())
    if season_name in preferred:
        return "preferred"
    if crop == "river_forget_me_not" and state.get("weather") == "rain":
        return "rain bonus"
    if crop == "moon_violet" and state.get("weather") == "fog":
        return "weather bonus"
    return "off-season"


def _base_builds(state: dict[str, Any]) -> list[str]:
    base_pos = state.get("base_pos")
    if not base_pos:
        return []
    return list(state.get("builds", {}).get(f"{base_pos[0]},{base_pos[1]}", []))


def _weather_bonus(state: dict[str, Any], crop: str, plot: dict[str, Any]) -> bool:
    if crop == "river_forget_me_not":
        nearby = nearby_terrains(state["seed"], plot.get("pos", state.get("pos", [12, 12])))
        return state.get("weather") == "rain" or "water" in nearby
    if crop == "hearth_marigold":
        return bool({"campfire", "hearth"}.intersection(_base_builds(state)))
    if crop == "moon_violet":
        return state.get("weather") == "fog" or state.get("time_slot") in {"dusk", "night"}
    return False


def quality_for_plot(state: dict[str, Any], plot: dict[str, Any]) -> str:
    crop = crop_identity(plot)
    score = 0
    watered_days = int(plot.get("watered_days", 0))
    if watered_days >= 2:
        score += 2
    elif watered_days == 1:
        score += 1
    if season_fit(state, crop) in {"preferred", "rain bonus", "weather bonus"}:
        score += 1
    if _weather_bonus(state, crop, plot):
        score += 1
    buddy = state.get("companion")
    if buddy and int(buddy.get("comfort", 0)) >= 4:
        score += 1
    if crop in {"berries", "herb"} and score >= 3:
        score -= 1
    if score >= 4:
        return "perfect"
    if score >= 2:
        return "good"
    return "normal"


def quality_item(item: str, quality: str) -> str | None:
    if quality in {"good", "perfect"}:
        return f"{quality}_{item}"
    return None


def rare_yields_for(state: dict[str, Any], item: str, quality: str, plot: dict[str, Any]) -> list[str]:
    rare = RARE_YIELDS.get(item)
    if not rare:
        if calendar_rules.season(state) == "autumn" and quality in {"good", "perfect"}:
            return ["seed_pod"]
        return []
    if item == "foxbell" and quality == "perfect":
        return [rare]
    if item == "foxbell" and quality == "good" and not state["flags"].get("first_high_quality_foxbell"):
        return [rare]
    if item == "dew_daisy" and quality in {"good", "perfect"}:
        return [rare]
    if item == "river_forget_me_not" and quality in {"good", "perfect"} and _weather_bonus(state, item, plot):
        return [rare]
    if item == "hearth_marigold" and quality in {"good", "perfect"} and _weather_bonus(state, item, plot):
        return [rare]
    if item == "moon_violet" and quality in {"good", "perfect"} and _weather_bonus(state, item, plot):
        return [rare]
    return []


def harvest_ready(state: dict[str, Any]) -> tuple[list[str], bool, list[str]]:
    ready = [plot for plot in plots(state) if plot.get("ready") and plot.get("crop")]
    if not ready:
        return (["还没有成熟的作物可以 harvest。"], False, [])
    counter = int(state.get("rng_counter", 0))
    state["rng_counter"] = counter + 1
    gained: dict[str, int] = {}
    quality_counts: dict[str, int] = {}
    rare_gained: dict[str, int] = {}
    harvested_crops: list[str] = []
    for index, plot in enumerate(ready):
        crop = str(plot["crop"])
        variety = plot.get("variety") if crop == "flower" else None
        item = str(variety or crop)
        quality = quality_for_plot(state, plot)
        harvested_crops.append(item)
        add_item_stack(state["inventory"], item, 2)
        if crop in FOOD_CROPS:
            note_food_added(state, crop)
        gained[item] = gained.get(item, 0) + 2
        quality_output = quality_item(item, quality)
        if quality_output:
            add_item_stack(state["inventory"], quality_output, 1)
            if crop in FOOD_CROPS:
                note_food_added(state, quality_output)
            gained[quality_output] = gained.get(quality_output, 0) + 1
        quality_counts[quality] = quality_counts.get(quality, 0) + 1
        rare_yields = rare_yields_for(state, item, quality, plot)
        for rare in rare_yields:
            add_item_stack(state["inventory"], rare, 1)
            gained[rare] = gained.get(rare, 0) + 1
            rare_gained[rare] = rare_gained.get(rare, 0) + 1
        seed = CROP_TO_SEED[crop]
        if deterministic_int(str(state["seed"]), counter + index, f"harvest:{item}:seed", 3) == 0:
            add_item_stack(state["inventory"], seed, 1)
            gained[seed] = gained.get(seed, 0) + 1
        if variety:
            record_flower(state, str(variety), "harvested", quality, rare_yields)
        else:
            _record_crop_log(state, item, "harvested", quality, rare_yields)
        plot.update(
            {
                "crop": None,
                "seed": None,
                "variety": None,
                "color": None,
                "growth": 0,
                "watered_today": False,
                "watered_days": 0,
                "growth_days": 0,
                "planted_day": None,
                "ready": False,
            }
        )
    for crop in harvested_crops:
        flag = f"first_harvest:{crop}"
        if not state["flags"].get(flag):
            state["flags"][flag] = True
            add_journal(state, f"你第一次从小菜地收获 {item_label(crop, include_id=False)}。")
    flower_harvests = [crop for crop in harvested_crops if crop in FLOWER_VARIETY_ITEMS or crop == "flower"]
    for flower in flower_harvests:
        if flower in FLOWER_VARIETIES:
            flag = f"first_harvest_flower:{flower}"
            if not state["flags"].get(flag):
                state["flags"][flag] = True
                if flower == "foxbell":
                    calendar_rules.record_memory_date(state, "first_foxbell_day")
                add_journal(state, FLOWER_VARIETIES[flower]["journal"])
    if "perfect_foxbell" in gained and not state["flags"].get("first_perfect_foxbell"):
        state["flags"]["first_perfect_foxbell"] = True
        add_journal(state, "你第一次收获 perfect foxbell，花色亮得像把家门口照了一下。")
    if rare_gained and not state["flags"].get("first_rare_flower_material"):
        state["flags"]["first_rare_flower_material"] = True
        first_rare = sorted(rare_gained)[0]
        add_journal(state, f"你第一次从花里收出稀有材料：{first_rare}。")
    if any(crop in FOOD_CROPS for crop in harvested_crops) and any(q in quality_counts for q in {"good", "perfect"}):
        add_journal(state, "高品质食材让你想到之后可以做更稳的一顿饭。")
    if flower_harvests and not state["flags"].get("first_flower_softens_home"):
        state["flags"]["first_flower_softens_home"] = True
        add_journal(state, "小屋旁边第一次有了花，这里像是更适合久住了一点。")
    gained_text = item_counts_text(gained)
    best_quality = max(quality_counts, key=lambda item: _quality_rank(item))
    rare_text = ", ".join(f"{item} x{amount}" for item, amount in sorted(rare_gained.items())) if rare_gained else "none"
    return (
        [
            "你把成熟的作物轻轻收进背包。",
            f"获得：{gained_text}",
            f"品质：{best_quality}",
            f"稀有产出：{rare_text}",
        ],
        True,
        harvested_crops,
    )


def garden_lines(state: dict[str, Any]) -> list[str]:
    items = plots(state)
    if not items:
        return ["garden: no plots"]
    lines = ["garden:"]
    for plot in items:
        crop = plot.get("crop")
        if not crop:
            status = "empty"
        else:
            watered = "rain" if state.get("weather") == "rain" and not plot.get("watered_today") else ("yes" if plot.get("watered_today") else "no")
            ready = "yes" if plot.get("ready") else "no"
            display = plot.get("variety") or crop
            color = f", color {plot['color']}" if plot.get("color") else ""
            fit = season_fit(state, str(display))
            status = f"{display} from {plot.get('seed')}{color}, growth {plot.get('growth', 0)}/{GROWTH_READY_AT}, watered {watered}, ready {ready}, season fit {fit}"
        lines.append(f"- plot {plot['id']}: {status} at {plot['pos']}")
    return lines
