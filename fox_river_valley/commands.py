from __future__ import annotations

from typing import Any

from . import actions
from .building import build
from .crafting import craft, recipe_lines
from .render import render
from .state import clone_state, create_state

GAME_OVER_ALLOWED = {"help", "status", "runtime", "observer", "load", "restart"}


def _help_lines(rest: str, state: dict[str, Any]) -> list[str]:
    topic = rest.lower().strip()
    if topic in {"family", "kits"}:
        return [
            "家庭相关命令：",
            "- family readiness",
            "- wish for kits",
            "- check kits",
            "- name kit <name>",
            "- play with kit",
            "- feed kit",
            "- debug family",
        ]
    if topic == "check kits":
        family = state.get("family", {})
        locked = "未解锁：需要先 family readiness -> wish for kits，并等第一只小崽到来。" if family.get("kit_status") != "arrived" else "已解锁。"
        return [
            "check kits",
            "用途：查看第一只小崽的 hunger / warmth / sleep / security / curiosity / mischief。",
            locked,
        ]
    topics = {
        "propose": [
            "propose with <item>",
            "用途：用 commitment_token 提出家庭承诺。",
            "大致条件：family mode、relationship stage 至少 shared_home、bond >= 10、trust >= 7、comfort >= 4、security >= 6、已命名 home、已有 shelter/base。",
        ],
        "hold ceremony": [
            "hold ceremony / commit family",
            "用途：在 promised_family 后完成家庭仪式。",
            "大致条件：promised_family、home_name、campfire 或 hearth、window_table 或 riverside_bench、warm_meal 或 flower。",
        ],
        "family readiness": [
            "family readiness",
            "用途：查看是否可以 wish for kits。",
            "大致条件：married_family、warm_cabin、家庭床、炉火、花/foxbell 锚点、食物安全、companion security/comfort。",
        ],
        "deposit": [
            "deposit <item> <count>",
            "用途：把物品放进 storage_box。",
            "大致条件：在 base tile，且家里已有 storage_box。",
        ],
        "withdraw": [
            "withdraw <item> <count>",
            "用途：从 storage_box 取出物品。",
            "大致条件：在 base tile，且 storage 里有足够物品。",
        ],
        "serve": [
            "serve warm_meal / serve cooked_fish / serve berries",
            "用途：和 companion 分享新鲜食物，能完成 find fresh food 类 wish。",
            "不适合：serve stale_food 会失败，建议 discard。",
        ],
        "weather": [
            "weather",
            "用途：查看今天的天气影响和 night pressure。",
            "提示：rain 会浇水，fog 会影响探索，cold_wind 需要保暖。",
        ],
        "discard": [
            "discard <item> [count|all]",
            "常用：discard stale food 会丢弃所有 stale_food / stale_fish / spoiled_berries。",
            "也可：discard spoiled_berries（默认丢 1 个），或 discard <item> all。",
        ],
    }
    if topic in topics:
        return topics[topic]
    if topic:
        return [f"暂时没有 help {rest} 的详细页。可试试 help family、help serve、help weather。"]
    lines = [
        "可用命令：status, runtime, recap, options, observer, open observer, calendar, weather, food, garden, inventory, storage, recipes, look, inspect, map, move, return home, relationship, home, decor, gather, collect water, chop, mine, fish, explore, plant, water crops, harvest, cook fish, make charcoal, make tea, make warm_meal, serve warm_meal, serve cooked_fish, serve berries, eat, wait, rest, sleep, check companion, ask companion, journal, goal, save, load。",
        "家庭相关命令可用 help family 查看。常用详细页：help propose, help hold ceremony, help family readiness, help check kits, help deposit, help withdraw, help serve, help weather。",
    ]
    if state.get("mode") == "family":
        lines.append("当前阶段提示：family mode 已开启，可用 check companion / relationship / home。")
    return lines


def _game_over_command_allowed(action: str, rest: str) -> bool:
    if action in GAME_OVER_ALLOWED:
        return True
    return action == "open" and rest.lower() == "observer"


def run_command(command: str, state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    state.pop("_relationship_stage_upgraded", None)
    original = state
    next_state = clone_state(state)
    text = command.strip()
    if not text:
        return render(["听不懂这个空命令。"], original), original

    head, _, rest = text.partition(" ")
    action = head.lower()
    rest = rest.strip()

    if action == "restart":
        restarted = create_state(
            original.get("seed"),
            difficulty=original.get("difficulty", "normal"),
            death_mode=original.get("death_mode", "cozy"),
        )
        return render(["你重新从狐狸河谷的清晨醒来。"], restarted), restarted

    if original.get("game_over") and not _game_over_command_allowed(action, rest):
        return render(["Game Over：你没能撑过这个季节。", "只能 restart / load。"], original), original

    if original.get("death_mode") == "ai_playtest" and action == "debug":
        return render(["AI Playtest 模式禁止 debug/dev 命令。"], original), original

    if action == "help":
        return render(_help_lines(rest, original), original), original
    if action == "status":
        return render(actions.status(original), original), original
    if action == "runtime":
        return render(actions.runtime_status(original), original), original
    if action == "recap":
        return render(actions.co_play_recap(original), original), original
    if action == "options":
        return render(actions.co_play_options(original), original), original
    if action == "observer" and not rest:
        return render(actions.observer_status(original), original), original
    if action == "open" and rest.lower() == "observer":
        return render(actions.open_observer_hint(original), original), original
    if action == "calendar":
        return render(actions.calendar_status(original), original), original
    if action == "weather":
        return render(actions.weather_status(original), original), original
    if action == "food":
        return render(actions.food_status(original), original), original
    if action == "garden" and not rest:
        return render(actions.garden_status(original), original), original
    if action == "inventory":
        return render(actions.inventory(original), original), original
    if action == "storage" and not rest:
        return render(actions.storage_status(original), original), original
    if action == "deposit":
        lines, ok = actions.deposit(next_state, rest)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "withdraw":
        lines, ok = actions.withdraw(next_state, rest)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "discard":
        lines, ok = actions.discard(next_state, rest)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "recipes":
        return render(recipe_lines(original, rest.lower() or None), original), original
    if action == "look":
        return render(actions.look(original), original), original
    if action == "inspect":
        return render(actions.inspect(original), original), original
    if action == "map":
        return render(actions.map_view(original), original), original
    if action == "relationship":
        return render(actions.relationship_status(next_state), next_state), next_state
    if action == "family" and rest.lower() == "readiness":
        return render(actions.family_readiness(original), original), original
    if action == "wish" and rest.lower() == "for kits":
        lines, ok = actions.wish_for_kits(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "check" and rest.lower() == "kits":
        return render(actions.check_kits(original), original), original
    if action == "play" and rest.lower() == "with kit":
        lines, ok = actions.play_with_kit(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "feed" and rest.lower() == "kit":
        lines, ok = actions.feed_kit(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "debug" and rest.lower() == "family":
        return render(actions.debug_family(original), original), original
    if action == "name" and (rest.lower() == "kit" or rest.lower().startswith("kit ")):
        name_text = rest[4:].strip() if rest.lower().startswith("kit ") else ""
        lines, ok = actions.name_kit(next_state, name_text)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "propose" and rest.lower().startswith("with "):
        lines, ok = actions.propose_with(next_state, rest[5:].strip())
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "hold" and rest.lower() == "ceremony":
        lines, ok = actions.hold_ceremony(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "commit" and rest.lower() == "family":
        lines, ok = actions.hold_ceremony(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "remember" and rest.lower() == "together":
        return render(actions.remember_together(original), original), original
    if action == "home" and not rest:
        return render(actions.home_status(original), original), original
    if action == "decor" and not rest:
        return render(actions.decor_status(original), original), original
    if action == "upgrade" and rest.lower().startswith("home to "):
        lines, ok = actions.upgrade_home(next_state, rest[8:].strip().lower())
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "name" and rest.lower().startswith("home "):
        lines, ok = actions.name_home(next_state, rest[5:].strip())
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "move":
        lines, ok = actions.move(next_state, rest.lower())
        return render(lines, next_state if ok else original), next_state if ok else original
    if action in {"north", "east", "south", "west"}:
        lines, ok = actions.move(next_state, action)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "return" and rest.lower() == "home":
        lines, ok = actions.return_home(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "gather":
        return render(actions.gather(next_state), next_state), next_state
    if action == "collect" and rest.lower() == "water":
        lines, ok = actions.collect_water(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "chop":
        lines, ok = actions.chop(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "mine":
        lines, ok = actions.mine(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "fish" and rest.lower() == "log":
        return render(actions.fish_log(original), original), original
    if action == "flower" and rest.lower() == "log":
        return render(actions.flower_log(original), original), original
    if action == "crop" and rest.lower() == "log":
        return render(actions.crop_log(original), original), original
    if action == "fishing" and not rest:
        return render(actions.fish_log(original), original), original
    if action == "findings" and not rest:
        return render(actions.findings(original), original), original
    if action == "materials" and rest.lower() == "log":
        return render(actions.materials_log(original), original), original
    if action == "fish":
        lines, ok = actions.fish(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "open" and rest.lower() in {"drift_bottle", "drift bottle"}:
        lines, ok = actions.open_drift_bottle(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "explore" and rest.lower() == "ruins":
        lines, ok = actions.explore_ruins(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "explore" and not rest:
        lines, ok = actions.explore(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "plant":
        lines, ok = actions.plant_seed(next_state, rest.lower())
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "water" and rest.lower() == "crops":
        lines, ok = actions.water_crops(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "harvest" and not rest:
        lines, ok = actions.harvest(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "eat":
        lines, ok = actions.eat(next_state, rest.lower())
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "wait":
        lines, ok = actions.wait(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "rest":
        if rest.lower() == "with companion":
            lines, ok = actions.rest_with_companion(next_state)
            return render(lines, next_state if ok else original), next_state if ok else original
        return render(actions.rest(next_state), next_state), next_state
    if action == "sleep":
        lines, ok = actions.sleep(next_state, confirm=rest.lower() == "confirm")
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "check" and rest.lower() == "companion":
        return render(actions.check_companion(original), original), original
    if action == "ask" and rest.lower() == "companion":
        return render(actions.ask_companion(original), original), original
    if action == "debug" and rest.lower() == "companion":
        return render(actions.debug_companion(original), original), original
    if action == "comfort" and rest.lower() == "companion":
        lines, ok = actions.comfort_companion(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "sit" and rest.lower() == "with companion":
        lines, ok = actions.sit_with_companion(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "cook" and rest.lower() == "fish":
        lines, ok = actions.cook_fish(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "make" and rest.lower() == "charcoal":
        lines, ok = actions.make_charcoal(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "make" and rest.lower() == "tea":
        lines, ok = actions.make_tea(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "make" and rest.lower() in {"warm meal", "warm_meal"}:
        lines, ok = actions.make_warm_meal(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "serve" and rest.lower() in {"warm meal", "warm_meal"}:
        lines, ok = actions.serve_warm_meal(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "serve" and rest.lower() in {"cooked_fish", "cooked fish", "berries"}:
        lines, ok = actions.serve_fresh_food(next_state, rest.lower().replace(" ", "_"))
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "serve" and rest.lower() in {"stale_food", "stale fish", "stale_fish", "spoiled berries", "spoiled_berries"}:
        normalized = rest.lower().replace(" ", "_")
        lines, ok = actions.serve_stale_food(next_state, normalized)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "share":
        lines, ok = actions.share_food(next_state, rest.lower())
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "talk" and rest.lower() == "companion":
        lines, ok = actions.talk_companion(next_state)
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "craft":
        lines, ok = craft(next_state, rest.lower())
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "build":
        lines, ok = build(next_state, rest.lower())
        return render(lines, next_state if ok else original), next_state if ok else original
    if action == "journal":
        return render(actions.journal(next_state, rest), next_state), next_state
    if action == "goal":
        return render(actions.set_goal(next_state, rest), next_state), next_state
    if action == "save":
        return render(actions.save_current(original), original), original
    if action == "load":
        try:
            lines, loaded = actions.load_current()
        except FileNotFoundError:
            return render(["没有找到存档。"], original), original
        return render(lines, loaded), loaded

    return render([f"听不懂：{command}。试试 help。"], original), original
