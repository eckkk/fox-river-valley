from __future__ import annotations

from pathlib import Path
from typing import Any

from .data import (
    DIFFICULTY_PROFILES,
    FISH_SPECIES_ITEMS,
    FOOD_ITEMS,
    FLOWER_VARIETY_ITEMS,
    MAX_COMPANION_NEED,
    MAX_ENERGY,
    MAX_HUNGER,
    PROCESSED_MATERIAL_ITEMS,
    PROCESS_RECIPES,
    RAW_MATERIAL_ITEMS,
    TOOL_ITEMS,
    TIME_SLOTS,
    item_count_text,
    item_counts_text,
    item_label,
    item_has_tag,
    normalize_item_id,
)
from .rng import deterministic_int
from . import calendar as calendar_rules
from . import companion as companion_rules
from . import exploration
from . import family as family_rules
from . import farming
from . import relationship as relationship_rules
from . import survival
from .state import (
    add_item_stack,
    add_journal,
    can_add_item_stack,
    discover,
    load_state,
    save_state,
)
from .runtime import manual_save_path, runtime_status_lines, save_path, runtime_root
from .world import describe_tile, in_bounds, is_passable, nearby_terrains, terrain_at

DIRECTIONS = {
    "north": [0, -1],
    "east": [1, 0],
    "south": [0, 1],
    "west": [-1, 0],
}


def advance_time(state: dict[str, Any]) -> None:
    state["consecutive_sleep_count"] = 0
    current = TIME_SLOTS.index(state["time_slot"])
    if current == len(TIME_SLOTS) - 1:
        state["time_slot"] = TIME_SLOTS[-1]
    else:
        state["time_slot"] = TIME_SLOTS[current + 1]


def difficulty_profile(state: dict[str, Any]) -> dict[str, Any]:
    return DIFFICULTY_PROFILES[state.get("difficulty", "normal")]


def scaled_yield(state: dict[str, Any], base: int) -> int:
    return max(1, int(base * difficulty_profile(state)["resource_yield"]))


STACK_LIMIT_WARNING = "某些物品已经接近叠加上限。"


def add_inventory(state: dict[str, Any], item: str, amount: int) -> tuple[int, bool]:
    gained = scaled_yield(state, amount)
    added = add_item_stack(state["inventory"], item, gained)
    if added:
        survival.note_food_added(state, item)
    return added, added < gained


def energy_cost(state: dict[str, Any], base: int = 1) -> int:
    cost = base * difficulty_profile(state)["energy_cost"]
    return max(1, int(cost + 0.999))


def spend_energy(state: dict[str, Any], base: int = 1) -> int:
    cost = energy_cost(state, base)
    state["energy"] = max(0, state["energy"] - cost)
    return cost


def need_decay(state: dict[str, Any], key: str) -> int:
    value = difficulty_profile(state)[key]
    return max(1, int(value + 0.999))


def clamp_need(value: int) -> int:
    return max(0, min(MAX_COMPANION_NEED, value))


def status(state: dict[str, Any]) -> list[str]:
    goal = state.get("goal") or "暂无"
    calendar = calendar_rules.ensure_calendar(state)
    companion_rules.refresh_inner_state(state)
    lines = [
        f"第 {state['day']} 天，Year {calendar['year']} {calendar_rules.season_title(str(calendar['season']))} Day {calendar['day_of_season']}，{state['time_slot']}，天气 {state['weather']}，难度 {state.get('difficulty', 'normal')}。",
        f"位置：{describe_tile(state['seed'], state['pos'])}；目标：{goal}。",
        f"HP {state.get('hp')} / hunger {state.get('hunger')} / energy {state.get('energy')}。",
        f"天气影响：{survival.WEATHER_LINES.get(state.get('weather'), '河谷暂时没有特殊天气影响。')}",
        f"家园保暖：{item_label(survival.warmth_protection(state))}；night pressure: {survival.night_pressure(state)}。",
        "你摸了摸背包，确认自己还能继续今天的小河谷生活。",
    ]
    expiring = expiring_food_counts(state, minimum_count=1)
    if expiring:
        foods = " / ".join(item_count_text(item, count) for item, count in expiring.items())
        lines.append(f"即将变质：{foods}。")
    buddy = companion(state)
    if buddy:
        lines.append(f"companion wish: {buddy.get('wish') or 'none'}")
    kit_warning = family_rules.kit_risk_summary(state)
    if kit_warning:
        lines.append(f"kit risk: {kit_warning}")
    return lines


def calendar_status(state: dict[str, Any]) -> list[str]:
    return calendar_rules.calendar_lines(state)


def co_play_recap(state: dict[str, Any]) -> list[str]:
    calendar = calendar_rules.ensure_calendar(state)
    nearby = ", ".join(nearby_terrains(state["seed"], state["pos"]))
    inventory_text = _format_item_counts(state.get("inventory", {}))
    lines = [
        "共同游玩 recap：",
        f"当前状态：Day {state['day']}，Year {calendar['year']} {calendar_rules.season_title(str(calendar['season']))} Day {calendar['day_of_season']}，{state['time_slot']}，天气 {state['weather']}。",
        f"位置：{describe_tile(state['seed'], state['pos'])}；附近：{nearby}。",
        f"背包重点：{inventory_text}。",
    ]
    if state.get("home_name") or state.get("base_pos"):
        lines.append(f"家：{state.get('home_name') or '未命名的家'}；home_level: {state.get('home_level') or 'none'}；base_pos: {state.get('base_pos')}.")
    else:
        lines.append("家：还没有 shelter/base。")
    rel = relationship_rules.compact_relationship(state)
    if rel:
        lines.append(f"关系：{rel['stage']}，bond {rel['bond']}，commitment {rel['commitment']}。")
    family = family_rules.compact_family(state)
    lines.append(f"家庭：kit_status {family['kit_status']}，kit_count {family['kit_count']}。")
    entries = state.get("journal", [])[-3:]
    lines.append("最近日志：")
    if entries:
        lines.extend(f"- Day {entry['day']} {entry['time']}: {entry['text']}" for entry in entries)
    else:
        lines.append("- 暂无。")
    return lines


def co_play_options(state: dict[str, Any]) -> list[str]:
    local = terrain_at(state["seed"], state["pos"])
    nearby = nearby_terrains(state["seed"], state["pos"])
    choices: list[tuple[str, str]] = []
    if not has_shelter(state):
        choices.append(("gather", "补 shelter 材料，先让今晚有地方落脚"))
    elif state.get("energy", 0) <= 2:
        choices.append(("rest", "恢复体力，避免今天走得太硬"))
    else:
        choices.append(("look", "重新确认附近线索"))
    if local == "water" or "water" in nearby:
        choices.append(("fish", "准备食物，也可能为之后的 warm_meal 留材料"))
    else:
        choices.append(("move", "找水声或森林，扩一点已知地图"))
    if state.get("mode") == "family":
        choices.append(("check companion", "看看 Yaya 的状态和 wish"))
    else:
        choices.append(("inventory", "确认背包，再决定下一步"))
    lines = ["可选下一步："]
    for index, (command, reason) in enumerate(choices[:3], start=1):
        lines.append(f"{index}. {command}：{reason}")
    lines.append("共同游玩提示：选 A/B/C，或直接告诉我下一条命令。")
    return lines


def observer_status(state: dict[str, Any]) -> list[str]:
    from .observer import OBSERVER_SERVER_URL, observer_paths

    paths = observer_paths()
    return [
        f"Runtime root: {runtime_root()}",
        f"Observer HTML: {paths['html']}",
        f"Observer state: {paths['state']}",
        f"Live URL: {OBSERVER_SERVER_URL}",
        "启动方式：双击 Start_Fox_River_Valley.bat，或运行 python scripts/run_observer_server.py。",
        "网页里有命令输入框、Run 按钮和常用快捷命令；执行后会写入同一个 save。",
        "如果直接用 file:// 打开，部分浏览器需要手动刷新。",
    ]


def open_observer_hint(state: dict[str, Any]) -> list[str]:
    from .observer import OBSERVER_SERVER_URL, observer_paths

    paths = observer_paths()
    return [
        f"Runtime root: {runtime_root()}",
        f"Observer HTML 已生成：{paths['html']}",
        f"Observer state 已生成：{paths['state']}",
        f"Live URL: {OBSERVER_SERVER_URL}",
        "网页里有命令输入框、Run 按钮和常用快捷命令；执行后会写入同一个 save。",
        "为了保持跨平台稳定，本命令不自动打开浏览器；请运行 Start_Fox_River_Valley.bat 或 python scripts/run_observer_server.py 后打开 URL。",
    ]


def runtime_status(state: dict[str, Any]) -> list[str]:
    return [
        *runtime_status_lines(),
        "Live URL: http://127.0.0.1:8765/observer.html",
        "启动方式：双击 Start_Fox_River_Valley.bat，或运行 python scripts/run_observer_server.py。",
    ]


def inventory(state: dict[str, Any]) -> list[str]:
    items = {key: value for key, value in sorted(state["inventory"].items()) if value > 0}
    if not items:
        return ["背包是空的，只有一点清晨的潮气。"]
    groups = [
        ("food", FOOD_ITEMS),
        ("raw materials", RAW_MATERIAL_ITEMS),
        ("processed materials", PROCESSED_MATERIAL_ITEMS),
        ("tools", TOOL_ITEMS),
    ]
    lines = ["背包里有："]
    grouped_keys: set[str] = set()
    for label, keys in groups:
        found = {key: items[key] for key in sorted(items) if key in keys}
        if found:
            grouped_keys.update(found)
            lines.append(f"{label}: " + _format_item_counts(found))
    other = {key: items[key] for key in sorted(items) if key not in grouped_keys}
    if other:
        lines.append("other: " + _format_item_counts(other))
    return lines


def _format_item_counts(items: dict[str, int]) -> str:
    return item_counts_text(items)


def _format_gained_items(items: dict[str, int]) -> str:
    positive = {key: value for key, value in sorted(items.items()) if value > 0}
    if not positive:
        return "没有能装下的新物品"
    return item_counts_text(positive)


def _with_stack_warning(lines: list[str], clipped: bool) -> list[str]:
    if clipped:
        return [*lines, STACK_LIMIT_WARNING]
    return lines


def _base_key(state: dict[str, Any]) -> str | None:
    base_pos = state.get("base_pos")
    if base_pos is None:
        return None
    return f"{base_pos[0]},{base_pos[1]}"


def _at_base(state: dict[str, Any]) -> bool:
    return state.get("base_pos") is not None and list(state["pos"]) == list(state["base_pos"])


def _base_builds(state: dict[str, Any]) -> list[str]:
    key = _base_key(state)
    if key is None:
        return []
    return state.get("builds", {}).get(key, [])


def _can_use_storage(state: dict[str, Any]) -> tuple[bool, str | None]:
    if not _at_base(state) or "storage_box" not in _base_builds(state):
        return False, "需要在 base 的 storage_box 旁边整理物品。"
    state.setdefault("storage", {})
    return True, None


def storage_summary(state: dict[str, Any]) -> str:
    return _format_item_counts(state.get("storage", {}))


def storage_status(state: dict[str, Any]) -> list[str]:
    ok, error = _can_use_storage(state)
    if not ok:
        return [error or "现在不能使用 storage。"]
    return [f"storage: {storage_summary(state)}"]


def weather_status(state: dict[str, Any]) -> list[str]:
    return survival.weather_lines(state)


def food_status(state: dict[str, Any]) -> list[str]:
    _clear_kit_arrival_focus(state)
    return survival.food_lines(state)


def garden_status(state: dict[str, Any]) -> list[str]:
    return farming.garden_lines(state)


def flower_log(state: dict[str, Any]) -> list[str]:
    return farming.flower_log_lines(state)


def crop_log(state: dict[str, Any]) -> list[str]:
    return farming.crop_log_lines(state)


def fish_log(state: dict[str, Any]) -> list[str]:
    return exploration.fish_log_lines(state)


def findings(state: dict[str, Any]) -> list[str]:
    return exploration.findings_lines(state)


def materials_log(state: dict[str, Any]) -> list[str]:
    return exploration.materials_log_lines(state)


def decor_status(state: dict[str, Any]) -> list[str]:
    return relationship_rules.decor_lines(state)


def _parse_item_count(rest: str) -> tuple[str | None, int | None, str | None]:
    item, _, count_text = rest.strip().partition(" ")
    if not item or not count_text:
        return None, None, "格式：deposit <item> <count> 或 withdraw <item> <count>。"
    try:
        count = int(count_text.strip())
    except ValueError:
        return None, None, "数量必须是整数。"
    if count <= 0:
        return None, None, "数量必须大于 0。"
    return normalize_item_id(item), count, None


def deposit(state: dict[str, Any], rest: str) -> tuple[list[str], bool]:
    ok, error = _can_use_storage(state)
    if not ok:
        return ([error or "现在不能使用 storage。"], False)
    item, count, parse_error = _parse_item_count(rest)
    if parse_error or item is None or count is None:
        return ([parse_error or "格式不对。"], False)
    inventory = state["inventory"]
    if inventory.get(item, 0) < count:
        return ([f"背包里没有足够的 {item_label(item)}。"], False)
    storage = state.setdefault("storage", {})
    if not can_add_item_stack(storage, item, count):
        return ([f"storage 里的 {item_label(item)} 会超过叠加上限。"], False)
    inventory[item] -= count
    add_item_stack(storage, item, count)
    return ([f"存入：{item_count_text(item, count)}", f"storage: {storage_summary(state)}"], True)


def withdraw(state: dict[str, Any], rest: str) -> tuple[list[str], bool]:
    ok, error = _can_use_storage(state)
    if not ok:
        return ([error or "现在不能使用 storage。"], False)
    item, count, parse_error = _parse_item_count(rest)
    if parse_error or item is None or count is None:
        return ([parse_error or "格式不对。"], False)
    storage = state.setdefault("storage", {})
    if storage.get(item, 0) < count:
        return ([f"storage 里没有足够的 {item_label(item)}。"], False)
    if not can_add_item_stack(state["inventory"], item, count):
        return ([f"背包里的 {item_label(item)} 会超过叠加上限。"], False)
    storage[item] -= count
    add_item_stack(state["inventory"], item, count)
    return ([f"取出：{item_count_text(item, count)}", f"storage: {storage_summary(state)}"], True)


def discard(state: dict[str, Any], rest: str) -> tuple[list[str], bool]:
    companion_rules.refresh_inner_state(state)
    inventory = state["inventory"]
    requests, parse_error = _discard_requests(rest, inventory)
    if parse_error:
        return ([parse_error], False)
    if not requests:
        return (["没有需要丢弃的变质食物。"], False)
    removed: dict[str, int] = {}
    for item, count in requests.items():
        available = int(inventory.get(item, 0))
        if available < count:
            return ([f"背包里没有足够的 {item_label(item)}。"], False)
        inventory[item] = available - count
        if inventory[item] <= 0:
            inventory.pop(item, None)
        survival.note_food_removed(state, item)
        removed[item] = removed.get(item, 0) + count
    if set(removed).intersection(survival.STALE_ITEMS) and not state["flags"].get("first_discard_spoiled_food"):
        state["flags"]["first_discard_spoiled_food"] = True
        add_journal(state, "你第一次把变质的食物丢掉，家里空气像清了一点。")
    if set(removed).intersection(survival.STALE_ITEMS):
        companion_rules.complete_wish(state, "discard stale food", reward="comfort")
        companion_rules.refresh_inner_state(state)
    return ([f"丢弃：{item_counts_text(removed)}"], True)


def _discard_requests(rest: str, inventory: dict[str, int]) -> tuple[dict[str, int], str | None]:
    text = " ".join(rest.strip().lower().split())
    if not text:
        return {}, "格式：discard <item> [count|all]；也可以 discard stale food。"
    if text == "stale food":
        stale = {item: int(inventory.get(item, 0)) for item in sorted(survival.STALE_ITEMS) if int(inventory.get(item, 0)) > 0}
        return stale, None
    item_text = text
    count_text: str | None = None
    if " " in text:
        item_text, _, maybe_count = text.rpartition(" ")
        if maybe_count == "all" or maybe_count.isdigit():
            count_text = maybe_count
        else:
            item_text = text
    item = normalize_item_id(item_text)
    if not item:
        return {}, "格式：discard <item> [count|all]；也可以 discard stale food。"
    available = int(inventory.get(item, 0))
    if count_text == "all":
        count = available
    elif count_text is None:
        count = 1
    else:
        count = int(count_text)
    if count <= 0:
        return {}, "数量必须大于 0。"
    return ({item: count}, None)


def look(state: dict[str, Any]) -> list[str]:
    terrain = terrain_at(state["seed"], state["pos"])
    nearby = ", ".join(nearby_terrains(state["seed"], state["pos"]))
    if state.get("weather") == "fog":
        nearby = "雾里只辨得出近处一两处轮廓"
    if terrain == "forest":
        first = "河谷北侧的树影把光切得很碎，脚下有软叶和细枝。"
    elif terrain == "grass":
        first = "狐狸河谷在你身边慢慢醒着，草地潮湿，远处有水声。"
    else:
        first = f"你停在{describe_tile(state['seed'], state['pos'])}边，听见风从河谷里穿过去。"
    return [
        first,
        f"附近线索：{nearby}。",
        "可尝试：map、move north、gather、journal。",
    ]


def map_view(state: dict[str, Any]) -> list[str]:
    px, py = state["pos"]
    discovered = set(state["discovered"])
    rows: list[str] = []
    for y in range(py - 2, py + 3):
        row = []
        for x in range(px - 2, px + 3):
            key = f"{x},{y}"
            if [x, y] == state["pos"]:
                row.append("@")
            elif not in_bounds([x, y]):
                row.append(" ")
            elif key not in discovered:
                row.append("?")
            else:
                row.append(terrain_at(state["seed"], [x, y])[0])
        rows.append("".join(row))
    return ["已发现的小地图：", *rows, "@ 是你现在的位置；? 是还没走过的地方。"]


def move(state: dict[str, Any], direction: str) -> tuple[list[str], bool]:
    if direction not in DIRECTIONS:
        return ([f"你还没决定往哪里走：{direction}。"], False)
    dx, dy = DIRECTIONS[direction]
    target = [state["pos"][0] + dx, state["pos"][1] + dy]
    if not is_passable(state["seed"], target):
        return (["前面过不去。你停下来重新判断路线。"], False)
    state["pos"] = target
    discover(state, target)
    companion_rules.sync_following_position(state)
    advance_time(state)
    return (
        [
            f"你向 {direction} 走去，来到{describe_tile(state['seed'], target)}。",
            "脚印留在身后的湿土里。",
        ],
        True,
    )


def gather(state: dict[str, Any]) -> list[str]:
    terrain = terrain_at(state["seed"], state["pos"])
    nearby = nearby_terrains(state["seed"], state["pos"])
    counter = state["rng_counter"]
    state["rng_counter"] += 1
    gained: dict[str, int] = {}
    clipped = False

    def gain(item: str, amount: int) -> None:
        nonlocal clipped
        amount = survival.adjust_gather_amount(state, item, amount)
        added, was_clipped = add_inventory(state, item, amount)
        gained[item] = gained.get(item, 0) + added
        clipped = clipped or was_clipped

    if terrain == "forest":
        gain("wood", 2 + deterministic_int(state["seed"], counter, "gather:wood", 2))
        gain("branch", 2)
        gain("fiber", 1)
        gain("herb", 1)
        if deterministic_int(state["seed"], counter, "gather:forest:berry_seed", 3) == 0:
            gain("berry_seed", 1)
        if deterministic_int(state["seed"], counter, "gather:forest:herb_seed", 4) == 0:
            gain("herb_seed", 1)
        if deterministic_int(state["seed"], counter, "gather:forest:berries", 2):
            gain("berries", 1)
        if {"hill", "stone", "cave"}.intersection(nearby):
            gain("stone", 3)
    elif terrain in {"hill", "stone", "cave"}:
        gain("stone", 2)
        gain("coal", 1)
        gain("clay", 1)
        if terrain == "cave" or deterministic_int(state["seed"], counter, "gather:iron", 2):
            gain("iron_ore", 1)
        if "water" in nearby:
            gain("sand", 1)
    elif terrain == "ruins":
        gain("stone", 1)
        gain("clay", 1)
        gain("paper", 1)
        if "water" in nearby:
            gain("reed", 1)
    else:
        gain("fiber", 1)
        gain("flower", 1)
        if deterministic_int(state["seed"], counter, "gather:grass:flower_seed", 3) == 0:
            gain("flower_seed", 1)
        if deterministic_int(state["seed"], counter, "gather:grass:herb_seed", 4) == 0:
            gain("herb_seed", 1)
        if deterministic_int(state["seed"], counter, "gather:grass:berry_seed", 5) == 0:
            gain("berry_seed", 1)
        if deterministic_int(state["seed"], counter, "gather:grass:food", 2):
            gain("berries", 1)
        else:
            gain("herb", 1)
        if "water" in nearby:
            gain("reed", 1)
            gain("clay", 1)
        if {"hill", "stone", "cave"}.intersection(nearby):
            gain("stone", 1)
    _apply_seasonal_forage(state, terrain, nearby, counter, gain)
    if terrain == "water" or "water" in nearby:
        hint = "提示：附近有水声，fish 或 reed 可能有用。"
    else:
        hint = "提示：材料开始分层，recipes 可以查下一步。"
    gained_text = _format_gained_items(gained)
    cost = spend_energy(state)
    advance_time(state)
    return _with_stack_warning([
        "你蹲下来翻找能用的东西，指尖沾了一点潮湿的泥。",
        f"获得：{gained_text}",
        f"消耗：energy -{cost}；时间推进到 {state['time_slot']}。",
        hint,
    ], clipped)


def _apply_seasonal_forage(state: dict[str, Any], terrain: str, nearby: list[str], counter: int, gain) -> None:
    season = calendar_rules.season(state)
    if season == "spring":
        if terrain in {"grass", "forest"}:
            gain("flower_seed", 1)
        if deterministic_int(state["seed"], counter, "season:spring:herb_seed", 2) == 0:
            gain("herb_seed", 1)
        if terrain == "water" or "water" in nearby:
            gain("reed", 1)
        if deterministic_int(state["seed"], counter, "season:spring:foxbell", 5) == 0:
            gain("foxbell", 1)
    elif season == "summer":
        if terrain in {"grass", "forest"}:
            gain("berries", 1)
            gain("herb", 1)
        if terrain == "water" or "water" in nearby:
            gain("reed", 1)
            gain("clay", 1)
    elif season == "autumn":
        gain("dry_branch", 1)
        if deterministic_int(state["seed"], counter, "season:autumn:mushroom", 2) == 0:
            gain("mushroom", 1)
        if terrain in {"grass", "forest"}:
            gain("seed_pod", 1)
    elif season == "winter":
        gain("branch", 1)
        if terrain in {"hill", "stone", "cave"} or {"hill", "stone", "cave"}.intersection(nearby):
            gain("stone", 1)
        if deterministic_int(state["seed"], counter, "season:winter:frost_flower_seed", 8) == 0:
            gain("frost_flower_seed", 1)


def chop(state: dict[str, Any]) -> tuple[list[str], bool]:
    terrain = terrain_at(state["seed"], state["pos"])
    if terrain != "forest":
        return (["这里树不够密，暂时没什么好砍的。"], False)
    has_axe = state["inventory"].get("stone_axe", 0) > 0
    wood = scaled_yield(state, 5 if has_axe else 3)
    branch = scaled_yield(state, 2 if has_axe else 1)
    wood_added = add_item_stack(state["inventory"], "wood", wood)
    branch_added = add_item_stack(state["inventory"], "branch", branch)
    clipped = wood_added < wood or branch_added < branch
    cost = spend_energy(state, 1)
    if has_axe and cost > 1:
        state["energy"] = min(MAX_ENERGY, state["energy"] + 1)
        cost -= 1
    advance_time(state)
    return (
        _with_stack_warning([
            "你挑了一棵枯倒的小树，把能用的枝干劈下来。",
            f"获得：{_format_gained_items({'wood': wood_added, 'branch': branch_added})}",
            f"消耗：energy -{cost}；时间推进到 {state['time_slot']}。",
        ], clipped),
        True,
    )


def mine(state: dict[str, Any]) -> tuple[list[str], bool]:
    local = terrain_at(state["seed"], state["pos"])
    nearby = nearby_terrains(state["seed"], state["pos"])
    if local not in {"hill", "stone", "cave"} and not {"hill", "stone", "cave"}.intersection(nearby):
        return (["附近没有明显能挖的石头。"], False)
    counter = state["rng_counter"]
    state["rng_counter"] += 1
    has_pickaxe = state["inventory"].get("stone_pickaxe", 0) > 0
    stone = scaled_yield(state, 3 if has_pickaxe else 2)
    clay = deterministic_int(state["seed"], counter, "mine:clay", 2)
    coal = scaled_yield(state, 1)
    inventory = state["inventory"]
    gained_items: dict[str, int] = {}
    stone_added = add_item_stack(inventory, "stone", stone)
    coal_added = add_item_stack(inventory, "coal", coal)
    gained_items["stone"] = stone_added
    gained_items["coal"] = coal_added
    clipped = stone_added < stone or coal_added < coal
    if clay:
        clay_added = add_item_stack(inventory, "clay", clay)
        gained_items["clay"] = clay_added
        clipped = clipped or clay_added < clay
    iron = 0
    if has_pickaxe:
        iron = 1
        iron_added = add_item_stack(inventory, "iron_ore", iron)
        gained_items["iron_ore"] = iron_added
        clipped = clipped or iron_added < iron
    cost = spend_energy(state)
    advance_time(state)
    gained = f"获得：{_format_gained_items(gained_items)}"
    return (
        _with_stack_warning([
            "你沿着露出的石脊敲了几下，碎石在手心里发凉。",
            gained,
            f"消耗：energy -{cost}；时间推进到 {state['time_slot']}。",
        ], clipped),
        True,
    )


def fish(state: dict[str, Any]) -> tuple[list[str], bool]:
    local = terrain_at(state["seed"], state["pos"])
    nearby = nearby_terrains(state["seed"], state["pos"])
    if local != "water" and "water" not in nearby:
        return (["这里听不见水声，钓不到鱼。"], False)
    has_rod = state["inventory"].get("fishing_rod", 0) > 0
    catches = exploration.fish_catches(state, has_rod=has_rod)
    added = exploration.apply_catches(state, catches)
    state["rng_counter"] += 1
    clipped = any(added.get(item, 0) < amount for item, amount in catches.items())
    cost = spend_energy(state)
    if not state["flags"].get("first_fish"):
        state["flags"]["first_fish"] = True
        add_journal(state, "你钓到第一条鱼，河谷终于开始像一个能养活人的地方。")
    advance_time(state)
    pressure = "夜色让水声更深，night_pressure 也跟着贴近了一点。" if state.get("time_slot") == "night" else ""
    return (
        _with_stack_warning([
            "你在水声最近的地方等了一会儿，线轻轻一沉。",
            f"获得：{_format_gained_items(added)}",
            f"消耗：energy -{cost}；时间推进到 {state['time_slot']}。",
            pressure,
        ], clipped),
        True,
    )


def open_drift_bottle(state: dict[str, Any]) -> tuple[list[str], bool]:
    return exploration.open_drift_bottle(state)


def explore_ruins(state: dict[str, Any]) -> tuple[list[str], bool]:
    lines, ok = exploration.explore_ruins(state)
    if ok:
        cost = spend_energy(state)
        advance_time(state)
        lines.append(f"消耗：energy -{cost}；时间推进到 {state['time_slot']}。")
    return (lines, ok)


def explore(state: dict[str, Any]) -> tuple[list[str], bool]:
    lines, ok = exploration.explore_event(state)
    if ok:
        cost = spend_energy(state)
        advance_time(state)
        lines.append(f"消耗：energy -{cost}；时间推进到 {state['time_slot']}。")
    return (lines, ok)


def plant_seed(state: dict[str, Any], seed: str) -> tuple[list[str], bool]:
    seed = normalize_item_id(seed)
    previous_wish = (companion(state) or {}).get("wish")
    lines, ok, crop = farming.plant_seed(state, seed)
    if not ok:
        return (lines, False)
    if seed == "flower_seed" and not state["flags"].get("first_plant_flower_seed"):
        state["flags"]["first_plant_flower_seed"] = True
        companion_rules.adjust(state, mood=1)
    companion_rules.complete_wish(state, f"plant {seed}", reward="comfort")
    companion_rules.complete_wish(state, "plant food crop", reward="security")
    buddy = companion(state)
    if seed == "flower_seed" and previous_wish == "plant flower_seed" and buddy:
        lines.append(f"{buddy['name']} 认可了这颗花种落进土里。")
    advance_time(state)
    lines.append(f"时间推进到 {state['time_slot']}。")
    return (lines, True)


def water_crops(state: dict[str, Any]) -> tuple[list[str], bool]:
    lines, ok = farming.water_crops(state)
    if ok:
        advance_time(state)
        lines.append(f"时间推进到 {state['time_slot']}。")
    return (lines, ok)


def harvest(state: dict[str, Any]) -> tuple[list[str], bool]:
    lines, ok, crops = farming.harvest_ready(state)
    if not ok:
        return (lines, False)
    flower_items = set(farming.FLOWER_VARIETIES) | {"flower"}
    if any(crop in flower_items for crop in crops):
        companion_rules.adjust(state, comfort=1, mood=1)
    if "foxbell" in crops:
        companion_rules.adjust(state, mood=1)
    if "river_forget_me_not" in crops and "water" in nearby_terrains(state["seed"], state["pos"]):
        companion_rules.adjust(state, comfort=1)
    if "hearth_marigold" in crops and survival.warmth_protection(state) in {"campfire", "hearth"}:
        companion_rules.adjust(state, warmth=1, comfort=1)
    if any(crop in {"berries", "herb"} for crop in crops) and not state["flags"].get("first_harvest_food_crop"):
        state["flags"]["first_harvest_food_crop"] = True
        companion_rules.adjust(state, security=1)
    advance_time(state)
    lines.append(f"时间推进到 {state['time_slot']}。")
    return (lines, True)


def eat(state: dict[str, Any], item: str) -> tuple[list[str], bool]:
    item = normalize_item_id(item)
    food_values = {
        "berries": 1,
        "fish": 2,
        "silver_fish": 2,
        "rain_carp": 2,
        "dusk_eel": 2,
        "river_crab": 1,
        "cooked_fish": 3,
        "warm_meal": 4,
        "stale_fish": 1,
        "stale_food": 1,
        "spoiled_berries": 1,
    }
    if item not in food_values:
        return ([f"{item_label(item)} 现在还不能吃。"], False)
    if state["inventory"].get(item, 0) <= 0:
        return ([f"背包里没有 {item_label(item)}。"], False)
    state["inventory"][item] -= 1
    if state["inventory"][item] <= 0:
        state["inventory"].pop(item, None)
    survival.note_food_removed(state, item)
    state["hunger"] = min(MAX_HUNGER, state["hunger"] + food_values[item])
    if item in survival.STALE_ITEMS:
        companion_rules.adjust(state, mood=-1, trust=-1)
        return ([f"你勉强吃掉了 {item_label(item)}，只能稍微顶一下。", f"hunger +{food_values[item]}；这味道不太适合分享。"], True)
    return ([f"你吃掉了 {item_label(item)}，胃里暖了一点。", f"hunger +{food_values[item]}"], True)


def _has_campfire_access(state: dict[str, Any]) -> bool:
    here = companion_rules.builds_here(state)
    if "campfire" in here or "hearth" in here:
        return True
    base_pos = state.get("base_pos")
    if not base_pos:
        return False
    base_key = f"{base_pos[0]},{base_pos[1]}"
    return bool({"campfire", "hearth"}.intersection(state.get("builds", {}).get(base_key, [])))


def cook_fish(state: dict[str, Any]) -> tuple[list[str], bool]:
    if not _has_campfire_access(state):
        return (["还没有 campfire 或 hearth，做不了 cooked_fish。"], False)
    fish_item = next((item for item in ("fish", "silver_fish", "rain_carp", "dusk_eel", "river_crab") if state["inventory"].get(item, 0) > 0), None)
    if fish_item is None:
        fish_names = ", ".join(sorted(FISH_SPECIES_ITEMS))
        return ([f"背包里没有可烤的鱼。cook fish 可处理：{fish_names}。"], False)
    if not can_add_item_stack(state["inventory"], "cooked_fish", 1):
        return ([f"{item_label('cooked_fish')} 会超过叠加上限，先整理背包或存进 storage。"], False)
    state["inventory"][fish_item] -= 1
    if state["inventory"][fish_item] <= 0:
        state["inventory"].pop(fish_item, None)
    survival.note_food_removed(state, fish_item)
    add_item_stack(state["inventory"], "cooked_fish", 1)
    survival.note_food_added(state, "cooked_fish")
    advance_time(state)
    return ([f"你把 {item_label(fish_item)} 架在火边慢慢烤熟。", f"获得：{item_count_text('cooked_fish', 1)}"], True)


def make_charcoal(state: dict[str, Any]) -> tuple[list[str], bool]:
    if not _has_campfire_access(state):
        return (["还没有 campfire，烧不了 charcoal。"], False)
    if state["inventory"].get("wood", 0) < PROCESS_RECIPES["charcoal"]["cost"]["wood"]:
        return (["材料不够：缺少 wood。"], False)
    if not can_add_item_stack(state["inventory"], "charcoal", 1):
        return (["charcoal 会超过叠加上限，先整理背包或存进 storage。"], False)
    state["inventory"]["wood"] -= 2
    add_item_stack(state["inventory"], "charcoal", 1)
    advance_time(state)
    return (["你把木头压进火里，留出能长期保存的 charcoal。", "获得：charcoal x1"], True)


def make_tea(state: dict[str, Any]) -> tuple[list[str], bool]:
    if not _has_campfire_access(state):
        return (["还没有 campfire 或 hearth，煮不了 herb tea。"], False)
    herb_item = "herb" if state["inventory"].get("herb", 0) > 0 else "dried_herb" if state["inventory"].get("dried_herb", 0) > 0 else None
    if herb_item is None:
        return (["背包里没有 herb 或 dried_herb，煮不了茶。"], False)
    state["inventory"][herb_item] -= 1
    if state["inventory"][herb_item] <= 0:
        state["inventory"].pop(herb_item, None)
    survival.note_food_removed(state, herb_item)
    before_energy = int(state.get("energy", 0))
    state["energy"] = min(MAX_ENERGY, before_energy + 1)
    companion_rules.adjust(state, warmth=1, mood=1)
    advance_time(state)
    if not state["flags"].get("first_make_tea"):
        state["flags"]["first_make_tea"] = True
        add_journal(state, "你第一次用 herb 煮了茶，家里的节奏慢下来一点。")
    lines = [f"你用 {item_label(herb_item)} 煮了一小壶茶，热气带着草叶味慢慢散开。"]
    gained = state["energy"] - before_energy
    if gained:
        lines.append(f"恢复：energy +{gained}")
    buddy = companion(state)
    if buddy:
        lines.append(f"{buddy['name']} warmth +1 / mood +1。")
    return (lines, True)


def rest(state: dict[str, Any]) -> list[str]:
    before = state["energy"]
    state["energy"] = min(MAX_ENERGY, state["energy"] + 2)
    advance_time(state)
    gained = state["energy"] - before
    return [
        "你找了块干一点的地方坐下，让呼吸慢慢稳住。",
        f"恢复：energy +{gained}",
        f"时间推进到 {state['time_slot']}。",
    ]


def wait(state: dict[str, Any]) -> tuple[list[str], bool]:
    _clear_kit_arrival_focus(state)
    before_time = state["time_slot"]
    advance_time(state)
    lines = [f"你停下来等了一会儿，时间从 {before_time} 走到 {state['time_slot']}。"]
    buddy = companion(state)
    if buddy and state["time_slot"] == "night":
        loss = survival.wait_warmth_loss(state)
        if loss:
            companion_rules.adjust(state, warmth=-loss)
            if not survival.at_base(state):
                companion_rules.adjust(state, security=-1)
            lines.append("夜色和天气让身边的人更想靠近一点火光。")
            if not state["flags"].get("first_weather_warmth_pressure"):
                state["flags"]["first_weather_warmth_pressure"] = True
                add_journal(state, "天气第一次真正压低了夜里的暖意。")
    state["night_pressure"] = survival.night_pressure(state)
    return (lines, True)


def companion(state: dict[str, Any]) -> dict[str, Any] | None:
    return state.get("companion")


def check_companion(state: dict[str, Any]) -> list[str]:
    buddy = companion(state)
    if not buddy:
        return ["现在是 solo mode，身边没有 companion。"]
    companion_rules.refresh_inner_state(state)
    profile = buddy["profile"]
    likes = []
    if profile.get("likes_window_table"):
        likes.append("window_table")
    if profile.get("likes_riverside_bench"):
        likes.append("riverside_bench")
    if profile.get("likes_warm_meal"):
        likes.append("warm_meal")
    dislikes = []
    if profile.get("dislikes_cave_at_night"):
        dislikes.append("cave_at_night")
    return [
        f"{buddy['name']} 和你在一起。",
        f"hunger {buddy['hunger']} / warmth {buddy['warmth']} / mood {buddy['mood']} / trust {buddy['trust']} / energy {buddy['energy']} / security {buddy['security']} / comfort {buddy['comfort']}",
        f"thought: {buddy['thought']}",
        f"wish: {buddy['wish'] or 'none'}",
        f"likes: {', '.join(likes) if likes else 'none'}",
        f"dislikes: {', '.join(dislikes) if dislikes else 'none'}",
        f"comfort_priority: {profile.get('comfort_priority', 'medium')}",
    ]


def ask_companion(state: dict[str, Any]) -> list[str]:
    return companion_rules.advice_lines(state)


def debug_companion(state: dict[str, Any]) -> list[str]:
    buddy = companion(state)
    if not buddy:
        return ["现在是 solo mode，没有 companion 可调试。"]
    companion_rules.refresh_inner_state(state)
    profile = buddy["profile"]
    commitment_profile = buddy.get("companion_profile", relationship_rules.build_companion_profile("default"))
    rel = relationship_rules.relationship(state)
    rel_lines = []
    if rel:
        milestones = rel["milestones"]
        rel_lines = [
            "relationship:",
            f"stage: {rel['stage']}",
            f"bond: {rel['bond']}",
            f"commitment: {relationship_rules.commitment_status(rel)}",
            f"affection_score: {relationship_rules.affection_score(state)}",
            "milestones: " + (", ".join(item["id"] for item in milestones) if milestones else "none"),
            "care_today（today only, reset each morning）:",
            "  " + ", ".join(f"{key}={str(value).lower()}" for key, value in rel["care_today"].items()),
            *relationship_rules.stage_eligibility_lines(state),
        ]
    return [
        "companion debug:",
        f"name: {buddy['name']}",
        f"hunger: {buddy['hunger']} / warmth: {buddy['warmth']} / mood: {buddy['mood']} / trust: {buddy['trust']} / energy: {buddy['energy']} / security: {buddy['security']} / comfort: {buddy['comfort']}",
        f"thought: {buddy['thought']}",
        f"wish: {buddy['wish'] or 'none'}",
        f"location: {buddy['location']}",
        f"profile id: {commitment_profile.get('id', 'default')}",
        f"companion_profile: {commitment_profile.get('id', 'default')}",
        f"preferred_commitment_tokens: {relationship_rules.preferred_tokens_line(commitment_profile)}",
        f"favorite_flower: {commitment_profile.get('favorite_flower') or 'none'}",
        f"family_species: {buddy.get('family_species') or 'none'}",
        f"hidden_breed: {commitment_profile.get('hidden_breed') or 'none'}",
        f"likes_window_table: {str(profile.get('likes_window_table', False)).lower()}",
        f"likes_riverside_bench: {str(profile.get('likes_riverside_bench', False)).lower()}",
        f"likes_warm_meal: {str(profile.get('likes_warm_meal', False)).lower()}",
        f"dislikes_cave_at_night: {str(profile.get('dislikes_cave_at_night', False)).lower()}",
        f"comfort_priority: {profile.get('comfort_priority', 'medium')}",
        *rel_lines,
    ]


def family_readiness(state: dict[str, Any]) -> list[str]:
    return family_rules.readiness_lines(state)


def wish_for_kits(state: dict[str, Any]) -> tuple[list[str], bool]:
    return family_rules.wish_for_kits(state)


def check_kits(state: dict[str, Any]) -> list[str]:
    return family_rules.check_kits_lines(state)


def name_kit(state: dict[str, Any], name: str) -> tuple[list[str], bool]:
    return family_rules.name_kit(state, name)


def play_with_kit(state: dict[str, Any]) -> tuple[list[str], bool]:
    return family_rules.play_with_kit(state)


def feed_kit(state: dict[str, Any]) -> tuple[list[str], bool]:
    before = dict(state.get("inventory", {}))
    lines, ok = family_rules.feed_kit(state)
    if ok:
        for item, count in before.items():
            if state.get("inventory", {}).get(item, 0) < count:
                survival.note_food_removed(state, item)
    return (lines, ok)


def debug_family(state: dict[str, Any]) -> list[str]:
    return family_rules.debug_family_lines(state)


def comfort_companion(state: dict[str, Any]) -> tuple[list[str], bool]:
    buddy = companion(state)
    if not buddy:
        return (["现在是 solo mode，没有 companion 需要安抚。"], False)
    companion_rules.adjust(state, security=1, mood=1)
    relationship_rules.mark_comforted(state)
    spend_energy(state)
    advance_time(state)
    if not state["flags"].get("first_comfort_companion"):
        state["flags"]["first_comfort_companion"] = True
        add_journal(state, f"你第一次认真安抚 {buddy['name']}，她像是安心了一点。")
    return ([f"你停下来陪了陪 {buddy['name']}，comfort 不是物品，但河谷里确实安静了一些。"], True)


def sit_with_companion(state: dict[str, Any]) -> tuple[list[str], bool]:
    buddy = companion(state)
    if not buddy:
        return (["现在是 solo mode，没有 companion 可以一起坐下。"], False)
    here = companion_rules.builds_here(state)
    if not {"riverside_bench", "window_table", "simple_shelter"}.intersection(here):
        return (["这里还没有适合一起坐下的地方。"], False)
    companion_rules.adjust(state, comfort=1, mood=1)
    advance_time(state)
    relationship_rules.mark_sit_together(state)
    if not state["flags"].get("first_sit_with_companion"):
        state["flags"]["first_sit_with_companion"] = True
        add_journal(state, f"你和 {buddy['name']} 第一次在河谷里并肩坐了一会儿。")
    return ([f"你和 {buddy['name']} 坐了一会儿，风从小屋或水声那边慢慢经过。"], True)


def make_warm_meal(state: dict[str, Any]) -> tuple[list[str], bool]:
    buddy = companion(state)
    if not _has_campfire_access(state):
        return ([f"还没有 {item_label('campfire')} 或 {item_label('hearth')}，做不了 {item_label('warm_meal')}。"], False)
    if state["inventory"].get("cooked_fish", 0) <= 0:
        return ([f"背包里没有 {item_label('cooked_fish')}，做不了 {item_label('warm_meal')}。"], False)
    if state["inventory"].get("herb", 0) <= 0:
        return (["背包里没有 herb，做不了 warm_meal。"], False)
    if not can_add_item_stack(state["inventory"], "warm_meal", 1):
        return ([f"{item_label('warm_meal')} 会超过叠加上限，先整理背包或存进 storage。"], False)
    state["inventory"]["cooked_fish"] -= 1
    state["inventory"]["herb"] -= 1
    survival.note_food_removed(state, "cooked_fish")
    survival.note_food_removed(state, "herb")
    add_item_stack(state["inventory"], "warm_meal", 1)
    survival.note_food_added(state, "warm_meal")
    advance_time(state)
    lines = [f"你把 {item_label('cooked_fish')} 和 herb 煮成一份 {item_label('warm_meal')}，热气慢慢升起来。"]
    if buddy:
        lines.append(f"可以用 serve warm_meal 和 {buddy['name']} 一起吃。")
    return (lines, True)


def serve_warm_meal(state: dict[str, Any]) -> tuple[list[str], bool]:
    buddy = companion(state)
    if not buddy:
        return ([f"现在没有 companion，serve {item_label('warm_meal')} 没有人可以一起分。"], False)
    if state["inventory"].get("warm_meal", 0) <= 0:
        return ([f"背包里没有 {item_label('warm_meal')}。"], False)
    state["inventory"]["warm_meal"] -= 1
    if state["inventory"]["warm_meal"] <= 0:
        state["inventory"].pop("warm_meal", None)
    survival.note_food_removed(state, "warm_meal")
    state["hunger"] = min(MAX_HUNGER, state["hunger"] + 2)
    companion_rules.adjust(state, hunger=2, warmth=1, mood=1)
    companion_rules.complete_wish(state, "find food", reward="trust")
    companion_rules.complete_wish(state, "find fresh food", reward="trust")
    companion_rules.complete_wish(state, "cook fresh food", reward="comfort")
    companion_rules.complete_wish(state, "make warm meal", reward="comfort")
    relationship_rules.mark_warm_meal(state)
    advance_time(state)
    if not state["flags"].get("first_warm_meal"):
        state["flags"]["first_warm_meal"] = True
        add_journal(state, f"你们一起吃了第一份 warm meal，{buddy['name']} 捧着热气笑了一下。")
    return (
        [
            f"你把 {item_label('warm_meal')} 分给 {buddy['name']}，热气在你们之间慢慢散开。",
            "warm meal 已分享。",
            f"hunger +2；{buddy['name']} hunger +2 / warmth +1 / mood +1",
        ],
        True,
    )


def serve_fresh_food(state: dict[str, Any], item: str) -> tuple[list[str], bool]:
    item = normalize_item_id(item)
    buddy = companion(state)
    if not buddy:
        return (["现在没有 companion，serve 没有人可以一起分。"], False)
    values = {"berries": 1, "cooked_fish": 2}
    if item not in values:
        return ([f"{item_label(item)} 现在不能 serve。可尝试 serve warm_meal、serve cooked_fish 或 serve berries。"], False)
    if state["inventory"].get(item, 0) <= 0:
        return ([f"背包里没有 {item_label(item)}。"], False)
    state["inventory"][item] -= 1
    if state["inventory"][item] <= 0:
        state["inventory"].pop(item, None)
    survival.note_food_removed(state, item)
    state["hunger"] = min(MAX_HUNGER, state["hunger"] + values[item])
    companion_rules.adjust(state, hunger=values[item], mood=1)
    companion_rules.complete_wish(state, "find food", reward="trust")
    companion_rules.complete_wish(state, "find fresh food", reward="trust")
    companion_rules.complete_wish(state, "cook fresh food", reward="comfort")
    relationship_rules.mark_shared_food(state)
    advance_time(state)
    return ([f"你把 {item_label(item)} 分给 {buddy['name']}。", f"hunger +{values[item]}；{buddy['name']} hunger +{values[item]} / mood +1"], True)


def serve_stale_food(state: dict[str, Any], item: str) -> tuple[list[str], bool]:
    item = normalize_item_id(item)
    if not companion(state):
        return (["现在没有 companion，serve 没有人可以一起分。"], False)
    if item not in survival.STALE_ITEMS:
        return ([f"{item_label(item)} 现在不能 serve。"], False)
    if state["inventory"].get(item, 0) <= 0:
        return ([f"背包里没有 {item_label(item)}。"], False)
    return ([f"{item_label(item)} 已经不太新鲜，不适合拿给 companion 吃。"], False)


def share_food(state: dict[str, Any], item: str) -> tuple[list[str], bool]:
    item = normalize_item_id(item)
    buddy = companion(state)
    if not buddy:
        return (["现在没有 companion 可以分享。"], False)
    food_values = {"berries": 1, "fish": 2}
    if item not in food_values:
        return ([f"{item_label(item)} 不适合分享。"], False)
    if state["inventory"].get(item, 0) <= 0:
        return ([f"背包里没有 {item_label(item)}。"], False)
    state["inventory"][item] -= 1
    if state["inventory"][item] <= 0:
        state["inventory"].pop(item, None)
    survival.note_food_removed(state, item)
    buddy["hunger"] = clamp_need(buddy["hunger"] + food_values[item])
    buddy["mood"] = clamp_need(buddy["mood"] + 1)
    companion_rules.complete_wish(state, "find food", reward="trust")
    companion_rules.complete_wish(state, "find fresh food", reward="trust")
    relationship_rules.mark_shared_food(state)
    if not state["flags"].get("first_share_food"):
        state["flags"]["first_share_food"] = True
        add_journal(state, f"第一次分享食物给 {buddy['name']}。")
    return ([f"你把 {item_label(item)} 分给 {buddy['name']}，她的神情松了一点。"], True)


def talk_companion(state: dict[str, Any]) -> tuple[list[str], bool]:
    buddy = companion(state)
    if not buddy:
        return (["现在是 solo mode，你只听见河谷里的风。"], False)
    line = companion_rules.talk_line(state)
    before_mood = buddy["mood"]
    before_trust = buddy["trust"]
    buddy["mood"] = clamp_need(buddy["mood"] + 1)
    buddy["trust"] = clamp_need(buddy["trust"] + 1)
    relationship_rules.mark_talked(state)
    if (buddy["mood"] > before_mood or buddy["trust"] > before_trust) and not state["flags"].get("first_companion_lift"):
        state["flags"]["first_companion_lift"] = True
        add_journal(state, f"{buddy['name']} 的 mood/trust 轻轻往上走了一点。")
    return ([line], True)


def rest_with_companion(state: dict[str, Any]) -> tuple[list[str], bool]:
    buddy = companion(state)
    if not buddy:
        return (["现在没有 companion 和你一起休息。"], False)
    lines = rest(state)
    buddy["energy"] = clamp_need(buddy["energy"] + 2)
    buddy["mood"] = clamp_need(buddy["mood"] + 1)
    lines[0] = f"你和 {buddy['name']} 找了块干一点的地方坐下，让呼吸慢慢稳住。"
    companion_rules.complete_wish(state, "rest together", reward="comfort")
    return (lines, True)


def has_shelter(state: dict[str, Any]) -> bool:
    return state.get("base_pos") is not None or any("simple_shelter" in builds for builds in state.get("builds", {}).values())


def at_base(state: dict[str, Any]) -> bool:
    return state.get("base_pos") is not None and list(state["pos"]) == list(state["base_pos"])


def return_home(state: dict[str, Any]) -> tuple[list[str], bool]:
    base_pos = state.get("base_pos")
    if base_pos is None:
        return (["还没有家。先搭一个 simple_shelter，狐狸河谷里才有能回去的地方。"], False)
    if list(state["pos"]) == list(base_pos):
        companion_rules.sync_following_position(state)
        return (["你已经在 shelter 旁边，家就在脚下。"], True)
    state["pos"] = list(base_pos)
    discover(state, state["pos"])
    companion_rules.sync_following_position(state)
    cost = spend_energy(state)
    advance_time(state)
    if not state["flags"].get("first_return_home"):
        state["flags"]["first_return_home"] = True
        add_journal(state, "你记住了回家的路。")
    return (
        [
            "你沿着记住的脚印往回走，树影慢慢让开。",
            f"回到 shelter；energy -{cost}；时间推进到 {state['time_slot']}。",
        ],
        True,
    )


def sleep(state: dict[str, Any], confirm: bool = False) -> tuple[list[str], bool]:
    _clear_kit_arrival_focus(state)
    if not has_shelter(state):
        return (["还没有庇护所，夜里直接睡下不安全。"], False)
    if not at_base(state):
        return (["家在别处。你得先回到 shelter 才能安心睡下。"], False)
    if state.get("death_mode") == "ai_playtest" and int(state.get("consecutive_sleep_count", 0)) >= 2:
        return (["AI Playtest 禁止跳天等待天气。请先进行有效行动，例如 gather、fish、explore、cook 或处理食物风险。"], False)
    if not confirm:
        warnings = _sleep_warnings(state)
        if warnings:
            return ([*warnings, "如果仍要睡，请输入 sleep confirm。"], False)
    state["consecutive_sleep_count"] = int(state.get("consecutive_sleep_count", 0)) + 1
    night_weather = state.get("weather", "clear")
    protection = survival.warmth_protection(state)
    warmth_loss = survival.sleep_warmth_loss(state, night_weather)
    calendar_rules.advance_day(state)
    state["time_slot"] = "morning"
    state["weather"] = survival.weather_for_day(str(state["seed"]), state["day"])
    farming.advance_garden_morning(state, night_weather)
    spoiled = survival.advance_food_morning(state)
    state["energy"] = MAX_ENERGY
    state["hunger"] = max(0, state["hunger"] - need_decay(state, "hunger_decay"))
    collapse_lines = _apply_player_pressure(state, night_weather, protection)
    buddy = companion(state)
    if buddy:
        loss = need_decay(state, "companion_need_decay")
        buddy["hunger"] = clamp_need(buddy["hunger"] - loss)
        buddy["warmth"] = clamp_need(buddy["warmth"] - warmth_loss)
        if warmth_loss >= 2:
            buddy["security"] = clamp_need(buddy["security"] - 1)
        buddy["energy"] = clamp_need(MAX_COMPANION_NEED)
        if buddy["hunger"] <= 2 or buddy["warmth"] <= 2:
            buddy["mood"] = clamp_need(buddy["mood"] - 1)
            buddy["trust"] = clamp_need(buddy["trust"] - 1)
        if night_weather == "rain" and not state["flags"].get("first_rain_night_at_home"):
            state["flags"]["first_rain_night_at_home"] = True
            add_journal(state, "你们第一次在雨夜里留在家中，听雨落在小棚子外面。")
        if protection == "campfire" and night_weather in {"rain", "cold_wind"} and not state["flags"].get("first_campfire_cold_night"):
            state["flags"]["first_campfire_cold_night"] = True
            add_journal(state, "你们第一次靠 campfire 度过一个发冷的夜晚。")
        if warmth_loss and night_weather in {"rain", "cold_wind"} and not state["flags"].get("first_weather_warmth_pressure"):
            state["flags"]["first_weather_warmth_pressure"] = True
            add_journal(state, "天气第一次真正压低了夜里的暖意。")
        relationship_rules.mark_sleep_at_home(state)
        relationship_rules.reset_care_today(state)
        add_journal(state, _sleep_journal_text(state, buddy["name"], night_weather, protection))
    else:
        add_journal(state, _sleep_journal_text(state, None, night_weather, protection))
    defeat_lines = _resolve_defeat_if_needed(state)
    if defeat_lines:
        return ([*collapse_lines, *defeat_lines], True)
    if spoiled and not state["flags"].get("first_food_spoilage"):
        state["flags"]["first_food_spoilage"] = True
        first = spoiled[0]
        if first["result"] in survival.BENIGN_AGING_RESULTS:
            add_journal(state, f"{first['item']} 慢慢变干，成了 {first['result']}，可以留着泡茶。")
        else:
            add_journal(state, f"{first['item']} 变质成了 {first['result']}，你记住了食物不能一直放着。")
    kit_arrival_lines = family_rules.advance_kit_morning(state)
    state["night_pressure"] = survival.night_pressure(state)
    if kit_arrival_lines:
        return (kit_arrival_lines, True)
    return (
        [
            *collapse_lines,
            _sleep_opening_line(state),
            ("醒来时，你和身边的人在家看见河谷的清晨又铺开了。" if buddy else "醒来时，你在家看见河谷的清晨又铺开了。"),
            "新的一天开始了。",
        ],
        True,
    )


def _sleep_warnings(state: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    player_hunger = int(state.get("hunger", 0))
    if player_hunger == 0:
        warnings.append("最高级警告：你现在 hunger 0，空腹睡下会直接伤到 HP。")
    elif player_hunger <= 2:
        warnings.append(f"你现在 hunger {state['hunger']}，空着肚子睡下可能会让明早更难。")
    buddy = companion(state)
    if buddy:
        buddy_hunger = int(buddy.get("hunger", 0))
        if buddy_hunger == 0:
            warnings.append(f"最高级警告：{buddy['name']} hunger 0，今晚最好先处理食物。")
        elif buddy_hunger <= 2:
            warnings.append(f"{buddy['name']} hunger {buddy['hunger']}，最好先找点能分的食物。")
    family = family_rules.ensure_family_state(state)
    for kit in family.get("kits", []):
        kit_hunger = int(kit.get("hunger", 0))
        if kit_hunger == 0:
            warnings.append("最高级警告：第一只小崽 hunger 0，不能假装没看见就睡。")
            break
        if kit_hunger <= 2:
            warnings.append(f"第一只小崽 hunger {kit['hunger']}，睡前最好确认食物。")
            break
    expiring = expiring_food_counts(state, minimum_count=2, spoilage_only=True)
    if expiring:
        foods = " / ".join(f"{item} x{count}" for item, count in expiring.items())
        warnings.append(f"背包或储物箱里有 {foods} 可能明早变质。")
    return warnings


def _sleep_journal_text(state: dict[str, Any], buddy_name: str | None, night_weather: str, protection: str) -> str:
    calendar = calendar_rules.ensure_calendar(state)
    season = calendar_rules.season_title(str(calendar.get("season", "spring")))
    home_level = state.get("home_level") or "shelter"
    home_label = {
        "shelter": "simple_shelter",
        "little_cabin": "little_cabin",
        "warm_cabin": "warm_cabin",
    }.get(str(home_level), str(home_level))
    weather_phrase = {
        "clear": "晴夜很轻",
        "cloudy": "云层压低了声音",
        "rain": "雨声守在屋外",
        "fog": "雾把河谷放得很近",
        "cold_wind": "冷风被挡在门外",
    }.get(night_weather, f"{night_weather} 从屋外经过")
    protection_phrase = {
        "hearth": "炉火留住了暖意",
        "campfire": "小火堆撑住了夜里的光",
        "none": "小屋本身替你们挡了一夜",
    }.get(protection, "家里的暖意还在")
    if buddy_name:
        return f"你和 {buddy_name} 在家里睡过一夜，醒来时是 {season} 的清晨；{home_label} 里，{weather_phrase}，{protection_phrase}。"
    return f"你在家里睡过一夜，醒来时是 {season} 的清晨；{home_label} 里，{weather_phrase}，{protection_phrase}。"


def expiring_food_counts(state: dict[str, Any], minimum_count: int = 2, spoilage_only: bool = False) -> dict[str, int]:
    survival.sync_food_age(state)
    expiring: dict[str, int] = {}
    inventory = state.get("inventory", {})
    storage = state.get("storage", {})
    for item, age in state.get("food_age", {}).items():
        limit = survival.PERISHABLE_DAYS.get(item)
        if limit is None or int(age) < limit - 1:
            continue
        result = survival.SPOILAGE_RESULTS.get(item)
        if spoilage_only and result in survival.BENIGN_AGING_RESULTS:
            continue
        count = int(inventory.get(item, 0)) + int(storage.get(item, 0))
        if count >= minimum_count:
            expiring[item] = count
    return expiring


def _apply_player_pressure(state: dict[str, Any], night_weather: str, protection: str) -> list[str]:
    lines: list[str] = []
    if int(state.get("hunger", 0)) <= 0:
        state["zero_hunger_days"] = int(state.get("zero_hunger_days", 0)) + 1
        loss = max(1, int(state["zero_hunger_days"]))
        state["hp"] = max(0, int(state.get("hp", 10)) - loss)
        state["energy"] = max(1, min(int(state.get("energy", MAX_ENERGY)), MAX_ENERGY - min(3, int(state["zero_hunger_days"]))))
        lines.append(f"饥饿压住了身体：HP -{loss}。")
    else:
        state["zero_hunger_days"] = 0
    if night_weather == "cold_wind" and protection == "none":
        state["hp"] = max(0, int(state.get("hp", 10)) - 1)
        lines.append("冷风钻过 simple_shelter 的缝，HP -1。")
    return lines


def _resolve_defeat_if_needed(state: dict[str, Any]) -> list[str]:
    if int(state.get("hp", 0)) > 0:
        return []
    mode = state.get("death_mode", "cozy")
    if mode == "cozy":
        _cozy_rescue_home(state)
        return [
            "你在清晨前昏倒了。",
            "有人把你救回家里。狐狸河谷没有结束，但这一天被丢在了身后。",
            "Cozy 模式：HP 回到 3，hunger 回到 2；一些背包物资散在路上。",
        ]
    state["game_over"] = True
    state["hp"] = 0
    return ["Game Over：你没能撑过这个季节。", "只能 restart / load。"]


def _cozy_rescue_home(state: dict[str, Any]) -> None:
    base_pos = state.get("base_pos") or state.get("shelter_pos") or state.get("pos")
    if base_pos:
        state["pos"] = list(base_pos)
        discover(state, state["pos"])
    state["hp"] = 3
    state["hunger"] = 2
    state["energy"] = max(1, min(MAX_ENERGY, int(state.get("energy", 1))))
    state["zero_hunger_days"] = 0
    state["game_over"] = False
    _drop_rescue_inventory(state)
    buddy = companion(state)
    if buddy:
        buddy["mood"] = clamp_need(int(buddy.get("mood", 0)) - 1)
        buddy["trust"] = clamp_need(int(buddy.get("trust", 0)) - 1)
        companion_rules.sync_following_position(state)
    add_journal(state, "你昏倒后被救回家里，醒来时只剩一点力气。")


def _drop_rescue_inventory(state: dict[str, Any]) -> None:
    inventory = state.setdefault("inventory", {})
    for item in sorted(survival.PERISHABLE_DAYS):
        count = int(inventory.get(item, 0))
        if count > 0:
            inventory[item] = max(0, count - max(1, count // 2))
            if inventory[item] <= 0:
                inventory.pop(item, None)
            survival.note_food_removed(state, item)
            break
    for item in ("wood", "fiber", "stone", "branch"):
        count = int(inventory.get(item, 0))
        if count > 0:
            inventory[item] = count - 1
            if inventory[item] <= 0:
                inventory.pop(item, None)
            break


def _sleep_opening_line(state: dict[str, Any]) -> str:
    builds = relationship_rules.base_builds(state)
    if state.get("home_level") == "warm_cabin" and "family_bed" in builds and "hearth" in builds:
        return "你们在家庭床上睡下，炉火的光留在屋角。"
    if state.get("home_level") == "little_cabin":
        return "你们在 little_cabin 里睡下，屋外的河谷慢慢安静。"
    return "你钻进 simple_shelter，听着夜风从枝叶间过去。"


def _clear_kit_arrival_focus(state: dict[str, Any]) -> None:
    state.setdefault("flags", {}).pop("kit_arrival_focus_day", None)


def relationship_status(state: dict[str, Any]) -> list[str]:
    relationship_rules.evaluate_stage(state)
    return relationship_rules.relationship_lines(state)


def _consume_one(state: dict[str, Any], item: str) -> None:
    state["inventory"][item] -= 1
    if state["inventory"][item] <= 0:
        state["inventory"].pop(item, None)
    survival.note_food_removed(state, item)


def _stage_at_least(current: str, required: str) -> bool:
    return relationship_rules.stage_index(current) >= relationship_rules.stage_index(required)


def _commitment_profile(state: dict[str, Any]) -> dict[str, Any]:
    buddy = companion(state)
    if not buddy:
        return relationship_rules.build_companion_profile("default")
    return buddy.get("companion_profile", relationship_rules.build_companion_profile("default"))


def _is_acceptable_commitment_item(state: dict[str, Any], item: str) -> bool:
    profile = _commitment_profile(state)
    return item_has_tag(item, "commitment_token") or relationship_rules.profile_prefers_token(profile, item)


def propose_with(state: dict[str, Any], item: str) -> tuple[list[str], bool]:
    item = item.strip().lower()
    buddy = companion(state)
    rel = relationship_rules.relationship(state)
    if state.get("mode") != "family" or not buddy or not rel:
        return (["现在是 solo mode，不能 propose family commitment。"], False)
    if not item:
        return (["格式：propose with <item>。"], False)
    if rel["stage"] in {"promised_family", "married_family"}:
        return (["已经有家庭承诺，不需要重复 propose。"], False)

    missing: list[str] = []
    if state["inventory"].get(item, 0) <= 0:
        missing.append(f"inventory has {item} x1")
    if not _is_acceptable_commitment_item(state, item):
        missing.append(f"{item} 不是 commitment_token，也不在 companion_profile.preferred_commitment_tokens")
    if not _stage_at_least(rel["stage"], "shared_home"):
        missing.append("relationship stage at least shared_home")
    if rel["bond"] < 10:
        missing.append("bond >= 10")
    if buddy.get("trust", 0) < 7:
        missing.append("trust >= 7")
    if buddy.get("comfort", 0) < 4:
        missing.append("comfort >= 4")
    if buddy.get("security", 0) < 6:
        missing.append("security >= 6")
    if not state.get("home_name"):
        missing.append("home_name 已存在")
    if not relationship_rules.shelter_exists(state):
        missing.append("shelter/base 存在")
    if missing:
        return (["还不能提出家庭承诺。", "缺少条件：", *[f"- {line}" for line in missing]], False)

    _consume_one(state, item)
    rel["stage"] = "promised_family"
    rel["next_stage_hint"] = None
    relationship_rules.add_milestone(state, "first_promise")
    calendar_rules.record_memory_date(state, "first_promise_day")
    add_journal(state, f"你用 {item} 向 {buddy['name']} 提出家庭承诺。")
    if relationship_rules.profile_prefers_token(_commitment_profile(state), item):
        companion_rules.adjust(state, mood=1, trust=1, comfort=1)
    return (
        [
            "SCENE: Promise",
            f"你拿出 {item}，向 {buddy['name']} 提出家庭承诺。",
            f"{buddy['name']} 接受了。",
            "关系阶段更新：promised_family",
            "新增里程碑：first_promise",
            "可尝试：relationship、hold ceremony、journal",
            "家里安静了一下，承诺被认真放下。",
        ],
        True,
    )


def _has_ceremony_ritual_item(state: dict[str, Any]) -> bool:
    inventory = state.get("inventory", {})
    if inventory.get("warm_meal", 0) > 0:
        return True
    if inventory.get("flower", 0) > 0:
        return True
    return any(inventory.get(item, 0) > 0 and item_has_tag(item, "flower") for item in FLOWER_VARIETY_ITEMS)


def hold_ceremony(state: dict[str, Any]) -> tuple[list[str], bool]:
    buddy = companion(state)
    rel = relationship_rules.relationship(state)
    if state.get("mode") != "family" or not buddy or not rel:
        return (["现在是 solo mode，不能 hold ceremony。"], False)

    base_builds = relationship_rules.base_builds(state)
    missing: list[str] = []
    if rel["stage"] != "promised_family":
        missing.append("需要先进入 promised_family")
    if not relationship_rules.shelter_exists(state) or state.get("base_pos") is None:
        missing.append("home/base 存在")
    if not state.get("home_name"):
        missing.append("home_name 已设置")
    if not {"campfire", "hearth"}.intersection(base_builds):
        missing.append("有 campfire 或 hearth")
    if not {"window_table", "riverside_bench"}.intersection(base_builds):
        missing.append("有 window_table 或 riverside_bench")
    if not _has_ceremony_ritual_item(state):
        missing.append("有 warm_meal 或 flower 类物品作为仪式物")
    if missing:
        return (["还不能举行家庭仪式。", "缺少条件：", *[f"- {line}" for line in missing]], False)

    rel["stage"] = "married_family"
    rel["next_stage_hint"] = None
    relationship_rules.add_milestone(state, "first_ceremony")
    calendar_rules.record_memory_date(state, "first_ceremony_day")
    relationship_rules.add_bond(state, 2, "first_ceremony")
    add_journal(state, f"你和 {buddy['name']} 在 {state['home_name']} 完成了第一次家庭仪式。")
    return (
        [
            "SCENE: Ceremony",
            f"你和 {buddy['name']} 在 {state['home_name']} 留下家庭仪式。",
            f"{buddy['name']} 接受了这个家。",
            "关系阶段更新：married_family",
            "新增里程碑：first_ceremony",
            "可尝试：relationship、remember together、journal",
            "火光和桌边的位置都在，家被确认下来。",
        ],
        True,
    )


def remember_together(state: dict[str, Any]) -> list[str]:
    return relationship_rules.remember_lines(state)


def name_home(state: dict[str, Any], name: str) -> tuple[list[str], bool]:
    return relationship_rules.name_home(state, name)


def home_status(state: dict[str, Any]) -> list[str]:
    return relationship_rules.home_lines(state)


def upgrade_home(state: dict[str, Any], target: str) -> tuple[list[str], bool]:
    lines, ok = relationship_rules.upgrade_home(state, target)
    if ok:
        advance_time(state)
        lines.append(f"时间推进到 {state['time_slot']}。")
    return (lines, ok)


def journal(state: dict[str, Any], rest: str) -> list[str]:
    _clear_kit_arrival_focus(state)
    if rest.startswith("add "):
        text = rest[4:].strip()
        if not text:
            return ["日志没有写入：内容是空的。"]
        add_journal(state, text, system=False)
        return [f"你把一句话写进日志：{text}"]

    entries = state["journal"][-5:]
    lines = ["最近日志："]
    for entry in entries:
        lines.append(f"- Day {entry['day']} {entry['time']}: {entry['text']}")
    if state.get("goal"):
        lines.append(f"当前目标：{state['goal']}")
    return lines


def set_goal(state: dict[str, Any], text: str) -> list[str]:
    goal = text.strip()
    if not goal:
        return ["目标没有记录：内容是空的。"]
    state["goal"] = goal
    add_journal(state, f"当前目标：{goal}")
    return [f"雅雅旁边递来一张小纸条：{goal}", "目标已记录，但系统不会自动替你完成。"]


def save_current(state: dict[str, Any], path: Path | None = None) -> list[str]:
    companion_rules.refresh_inner_state(state)
    path = Path(path) if path is not None else save_path()
    save_state(state, path)
    if path == save_path():
        save_state(state, manual_save_path())
    return [f"已保存到 {path}。"]


def load_current(path: Path | None = None) -> tuple[list[str], dict[str, Any]]:
    if path is None:
        manual_path = manual_save_path()
        auto_path = save_path()
        if manual_path.exists() and auto_path.exists():
            path = _choose_load_path(auto_path, manual_path)
        elif manual_path.exists():
            path = manual_path
        else:
            path = auto_path
    else:
        path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    loaded = load_state(path)
    return ([f"已读取 {path}，你回到上次留下脚印的地方。"], loaded)


def _choose_load_path(auto_path: Path, manual_path: Path) -> Path:
    if auto_path.stat().st_mtime <= manual_path.stat().st_mtime:
        return manual_path
    try:
        auto_state = load_state(auto_path)
        manual_state = load_state(manual_path)
    except Exception:
        return manual_path
    if auto_state.get("seed") == manual_state.get("seed"):
        return auto_path
    return manual_path
