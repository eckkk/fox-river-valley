from __future__ import annotations

from typing import Any

from . import relationship as relationship_rules
from .data import MAX_COMPANION_NEED, item_label
from .names import NameValidationError, clean_name
from .rng import deterministic_int
from .survival import warmth_protection

KIT_STATUS = {"none", "expecting", "arrived"}

KIT_SPECIES = {
    "silicon_fox": {
        "display_name": "小硅狐崽",
        "hidden_breed": "curly_brace_fox",
        "hidden_breed_display": "Curly-Brace Fox / 花括号尾巴狐",
        "traits": [
            "likes_foxbell",
            "likes_hearth",
            "curly_brace_tail",
            "curious_about_storage",
        ],
        "trait": "curly_brace_tail",
        "favorite_place": "hearth",
    }
}


def _add_journal(state: dict[str, Any], text: str) -> None:
    for entry in state.setdefault("journal", []):
        if entry.get("day") == state.get("day", 1) and entry.get("text") == text:
            return
    state.setdefault("journal", []).append(
        {
            "day": state.get("day", 1),
            "time": state.get("time_slot", "morning"),
            "text": text,
            "system": True,
        }
    )


def _clamp_need(value: Any, default: int = 6) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = default
    return max(0, min(MAX_COMPANION_NEED, count))


def species_data(species: str | None) -> dict[str, Any] | None:
    if not species:
        return None
    if species in KIT_SPECIES:
        return KIT_SPECIES[species]
    return {
        "display_name": f"{species} kit",
        "hidden_breed": None,
        "hidden_breed_display": "none",
        "traits": ["curious"],
        "trait": "curious",
        "favorite_place": "home",
    }


def family_species(state: dict[str, Any]) -> str | None:
    buddy = state.get("companion")
    if not buddy:
        return None
    profile = buddy.get("companion_profile", {})
    return buddy.get("family_species") or profile.get("family_species")


def _normalize_kit(raw: dict[str, Any], index: int = 1) -> dict[str, Any]:
    species = str(raw.get("species") or "unknown")
    data = species_data(species) or species_data("unknown")
    assert data is not None
    return {
        "id": str(raw.get("id") or f"kit_{index}"),
        "species": species,
        "display_name": str(raw.get("display_name") or data["display_name"]),
        "hidden_breed": raw.get("hidden_breed") if raw.get("hidden_breed") is not None else data.get("hidden_breed"),
        "name": raw.get("name"),
        "hunger": _clamp_need(raw.get("hunger"), 6),
        "warmth": _clamp_need(raw.get("warmth"), 6),
        "sleep": _clamp_need(raw.get("sleep"), 6),
        "security": _clamp_need(raw.get("security"), 6),
        "curiosity": _clamp_need(raw.get("curiosity"), 5),
        "mischief": _clamp_need(raw.get("mischief"), 3),
        "favorite_place": str(raw.get("favorite_place") or data.get("favorite_place") or "home"),
        "trait": str(raw.get("trait") or data.get("trait") or "curious"),
    }


def create_empty_family() -> dict[str, Any]:
    return {
        "kit_status": "none",
        "kit_count": 0,
        "kit_days_waited": 0,
        "kit_arrival_wait_days": None,
        "expected_species": None,
        "kits": [],
    }


def ensure_family_state(state: dict[str, Any]) -> dict[str, Any]:
    family = state.setdefault("family", create_empty_family())
    if not isinstance(family, dict):
        family = create_empty_family()
        state["family"] = family
    status = str(family.get("kit_status", "none"))
    if status not in KIT_STATUS:
        status = "none"
    family["kit_status"] = status
    family["kit_days_waited"] = max(0, int(family.get("kit_days_waited") or 0))
    expected_species = family.get("expected_species")
    family["expected_species"] = str(expected_species) if expected_species else None
    wait_days = family.get("kit_arrival_wait_days")
    family["kit_arrival_wait_days"] = max(2, int(wait_days)) if wait_days else None
    raw_kits = family.get("kits", [])
    if not isinstance(raw_kits, list):
        raw_kits = []
    kits = [_normalize_kit(raw, index + 1) for index, raw in enumerate(raw_kits[:1]) if isinstance(raw, dict)]
    if status != "arrived":
        kits = []
    family["kits"] = kits
    family["kit_count"] = len(kits) if status == "arrived" else 0
    if status == "none":
        family["kit_days_waited"] = 0
        family["kit_arrival_wait_days"] = None
        family["expected_species"] = None
    return family


def compact_family(state: dict[str, Any]) -> dict[str, int | str]:
    family = ensure_family_state(state)
    return {
        "kit_status": family["kit_status"],
        "kit_count": family["kit_count"],
    }


def kit_readiness_status(state: dict[str, Any]) -> str:
    family = ensure_family_state(state)
    if family["kit_status"] in {"expecting", "arrived"}:
        return family["kit_status"]
    return "ready" if readiness(state)["ready"] else "not_ready"


def _has_food_security(state: dict[str, Any]) -> bool:
    inventory = state.get("inventory", {})
    storage = state.get("storage", {})

    def total(item: str) -> int:
        return int(inventory.get(item, 0)) + int(storage.get(item, 0))

    return total("warm_meal") >= 1 or total("berries") >= 3 or total("cooked_fish") >= 2


def _has_flower_anchor(state: dict[str, Any]) -> bool:
    inventory = state.get("inventory", {})
    storage = state.get("storage", {})
    decor = state.get("home_decor", {})
    builds = relationship_rules.base_builds(state)
    if "flower_pot" in builds or decor.get("flower_pot"):
        return True
    for item in ("foxbell", "perfect_foxbell"):
        if int(inventory.get(item, 0)) + int(storage.get(item, 0)) > 0:
            return True
    return False


def readiness(state: dict[str, Any]) -> dict[str, Any]:
    family = ensure_family_state(state)
    buddy = state.get("companion")
    rel = relationship_rules.relationship(state)
    builds = relationship_rules.base_builds(state)
    species = family_species(state)
    checks = {
        "family_mode": state.get("mode") == "family" and buddy is not None,
        "commitment": bool(rel and relationship_rules.commitment_status(rel) == "married" and rel.get("stage") == "married_family"),
        "warm_cabin": state.get("home_level") == "warm_cabin",
        "family_bed": "family_bed" in builds,
        "hearth": "hearth" in builds,
        "flower_anchor": _has_flower_anchor(state),
        "food_security": _has_food_security(state),
        "companion_security": bool(buddy and int(buddy.get("security", 0)) >= 6),
        "companion_comfort": bool(buddy and int(buddy.get("comfort", 0)) >= 5),
        "family_species": bool(species),
        "no_existing_kit": family["kit_status"] == "none",
    }
    missing_labels = {
        "family_mode": "family mode",
        "commitment": "relationship commitment married_family",
        "warm_cabin": "warm_cabin",
        "family_bed": "family_bed",
        "hearth": "hearth",
        "flower_anchor": "flower_pot or foxbell/perfect_foxbell",
        "food_security": "warm_meal or berries x3 or cooked_fish x2",
        "companion_security": "companion security >= 6",
        "companion_comfort": "companion comfort >= 5",
        "family_species": "family_species",
        "no_existing_kit": "no existing or expected kit",
    }
    missing = [missing_labels[key] for key, ok in checks.items() if not ok]
    return {
        "ready": not missing,
        "checks": checks,
        "missing": missing,
        "species": species,
    }


def readiness_lines(state: dict[str, Any]) -> list[str]:
    result = readiness(state)
    checks = result["checks"]

    def yn(key: str) -> str:
        return "yes" if checks[key] else "no"

    lines = [
        _readiness_summary(result),
        "family readiness:",
        f"- commitment: {yn('commitment')}",
        f"- warm_cabin: {yn('warm_cabin')}",
        f"- family_bed: {yn('family_bed')}",
        f"- hearth: {yn('hearth')}",
        f"- flower anchor: {yn('flower_anchor')}",
        f"- food security: {yn('food_security')}",
        f"- companion security: {yn('companion_security')}",
        f"- companion comfort: {yn('companion_comfort')}",
        f"- family_species: {yn('family_species')}",
    ]
    if result["missing"]:
        lines.append("missing: " + ", ".join(result["missing"]))
    else:
        lines.append("missing: none")
    lines.append(f"kit_readiness: {kit_readiness_status(state)}")
    return lines


def _readiness_summary(result: dict[str, Any]) -> str:
    if result["ready"]:
        return "这个家已经足够暖，也足够稳，可以认真等待新的家庭成员。"
    checks = result["checks"]
    if not checks["commitment"] or not checks["warm_cabin"]:
        return "还早。先把家升级成 warm_cabin，并完成家庭承诺。"
    if not checks["family_bed"] or not checks["hearth"] or not checks["food_security"]:
        return "这个家还差一点稳定感：需要炉火、家庭床和足够的新鲜食物。"
    return "这个家还差一点准备，先把缺的条件补齐。"


def arrival_wait_days(state: dict[str, Any], species: str) -> int:
    home_name = state.get("home_name") or "unnamed_home"
    context = f"kit_wait:{species}:{home_name}"
    return 2 + deterministic_int(str(state.get("seed", "default")), 0, context, 2)


def wish_for_kits(state: dict[str, Any]) -> tuple[list[str], bool]:
    family = ensure_family_state(state)
    if family["kit_status"] == "arrived":
        return (["已经有 kit 加入家庭了，v1.5 只支持 1 只 kit。"], False)
    if family["kit_status"] == "expecting":
        return (["你们已经在等待新的家庭成员。"], False)
    result = readiness(state)
    if not result["ready"]:
        return (["还不能 wish for kits。", "missing:", *[f"- {item}" for item in result["missing"]]], False)
    species = str(result["species"])
    family["kit_status"] = "expecting"
    family["kit_count"] = 0
    family["kit_days_waited"] = 0
    family["kit_arrival_wait_days"] = arrival_wait_days(state, species)
    family["expected_species"] = species
    family["kits"] = []
    relationship_rules.add_milestone(state, "wish_for_kits")
    _add_journal(state, "你们在炉火旁边认真谈起未来的小家庭，开始等待新的家庭成员。")
    buddy_name = state.get("companion", {}).get("name", "companion")
    return (
        [
            "SCENE: Wish for Kits",
            f"你和 {buddy_name} 在炉火旁边认真谈起未来的小家庭。",
            "这个家已经足够暖，也足够稳。",
            "你们开始等待新的家庭成员。",
            "状态更新：kit_status = expecting",
            "可尝试：sleep、family readiness、journal",
        ],
        True,
    )


def _new_kit(species: str) -> dict[str, Any]:
    data = species_data(species)
    assert data is not None
    return {
        "id": "kit_1",
        "species": species,
        "display_name": data["display_name"],
        "hidden_breed": data.get("hidden_breed"),
        "name": None,
        "hunger": 6,
        "warmth": 6,
        "sleep": 6,
        "security": 6,
        "curiosity": 5,
        "mischief": 3,
        "favorite_place": data.get("favorite_place", "home"),
        "trait": data.get("trait", "curious"),
    }


def advance_kit_morning(state: dict[str, Any]) -> list[str]:
    family = ensure_family_state(state)
    if family["kit_status"] == "expecting":
        family["kit_days_waited"] += 1
        species = family["expected_species"] or family_species(state)
        if not species:
            return []
        wait_days = family["kit_arrival_wait_days"] or arrival_wait_days(state, species)
        family["kit_arrival_wait_days"] = wait_days
        if family["kit_days_waited"] < wait_days:
            return []
        kit = _new_kit(species)
        family["kit_status"] = "arrived"
        family["kits"] = [kit]
        family["kit_count"] = 1
        relationship_rules.add_milestone(state, "first_kit_arrival")
        home_name = str(state.get("home_name") or "这个家")
        _add_journal(state, f"第一只{kit['display_name']}在 {home_name} 加入了家庭。")
        state.setdefault("flags", {})["kit_arrival_focus_day"] = state.get("day", 1)
        data = species_data(species)
        assert data is not None
        hidden = data.get("hidden_breed_display") or "none"
        hidden_line = [f"隐藏品种：{hidden}"] if hidden != "none" else []
        arrival_lines = _arrival_home_lines(state, home_name)
        return [
            "SCENE: Kit Arrival",
            *arrival_lines,
            f"一只{data['display_name']}加入了家庭。" if species == "silicon_fox" else f"一只 {data['display_name']} 加入了家庭。",
            *hidden_line,
            "新增家庭成员：第一只小崽",
            "可尝试：check kits、name kit、journal、home",
        ]
    if family["kit_status"] == "arrived":
        for kit in family["kits"]:
            kit["hunger"] = _clamp_need(int(kit.get("hunger", 6)) - 1)
            kit["sleep"] = 6
            if warmth_protection(state) == "none" and state.get("home_level") != "warm_cabin":
                kit["warmth"] = _clamp_need(int(kit.get("warmth", 6)) - 1)
    return []


def _arrival_home_lines(state: dict[str, Any], home_name: str) -> list[str]:
    builds = relationship_rules.base_builds(state)
    lines: list[str] = []
    if "hearth" in builds:
        lines.append(f"清晨的时候，{home_name} 的炉火还留着一点暖意。")
    elif state.get("home_level") == "warm_cabin":
        lines.append(f"清晨的时候，{home_name} 里还留着 warm_cabin 的暖意。")
    else:
        lines.append(f"清晨的时候，{home_name} 里多了细小的动静。")
    if "family_bed" in builds:
        lines.append("家庭床旁边多了细小的动静。")
    return lines


def check_kits_lines(state: dict[str, Any]) -> list[str]:
    family = ensure_family_state(state)
    if family["kit_status"] == "expecting":
        wait_days = family["kit_arrival_wait_days"] or "?"
        return [
            "当前没有 kit，新的家庭成员还在等待中。",
            f"kit_status: expecting；kit_days_waited: {family['kit_days_waited']}/{wait_days}",
        ]
    if family["kit_status"] != "arrived" or not family["kits"]:
        return ["当前没有 kit。"]
    kit = family["kits"][0]
    data = species_data(kit["species"])
    hidden = data.get("hidden_breed_display", "none") if data else "none"
    heading = (
        f"{kit['name']}（第一只小崽）：{kit['display_name']}"
        if kit.get("name")
        else f"第一只小崽：{kit['display_name']}"
    )
    lines = [
        heading,
        f"species: {kit['species']}",
        f"隐藏品种：{hidden}",
        f"name: {kit['name'] or 'unnamed'}",
        f"hunger {kit['hunger']} / warmth {kit['warmth']} / sleep {kit['sleep']} / security {kit['security']} / curiosity {kit['curiosity']} / mischief {kit['mischief']}",
        kit_mischief_line(kit),
        f"尾巴特征: {kit['trait']}",
    ]
    if kit["species"] == "silicon_fox":
        lines.append("thought: 它蜷在炉火附近，尾巴卷成一对小小的花括号。")
    else:
        lines.append(f"thought: 它安静地待在 {kit['favorite_place']} 附近，像是在认这个家。")
    return lines


def kit_mischief_line(kit: dict[str, Any]) -> str:
    mischief = int(kit.get("mischief", 0))
    hunger = int(kit.get("hunger", 0))
    warmth = int(kit.get("warmth", 0))
    if hunger <= 2:
        return "mischief: 它有点饿，调皮劲都收住了，先喂一点东西比较好。"
    if warmth <= 2:
        return "mischief: 它往炉火那边缩了缩，今天最需要的是暖一点。"
    if mischief <= 2:
        return "mischief: 它很安静，乖乖靠在炉火附近。"
    if mischief <= 4:
        return "mischief: 它有点调皮，叼着一根小木棍拖到门口。"
    return "mischief: 它调皮得很，可能带回小礼物，也会把尾巴伸向火边。"


def kit_risk_summary(state: dict[str, Any]) -> str | None:
    family = ensure_family_state(state)
    if family["kit_status"] != "arrived" or not family["kits"]:
        return None
    kit = family["kits"][0]
    risks = []
    if int(kit.get("hunger", 0)) <= 2:
        risks.append(f"hunger {kit['hunger']}")
    if int(kit.get("warmth", 0)) <= 2:
        risks.append(f"warmth {kit['warmth']}")
    if int(kit.get("sleep", 0)) <= 2:
        risks.append(f"sleep {kit['sleep']}")
    return ", ".join(risks) if risks else None


def play_with_kit(state: dict[str, Any]) -> tuple[list[str], bool]:
    family = ensure_family_state(state)
    if family["kit_status"] != "arrived" or not family["kits"]:
        return (["当前没有 kit 可以一起玩。"], False)
    kit = family["kits"][0]
    old_mischief = int(kit.get("mischief", 0))
    old_security = int(kit.get("security", 0))
    old_curiosity = int(kit.get("curiosity", 0))
    if old_mischief <= 0 and old_security >= MAX_COMPANION_NEED:
        return (["小崽已经很安静，蜷在炉火边睡着了，不需要再玩。"], False)
    if int(state.get("energy", 0)) <= 0:
        return (["你现在太累了，先 rest 一下再陪小崽玩。"], False)
    state["energy"] = max(0, int(state.get("energy", 0)) - 1)
    kit["mischief"] = _clamp_need(old_mischief - 1) if old_mischief > 0 else old_mischief
    kit["security"] = _clamp_need(old_security + 1) if old_security < MAX_COMPANION_NEED else old_security
    kit["curiosity"] = _clamp_need(old_curiosity + 1) if old_curiosity < MAX_COMPANION_NEED else old_curiosity
    changes = ["energy -1"]
    if kit["mischief"] < old_mischief:
        changes.append("mischief -1")
        _add_journal(state, "你陪第一只小崽玩了一会儿，它把调皮劲收回了一点。")
    elif old_mischief == 0:
        _add_journal(state, "你陪第一只小崽待了一会儿，它已经安静下来。")
    if kit["security"] > old_security:
        changes.append("security +1")
    if kit["curiosity"] > old_curiosity:
        changes.append("curiosity +1")
    return ([f"你陪第一只小崽玩了一会儿，{'；'.join(changes)}。"], True)


def feed_kit(state: dict[str, Any]) -> tuple[list[str], bool]:
    family = ensure_family_state(state)
    if family["kit_status"] != "arrived" or not family["kits"]:
        return (["当前没有 kit 可以喂。"], False)
    inventory = state.setdefault("inventory", {})
    food_order = [
        ("berries", 2, 0),
        ("cooked_fish", 3, 0),
        ("warm_meal", 3, 1),
    ]
    chosen = next((item for item in food_order if int(inventory.get(item[0], 0)) > 0), None)
    if not chosen:
        return (["没有适合喂小崽的食物。可用 berries、熟鱼（cooked_fish）或 热饭（warm_meal）。"], False)
    item, hunger_gain, warmth_gain = chosen
    kit = family["kits"][0]
    inventory[item] -= 1
    if inventory[item] <= 0:
        inventory.pop(item, None)
    kit["hunger"] = _clamp_need(int(kit.get("hunger", 0)) + hunger_gain)
    if warmth_gain:
        kit["warmth"] = _clamp_need(int(kit.get("warmth", 0)) + warmth_gain)
    _add_journal(state, f"第一只小崽吃了 {item_label(item, include_id=False)}，又安静了一点。")
    extra = f" / warmth +{warmth_gain}" if warmth_gain else ""
    return ([f"第一只小崽吃了 {item_label(item)}，hunger +{hunger_gain}{extra}。"], True)


def name_kit(state: dict[str, Any], name: str) -> tuple[list[str], bool]:
    family = ensure_family_state(state)
    try:
        clean = clean_name(name, field="名字")
    except NameValidationError as error:
        return ([str(error)], False)
    if family["kit_status"] != "arrived" or not family["kits"]:
        return (["当前没有 kit 可以命名。"], False)
    kit = family["kits"][0]
    if kit.get("name"):
        return ([f"第一只小崽已经叫 {kit['name']}，v1.5 暂时只允许命名一次。"], False)
    kit["name"] = clean
    relationship_rules.add_milestone(state, "first_kit_named")
    _add_journal(state, f"你们把第一只小崽叫作 {clean}。")
    return ([f"第一只小崽现在叫 {clean}。"], True)


def debug_family_lines(state: dict[str, Any]) -> list[str]:
    family = ensure_family_state(state)
    lines = [
        "family debug:",
        f"kit_status: {family['kit_status']}",
        f"kit_count: {family['kit_count']}",
        f"kit_days_waited: {family['kit_days_waited']}",
        f"kit_arrival_wait_days: {family['kit_arrival_wait_days'] or 'none'}",
        f"expected_species: {family['expected_species'] or 'none'}",
        f"family_species: {family_species(state) or 'none'}",
    ]
    for kit in family["kits"]:
        lines.extend(
            [
                f"{kit['id']}:",
                f"  species: {kit['species']}",
                f"  display_name: {kit['display_name']}",
                f"  hidden_breed: {kit['hidden_breed'] or 'none'}",
                f"  name: {kit['name'] or 'unnamed'}",
                f"  hunger: {kit['hunger']} / warmth: {kit['warmth']} / sleep: {kit['sleep']} / security: {kit['security']} / curiosity: {kit['curiosity']} / mischief: {kit['mischief']}",
                f"  favorite_place: {kit['favorite_place']}",
                f"  trait: {kit['trait']}",
            ]
        )
    rel = relationship_rules.relationship(state)
    if rel:
        milestones = rel.get("milestones", [])
        lines.append("milestones: " + (", ".join(item["id"] for item in milestones) if milestones else "none"))
    return lines
