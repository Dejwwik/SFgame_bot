"""Gem utility functions — average gem attribute calculations."""

LEGENDARY_FACTOR = 0.25


def _calc_base(character_level: int, mine_level: int, total_knights: int) -> float:
    """Calculate average gem attribute for mine level <= 25."""
    value = (
        character_level * LEGENDARY_FACTOR * (1 + 0.25 * (min(mine_level, 25) - 1))
        + total_knights / 3
    )
    return value


def _calc_above_25(character_level: int, mine_level: int, total_knights: int) -> float:
    """Calculate average gem attribute for mine level > 25 using regression."""
    a = -8543.13499118391
    b = 44.0797096956705
    c = 223305.008474091
    d = -0.067010811487377
    e = -3075546.61138002
    f = -632.101592233341
    g = 3.75316086045586e-05
    h = 20471919.6170508
    i = 3153.33229655608
    j = 0.421506101603155

    lvl = character_level
    ml = mine_level

    base = (
        a
        + b * lvl
        + c / ml
        + d * lvl**2
        + e / ml**2
        + f * lvl / ml
        + g * lvl**3
        + h / ml**3
        + i * lvl / ml**2
        + j * lvl**2 / ml
    )
    return base + total_knights / 3


def calc_average_gem_attribute(
    character_level: int, total_knights: int, mine_level: int
) -> float:
    """Calculate average single-attr gem value.

    Args:
        character_level: Character level.
        total_knights: Sum of all guild members' Hall of Knights levels (from owngroupknights).
        mine_level: Fortress gem mine building level.
    """
    if mine_level > 25:
        single = _calc_above_25(character_level, mine_level, total_knights)
    else:
        single = _calc_base(character_level, mine_level, total_knights)

    return single
