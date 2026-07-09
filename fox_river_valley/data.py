MAP_SIZE = 24
START_POS = [12, 12]

TIME_SLOTS = [
    "morning",
    "late_morning",
    "midday",
    "afternoon",
    "late_afternoon",
    "evening",
    "dusk",
    "night",
]

MAX_ENERGY = 6
MAX_HUNGER = 8
MAX_COMPANION_NEED = 8
ITEM_STACK_LIMIT = 999

DIFFICULTY_PROFILES = {
    "casual": {
        "hunger_decay": 0.5,
        "energy_cost": 0.8,
        "resource_yield": 1.4,
        "night_penalty": "low",
        "companion_need_decay": 0.5,
    },
    "normal": {
        "hunger_decay": 1.0,
        "energy_cost": 1.0,
        "resource_yield": 1.0,
        "night_penalty": "medium",
        "companion_need_decay": 1.0,
    },
    "hard": {
        "hunger_decay": 1.3,
        "energy_cost": 1.2,
        "resource_yield": 0.8,
        "night_penalty": "high",
        "companion_need_decay": 1.3,
    },
    "hell": {
        "hunger_decay": 1.6,
        "energy_cost": 1.4,
        "resource_yield": 0.6,
        "night_penalty": "severe",
        "companion_need_decay": 1.6,
    },
}

TERRAIN_LABELS = {
    "grass": "草地",
    "forest": "森林",
    "water": "河水",
    "hill": "山丘",
    "stone": "石坡",
    "cave": "洞口",
    "ruins": "遗迹",
}

PASSABLE_TERRAINS = {"grass", "forest", "hill", "stone", "cave", "ruins"}

RECIPES = {
    "stick": [
        {"cost": {"branch": 1}, "output": 3},
        {"cost": {"wood": 1}, "output": 2},
    ],
    "plank": {"cost": {"wood": 2}, "output": 2},
    "cord": {"cost": {"fiber": 2}, "output": 1},
    "paper": {"cost": {"reed": 2}, "output": 1},
    "cloth": {"cost": {"fiber": 3}, "output": 1, "station": "loom"},
    "brick": {"cost": {"clay": 2}, "output": 1, "station": "kiln"},
    "glass": {"cost": {"sand": 2}, "output": 1, "station": "kiln"},
    "stone_axe": {"cost": {"stick": 1, "stone": 2, "cord": 1}, "output": 1},
    "stone_pickaxe": {"cost": {"stick": 2, "stone": 3, "cord": 1}, "output": 1},
    "fishing_rod": {"cost": {"stick": 2, "cord": 2}, "output": 1},
    "hoe": {"cost": {"stick": 1, "stone": 2, "cord": 1}, "output": 1},
    "watering_can": {"cost": {"clay": 2, "cord": 1}, "output": 1},
    "water_flask": {"cost": {"clay": 1, "cord": 1}, "output": 1},
    "shovel": {"cost": {"stick": 1, "stone": 1, "cord": 1}, "output": 1},
    "hammer": {"cost": {"stick": 1, "stone": 2, "cord": 1}, "output": 1},
    "basket": {"cost": {"reed": 2, "fiber": 1}, "output": 1},
    "repair_kit": {"cost": {"stick": 1, "fiber": 1, "stone": 1}, "output": 1},
}

PROCESS_RECIPES = {
    "cooked_fish": {"command": "cook fish", "cost": {"fish": 1}, "output": 1, "station": "campfire"},
    "charcoal": {"command": "make charcoal", "cost": {"wood": 2}, "output": 1, "station": "campfire"},
    "warm_meal": {
        "command": "make warm_meal",
        "cost": {"cooked_fish": 1, "herb": 1},
        "output": 1,
        "station": "campfire",
    },
}

CRAFT_STATIONS = {
    "stone_axe": "workbench",
    "stone_pickaxe": "workbench",
    "fishing_rod": "workbench",
    "hoe": "workbench",
    "watering_can": "workbench",
    "water_flask": "workbench",
    "hammer": "workbench",
    "basket": "workbench",
    "repair_kit": "workbench",
}

BUILD_COSTS = {
    "workbench": {"plank": 2, "stick": 2},
    "campfire": {"stone": 3, "stick": 2},
    "simple_shelter": {"wood": 4, "fiber": 1},
    "garden_plot": {},
    "storage_box": {"plank": 2},
    "riverside_bench": {"plank": 2, "stick": 1},
    "window_table": {"plank": 2, "stick": 2},
    "simple_bed": {"plank": 2, "cloth": 1, "fiber": 2},
    "family_bed": {"plank": 4, "moss_thread": 1, "cloth": 2},
    "flower_pot": {},
    "bedroll": {"fiber": 2},
    "storage_shelf": {"plank": 2, "stick": 1},
    "door_charm": {"stinky_shoe": 1, "stick": 1},
    "tool_wall": {"plank": 2, "stick": 1},
    "drying_rack": {"stick": 2, "fiber": 1},
    "glass_window": {"river_glass": 1, "plank": 1},
    "tile_floor": {"old_tile": 1, "stone": 2},
    "hearth": {"stone": 6, "river_clay": 1, "charcoal": 1},
    "kiln": {"stone": 4, "clay": 2},
    "loom": {"plank": 2, "stick": 2, "cord": 2},
}

BUILD_STATIONS = {
    "window_table": "workbench",
    "simple_bed": "workbench",
    "family_bed": "workbench",
}

FISH_SPECIES_ITEMS = {
    "fish",
    "silver_fish",
    "rain_carp",
    "dusk_eel",
    "river_crab",
}

FINDING_ITEMS = {
    "drift_bottle",
    "old_boot",
    "stinky_shoe",
    "map_fragment",
    "old_coin",
    "cracked_tile",
    "small_charm",
    "crafted_charm",
    "river_glass",
    "old_tile",
    "moss_thread",
    "weathered_wood",
    "moon_shard",
    "river_clay",
}
FLOWER_VARIETY_ITEMS = {
    "foxbell",
    "dew_daisy",
    "river_forget_me_not",
    "hearth_marigold",
    "moon_violet",
}
QUALITY_FLOWER_ITEMS = {
    f"{quality}_{item}"
    for item in FLOWER_VARIETY_ITEMS
    for quality in ("good", "perfect")
}
QUALITY_FOOD_ITEMS = {
    "good_berries",
    "perfect_berries",
    "good_herb",
    "perfect_herb",
}
RARE_CROP_YIELD_ITEMS = {
    "foxbell_dye_material",
    "dew_petal",
    "river_blue_petal",
    "hearth_gold_petal",
    "moon_violet_pigment",
    "seed_pod",
}

COMMITMENT_TOKEN_ITEMS = {
    "foxbell",
    "river_forget_me_not",
    "hearth_marigold",
    "moon_violet",
    "crafted_charm",
    "old_coin",
}
HOME_TOKEN_ITEMS = set(COMMITMENT_TOKEN_ITEMS)

FOOD_ITEMS = {
    "berries",
    *FISH_SPECIES_ITEMS,
    "cooked_fish",
    "warm_meal",
    "stale_fish",
    "stale_food",
    "spoiled_berries",
    *QUALITY_FOOD_ITEMS,
}
RAW_MATERIAL_ITEMS = {
    "wood",
    "fiber",
    "stone",
    "clay",
    "branch",
    "reed",
    "sand",
    "herb",
    "coal",
    "flower",
    "mushroom",
    "dry_branch",
    "seed_pod",
    "frost_flower_seed",
    "iron_ore",
    "water",
    "dried_herb",
    "river_glass",
    "old_tile",
    "moss_thread",
    "weathered_wood",
    "moon_shard",
    "river_clay",
    "berry_seed",
    "herb_seed",
    "flower_seed",
    *FLOWER_VARIETY_ITEMS,
    *QUALITY_FLOWER_ITEMS,
    *RARE_CROP_YIELD_ITEMS,
}
PROCESSED_MATERIAL_ITEMS = {"stick", "plank", "cord", "charcoal", "brick", "glass", "paper", "cloth"}
TOOL_ITEMS = {
    "stone_axe",
    "stone_pickaxe",
    "fishing_rod",
    "hoe",
    "watering_can",
    "water_flask",
    "shovel",
    "hammer",
    "basket",
    "repair_kit",
}

ITEM_LABELS = {
    "warm_meal": "热饭",
    "cooked_fish": "熟鱼",
    "garden_plot": "小菜地",
    "window_table": "窗边小桌",
    "campfire": "小火堆",
    "hearth": "火塘",
    "foxbell": "狐铃花",
    "spoiled_berries": "坏浆果",
    "stale_food": "变质食物",
    "stale_fish": "变味鱼",
    "dried_herb": "干香草",
    "cord": "绳子",
    "water": "清水",
    "water_flask": "水壶",
    "repair_kit": "修理包",
    "basket": "篮子",
    "bedroll": "铺盖卷",
    "storage_shelf": "储物架",
    "door_charm": "门口小挂饰",
    "tool_wall": "工具墙",
    "drying_rack": "晾晒架",
    "stinky_shoe": "臭鞋",
}

ITEM_ALIASES = {
    "rope": "cord",
    "fiber cord": "cord",
    "basic axe": "stone_axe",
    "stone axe": "stone_axe",
    "water flask": "water_flask",
    "repair kit": "repair_kit",
    "stinky shoe": "stinky_shoe",
    "warm meal": "warm_meal",
    "cooked fish": "cooked_fish",
    "stale food": "stale_food",
    "stale fish": "stale_fish",
    "spoiled berries": "spoiled_berries",
}


def normalize_item_id(item: str) -> str:
    clean = " ".join(str(item).strip().lower().replace("_", " ").split())
    if not clean:
        return ""
    return ITEM_ALIASES.get(clean, clean.replace(" ", "_"))


def item_label(item: str, *, include_id: bool = True) -> str:
    label = ITEM_LABELS.get(item)
    if not label:
        return item
    if include_id:
        return f"{label}（{item}）"
    return label


def item_count_text(item: str, amount: int, *, include_id: bool = True) -> str:
    label = ITEM_LABELS.get(item)
    if label and include_id:
        return f"{label} x{amount}（{item}）"
    return f"{item_label(item, include_id=include_id)} x{amount}"


def item_counts_text(items: dict[str, int], *, include_id: bool = True) -> str:
    positive = {key: value for key, value in sorted(items.items()) if value > 0}
    if not positive:
        return "empty"
    return ", ".join(item_count_text(item, amount, include_id=include_id) for item, amount in positive.items())


def _add_tag(tags: dict[str, set[str]], item: str, tag: str) -> None:
    tags.setdefault(item, set()).add(tag)


ITEM_TAGS: dict[str, set[str]] = {}
for _item in FLOWER_VARIETY_ITEMS | {"flower"}:
    _add_tag(ITEM_TAGS, _item, "flower")
for _item in FOOD_ITEMS:
    _add_tag(ITEM_TAGS, _item, "food")
for _item in FINDING_ITEMS:
    _add_tag(ITEM_TAGS, _item, "finding")
for _item in HOME_TOKEN_ITEMS:
    _add_tag(ITEM_TAGS, _item, "home_token")
for _item in COMMITMENT_TOKEN_ITEMS:
    _add_tag(ITEM_TAGS, _item, "commitment_token")


def item_has_tag(item: str, tag: str) -> bool:
    return tag in ITEM_TAGS.get(item, set())
