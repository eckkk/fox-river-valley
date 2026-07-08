from .data import MAP_SIZE, PASSABLE_TERRAINS, START_POS, TERRAIN_LABELS
from .rng import deterministic_int


def tile_key(pos: list[int]) -> str:
    return f"{pos[0]},{pos[1]}"


def parse_tile_key(key: str) -> list[int]:
    x, y = key.split(",", 1)
    return [int(x), int(y)]


def in_bounds(pos: list[int]) -> bool:
    return 0 <= pos[0] < MAP_SIZE and 0 <= pos[1] < MAP_SIZE


def terrain_at(seed: str, pos: list[int]) -> str:
    if pos == START_POS:
        return "grass"
    if pos == [START_POS[0], START_POS[1] - 1]:
        return "forest"
    if pos == [START_POS[0] + 1, START_POS[1]]:
        return "water"
    if pos == [START_POS[0] - 2, START_POS[1] - 1]:
        return "ruins"

    value = deterministic_int(seed, 0, f"terrain:{pos[0]},{pos[1]}", 100)
    if value < 9:
        return "water"
    if value < 40:
        return "forest"
    if value < 55:
        return "hill"
    if value < 68:
        return "stone"
    if value < 72:
        return "cave"
    if value < 76:
        return "ruins"
    return "grass"


def is_passable(seed: str, pos: list[int]) -> bool:
    return in_bounds(pos) and terrain_at(seed, pos) in PASSABLE_TERRAINS


def neighboring_positions(pos: list[int]) -> list[list[int]]:
    x, y = pos
    return [[x, y - 1], [x + 1, y], [x, y + 1], [x - 1, y]]


def nearby_terrains(seed: str, pos: list[int]) -> list[str]:
    found: list[str] = []
    for neighbor in neighboring_positions(pos):
        if not in_bounds(neighbor):
            continue
        terrain = terrain_at(seed, neighbor)
        if terrain not in found:
            found.append(terrain)
    return found


def describe_tile(seed: str, pos: list[int]) -> str:
    terrain = terrain_at(seed, pos)
    return TERRAIN_LABELS.get(terrain, terrain)
