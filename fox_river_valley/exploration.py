from __future__ import annotations

from typing import Any

from . import companion as companion_rules
from .data import FINDING_ITEMS, FISH_SPECIES_ITEMS
from .rng import deterministic_int
from .state import add_item_stack, add_journal
from .survival import note_food_added
from .world import nearby_terrains, terrain_at

FISH_FOOD = FISH_SPECIES_ITEMS

BOTTLE_TEXTS = [
    "漂流瓶里的纸条写着：顺着水声走，别急着把夜色当成敌人。",
    "漂流瓶里的纸条已经泛黄：河谷会记得慢慢搭起来的家。",
    "漂流瓶里夹着一小片干草：有人曾在雨后从这里经过。",
]

BOTTLE_REWARDS = ("paper", "reed", "map_fragment", "small_charm", "river_glass")

HIDDEN_MATERIALS = {
    "river_glass": {
        "source": "rain by water / drift_bottle",
        "future": "window glass or small decoration",
        "journal": "你第一次捡到 river_glass，像雨把水边旧光磨亮了一点。",
    },
    "old_tile": {
        "source": "ruins",
        "future": "floor or hearth decoration",
        "journal": "你第一次从 ruins 里取出 old_tile，旧纹路还留着一点温度。",
    },
    "moss_thread": {
        "source": "foggy forest / ruins / rainy forest edge",
        "future": "rug, cushion, or soft bedding",
        "journal": "你第一次收起 moss_thread，它细得像雾里抽出的线。",
    },
    "weathered_wood": {
        "source": "abandoned_camp / rainy river edge",
        "future": "advanced furniture",
        "journal": "你第一次从旧营地收集 weathered_wood，木纹被风雨磨得很稳。",
    },
    "moon_shard": {
        "source": "rare dusk or night ruins / fog",
        "future": "moon_violet decoration",
        "journal": "你第一次发现 moon_shard，Yaya 看了很久。",
    },
    "river_clay": {
        "source": "muddy_bank / water edge",
        "future": "pots or ceramics",
        "journal": "你第一次挖到 river_clay，泥色比普通 clay 更细。",
    },
}

HIDDEN_MATERIAL_ITEMS = set(HIDDEN_MATERIALS)


def _record_fish_log(state: dict[str, Any], item: str, amount: int) -> None:
    if item not in FISH_FOOD or amount <= 0:
        return
    log = state.setdefault("fish_log", {})
    log[item] = int(log.get(item, 0)) + amount


def record_finding(state: dict[str, Any], item: str, amount: int = 1) -> None:
    if item not in FINDING_ITEMS or amount <= 0:
        return
    log = state.setdefault("findings_log", {})
    log[item] = int(log.get(item, 0)) + amount


def _format_items(items: dict[str, int]) -> str:
    found = {item: count for item, count in sorted(items.items()) if count > 0}
    if not found:
        return "none"
    return ", ".join(f"{item} x{count}" for item, count in found.items())


def _add_item(state: dict[str, Any], item: str, amount: int) -> int:
    added = add_item_stack(state["inventory"], item, amount)
    if added and item in FISH_FOOD:
        note_food_added(state, item)
    if added and item in FISH_FOOD:
        _record_fish_log(state, item, added)
    if added and item in FINDING_ITEMS:
        record_finding(state, item, added)
    return added


def add_hidden_material(state: dict[str, Any], item: str, amount: int, lines: list[str]) -> int:
    if item not in HIDDEN_MATERIAL_ITEMS:
        return 0
    before = int(state.get("inventory", {}).get(item, 0))
    added = add_item_stack(state["inventory"], item, amount)
    if not added:
        return 0
    record_finding(state, item, added)
    first_flag = f"first_hidden_material:{item}"
    if before == 0 and not state["flags"].get(first_flag):
        state["flags"][first_flag] = True
        add_journal(state, str(HIDDEN_MATERIALS[item]["journal"]))
        buddy = companion_rules.companion(state)
        if buddy:
            if item == "moon_shard":
                lines.append(f"{buddy['name']} 看着 moon_shard 很久，没有急着说话。")
            else:
                companion_rules.adjust(state, mood=1)
    return added


def add_map_fragment(state: dict[str, Any], amount: int, lines: list[str]) -> None:
    before = int(state["inventory"].get("map_fragment", 0))
    added = add_item_stack(state["inventory"], "map_fragment", amount)
    after = before + added
    if added:
        record_finding(state, "map_fragment", added)
    if added and after >= 3 and not state["flags"].get("map_fragment_hint"):
        state["flags"]["map_fragment_hint"] = True
        hint = "你拼出了一小段河谷旧路的线索。"
        lines.append(hint)
        add_journal(state, hint)


def fish_catches(state: dict[str, Any], *, has_rod: bool) -> dict[str, int]:
    weather = state.get("weather", "clear")
    time_slot = state.get("time_slot", "morning")
    counter = int(state.get("rng_counter", 0))

    main = "fish"
    if weather == "rain":
        main = "rain_carp"
    elif time_slot in {"dusk", "night"}:
        main = "dusk_eel"
    elif weather == "clear" and time_slot in {"morning", "late_morning"}:
        if deterministic_int(str(state["seed"]), counter, "fish:main_clear", 2) == 0:
            main = "silver_fish"

    catches: dict[str, int] = {main: 1}
    bonus_added = False
    if weather == "rain" and deterministic_int(str(state["seed"]), counter, "fish:rain:bonus", 3) == 0:
        catches["fish"] = catches.get("fish", 0) + 1
        bonus_added = True
    if has_rod and not bonus_added and deterministic_int(str(state["seed"]), counter, "fish:rod:extra", 5) == 0:
        catches["fish"] = catches.get("fish", 0) + 1
        bonus_added = True
    if not bonus_added and deterministic_int(str(state["seed"]), counter, "fish:crab", 16) == 0:
        catches["river_crab"] = catches.get("river_crab", 0) + 1

    rare_roll = deterministic_int(str(state["seed"]), counter, "fish:rare_finding", 23)
    if rare_roll == 0:
        catches["old_boot"] = 1
    elif rare_roll in {1, 8}:
        catches["drift_bottle"] = 1
    return catches


def apply_catches(state: dict[str, Any], catches: dict[str, int]) -> dict[str, int]:
    added: dict[str, int] = {}
    for item, amount in catches.items():
        got = _add_item(state, item, amount)
        if got:
            added[item] = got
    return added


def fish_log_lines(state: dict[str, Any]) -> list[str]:
    log = {
        key: value
        for key, value in sorted(state.get("fish_log", {}).items())
        if key in FISH_FOOD and value > 0
    }
    if not log:
        return ["fish log: empty"]
    return ["fish log:", *[f"- {item} x{count}" for item, count in log.items()]]


def findings_lines(state: dict[str, Any]) -> list[str]:
    log = {
        key: value
        for key, value in sorted(state.get("findings_log", {}).items())
        if key in FINDING_ITEMS and value > 0
    }
    if not log:
        return ["findings: empty"]
    return ["findings:", *[f"- {item} x{count}" for item, count in log.items()]]


def materials_log_lines(state: dict[str, Any]) -> list[str]:
    log = {
        key: value
        for key, value in sorted(state.get("findings_log", {}).items())
        if key in HIDDEN_MATERIAL_ITEMS and value > 0
    }
    if not log:
        return ["materials log: empty"]
    lines = ["materials log:"]
    for item, count in log.items():
        details = HIDDEN_MATERIALS[item]
        lines.append(f"- {item} x{count}: source {details['source']}; future use {details['future']}")
    return lines


def open_drift_bottle(state: dict[str, Any]) -> tuple[list[str], bool]:
    if state["inventory"].get("drift_bottle", 0) <= 0:
        return (["背包里没有 drift_bottle。"], False)
    counter = int(state.get("rng_counter", 0))
    text = BOTTLE_TEXTS[deterministic_int(str(state["seed"]), counter, "drift_bottle:text", len(BOTTLE_TEXTS))]
    reward = BOTTLE_REWARDS[deterministic_int(str(state["seed"]), counter, "drift_bottle:reward", len(BOTTLE_REWARDS))]
    state["inventory"]["drift_bottle"] -= 1
    if state["inventory"]["drift_bottle"] <= 0:
        state["inventory"].pop("drift_bottle", None)
    state["rng_counter"] = counter + 1
    lines = [text]
    if reward == "map_fragment":
        add_map_fragment(state, 1, lines)
    elif reward in HIDDEN_MATERIAL_ITEMS:
        add_hidden_material(state, reward, 1, lines)
    else:
        add_item_stack(state["inventory"], reward, 1)
        record_finding(state, reward)
    lines.append(f"获得：{reward} x1")
    if not state["flags"].get("first_drift_bottle"):
        state["flags"]["first_drift_bottle"] = True
        add_journal(state, "你们第一次打开 drift_bottle，水声像把远处的一句话送来了。")
    return (lines, True)


def has_ruins_nearby(state: dict[str, Any]) -> bool:
    return terrain_at(state["seed"], state["pos"]) == "ruins" or "ruins" in nearby_terrains(state["seed"], state["pos"])


def explore_ruins(state: dict[str, Any]) -> tuple[list[str], bool]:
    if not has_ruins_nearby(state):
        return (["附近没有遗迹可以探索。"], False)
    counter = int(state.get("rng_counter", 0))
    state["rng_counter"] = counter + 1
    terrain = terrain_at(state["seed"], state["pos"])
    lines = ["你拨开碎石和草根，遗迹的边缘露出一点旧纹路。"]
    hidden: dict[str, int] = {}

    def hidden_gain(item: str, amount: int = 1) -> None:
        added = add_hidden_material(state, item, amount, lines)
        if added:
            hidden[item] = hidden.get(item, 0) + added

    add_item_stack(state["inventory"], "stone", 1)
    add_item_stack(state["inventory"], "clay", 1)
    add_map_fragment(state, 1, lines)
    hidden_gain("old_tile")
    if state.get("time_slot") in {"dusk", "night"} and (
        state.get("weather") == "fog" or terrain == "ruins" or "ruins" in nearby_terrains(state["seed"], state["pos"])
    ):
        if deterministic_int(str(state["seed"]), counter, "ruins:moon_shard", 19) == 0:
            hidden_gain("moon_shard")
    if state.get("weather") == "fog" and deterministic_int(str(state["seed"]), counter, "ruins:moss_thread", 2) == 0:
        hidden_gain("moss_thread")
    if deterministic_int(str(state["seed"]), counter, "ruins:paper", 2) == 0:
        add_item_stack(state["inventory"], "paper", 1)
    if deterministic_int(str(state["seed"]), counter, "ruins:coin", 3) == 0:
        add_item_stack(state["inventory"], "old_coin", 1)
        record_finding(state, "old_coin")
    if deterministic_int(str(state["seed"]), counter, "ruins:tile", 4) == 0:
        add_item_stack(state["inventory"], "cracked_tile", 1)
        record_finding(state, "cracked_tile")
    if deterministic_int(str(state["seed"]), counter, "ruins:herb", 5) == 0:
        add_item_stack(state["inventory"], "herb", 1)
        note_food_added(state, "herb")
    if not state["flags"].get("first_ruins_found"):
        state["flags"]["first_ruins_found"] = True
        add_journal(state, "你第一次发现 ruins，河谷像露出一块旧骨头。")
    if not state["flags"].get("first_ruins_explore"):
        state["flags"]["first_ruins_explore"] = True
        add_journal(state, "你第一次认真 explore ruins，没有找到答案，但找到了一点旧路的线索。")
    buddy = companion_rules.companion(state)
    if buddy:
        if state.get("time_slot") in {"dusk", "night"}:
            companion_rules.adjust(state, security=-1)
            lines.append(f"{buddy['name']} 在遗迹边停得更近了一点。")
        else:
            companion_rules.adjust(state, trust=1)
    lines.append("获得：stone x1, clay x1, map_fragment x1")
    if hidden:
        lines.append(f"隐藏材料：{_format_items(hidden)}")
    if terrain != "ruins":
        lines.append("提示：真正的 ruins 就在附近。")
    return (lines, True)


def explore_event(state: dict[str, Any]) -> tuple[list[str], bool]:
    weather = state.get("weather", "clear")
    counter = int(state.get("rng_counter", 0))
    state["rng_counter"] = counter + 1
    terrain = terrain_at(state["seed"], state["pos"])
    nearby = nearby_terrains(state["seed"], state["pos"])
    water_nearby = terrain == "water" or "water" in nearby
    ruins_nearby = terrain == "ruins" or "ruins" in nearby
    forest_nearby = terrain == "forest" or "forest" in nearby
    tile = f"{state['pos'][0]},{state['pos'][1]}"
    explore_memory = state.setdefault("flags", {}).setdefault("explore_memory", {})
    if not isinstance(explore_memory, dict):
        explore_memory = {}
        state["flags"]["explore_memory"] = explore_memory
    tile_memory = explore_memory.setdefault(tile, {"count": 0, "recent": []})
    if not isinstance(tile_memory, dict):
        tile_memory = {"count": 0, "recent": []}
        explore_memory[tile] = tile_memory
    tile_memory["count"] = int(tile_memory.get("count", 0)) + 1

    def hidden_bad_weather_lines() -> tuple[list[str], bool] | None:
        hidden: dict[str, int] = {}
        lines = ["天气让路变得含糊，你绕了一小圈，只带回一点湿气。"]

        def hidden_gain(item: str, amount: int = 1) -> None:
            added = add_hidden_material(state, item, amount, lines)
            if added:
                hidden[item] = hidden.get(item, 0) + added

        if weather == "rain" and water_nearby:
            hidden_gain("river_glass")
            hidden_gain("river_clay")
            if deterministic_int(str(state["seed"]), counter, "explore:rain:weathered_wood", 3) == 0:
                hidden_gain("weathered_wood")
        if weather == "rain" and forest_nearby:
            if deterministic_int(str(state["seed"]), counter, "explore:rain:moss_thread", 3) == 0:
                hidden_gain("moss_thread")
        if weather == "fog" and (forest_nearby or ruins_nearby):
            hidden_gain("moss_thread")
        if weather == "fog" and state.get("time_slot") in {"dusk", "night"} and ruins_nearby:
            if deterministic_int(str(state["seed"]), counter, "explore:fog:moon_shard", 23) == 0:
                hidden_gain("moon_shard")
        if hidden:
            lines.append(f"隐藏材料：{_format_items(hidden)}")
            return (lines, True)
        return None

    if weather in {"rain", "fog"}:
        weather_result = hidden_bad_weather_lines()
        if weather_result:
            return weather_result
        return (["天气让路变得含糊，你绕了一小圈，只带回一点湿气。"], True)
    if tile_memory["count"] >= 4:
        return (["这里刚刚已经找过了，也许换个方向，或者明天再来会更有发现。"], True)
    candidates = [
        "fox_tracks",
        "herb_patch",
        "quiet_view",
        "smooth_stone",
        "bird_call",
        "old_path_marker",
        "flower_glimpse",
        "windfall_branch",
    ]
    if terrain == "forest" or "forest" in nearby:
        candidates.extend(["abandoned_camp", "mossy_root", "fallen_nest"])
    if terrain == "water" or "water" in nearby:
        candidates.extend(["muddy_bank", "reed_shelter", "river_light"])
    if terrain == "ruins" or "ruins" in nearby:
        candidates.extend(["ruins_edge", "old_tile_hint"])
    season = str(state.get("calendar", {}).get("season", "spring"))
    if season == "spring":
        candidates.extend(["spring_seed", "spring_foxbell_trace"])
    elif season == "summer":
        candidates.extend(["summer_berries", "warm_reedbed"])
    elif season == "autumn":
        candidates.extend(["autumn_seed_pod", "dry_branch_cache"])
    elif season == "winter":
        candidates.extend(["winter_tracks", "frost_flower_trace"])
    recent = [item for item in tile_memory.get("recent", []) if item in candidates]
    available = [item for item in candidates if item not in recent] or candidates
    event = available[deterministic_int(str(state["seed"]), counter, "explore:event", len(available))]
    tile_memory["recent"] = ([event] + recent)[:4]
    if event == "fox_tracks":
        if not state["flags"].get("first_fox_tracks"):
            state["flags"]["first_fox_tracks"] = True
            add_journal(state, "你第一次看见 fox tracks，脚印细细地绕过草丛。")
        return (["你在泥地边发现一串 fox tracks，它们很快消失在草里。"], True)
    if event == "abandoned_camp":
        hidden: dict[str, int] = {}
        add_item_stack(state["inventory"], "branch", 1)
        add_item_stack(state["inventory"], "charcoal", 1)
        weathered = add_hidden_material(state, "weathered_wood", 1, [])
        if weathered:
            hidden["weathered_wood"] = weathered
        if deterministic_int(str(state["seed"]), counter, "explore:camp:fragment", 2) == 0:
            lines = ["你找到一个很旧的 abandoned camp，灰里还埋着能用的东西。"]
            add_map_fragment(state, 1, lines)
            lines.append("获得：branch x1, charcoal x1, map_fragment x1")
            if hidden:
                lines.append(f"隐藏材料：{_format_items(hidden)}")
            return (lines, True)
        lines = ["你找到一个很旧的 abandoned camp，收起还能用的 branch 和 charcoal。", "获得：branch x1, charcoal x1"]
        if hidden:
            lines.append(f"隐藏材料：{_format_items(hidden)}")
        return (lines, True)
    if event == "herb_patch":
        add_item_stack(state["inventory"], "herb", 1)
        add_item_stack(state["inventory"], "flower", 1)
        if deterministic_int(str(state["seed"]), counter, "explore:herb_patch:herb_seed", 2) == 0:
            add_item_stack(state["inventory"], "herb_seed", 1)
        if deterministic_int(str(state["seed"]), counter, "explore:herb_patch:flower_seed", 3) == 0:
            add_item_stack(state["inventory"], "flower_seed", 1)
        note_food_added(state, "herb")
        return (["你在草根边发现一小片 herb patch。", "获得：herb x1, flower x1，也可能夹着能种下的 seed。"], True)
    if event == "smooth_stone":
        add_item_stack(state["inventory"], "stone", 1)
        return (["你在草根下摸到一块被水磨圆的 stone。", "获得：stone x1"], True)
    if event == "bird_call":
        companion_rules.adjust(state, mood=1)
        return (["远处有鸟声落下来，你们停了一小会儿，心情也松了一点。"], True)
    if event == "old_path_marker":
        add_map_fragment(state, 1, [])
        return (["你找到一截旧路标，方向已经模糊，但还能拼进河谷的线索里。", "获得：map_fragment x1"], True)
    if event == "flower_glimpse":
        add_item_stack(state["inventory"], "flower", 1)
        return (["草丛里有一点颜色晃了一下，你摘下一朵普通的小花。", "获得：flower x1"], True)
    if event == "windfall_branch":
        add_item_stack(state["inventory"], "branch", 2)
        return (["树影边落着几根刚断下来的 branch，像是风替你先收过一遍。", "获得：branch x2"], True)
    if event == "mossy_root":
        add_item_stack(state["inventory"], "fiber", 1)
        hidden: dict[str, int] = {}
        if deterministic_int(str(state["seed"]), counter, "explore:mossy_root:moss_thread", 4) == 0:
            added = add_hidden_material(state, "moss_thread", 1, [])
            if added:
                hidden["moss_thread"] = added
        lines = ["树根上覆着一点软苔，你只取走不会伤到它的一小缕。", "获得：fiber x1"]
        if hidden:
            lines.append(f"隐藏材料：{_format_items(hidden)}")
        return (lines, True)
    if event == "fallen_nest":
        add_item_stack(state["inventory"], "fiber", 1)
        add_item_stack(state["inventory"], "dry_branch", 1)
        return (["你在树下发现一个已经空掉的旧巢，只收起散落的软草和干枝。", "获得：fiber x1, dry_branch x1"], True)
    if event == "muddy_bank":
        add_item_stack(state["inventory"], "clay", 1)
        add_item_stack(state["inventory"], "reed", 1)
        hidden: dict[str, int] = {}
        added = add_hidden_material(state, "river_clay", 1, [])
        if added:
            hidden["river_clay"] = added
        lines = ["水边有一处 muddy bank，泥里夹着能用的 reed。", "获得：clay x1, reed x1"]
        if hidden:
            lines.append(f"隐藏材料：{_format_items(hidden)}")
        return (lines, True)
    if event == "reed_shelter":
        add_item_stack(state["inventory"], "reed", 2)
        return (["水边的 reed 长得很密，你折下几根还能用的。", "获得：reed x2"], True)
    if event == "river_light":
        hidden: dict[str, int] = {}
        if deterministic_int(str(state["seed"]), counter, "explore:river_light:glass", 3) == 0:
            added = add_hidden_material(state, "river_glass", 1, [])
            if added:
                hidden["river_glass"] = added
        lines = ["水面亮了一下，你蹲下来找了找，只带回一点河岸的湿光。"]
        if hidden:
            lines.append(f"隐藏材料：{_format_items(hidden)}")
        return (lines, True)
    if event == "ruins_edge":
        return explore_ruins(state)
    if event == "old_tile_hint":
        lines: list[str] = ["草下露出一角旧砖纹，你没有深挖，只记住了遗迹的方向。"]
        add_hidden_material(state, "old_tile", 1, lines)
        return (lines, True)
    if event == "spring_seed":
        add_item_stack(state["inventory"], "herb_seed", 1)
        return (["春天的草根边藏着一点能种下的 seed。", "获得：herb_seed x1"], True)
    if event == "spring_foxbell_trace":
        add_item_stack(state["inventory"], "flower_seed", 1)
        return (["你看到一小串像狐铃花的叶影，但花还没开，只留下 seed。", "获得：flower_seed x1"], True)
    if event == "summer_berries":
        add_item_stack(state["inventory"], "berries", 1)
        note_food_added(state, "berries")
        return (["夏天的灌木上还有几颗 berries，被叶子遮得很好。", "获得：berries x1"], True)
    if event == "warm_reedbed":
        add_item_stack(state["inventory"], "reed", 1)
        add_item_stack(state["inventory"], "flower", 1)
        return (["热一点的风穿过 reedbed，你找到几根干爽的 reed 和一朵小花。", "获得：reed x1, flower x1"], True)
    if event == "autumn_seed_pod":
        add_item_stack(state["inventory"], "seed_pod", 1)
        return (["秋天把一只 seed_pod 留在草间，晃起来有很轻的声响。", "获得：seed_pod x1"], True)
    if event == "dry_branch_cache":
        add_item_stack(state["inventory"], "dry_branch", 2)
        return (["落叶底下压着几根 dry_branch，正适合留作之后的火。", "获得：dry_branch x2"], True)
    if event == "winter_tracks":
        add_item_stack(state["inventory"], "branch", 1)
        return (["冬天的地面留下浅浅脚印，你顺着看了一会儿，只捡到一根 branch。", "获得：branch x1"], True)
    if event == "frost_flower_trace":
        add_item_stack(state["inventory"], "frost_flower_seed", 1)
        return (["霜边有一点像花籽的东西，很轻，像不该被风带走。", "获得：frost_flower_seed x1"], True)
    companion_rules.adjust(state, mood=1, comfort=1)
    if not state["flags"].get("first_quiet_view"):
        state["flags"]["first_quiet_view"] = True
        add_journal(state, "你们第一次在河谷里停下来看 quiet view。")
    return (["你们在一处 quiet view 前停了停，风把远处的水声带过来。"], True)
