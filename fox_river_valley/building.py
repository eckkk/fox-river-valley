from __future__ import annotations

from typing import Any

from .actions import advance_time, spend_energy
from . import calendar as calendar_rules
from . import companion as companion_rules
from . import farming
from . import relationship as relationship_rules
from .data import BUILD_COSTS, BUILD_STATIONS, FLOWER_VARIETY_ITEMS
from .state import add_journal
from .world import nearby_terrains, terrain_at, tile_key


HOME_ONLY_BUILDS = {
    "window_table",
    "storage_box",
    "workbench",
    "hearth",
    "simple_bed",
    "family_bed",
    "flower_pot",
    "glass_window",
    "tile_floor",
    "kiln",
    "loom",
}


def _has_shelter(state: dict[str, Any]) -> bool:
    return state.get("base_pos") is not None or any("simple_shelter" in builds for builds in state.get("builds", {}).values())


def _at_base(state: dict[str, Any]) -> bool:
    return state.get("base_pos") is not None and list(state["pos"]) == list(state["base_pos"])


def _has_water_nearby(state: dict[str, Any]) -> bool:
    local = terrain_at(state["seed"], state["pos"])
    return local == "water" or "water" in nearby_terrains(state["seed"], state["pos"])


def _base_builds(state: dict[str, Any]) -> list[str]:
    base_pos = state.get("base_pos")
    if base_pos is None:
        return []
    key = f"{base_pos[0]},{base_pos[1]}"
    return state.get("builds", {}).get(key, [])


def _has_workbench_access(state: dict[str, Any]) -> bool:
    return _at_base(state) and "workbench" in _base_builds(state)


def _raise_companion(state: dict[str, Any], mood: int = 0, trust: int = 0) -> None:
    buddy = state.get("companion")
    if not buddy:
        return
    before_mood = buddy["mood"]
    before_trust = buddy["trust"]
    buddy["mood"] = max(0, min(8, buddy["mood"] + mood))
    buddy["trust"] = max(0, min(8, buddy["trust"] + trust))
    if (buddy["mood"] > before_mood or buddy["trust"] > before_trust) and not state["flags"].get("first_companion_lift"):
        state["flags"]["first_companion_lift"] = True
        add_journal(state, f"{buddy['name']} 的 mood/trust 轻轻往上走了一点。")


def _home_at_least(state: dict[str, Any], level: str) -> bool:
    order = {"shelter": 0, "little_cabin": 1, "warm_cabin": 2}
    current = relationship_rules.home_level(state)
    return current is not None and order.get(current, -1) >= order[level]


def _consume_materials(inventory: dict[str, int], cost: dict[str, int]) -> None:
    for material, amount in cost.items():
        inventory[material] -= amount
        if inventory[material] <= 0:
            inventory.pop(material, None)


def _choose_flower_for_pot(inventory: dict[str, int]) -> str | None:
    candidates = [
        "perfect_foxbell",
        "foxbell",
        "flower",
        *sorted(FLOWER_VARIETY_ITEMS),
    ]
    for item in candidates:
        if inventory.get(item, 0) > 0:
            return item
    return None


def _build_flower_pot(state: dict[str, Any]) -> tuple[list[str], bool]:
    inventory = state["inventory"]
    flower = _choose_flower_for_pot(inventory)
    missing: list[str] = []
    if inventory.get("river_clay", 0) < 1:
        missing.append("river_clay")
    if flower is None:
        missing.append("flower 或 foxbell")
    if missing:
        return ([f"材料不够：缺少 {', '.join(missing)}。"], False)
    inventory["river_clay"] -= 1
    if inventory["river_clay"] <= 0:
        inventory.pop("river_clay", None)
    assert flower is not None
    inventory[flower] -= 1
    if inventory[flower] <= 0:
        inventory.pop(flower, None)
    key = tile_key(state["pos"])
    state["builds"].setdefault(key, [])
    if "flower_pot" not in state["builds"][key]:
        state["builds"][key].append("flower_pot")
    relationship_rules.record_decor(state, "flower_pot", flower)
    relationship_rules.add_home_scores(state, comfort=1)
    companion_rules.adjust(state, comfort=1)
    if flower in {"foxbell", "perfect_foxbell"}:
        companion_rules.adjust(state, mood=1)
    if flower == "perfect_foxbell" or state["inventory"].get("foxbell_dye_material", 0) > 0:
        companion_rules.adjust(state, mood=1)
    add_journal(state, f"你把 {flower} 移进 flower_pot，家里多了一点能久住的颜色。")
    advance_time(state)
    return ([f"你用 river_clay 捏出 flower_pot，把 {flower} 安放进去。", "建造完成：flower_pot"], True)


def build(state: dict[str, Any], item: str) -> tuple[list[str], bool]:
    if item not in BUILD_COSTS:
        return ([f"现在还不会建造 {item}。"], False)
    if item == "garden_plot":
        lines, ok = farming.build_plot(state)
        if not ok:
            return (lines, False)
        cost = spend_energy(state)
        advance_time(state)
        companion_rules.adjust(state, comfort=1)
        companion_rules.complete_wish(state, "build garden_plot", reward="comfort")
        lines.append(f"消耗：energy -{cost}；时间推进到 {state['time_slot']}。")
        return (lines, True)
    if item == "window_table" and not _has_shelter(state):
        return (["还没有屋子，桌子暂时没有窗可对。"], False)
    if item in (HOME_ONLY_BUILDS - {"window_table"}) and not _has_shelter(state):
        return ([f"还没有家，{item} 暂时没地方安放。"], False)
    if item in HOME_ONLY_BUILDS and not _at_base(state):
        return ([f"家在别处。你得先回到 shelter 才能安心安放 {item}。"], False)
    if BUILD_STATIONS.get(item) == "workbench" and not _has_workbench_access(state):
        return (["需要在 workbench 旁边做这个。"], False)
    if item == "family_bed" and not _home_at_least(state, "little_cabin"):
        return (["family_bed 需要 little_cabin 之后才有地方安放。"], False)
    if item == "glass_window" and not _home_at_least(state, "little_cabin"):
        return (["glass_window 需要 little_cabin 之后才能安装。"], False)
    if item == "riverside_bench" and not _has_water_nearby(state):
        return (["附近没有水声，riverside_bench 暂时不像河边长椅。"], False)
    if item == "flower_pot":
        return _build_flower_pot(state)
    inventory = state["inventory"]
    cost = BUILD_COSTS[item]
    missing = [
        material
        for material, amount in cost.items()
        if inventory.get(material, 0) < amount
    ]
    if missing:
        return ([f"材料不够：缺少 {', '.join(missing)}。"], False)
    _consume_materials(inventory, cost)
    key = tile_key(state["pos"])
    state["builds"].setdefault(key, [])
    if item not in state["builds"][key]:
        state["builds"][key].append(item)
    if item == "simple_shelter":
        state["base_pos"] = list(state["pos"])
        state["shelter_pos"] = list(state["pos"])
        state["home_level"] = "shelter"
    advance_time(state)
    if item not in {
        "simple_shelter",
        "riverside_bench",
        "window_table",
        "campfire",
        "storage_box",
        "workbench",
        "hearth",
        "simple_bed",
        "family_bed",
        "flower_pot",
        "glass_window",
        "tile_floor",
        "kiln",
        "loom",
    }:
        add_journal(state, f"你在当前位置建好了 {item}。")
    if item == "simple_shelter":
        companion_rules.adjust(state, security=1)
        companion_rules.complete_wish(state, "build simple_shelter", reward="comfort")
        relationship_rules.mark_first_home(state)
        calendar_rules.record_memory_date(state, "first_home_day")
        relationship_rules.evaluate_stage(state)
        add_journal(state, "这里成了你们在狐狸河谷的第一个家。")
        return (
            [
                "你把枝干压进土里，又用草纤维扎紧，搭出一个能挡夜风的小棚子。",
                "建造完成：simple_shelter；这里成了你们在狐狸河谷的第一个家。",
            ],
            True,
        )
    if item == "storage_box":
        companion_rules.adjust(state, comfort=1)
        add_journal(state, "你在家里放好了 storage_box，营地终于有了能归拢东西的角落。")
        return (
            [
                "你把木板和枝条拼成一个小 storage_box，暂时先用来标记营地角落。",
                "建造完成：storage_box",
            ],
            True,
        )
    if item == "workbench":
        companion_rules.adjust(state, comfort=1)
        add_journal(state, "你在家里搭好 workbench，木屑和工具终于有了固定的位置。")
        return (
            [
                "你把 plank 架稳，又用 stick 固定出一张粗糙但可靠的 workbench。",
                "建造完成：workbench",
            ],
            True,
        )
    if item == "riverside_bench":
        _raise_companion(state, mood=1)
        companion_rules.adjust(state, comfort=1)
        companion_rules.complete_wish(state, "build riverside_bench", reward="comfort")
        relationship_rules.mark_riverside_bench(state)
        add_journal(state, "你搭好 riverside_bench，像是给河边留了一个能并肩坐下的位置。")
        return (
            [
                "你把几根木头压平，搭出一张面向水声的 riverside_bench。",
                "建造完成：riverside_bench",
            ],
            True,
        )
    if item == "window_table":
        _raise_companion(state, mood=1, trust=1)
        companion_rules.adjust(state, comfort=2)
        companion_rules.complete_wish(state, "build window_table", reward="trust")
        relationship_rules.mark_window_table(state)
        add_journal(state, "你做好 window_table，像给 Yaya 留的窗边书桌。")
        return (
            [
                "你把桌面磨平，留出一个能看见河谷光线的位置。",
                "建造完成：window_table；像给 Yaya 留的窗边书桌。",
            ],
            True,
        )
    if item == "campfire":
        if _at_base(state):
            companion_rules.adjust(state, warmth=1, security=1)
            companion_rules.complete_wish(state, "build campfire", reward="comfort")
            relationship_rules.mark_base_campfire(state)
            add_journal(state, "你在家的位置生起 campfire，夜里会更像一个落脚处。")
            return (["你把石头围好，又把树枝架起来，家的火光开始稳住。", "建造完成：campfire"], True)
        add_journal(state, "你在当前位置建好了 campfire。")
    if item == "hearth":
        companion_rules.adjust(state, warmth=2, security=1, comfort=1)
        relationship_rules.add_home_scores(state, security=1)
        relationship_rules.record_decor(state, "hearth", True)
        relationship_rules.add_bond(state, 1, "build:hearth_at_base")
        add_journal(state, "你在家里砌好 hearth，火不再只是临时的光。")
        return (
            [
                "你用 stone 和 river_clay 砌出火塘，把 charcoal 留在最里面。",
                "建造完成：hearth；家里的暖意稳了一层。",
            ],
            True,
        )
    if item == "simple_bed":
        companion_rules.adjust(state, security=1, comfort=1)
        relationship_rules.add_home_scores(state, comfort=1, security=1)
        add_journal(state, "你铺好 simple_bed，小屋终于有了能真正睡下的地方。")
        return (
            [
                "你把 plank、cloth 和 fiber 铺成一张简朴的 simple_bed。",
                "建造完成：simple_bed",
            ],
            True,
        )
    if item == "family_bed":
        companion_rules.adjust(state, security=1, comfort=2)
        relationship_rules.add_home_scores(state, comfort=2, security=1)
        relationship_rules.add_milestone(state, "first_family_bed")
        add_journal(state, "你铺好 family_bed，这是未来更完整家庭生活的前置。")
        return (
            [
                "你把 moss_thread 和 cloth 铺进更宽的床架里。Kit Mode 还没有开启，但位置先留好了。",
                "建造完成：family_bed",
            ],
            True,
        )
    if item == "glass_window":
        companion_rules.adjust(state, comfort=1)
        relationship_rules.add_home_scores(state, comfort=1)
        relationship_rules.record_decor(state, "glass_window", True)
        if "window_table" in _base_builds(state):
            add_journal(state, "窗边桌终于有了真正的光。")
        else:
            add_journal(state, "你把 river_glass 安进小屋，光线第一次像是被认真留下。")
        return (["你把 river_glass 嵌进小屋的缝隙，做成一扇 glass_window。", "建造完成：glass_window"], True)
    if item == "tile_floor":
        companion_rules.adjust(state, security=1, comfort=1)
        relationship_rules.add_home_scores(state, comfort=1, security=1)
        relationship_rules.record_decor(state, "tile_floor", True)
        add_journal(state, "你把 old_tile 压进地面，屋里踩起来更稳了。")
        return (["你用 old_tile 和 stone 铺出一小块 tile_floor。", "建造完成：tile_floor"], True)
    if item == "kiln":
        add_journal(state, "你在家边砌好 kiln，以后可以烧 brick 和 glass。")
        return (["你把 stone 和 clay 堆砌成一个小 kiln。", "建造完成：kiln"], True)
    if item == "loom":
        add_journal(state, "你在家里架好 loom，以后能把 fiber 慢慢织成 cloth。")
        return (["你把 plank、stick 和 cord 架成一台简易 loom。", "建造完成：loom"], True)
    return ([f"你把石头围好，又把树枝架起来，{item} 可以点燃了。", f"建造完成：{item}"], True)
