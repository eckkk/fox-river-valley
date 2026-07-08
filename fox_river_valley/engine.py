from __future__ import annotations

from typing import Any

from .commands import run_command
from .names import clean_name
from .render import render
from .runtime import observer_enabled, save_path
from .state import create_state, load_state, save_state

_current_state: dict[str, Any] | None = None


def _write_observer_if_enabled(state: dict[str, Any], *, last_command: str, output: str, reset_turn: bool = False) -> None:
    if not observer_enabled():
        return
    from .observer import write_observer_files

    write_observer_files(state, last_command=last_command, output=output, reset_turn=reset_turn)


def new_game(
    seed: int | str | None = None,
    difficulty: str = "normal",
    companion_name: str | None = None,
    companion_profile: str = "default",
    family_species: str | None = None,
    death_mode: str = "cozy",
) -> str:
    global _current_state
    clean_companion_name = clean_name(companion_name, field="companion_name") if companion_name else None
    clean_family_species = clean_name(family_species, field="family_species") if family_species else None
    _current_state = create_state(
        seed,
        difficulty=difficulty,
        companion_name=clean_companion_name,
        companion_profile=companion_profile,
        family_species=clean_family_species,
        death_mode=death_mode,
    )
    opening = "狐狸河谷在清晨展开，像一张还没有写满的纸。"
    if clean_companion_name:
        opening = f"狐狸河谷在清晨展开，{clean_companion_name} 就在你身边。"
    output = render(
        [
            opening,
            "你站在草地中央，背包很轻，但今天可以开始留下脚印。",
            "可尝试：look、map、move north、gather。",
        ],
        _current_state,
    )
    save_state(_current_state)
    _write_observer_if_enabled(_current_state, last_command="new_game", output=output, reset_turn=True)
    return output


def cmd(command: str) -> str:
    global _current_state
    path = save_path()
    if path.exists():
        _current_state = load_state(path)
    elif _current_state is None:
        _current_state = create_state(None)
    output, _current_state = run_command(command, _current_state)
    save_state(_current_state)
    _write_observer_if_enabled(_current_state, last_command=command.strip() or "(empty)", output=output)
    return output
