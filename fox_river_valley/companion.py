from __future__ import annotations

from typing import Any

from . import farming
from .data import MAX_COMPANION_NEED, START_POS
from . import relationship as relationship_rules
from . import survival
from .rng import deterministic_int
from .state import add_journal
from .world import nearby_terrains, terrain_at

DEFAULT_PROFILE = {
    "likes_window_table": True,
    "likes_riverside_bench": True,
    "likes_warm_meal": True,
    "dislikes_cave_at_night": True,
    "comfort_priority": "medium",
}

INNER_DEFAULTS = {
    "security": 5,
    "comfort": 0,
    "thought": "她看着还没有家的草地，像在等你决定第一件事。",
    "wish": "build simple_shelter",
    "profile": DEFAULT_PROFILE,
}

THOUGHT_TEMPLATES = {
    "no_shelter_day": [
        "她看着还没有家的草地，像在等你决定第一件事。",
        "她把随身的小包抱紧了一点，目光落在附近的树林上。",
        "河谷很安静，她没有催你，只是看着这片还没有名字的地方。",
    ],
    "no_shelter_night": [
        "天色暗下来，她往你身边靠近了一点，像是在等你决定今晚怎么办。",
        "风开始凉了，她看了一眼空地，又看向你手里的木头。",
        "夜色压下来，她没有说怕，但你能看出这里还不能算家。",
    ],
    "shelter_no_window": [
        "她看了看小屋空着的角落，也许那里可以放一张桌子。",
        "小棚子能挡风了，但角落还空着，像少了一点生活气。",
        "她站在屋里看光从缝隙落进来，好像在想那里可以有张桌子。",
    ],
    "window_table": [
        "她把手放在桌沿，说这里能看见早晨的光。",
        "她在桌边停了一会儿，像是终于确认这里不只是临时避难所。",
        "桌面还粗糙，但她看起来比刚来河谷时安心了一点。",
    ],
    "glass_window_table": [
        "窗边桌终于有了真正的光。",
        "她站在 glass_window 旁边看了一会儿，桌面上第一次落下清亮的光。",
        "river_glass 把早晨留在桌边，她看起来很安静。",
    ],
    "hunger_low": [
        "她看了一眼空掉的背包，没有催你。",
        "她把浆果袋扎紧了一点，像是在计算还能撑多久。",
        "她没有说饿，但脚步比刚才慢了一些。",
    ],
    "warmth_low": [
        "她把手拢在袖口里，像是在忍着冷。",
        "夜风贴着草叶过来，她往火光可能出现的地方看了一眼。",
        "她没有抱怨，只是站得离你更近了一点。",
    ],
    "rain_no_fire": [
        "她听着雨声，看了一眼还没生火的角落。",
        "雨声贴着小屋外沿落下来，她像是在等一点火光。",
        "她没有抱怨雨，只是把目光放到能生火的地方。",
    ],
    "stale_food": [
        "她看了一眼那份已经不太新鲜的食物，没有说什么。",
        "她把变味的食物往远处推了推，像是在提醒你先别分给她。",
        "背包里有点不新鲜的味道，她安静地看了你一眼。",
    ],
    "fire_at_base": [
        "火光让小屋稳了一点。",
        "campfire 在家里低低亮着，屋角没那么冷了。",
        "她看着火光，肩膀像是松下来一点。",
    ],
    "hearth_at_base": [
        "这个家终于有了真正留住暖意的地方。",
        "hearth 让小屋里的暖意沉下来，不再像临时借来的火。",
        "她站在火塘旁边，像是第一次相信暖意能留到明天。",
    ],
    "garden_flower": [
        "她看了一眼小屋旁边的花，像是觉得这里更像能久住的地方。",
        "花在屋边轻轻晃了一下，她的神情也软了一点。",
        "她停在 garden_plot 旁边，看了看那点颜色，好像家又稳了一些。",
    ],
    "kit_arrival": [
        "她看着刚到家的小崽，声音放得很轻。",
        "小崽的动静让屋里安静了一会儿，她像是在重新确认这个家。",
        "她看了一眼炉火旁的小崽，神情比刚才更柔和。",
    ],
    "kit_hungry": [
        "她先看了看小崽的食盆，又看向背包里还能分出的东西。",
        "小崽靠在炉火边蹭了一下，她像是在提醒你先照顾它的肚子。",
        "她没有责备，只是把目光停在小崽有点空的食盆旁。",
    ],
    "kit_mischief": [
        "小崽把一小截木棍拖到门口，她忍着笑看了你一眼。",
        "她看着小崽在屋角转来转去，像是在等你陪它消耗一点精神。",
        "小崽的尾巴已经快碰到炉火边，她轻轻咳了一声提醒你。",
    ],
    "kit_calm": [
        "小崽在炉火旁睡得很沉，她说话也放轻了。",
        "她看着安静下来的小崽，像是终于能把肩膀松下来。",
        "小崽蜷成很小的一团，屋里连木头轻响都显得温柔。",
    ],
    "food_secure": [
        "她整理了一下存着的食物，像是确认今晚不用慌。",
        "家里有能吃的东西，她看起来比前几天稳了一点。",
        "她把新鲜食物放到顺手的位置，像是在给明天留余地。",
    ],
    "spring_home": [
        "春天的水声从门外过来，她像是在听小菜地醒过来。",
        "她看了看屋边新绿的草，声音里有一点轻快。",
        "春风把门口的花吹动了一下，她像是觉得日子能慢慢展开。",
    ],
    "summer_home": [
        "夏天的光落得很满，她把窗边那点亮处留给你看。",
        "她听着外面的虫声，像是在判断今天适不适合走远一点。",
        "屋里比清晨更暖，她把能晒干的东西往光里挪了挪。",
    ],
    "autumn_home": [
        "秋风擦过屋角，她开始把能收起来的东西理得更靠里。",
        "她看着落叶堆在门口，说家也该为冷天留点余地。",
        "傍晚的光短了一点，她像是在盘算火和食物够不够。",
    ],
    "winter_home": [
        "冬天让屋外安静得很深，她更珍惜炉火留住的暖意。",
        "她把手伸向炉火边，像是在确认这个家真的能过冬。",
        "门外的冷意贴得很近，她把小崽睡的地方又整理了一下。",
    ],
    "moon_shard_memory": [
        "她想起那片 moon_shard，看了很久才把它收好。",
        "那点月色一样的碎片还在她心里，她说它不像普通石头。",
        "她没有急着解释 moon_shard，只是把它放在安全的角落。",
    ],
    "moon_violet": [
        "她看着月影堇淡淡的边，像是把雾和夜色都放轻了一点。",
        "月影堇在暗下来的光里很安静，她也跟着放低了声音。",
        "雾气经过那点淡紫色时，她像是忽然觉得夜晚没那么空。",
    ],
    "security_high": [
        "她看起来比刚来河谷时安心了一点。",
        "她走路时不再一直回头看，像是开始认得这个地方。",
        "她靠在门边听风，神情比前几天稳了一些。",
    ],
    "comfort_high": [
        "这个小屋终于不像临时避难所了。",
        "她把东西摆得更顺手了一点，小屋也慢慢有了生活气。",
        "风从屋外过去时，她像是没有以前那么紧绷了。",
    ],
    "default": [
        "她安静地看着河谷，等你决定下一步。",
        "她低头整理了一下随身的小包，像是在给今天留一点余地。",
        "她没有打断你，只是把目光放回这片河谷。",
    ],
}


def clamp_need(value: int) -> int:
    return max(0, min(MAX_COMPANION_NEED, value))


def ensure_inner_fields(buddy: dict[str, Any]) -> None:
    for key, value in INNER_DEFAULTS.items():
        if key == "profile":
            profile = dict(DEFAULT_PROFILE)
            profile.update(buddy.get("profile", {}))
            buddy["profile"] = profile
        else:
            buddy.setdefault(key, value)
    location = buddy.get("location_mode") or buddy.get("location") or "with_player"
    if location not in {"with_player", "at_home", "unavailable"}:
        location = "with_player"
    buddy["location_mode"] = location
    buddy["location"] = location
    pos = buddy.get("pos")
    if not isinstance(pos, list) or len(pos) != 2:
        buddy["pos"] = list(START_POS)


def companion(state: dict[str, Any]) -> dict[str, Any] | None:
    buddy = state.get("companion")
    if buddy:
        ensure_inner_fields(buddy)
    return buddy


def sync_following_position(state: dict[str, Any]) -> None:
    buddy = companion(state)
    if not buddy:
        return
    if buddy.get("location_mode") == "with_player":
        buddy["location"] = "with_player"
        buddy["pos"] = list(state.get("pos", START_POS))


def send_home(state: dict[str, Any]) -> None:
    buddy = companion(state)
    if not buddy:
        return
    base_pos = state.get("base_pos")
    if not base_pos:
        sync_following_position(state)
        return
    buddy["location_mode"] = "at_home"
    buddy["location"] = "at_home"
    buddy["pos"] = list(base_pos)


def all_builds(state: dict[str, Any]) -> list[str]:
    return [item for builds in state.get("builds", {}).values() for item in builds]


def builds_here(state: dict[str, Any]) -> list[str]:
    key = f"{state['pos'][0]},{state['pos'][1]}"
    return state.get("builds", {}).get(key, [])


def has_build(state: dict[str, Any], item: str) -> bool:
    return item in all_builds(state)


def has_warmth_source(state: dict[str, Any]) -> bool:
    return survival.warmth_protection(state) in {"campfire", "hearth"} or state.get("home_level") == "warm_cabin"


def has_fire_source(state: dict[str, Any]) -> bool:
    return survival.warmth_protection(state) in {"campfire", "hearth"}


def has_shelter(state: dict[str, Any]) -> bool:
    return state.get("base_pos") is not None or has_build(state, "simple_shelter")


def has_water_nearby(state: dict[str, Any]) -> bool:
    local = terrain_at(state["seed"], state["pos"])
    return local == "water" or "water" in nearby_terrains(state["seed"], state["pos"])


def _family_kit(state: dict[str, Any]) -> dict[str, Any] | None:
    family = state.get("family", {})
    kits = family.get("kits", []) if isinstance(family, dict) else []
    if family.get("kit_status") == "arrived" and kits:
        return kits[0]
    return None


def _food_security_score(state: dict[str, Any]) -> int:
    inventory = state.get("inventory", {})
    storage = state.get("storage", {})

    def total(item: str) -> int:
        return int(inventory.get(item, 0)) + int(storage.get(item, 0))

    return total("warm_meal") * 3 + total("cooked_fish") * 2 + total("berries") + total("fish")


def garden_followup_wish(state: dict[str, Any]) -> str | None:
    garden = state.get("garden", {})
    plots = garden.get("plots", []) if isinstance(garden, dict) else []
    growing = [plot for plot in plots if plot.get("crop") and not plot.get("ready")]
    if growing:
        if state.get("weather") != "rain" and any(not plot.get("watered_today") for plot in growing):
            if state.get("inventory", {}).get("watering_can", 0) > 0:
                return "water crops"
            return "make watering_can"
        return "wait for flower"
    if state.get("inventory", {}).get("flower_seed", 0) > 0:
        if state.get("flags", {}).get("first_plant_flower_seed"):
            return "plant another flower_seed"
        return "plant flower_seed"
    return None


def thought_key(state: dict[str, Any]) -> str:
    buddy = companion(state)
    if not buddy:
        return ""
    if state.get("flags", {}).get("kit_arrival_focus_day") == state.get("day"):
        return "kit_arrival"
    kit = _family_kit(state)
    if kit and int(kit.get("hunger", 0)) <= 2:
        return "kit_hungry"
    if kit and int(kit.get("mischief", 0)) >= 5:
        return "kit_mischief"
    if kit and int(kit.get("mischief", 0)) <= 0 and int(kit.get("security", 0)) >= 8:
        return "kit_calm"
    if survival.has_stale_food(state):
        return "stale_food"
    if state.get("flags", {}).get("first_hidden_material:moon_shard"):
        return "moon_shard_memory"
    if state.get("weather") == "rain" and survival.warmth_protection(state) == "none":
        return "rain_no_fire"
    if not has_shelter(state) and state["time_slot"] in {"dusk", "night"}:
        return "no_shelter_night"
    if buddy["hunger"] <= 3:
        return "hunger_low"
    if buddy["warmth"] <= 3 or state.get("weather") == "cold_wind":
        return "warmth_low"
    if not has_shelter(state):
        return "no_shelter_day"
    season = str(state.get("calendar", {}).get("season", ""))
    if state.get("home_level") in {"little_cabin", "warm_cabin"} and season in {"spring", "summer", "autumn", "winter"}:
        if season == "winter" or deterministic_int(str(state["seed"]), int(state.get("day", 1)), f"thought:season:{season}", 3) == 0:
            return f"{season}_home"
    if survival.warmth_protection(state) == "hearth":
        return "hearth_at_base"
    if survival.warmth_protection(state) == "campfire":
        return "fire_at_base"
    if farming.has_flower_variety(state, "moon_violet") and (
        state.get("weather") == "fog" or state.get("time_slot") in {"dusk", "night"}
    ):
        return "moon_violet"
    if farming.has_flower_crop(state):
        return "garden_flower"
    if has_build(state, "window_table") and has_build(state, "glass_window"):
        return "glass_window_table"
    if has_shelter(state) and not has_build(state, "window_table"):
        return "shelter_no_window"
    if has_build(state, "window_table"):
        return "window_table"
    if buddy["security"] >= 7:
        return "security_high"
    if _food_security_score(state) >= 5:
        return "food_secure"
    if buddy["comfort"] >= 3:
        return "comfort_high"
    return "default"


def current_thought(state: dict[str, Any]) -> str:
    key = thought_key(state)
    templates = THOUGHT_TEMPLATES.get(key, THOUGHT_TEMPLATES["default"])
    buddy = companion(state)
    if not buddy:
        return ""
    context = ":".join(
        [
            "thought",
            key,
            str(state.get("day", 1)),
            str(state.get("time_slot", "morning")),
            f"{state['pos'][0]},{state['pos'][1]}",
            str(buddy.get("hunger", 0)),
            str(buddy.get("warmth", 0)),
            str(buddy.get("security", 0)),
            str(buddy.get("comfort", 0)),
            str(has_build(state, "window_table")),
        ]
    )
    index = deterministic_int(str(state["seed"]), 0, context, len(templates))
    return templates[index]


def current_wish(state: dict[str, Any]) -> str | None:
    buddy = companion(state)
    if not buddy:
        return None
    profile = buddy["profile"]
    if not has_shelter(state):
        return "build simple_shelter"
    candidates: list[tuple[int, str]] = []
    bad_weather_or_pressure = state.get("weather") in {"rain", "cold_wind"} or survival.night_pressure(state) in {"mild", "high"}
    if survival.has_stale_food(state):
        candidates.append((98, "discard stale food"))
    if bad_weather_or_pressure and not has_warmth_source(state):
        candidates.append((96, "build campfire"))
    if buddy["hunger"] <= 3:
        candidates.append((95 if has_fire_source(state) and profile["likes_warm_meal"] else 90, "make warm meal" if has_fire_source(state) and profile["likes_warm_meal"] else "find food"))
    if buddy["warmth"] <= 3:
        if has_fire_source(state) and profile["likes_warm_meal"]:
            candidates.append((88, "make warm meal"))
        else:
            candidates.append((84, "build campfire"))
    if not has_build(state, "window_table") and profile["likes_window_table"]:
        candidates.append((80, "build window_table"))
    if has_build(state, "window_table") and not farming.has_garden_plot(state):
        candidates.append((78, "build garden_plot"))
    if farming.has_garden_plot(state):
        followup = garden_followup_wish(state)
        if followup:
            weight = 76 if followup == "plant flower_seed" else 62
            candidates.append((weight, followup))
    if buddy["hunger"] <= 3 and farming.has_garden_plot(state) and farming.has_food_seed(state):
        candidates.append((94, "plant food crop"))
    if not has_warmth_source(state):
        candidates.append((70, "build campfire"))
    if has_water_nearby(state) and not has_build(state, "riverside_bench") and profile["likes_riverside_bench"]:
        candidates.append((55, "build riverside_bench"))
    if buddy["comfort"] <= 1:
        comfort_weight = {"low": 30, "medium": 45, "high": 60}.get(profile.get("comfort_priority"), 45)
        if {"riverside_bench", "window_table", "simple_shelter"}.intersection(builds_here(state)):
            candidates.append((comfort_weight, "sit with companion"))
        elif not has_build(state, "storage_box"):
            candidates.append((comfort_weight - 5, "build storage_box"))
    if buddy["energy"] <= 2:
        candidates.append((35, "rest together"))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (-item[0], item[1]))[0][1]


def refresh_inner_state(state: dict[str, Any]) -> None:
    buddy = companion(state)
    if not buddy:
        return
    buddy["thought"] = current_thought(state)
    buddy["wish"] = current_wish(state)


def advice_lines(state: dict[str, Any]) -> list[str]:
    buddy = companion(state)
    if not buddy:
        return ["现在是 solo mode，没有 companion 可以询问。"]
    refresh_inner_state(state)
    thought = buddy["thought"]
    wish = buddy.get("wish")
    name = buddy["name"]
    natural = {
        "build simple_shelter": f"{name} 没有催你，只是看了一眼天色：今晚最好先把能睡下的地方稳住。",
        "build window_table": f"{name} 看了看小屋空着的角落，轻声说：如果今天木头够，也许可以先做一张桌子。",
        "build campfire": f"{name} 把目光停在冷下来的地面上：要是能有一点火光，夜里会稳很多。",
        "build riverside_bench": f"{name} 听了听远处的水声：那边也许可以留一个能坐下来的地方。",
        "make warm meal": f"{name} 看了一眼 campfire：如果还有吃的，也许可以做点热的。",
        "find food": f"{name} 没有说饿，只是把背包带子理紧：也许该先找点能吃的。",
        "find fresh food": f"{name} 看了一眼不太新鲜的食物：也许今天该找点新的吃的。",
        "cook fresh food": f"{name} 望向火光：如果能把新鲜食材做热，会比勉强吃旧食物好。",
        "discard stale food": f"{name} 把不太新鲜的食物往远处推了推：也许先清掉这些，家里会舒服一点。",
        "sit with companion": f"{name} 看向能坐下的地方：如果不急，也许可以一起歇一会儿。",
        "build storage_box": f"{name} 看了看散放的材料：家里要是有个箱子，东西会更踏实。",
        "build garden_plot": f"{name} 看向小屋旁边的空地：也许可以翻出一小块能种东西的土。",
        "plant flower_seed": f"{name} 看了看你手里的 flower_seed：如果不急，也许可以先种一点颜色。",
        "plant another flower_seed": f"{name} 看着刚种下的花种，轻轻点头：如果还有余裕，可以再添一点颜色。",
        "water crops": f"{name} 看了看小菜地的土色：刚种下的东西也许需要一点水。",
        "make watering_can": f"{name} 看向空着的菜地边：如果有 watering_can，照顾作物会稳一些。",
        "wait for flower": f"{name} 看着小菜地，声音放轻了一点：种子已经在土里了，接下来就等它慢慢长。",
        "plant food crop": f"{name} 看了一眼空下来的地：能吃的种子也许该先落进土里。",
        "rest together": f"{name} 的声音放得很轻：今天可以慢一点，先一起休息也好。",
    }
    if wish:
        return [f"thought: {thought}", natural.get(wish, f"{name} 轻声说：今天先照顾眼前最稳的事。")]
    return [f"thought: {thought}", f"{name} 轻轻摇头：现在这样也可以。"]


def talk_line(state: dict[str, Any]) -> str:
    buddy = companion(state)
    if not buddy:
        return "河谷里只有风声回答你。"
    name = buddy["name"]
    kit = _family_kit(state)
    season = str(state.get("calendar", {}).get("season", "spring"))
    weather = str(state.get("weather", "clear"))
    stage = str(relationship_rules.relationship(state).get("stage", "new_arrival")) if relationship_rules.relationship(state) else "solo"
    if survival.has_stale_food(state):
        return f"你和 {name} 低声说起食物，她提醒你：先把不新鲜的东西清掉，家里会舒服一点。"
    if kit and int(kit.get("hunger", 0)) <= 2:
        return f"{name} 看了看第一只小崽：它现在最需要的不是玩，是先吃一点。"
    if kit and int(kit.get("mischief", 0)) >= 5:
        return f"{name} 忍着笑说：它今天精神太足了，得有人陪它把调皮劲用掉。"
    if kit and int(kit.get("mischief", 0)) <= 0 and int(kit.get("security", 0)) >= 8:
        return f"{name} 放低声音：它睡得很好，今天就让炉火替我们陪它一会儿。"
    if weather == "rain":
        return f"雨声落在屋外，你和 {name} 说起今天可以慢一点，听雨也算把家照顾好。"
    if weather == "cold_wind":
        return f"冷风贴着门缝，你和 {name} 先确认炉火、热饭和小崽睡的地方都稳。"
    if weather == "fog":
        return f"雾把远处藏起来了，{name} 说今天若要探索，最好别走得太远。"
    if state.get("flags", {}).get("first_hidden_material:moon_shard"):
        return f"{name} 又看了一眼 moon_shard：有些东西不用马上派上用场，先好好收着。"
    if buddy.get("hunger", 0) <= 3:
        return f"{name} 没有催你，只说：今天如果能先找点吃的，后面的事都会稳一些。"
    if state.get("home_level") == "shelter":
        return f"{name} 看了看 simple_shelter 的屋角：它能挡风，但还不像能长期放心的家。"
    if season == "winter":
        return f"冬天让声音都变轻了，{name} 说这个季节最重要的是把暖意留住。"
    if season == "autumn":
        return f"秋天的风有点短，{name} 说也许该多存一点木头和食物。"
    if season == "summer":
        return f"夏天的光很满，{name} 说今天适合把能晒、能整理的事先做完。"
    if season == "spring":
        return f"春天让门口的草都亮了一点，{name} 说小菜地也许会慢慢给家一个答案。"
    if state.get("home_level") == "warm_cabin":
        return f"你和 {name} 说起 {state.get('home_name') or '这个家'}，她说 warm_cabin 最好的地方，是夜里不用一直担心风。"
    if state.get("home_level") == "little_cabin":
        return f"{name} 看了看屋角：little_cabin 已经不只是避雨的地方了，还可以继续变暖。"
    if stage == "married_family":
        return f"你和 {name} 说了几句家里的小事，它们听起来已经不像任务，更像日子。"
    if stage in {"trusted_family", "shared_home"}:
        return f"{name} 说：这里已经比刚来时稳很多了，我们可以一点点补上缺的东西。"
    return f"你和 {name} 低声说了几句，河谷安静地听着。"


def adjust(
    state: dict[str, Any],
    *,
    hunger: int = 0,
    warmth: int = 0,
    mood: int = 0,
    trust: int = 0,
    energy: int = 0,
    security: int = 0,
    comfort: int = 0,
) -> None:
    buddy = companion(state)
    if not buddy:
        return
    for key, amount in {
        "hunger": hunger,
        "warmth": warmth,
        "mood": mood,
        "trust": trust,
        "energy": energy,
        "security": security,
        "comfort": comfort,
    }.items():
        if amount:
            buddy[key] = clamp_need(buddy[key] + amount)


def complete_wish(state: dict[str, Any], completed: str, reward: str = "comfort") -> None:
    buddy = companion(state)
    if not buddy:
        return
    previous_wish = buddy.get("wish")
    if previous_wish != completed:
        return
    buddy["mood"] = clamp_need(buddy["mood"] + 1)
    if reward == "trust":
        buddy["trust"] = clamp_need(buddy["trust"] + 1)
    else:
        buddy["comfort"] = clamp_need(buddy["comfort"] + 1)
    flag = f"wish_completed:{completed}"
    if not state["flags"].get(flag):
        state["flags"][flag] = True
        relationship_rules.complete_wish(state, completed)
        add_journal(state, f"你完成了 {buddy['name']} 的 wish：{completed}。")
