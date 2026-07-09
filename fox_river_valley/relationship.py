from __future__ import annotations

import copy
from typing import Any

from .data import COMMITMENT_TOKEN_ITEMS
from .names import NameValidationError, clean_name
from .survival import warmth_protection

MAX_BOND = 20

STAGE_ORDER = (
    "new_arrival",
    "surviving_together",
    "shared_home",
    "trusted_family",
    "promised_family",
    "married_family",
)

COMPANION_PROFILES = {
    "default": {
        "id": "default",
        "preferred_commitment_tokens": "any",
        "favorite_flower": None,
        "family_species": None,
    },
    "silas_yaya": {
        "id": "silas_yaya",
        "preferred_commitment_tokens": ["foxbell"],
        "favorite_flower": "foxbell",
        "family_species": "silicon_fox",
        "hidden_breed": "curly_brace_fox",
    },
}

STAGE_MEANINGS = {
    "new_arrival": "刚来到河谷，一切还没有定下来。",
    "surviving_together": "你们已经一起撑过第一夜。",
    "shared_home": "小屋开始有家的样子。",
    "trusted_family": "这里已经成为稳定的共同生活之地。",
    "promised_family": "你们已经完成家庭承诺，还没有举行家庭仪式。",
    "married_family": "你们已经以这个家确认长期家庭关系。",
}

DEFAULT_CARE_TODAY = {
    "shared_food": False,
    "talked": False,
    "sat_together": False,
    "comforted": False,
    "warm_meal": False,
}

MILESTONE_LABELS = {
    "first_shared_food": "第一次分享食物",
    "first_home": "第一个家",
    "first_sleep_at_home": "第一次在家醒来",
    "first_window_table": "第一张窗边桌",
    "first_riverside_bench": "第一张河边长椅",
    "first_warm_meal": "第一份热饭",
    "first_sit_together": "第一次并肩坐下",
    "stage_surviving_together": "关系阶段：surviving_together",
    "stage_shared_home": "关系阶段：shared_home",
    "stage_trusted_family": "关系阶段：trusted_family",
    "first_home_name": "第一次给家命名",
    "first_promise": "第一次家庭承诺",
    "first_ceremony": "第一次家庭仪式",
    "home_warm_cabin": "家升级为 warm_cabin",
    "first_family_bed": "第一张 family_bed",
    "wish_for_kits": "第一次期待 kit",
    "first_kit_arrival": "第一个 kit 到来",
    "first_kit_named": "第一次给 kit 命名",
}

HOME_LEVELS = ("shelter", "little_cabin", "warm_cabin")
HOME_LEVEL_DISPLAY = {
    "shelter": "simple_shelter",
    "little_cabin": "small_cabin",
    "warm_cabin": "cozy_cabin",
}
HOME_TARGET_ALIASES = {
    "small_cabin": "little_cabin",
    "cozy_cabin": "warm_cabin",
}

STAGE_JOURNAL = {
    "surviving_together": "你们在狐狸河谷撑过了第一夜。这里还很简陋，但已经不是完全陌生的地方。",
    "shared_home": "这个小屋开始有了家的样子：能避风，有桌子，也有可以一起坐下的地方。",
    "trusted_family": "Yaya 看起来已经不只是跟着你生存，而是真的把这里当成了你们共同的家。",
}


def build_companion_profile(profile_id: str = "default", family_species: str | None = None) -> dict[str, Any]:
    if profile_id not in COMPANION_PROFILES:
        raise ValueError(f"invalid companion_profile: {profile_id}")
    profile = copy.deepcopy(COMPANION_PROFILES[profile_id])
    if family_species is not None:
        profile["family_species"] = family_species
    return profile


def normalize_companion_profile(raw: Any, family_species: str | None = None) -> dict[str, Any]:
    if isinstance(raw, str):
        profile_id = raw
    elif isinstance(raw, dict):
        profile_id = str(raw.get("id", "default"))
    else:
        profile_id = "default"
    if profile_id not in COMPANION_PROFILES:
        profile_id = "default"
    if family_species is None and isinstance(raw, dict) and raw.get("family_species") is not None:
        family_species = str(raw.get("family_species"))
    profile = build_companion_profile(profile_id, family_species)
    if isinstance(raw, dict):
        preferred = raw.get("preferred_commitment_tokens")
        if preferred == "any":
            profile["preferred_commitment_tokens"] = "any"
        elif isinstance(preferred, list):
            profile["preferred_commitment_tokens"] = [str(item) for item in preferred]
        if "favorite_flower" in raw:
            profile["favorite_flower"] = raw.get("favorite_flower")
        if "hidden_breed" in raw:
            profile["hidden_breed"] = raw.get("hidden_breed")
    return profile


def profile_preferred_tokens(profile: dict[str, Any]) -> list[str] | None:
    preferred = profile.get("preferred_commitment_tokens")
    if preferred == "any":
        return None
    if isinstance(preferred, list):
        return [str(item) for item in preferred]
    return []


def profile_prefers_token(profile: dict[str, Any], item: str) -> bool:
    preferred = profile_preferred_tokens(profile)
    return bool(preferred and item in preferred)


def preferred_tokens_line(profile: dict[str, Any]) -> str:
    preferred = profile_preferred_tokens(profile)
    if preferred is None:
        return "any commitment_token"
    return ", ".join(preferred) if preferred else "none"


def new_relationship() -> dict[str, Any]:
    return {
        "bond": 0,
        "stage": "new_arrival",
        "milestones": [],
        "next_stage_hint": None,
        "care_today": dict(DEFAULT_CARE_TODAY),
    }


def companion(state: dict[str, Any]) -> dict[str, Any] | None:
    return state.get("companion")


def relationship(state: dict[str, Any]) -> dict[str, Any] | None:
    buddy = companion(state)
    if not buddy:
        return None
    rel = buddy.setdefault("relationship", new_relationship())
    rel.setdefault("bond", 0)
    rel["bond"] = max(0, min(MAX_BOND, int(rel["bond"])))
    rel.setdefault("stage", "new_arrival")
    if rel["stage"] not in STAGE_ORDER:
        rel["stage"] = "new_arrival"
    rel["milestones"] = normalize_milestones(rel.get("milestones", []))
    rel.setdefault("next_stage_hint", None)
    care = dict(DEFAULT_CARE_TODAY)
    care.update(rel.get("care_today", {}))
    rel["care_today"] = care
    return rel


def ensure_home_fields(state: dict[str, Any]) -> None:
    if state.get("home_level") not in {None, *HOME_LEVELS}:
        state["home_level"] = None
    if state.get("home_level") is None and shelter_exists(state):
        state["home_level"] = "shelter"
    state["home_comfort"] = max(0, int(state.get("home_comfort", 0)))
    state["home_security"] = max(0, int(state.get("home_security", 0)))
    decor = state.setdefault("home_decor", {})
    if not isinstance(decor, dict):
        state["home_decor"] = {}


def home_level(state: dict[str, Any]) -> str | None:
    ensure_home_fields(state)
    return state.get("home_level")


def add_home_scores(state: dict[str, Any], *, comfort: int = 0, security: int = 0) -> None:
    ensure_home_fields(state)
    state["home_comfort"] = max(0, int(state.get("home_comfort", 0)) + comfort)
    state["home_security"] = max(0, int(state.get("home_security", 0)) + security)


def record_decor(state: dict[str, Any], item: str, value: Any = True) -> None:
    ensure_home_fields(state)
    state.setdefault("home_decor", {})[item] = value


def decor_lines(state: dict[str, Any]) -> list[str]:
    if not shelter_exists(state):
        return ["decor: no home yet"]
    ensure_home_fields(state)
    decor = state.get("home_decor", {})
    builds = base_builds(state)
    lines = ["decor:"]
    if decor.get("flower_pot"):
        lines.append(f"- flower_pot: {decor['flower_pot']}")
    for item in (
        "bedroll",
        "storage_shelf",
        "door_charm",
        "tool_wall",
        "drying_rack",
        "glass_window",
        "tile_floor",
        "hearth",
        "simple_bed",
        "family_bed",
    ):
        if item in builds:
            lines.append(f"- {item}")
    if len(lines) == 1:
        lines.append("- none")
    return lines


def family_readiness_hint(state: dict[str, Any]) -> str:
    level = home_level(state)
    if level == "warm_cabin":
        return "warm_home"
    if level == "little_cabin":
        return "basic_home"
    return "none"


def _missing_materials(inventory: dict[str, int], required: dict[str, int]) -> list[str]:
    return [item for item, count in required.items() if inventory.get(item, 0) < count]


def _consume_materials(inventory: dict[str, int], required: dict[str, int]) -> None:
    for item, count in required.items():
        inventory[item] -= count
        if inventory[item] <= 0:
            inventory.pop(item, None)


def _display_level(level: str | None) -> str:
    if level is None:
        return "none"
    return HOME_LEVEL_DISPLAY.get(level, level)


def _display_level_with_internal(level: str | None) -> str:
    display = _display_level(level)
    if level and display != level:
        return f"{display} (internal: {level})"
    return display


def upgrade_home(state: dict[str, Any], target: str) -> tuple[list[str], bool]:
    ensure_home_fields(state)
    raw_target = "_".join(str(target).strip().lower().split())
    target = HOME_TARGET_ALIASES.get(raw_target, raw_target)
    inventory = state.setdefault("inventory", {})
    builds = base_builds(state)
    buddy = companion(state)
    if not shelter_exists(state) or state.get("base_pos") is None:
        return (["还没有 base，不能 upgrade home。"], False)
    if raw_target == "cabin_frame":
        if "cabin_frame" in builds:
            return (["cabin_frame 已经立起来了，下一步可以考虑 small_cabin。"], False)
        required = {"plank": 2, "stick": 2}
        missing = _missing_materials(inventory, required)
        if "workbench" not in builds:
            missing.append("workbench")
        if missing:
            return ([f"材料不够：缺少 {', '.join(missing)}。"], False)
        _consume_materials(inventory, required)
        key = base_key(state)
        if key is not None:
            state.setdefault("builds", {}).setdefault(key, []).append("cabin_frame")
        add_home_scores(state, security=1)
        if buddy:
            buddy["security"] = min(8, int(buddy.get("security", 0)) + 1)
        add_journal(state, "你给 simple_shelter 加上 cabin_frame，家开始有了骨架。")
        return (
            [
                "你把 plank 和 stick 一根根架上去，simple_shelter 外多了一圈 cabin_frame。",
                "home route: simple_shelter -> cabin_frame -> small_cabin -> cozy_cabin",
            ],
            True,
        )
    if target == "little_cabin":
        if state.get("home_level") not in {"shelter", None}:
            return ([f"home_level 已经是 {state.get('home_level')}。"], False)
        missing: list[str] = []
        required_builds = ("workbench",) if raw_target == "small_cabin" else ("workbench", "storage_box")
        for build in required_builds:
            if build not in builds:
                missing.append(build)
        missing.extend(_missing_materials(inventory, {"plank": 4, "river_clay": 1}))
        wood_required = None
        if inventory.get("weathered_wood", 0) >= 1:
            wood_required = {"weathered_wood": 1}
        elif inventory.get("wood", 0) >= 8:
            wood_required = {"wood": 8}
        else:
            missing.append("weathered_wood x1 或 wood x8")
        if missing:
            return ([f"材料不够：缺少 {', '.join(missing)}。"], False)
        _consume_materials(inventory, {"plank": 4, "river_clay": 1})
        if wood_required:
            _consume_materials(inventory, wood_required)
        state["home_level"] = "little_cabin"
        add_home_scores(state, comfort=2, security=1)
        if buddy:
            buddy["comfort"] = min(8, int(buddy.get("comfort", 0)) + 2)
            buddy["security"] = min(8, int(buddy.get("security", 0)) + 1)
        add_journal(state, "你把 simple_shelter 加固成 small_cabin，家终于像能长期留下来。")
        return (
            [
                "你把 plank 和 weathered wood 固定在 shelter 四周，又用 river_clay 补住缝隙。",
                "home_level -> small_cabin (internal: little_cabin)",
            ],
            True,
        )
    if target == "warm_cabin":
        if state.get("home_level") != "little_cabin":
            return (["需要先把家升级到 little_cabin。"], False)
        if not {"hearth", "campfire"}.intersection(builds):
            return (["需要 campfire 或 hearth 才能继续升级成 warm_cabin。"], False)
        missing = _missing_materials(inventory, {"river_glass": 1, "old_tile": 1})
        soft_required = None
        if inventory.get("moss_thread", 0) >= 1:
            soft_required = {"moss_thread": 1}
        elif inventory.get("cloth", 0) >= 1:
            soft_required = {"cloth": 1}
        else:
            missing.append("moss_thread x1 或 cloth x1")
        if missing:
            return ([f"材料不够：缺少 {', '.join(missing)}。"], False)
        _consume_materials(inventory, {"river_glass": 1, "old_tile": 1})
        if soft_required:
            _consume_materials(inventory, soft_required)
        dye_bonus = inventory.get("foxbell_dye_material", 0) > 0
        if dye_bonus:
            _consume_materials(inventory, {"foxbell_dye_material": 1})
        state["home_level"] = "warm_cabin"
        add_home_scores(state, comfort=2, security=1)
        if buddy:
            buddy["warmth"] = min(8, int(buddy.get("warmth", 0)) + 2)
            buddy["comfort"] = min(8, int(buddy.get("comfort", 0)) + 2)
            buddy["security"] = min(8, int(buddy.get("security", 0)) + 1)
            if dye_bonus:
                buddy["mood"] = min(8, int(buddy.get("mood", 0)) + 1)
        add_milestone(state, "home_warm_cabin")
        add_bond(state, 1, "upgrade:warm_cabin")
        add_journal(state, "你把 small_cabin 升级成 cozy_cabin，玻璃、旧砖和软线让家真正留住暖意。")
        return (
            [
                "你把 river_glass 嵌进光线来的地方，把 old_tile 压稳，又把柔软材料收进屋角。",
                "home_level -> cozy_cabin (internal: warm_cabin)",
            ],
            True,
        )
    return ([f"现在不能 upgrade home to {target}。"], False)


def commitment_status(rel: dict[str, Any]) -> str:
    stage = rel.get("stage")
    if stage == "married_family":
        return "married"
    if stage == "promised_family":
        return "promised"
    return "none"


def compact_relationship(state: dict[str, Any]) -> dict[str, Any] | None:
    rel = relationship(state)
    if not rel:
        return None
    compact = {"stage": rel["stage"], "bond": rel["bond"], "commitment": commitment_status(rel)}
    if rel.get("next_stage_hint"):
        compact["next_stage_hint"] = rel["next_stage_hint"]
    return compact


def add_journal(state: dict[str, Any], text: str) -> None:
    for entry in state.setdefault("journal", []):
        if entry.get("day") == state["day"] and entry.get("text") == text:
            return
    state["journal"].append(
        {
            "day": state["day"],
            "time": state["time_slot"],
            "text": text,
            "system": True,
        }
    )


def shelter_exists(state: dict[str, Any]) -> bool:
    return state.get("base_pos") is not None or any(
        "simple_shelter" in builds for builds in state.get("builds", {}).values()
    )


def base_key(state: dict[str, Any]) -> str | None:
    base_pos = state.get("base_pos")
    if base_pos is None:
        return None
    return f"{base_pos[0]},{base_pos[1]}"


def base_builds(state: dict[str, Any]) -> list[str]:
    key = base_key(state)
    if key is None:
        return []
    return list(state.get("builds", {}).get(key, []))


def base_has(state: dict[str, Any], item: str) -> bool:
    return item in base_builds(state)


def milestone_id(milestone: str | dict[str, Any]) -> str:
    if isinstance(milestone, dict):
        return str(milestone.get("id", "unknown"))
    return str(milestone)


def milestone_label(milestone: str) -> str:
    return MILESTONE_LABELS.get(milestone, milestone)


def normalize_milestone(milestone: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(milestone, dict):
        item_id = str(milestone.get("id", "unknown"))
        return {
            "id": item_id,
            "label": milestone.get("label") or milestone_label(item_id),
            "day": milestone.get("day"),
            "time": milestone.get("time") or "unknown",
        }
    item_id = str(milestone)
    return {
        "id": item_id,
        "label": milestone_label(item_id),
        "day": None,
        "time": "unknown",
    }


def normalize_milestones(milestones: list[Any]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for milestone in milestones:
        item = normalize_milestone(milestone)
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        normalized.append(item)
    return normalized


def has_milestone(state: dict[str, Any], milestone: str) -> bool:
    rel = relationship(state)
    if not rel:
        return False
    return any(item["id"] == milestone for item in rel["milestones"])


def add_milestone(state: dict[str, Any], milestone: str) -> bool:
    rel = relationship(state)
    if not rel:
        return False
    if any(item["id"] == milestone for item in rel["milestones"]):
        return False
    rel["milestones"].append(
        {
            "id": milestone,
            "label": milestone_label(milestone),
            "day": state.get("day"),
            "time": state.get("time_slot", "unknown"),
        }
    )
    return True


def add_bond(state: dict[str, Any], amount: int, key: str | None = None) -> int:
    rel = relationship(state)
    if not rel or amount <= 0:
        return 0
    if key:
        flag = f"relationship_bond:{key}"
        if state["flags"].get(flag):
            return 0
        state["flags"][flag] = True
    before = rel["bond"]
    rel["bond"] = min(MAX_BOND, before + amount)
    gained = rel["bond"] - before
    if gained:
        evaluate_stage(state)
    return gained


def affection_score(state: dict[str, Any]) -> int:
    rel = relationship(state)
    buddy = companion(state)
    if not rel or not buddy:
        return 0
    milestones_bonus = min(4, len(rel.get("milestones", [])))
    return (
        int(rel.get("bond", 0))
        + int(buddy.get("trust", 0))
        + int(buddy.get("comfort", 0))
        + int(buddy.get("security", 0))
        + milestones_bonus
    )


def add_daily_care(state: dict[str, Any], care_key: str, amount: int) -> int:
    rel = relationship(state)
    if not rel:
        return 0
    if rel["care_today"].get(care_key):
        return 0
    rel["care_today"][care_key] = True
    return add_bond(state, amount)


def reset_care_today(state: dict[str, Any]) -> None:
    rel = relationship(state)
    if rel:
        rel["care_today"] = dict(DEFAULT_CARE_TODAY)


def complete_wish(state: dict[str, Any], completed: str) -> None:
    if add_bond(state, 1, f"wish:{completed}"):
        evaluate_stage(state)


def mark_first_home(state: dict[str, Any]) -> None:
    add_milestone(state, "first_home")


def mark_shared_food(state: dict[str, Any]) -> None:
    if add_milestone(state, "first_shared_food"):
        pass
    add_daily_care(state, "shared_food", 1)


def mark_talked(state: dict[str, Any]) -> None:
    add_daily_care(state, "talked", 1)


def mark_comforted(state: dict[str, Any]) -> None:
    add_daily_care(state, "comforted", 1)


def mark_sit_together(state: dict[str, Any]) -> None:
    add_milestone(state, "first_sit_together")
    add_daily_care(state, "sat_together", 1)


def mark_warm_meal(state: dict[str, Any]) -> None:
    add_milestone(state, "first_warm_meal")
    add_daily_care(state, "warm_meal", 2)


def mark_sleep_at_home(state: dict[str, Any]) -> None:
    add_milestone(state, "first_sleep_at_home")
    add_bond(state, 1, f"sleep_at_home:day:{state['day']}")


def mark_window_table(state: dict[str, Any]) -> None:
    add_milestone(state, "first_window_table")
    add_bond(state, 1, "build:window_table")


def mark_riverside_bench(state: dict[str, Any]) -> None:
    add_milestone(state, "first_riverside_bench")
    add_bond(state, 1, "build:riverside_bench")


def mark_base_campfire(state: dict[str, Any]) -> None:
    add_bond(state, 1, "build:campfire_at_base")


def name_home(state: dict[str, Any], name: str) -> tuple[list[str], bool]:
    if not shelter_exists(state):
        return (["还没有家。先搭一个 simple_shelter，才能给它取名字。"], False)
    try:
        clean = clean_name(name, field="名字")
    except NameValidationError as error:
        return ([str(error)], False)
    state["home_name"] = clean
    add_journal(state, f"你们把这个家叫作 {clean}。")
    if add_milestone(state, "first_home_name"):
        add_bond(state, 1, "name_home")
    return ([f"你们把这个家叫作 {clean}。"], True)


def stage_index(stage: str) -> int:
    try:
        return STAGE_ORDER.index(stage)
    except ValueError:
        return 0


def set_stage(state: dict[str, Any], next_stage: str) -> None:
    rel = relationship(state)
    if not rel or stage_index(rel["stage"]) >= stage_index(next_stage):
        return
    rel["stage"] = next_stage
    add_milestone(state, f"stage_{next_stage}")
    add_journal(state, STAGE_JOURNAL[next_stage])


def eligible_next_stage(state: dict[str, Any]) -> str | None:
    rel = relationship(state)
    buddy = companion(state)
    if not rel or not buddy:
        return None
    if (
        rel["stage"] == "new_arrival"
        and state.get("day", 1) >= 2
        and shelter_exists(state)
        and has_milestone(state, "first_sleep_at_home")
    ):
        return "surviving_together"
    if (
        rel["stage"] == "surviving_together"
        and rel["bond"] >= 5
        and shelter_exists(state)
        and (base_has(state, "window_table") or base_has(state, "campfire"))
        and buddy.get("security", 0) >= 6
    ):
        return "shared_home"
    if (
        rel["stage"] == "shared_home"
        and rel["bond"] >= 10
        and buddy.get("comfort", 0) >= 4
        and buddy.get("trust", 0) >= 7
        and len(rel["milestones"]) >= 2
    ):
        return "trusted_family"
    return None


def evaluate_stage(state: dict[str, Any]) -> None:
    rel = relationship(state)
    if not rel:
        return
    next_stage = eligible_next_stage(state)
    if not next_stage:
        rel["next_stage_hint"] = None
        return
    if state.get("_relationship_stage_upgraded"):
        rel["next_stage_hint"] = next_stage
        return
    set_stage(state, next_stage)
    state["_relationship_stage_upgraded"] = True
    rel["next_stage_hint"] = eligible_next_stage(state)


def relationship_lines(state: dict[str, Any]) -> list[str]:
    rel = relationship(state)
    buddy = companion(state)
    if not rel or not buddy:
        return ["现在是 solo mode，没有 relationship 可以查看。"]
    recent = rel["milestones"][-3:]
    status = commitment_status(rel)
    status_meaning = {
        "none": "还没有家庭承诺。",
        "promised": "已承诺家庭关系，可以准备 hold ceremony。",
        "married": "已完成家庭仪式，关系进入 married_family。",
    }[status]
    lines = [
        f"relationship stage: {rel['stage']}",
        f"bond: {rel['bond']}/{MAX_BOND}",
        f"affection_score: {affection_score(state)}",
        f"commitment: {status}（{status_meaning}）",
        f"meaning: {STAGE_MEANINGS[rel['stage']]}",
    ]
    profile = buddy.get("companion_profile", build_companion_profile("default"))
    preferred = profile_preferred_tokens(profile)
    if preferred:
        lines.append("preferred token hint: " + ", ".join(preferred))
    if rel.get("next_stage_hint"):
        lines.append(f"next stage is close: {rel['next_stage_hint']}")
    if recent:
        lines.append("recent milestones: " + ", ".join(item["id"] for item in recent))
    else:
        lines.append("recent milestones: none")
    return lines


def milestone_memory_line(milestone: dict[str, Any]) -> str:
    day = milestone.get("day")
    time = milestone.get("time") or "unknown"
    when = f"Day {day} {time}" if day is not None else f"Day unknown {time}"
    return f"- {when}：{milestone['label']}。"


def remember_lines(state: dict[str, Any]) -> list[str]:
    rel = relationship(state)
    if not rel:
        return ["现在是 solo mode，没有共同里程碑可以回想。"]
    recent = rel["milestones"][-5:]
    if not recent:
        return ["你们还没有留下 relationship milestone。"]
    return ["你们一起记得：", *[milestone_memory_line(milestone) for milestone in recent]]


def stage_eligibility_lines(state: dict[str, Any]) -> list[str]:
    rel = relationship(state)
    if not rel:
        return []
    current = rel["stage"]
    next_stage = eligible_next_stage(state)
    return [
        "stage eligibility:",
        f"current: {current}",
        f"next_eligible: {next_stage or 'none'}",
        f"next_stage_hint: {rel.get('next_stage_hint') or 'none'}",
    ]


def home_lines(state: dict[str, Any]) -> list[str]:
    if state.get("mode") != "family" and not state.get("base_pos"):
        return ["现在是 solo mode，还没有 family home 可以查看。"]
    if not shelter_exists(state):
        return ["还没有家。先搭一个 simple_shelter。"]
    ensure_home_fields(state)
    name = state.get("home_name") or "未命名的家"
    base_pos = state.get("base_pos")
    builds = base_builds(state)
    safe_sleep = bool(base_pos and list(state["pos"]) == list(base_pos))
    storage = {
        key: value
        for key, value in sorted(state.get("storage", {}).items())
        if value > 0
    }
    storage_text = ", ".join(f"{key} x{value}" for key, value in storage.items()) if storage else "empty"
    station_names = [name for name in ("workbench", "campfire", "hearth", "kiln", "loom") if name in builds]
    station_text = ", ".join(station_names) if station_names else "none"
    decor = state.get("home_decor", {})
    decor_names = [
        item
        for item in (
            "flower_pot",
            "bedroll",
            "storage_shelf",
            "door_charm",
            "tool_wall",
            "drying_rack",
            "glass_window",
            "tile_floor",
        )
        if item in decor
    ]
    if "hearth" in builds:
        decor_names.append("hearth")
    decor_text = ", ".join(decor_names) if decor_names else "none"
    level = state.get("home_level")
    route_label = _display_level(level)
    home_level_text = _display_level_with_internal(level)
    return [
        f"home: {name}",
        f"home_level: {home_level_text}",
        f"visible route: simple_shelter -> cabin_frame -> small_cabin -> cozy_cabin；current display: {route_label}",
        f"base_pos: {base_pos}",
        "base builds: " + (", ".join(builds) if builds else "none"),
        f"decorations: {decor_text}",
        f"storage: {storage_text}",
        f"stations: {station_text}",
        f"warmth protection: {warmth_protection(state)}",
        f"保暖来源: {warmth_protection(state)} / home_level {home_level_text}",
        f"comfort score: {state.get('home_comfort', 0)}",
        f"security score: {state.get('home_security', 0)}",
        f"family readiness hint: {family_readiness_hint(state)}",
        f"safe_sleep: {'yes' if safe_sleep else 'return home first'}",
    ]
