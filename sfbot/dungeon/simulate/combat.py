"""Combat helper functions: hit damage, dodge/skip checks, damage estimation.

Port of HafisCZ's sf-tools simulator.
"""

import random
from math import ceil

from sfbot.constants.enums import CharClass
from sfbot.dungeon.models import Fighter
from sfbot.dungeon.simulate.constants import (
    HAND_DAMAGE_MAX_RATIO,
    HAND_DAMAGE_MIN_RATIO,
    HAND_DAMAGE_MULTIPLIER,
    SKIP_TYPE,
    SKIP_TYPE_DEFAULT,
    TWISTER_DAMAGE_PER_LEVEL,
    TWISTER_WEAPON_BASE_CLASS,
)
from sfbot.simulate.constants import (
    BYPASS_SKIP_CHANCE,
    SKIP_CHANCE,
    WEAPON_MULTIPLIER,
)

# --- Damage estimation for monsters without weapon data ---


def estimate_hand_damage(level: int, char_class: CharClass) -> tuple[float, float]:
    """Estimate unarmed damage based on level and class.

    Used for companions without equipped weapons and as a fallback.
    Source: rust_reference/src/simulate/damage.rs get_hand_damage()
    """
    if level <= 10:
        return 1.0, 2.0
    base = HAND_DAMAGE_MULTIPLIER * (level - 9) * WEAPON_MULTIPLIER[char_class]
    min_dmg = max(1.0, float(ceil(base * HAND_DAMAGE_MIN_RATIO)))
    max_dmg = max(2.0, float(round(base * HAND_DAMAGE_MAX_RATIO)))
    return min_dmg, max_dmg


def estimate_weapon_damage(level: int, char_class: CharClass) -> tuple[float, float]:
    """Estimate weapon damage for a Twister monster based on per-level constants.

    Uses observed damage-per-level ratios. Hybrid classes are mapped to their
    weapon base class. Returns (dmg, dmg) — min equals max for simplicity.
    """
    base_class = TWISTER_WEAPON_BASE_CLASS.get(char_class, CharClass.WARRIOR)
    ratio = TWISTER_DAMAGE_PER_LEVEL[base_class]
    damage = max(1.0, ratio * level)
    return damage, damage


# --- Hit damage and dodge/skip ---


def calc_hit_damage(
    damage_min: float,
    damage_max: float,
    rage: float,
    crit_chance: float,
    crit_multiplier: float,
) -> float:
    """Roll random damage in [min, max], scaled by rage, with crit chance."""
    base = random.random() * (1.0 + damage_max - damage_min) + damage_min
    damage = base * rage
    if random.random() < crit_chance:
        damage *= crit_multiplier
    return damage


def will_skip(
    defender: Fighter,
    attacker: Fighter,
    skip_type: int = SKIP_TYPE_DEFAULT,
    skip_count: int = 0,
    skip_limit: int = 999,
    override_skip_chance: float | None = None,
) -> bool:
    """Check if the defender dodges/blocks/skips the incoming attack."""
    if SKIP_TYPE[defender.char_class] != skip_type:
        return False
    if attacker.char_class in BYPASS_SKIP_CHANCE:
        return False
    if defender.is_companion and defender.char_class == CharClass.WARRIOR:
        return False
    if skip_count >= skip_limit:
        return False
    if override_skip_chance is not None:
        chance = override_skip_chance
    else:
        chance = SKIP_CHANCE[defender.char_class]
    if chance <= 0.0:
        return False
    return random.random() < chance
