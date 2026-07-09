from __future__ import annotations

from typing import Any

from .actions import advance_time
from .data import (
    BUILD_COSTS,
    BUILD_STATIONS,
    CRAFT_STATIONS,
    PROCESS_RECIPES,
    RECIPES,
    item_count_text,
    item_label,
    normalize_item_id,
)
from .state import add_item_stack, can_add_item_stack


def _all_builds(state: dict[str, Any]) -> list[str]:
    return [item for builds in state.get("builds", {}).values() for item in builds]


def _has_station(state: dict[str, Any], station: str | None) -> bool:
    if not station:
        return True
    return station in _all_builds(state)


def _base_builds(state: dict[str, Any]) -> list[str]:
    base_pos = state.get("base_pos")
    if base_pos is None:
        return []
    key = f"{base_pos[0]},{base_pos[1]}"
    return state.get("builds", {}).get(key, [])


def _at_base(state: dict[str, Any]) -> bool:
    return state.get("base_pos") is not None and list(state["pos"]) == list(state["base_pos"])


def _has_workbench_access(state: dict[str, Any]) -> bool:
    return _at_base(state) and "workbench" in _base_builds(state)


def _recipe_options(item: str) -> list[dict[str, Any]]:
    recipe = RECIPES[item]
    if isinstance(recipe, list):
        return recipe
    return [recipe]


def _format_cost(cost: dict[str, int]) -> str:
    return ", ".join(item_count_text(name, amount) for name, amount in cost.items())


def _choose_recipe(state: dict[str, Any], item: str) -> tuple[dict[str, Any] | None, list[str], str | None]:
    inventory = state["inventory"]
    blocked_station = None
    first_missing: list[str] = []
    for recipe in _recipe_options(item):
        station = recipe.get("station")
        if not _has_station(state, station):
            blocked_station = station
            continue
        cost = recipe["cost"]
        missing = [
            material
            for material, amount in cost.items()
            if inventory.get(material, 0) < amount
        ]
        if not missing:
            return recipe, [], None
        if not first_missing:
            first_missing = missing
    return None, first_missing, blocked_station


def craft(state: dict[str, Any], item: str) -> tuple[list[str], bool]:
    requested = " ".join(str(item).strip().lower().replace("_", " ").split())
    item = normalize_item_id(item)
    if item not in RECIPES:
        return ([f"现在还不会制作 {item_label(item)}。"], False)
    if CRAFT_STATIONS.get(item) == "workbench" and not _has_workbench_access(state):
        return (["需要在 workbench 旁边做这个。"], False)
    recipe, missing, blocked_station = _choose_recipe(state, item)
    if recipe is None and blocked_station:
        return ([f"还没有 {item_label(blocked_station)}，暂时做不了 {item_label(item)}。"], False)
    if recipe is None:
        return ([f"材料不够：缺少 {', '.join(item_label(name) for name in missing)}。"], False)
    inventory = state["inventory"]
    output = int(recipe.get("output", 1))
    if not can_add_item_stack(inventory, item, output):
        return ([f"{item_label(item)} 会超过叠加上限，先整理背包或存进 storage。"], False)
    for material, amount in recipe["cost"].items():
        inventory[material] -= amount
    add_item_stack(inventory, item, output)
    advance_time(state)
    if item == "stone_axe":
        if requested == "basic axe":
            text = "你把石片绑在木柄上，做出一把 basic_axe；它会作为 stone_axe 使用，砍树终于不全靠手。"
        else:
            text = "你把石片绑在木柄上，做出一把能认真砍树的 stone_axe。"
    elif item == "stone_pickaxe":
        text = "你把尖石固定好，做出一把能撬开石缝的 stone_pickaxe。"
    elif item == "fishing_rod":
        text = "你把细枝和纤维拧在一起，做出一根安静等鱼的 fishing_rod。"
    elif item == "hoe":
        text = "你把石片固定在木柄上，做出一把能翻开小块土地的 hoe。"
    elif item == "watering_can":
        text = "你把 clay 和 绳子（cord）整成一个粗朴的 watering_can，水能慢慢倒出来。"
    elif item == "water_flask":
        text = "你把 clay 捏成水壶（water_flask），又用 cord 固住瓶口，终于能把水带离河边。"
    elif item == "basket":
        text = "你把 reed 和 fiber 编成篮子（basket），零碎材料有了一个能待着的地方。"
    elif item == "repair_kit":
        text = "你把能补、能绑、能垫的小材料收成修理包（repair_kit），像给工具留了一次后悔机会。"
    elif item in {"plank", "cord", "paper", "cloth", "brick", "glass"}:
        text = f"你把原始材料慢慢整理成 {item_label(item)}，材料链往前走了一步。"
    elif item in {"shovel", "hammer"}:
        text = f"你把石头、枝条和 绳子（cord）绑紧，做出一件能长期用的 {item}。"
    else:
        text = f"你削出一根能派上用场的 {item}。"
    return ([text, f"获得：{item_count_text(item, output)}"], True)


def recipe_lines(state: dict[str, Any], item: str | None = None) -> list[str]:
    if item:
        item = normalize_item_id(item)
        if item == "garden_plot":
            return [
                "小菜地（garden_plot）：需要 hoe；可在家附近开垦 garden_plot。",
                "如果还没有 hoe：可用 recipes hoe 查看 hoe 的配方。",
            ]
        if item in RECIPES:
            options = []
            for recipe in _recipe_options(item):
                station = recipe.get("station") or CRAFT_STATIONS.get(item)
                station_text = f"；需要 {item_label(station)}" if station else ""
                options.append(f"{_format_cost(recipe['cost'])} -> {item_count_text(item, recipe.get('output', 1))}{station_text}")
            return [f"{item_label(item)} 配方：", *options]
        if item in BUILD_COSTS:
            station = BUILD_STATIONS.get(item)
            station_text = f"；需要 {item_label(station)}" if station else ""
            return [f"{item_label(item)} 建造：{_format_cost(BUILD_COSTS[item])}{station_text}"]
        if item in PROCESS_RECIPES:
            recipe = PROCESS_RECIPES[item]
            if item == "warm_meal":
                return [
                    "warm_meal 加工：cooked_fish x1, herb x1，需要 campfire（显示：热饭 / 熟鱼 / 小火堆）",
                    "serve warm_meal：消耗 warm_meal x1，恢复自己和 companion（显示：热饭 x1）",
                ]
            return [
                f"{item_label(item)} 加工：{_format_cost(recipe['cost'])} -> {item_count_text(item, recipe.get('output', 1))}；需要 {item_label(recipe['station'])}；命令 {recipe['command']}"
            ]
        return [f"还不知道 {item_label(item)} 的配方。"]

    craft_names = ", ".join(sorted(RECIPES))
    build_names = ", ".join(sorted(BUILD_COSTS))
    process_names = ", ".join(recipe["command"] for recipe in PROCESS_RECIPES.values())
    return [
        "已知配方：",
        f"craft: {craft_names}",
        f"build: {build_names}",
        f"campfire: {process_names}",
        "可用 recipes <item> 查看单项配方。",
    ]
