"""Shared combat calculation functions used by both dungeon and pet simulation.

These formulas are identical between dungeon and pet combat. Domain-specific
calculations (rune bonuses, portal bonuses, enchantments, class matchups)
remain in their respective simulate packages.
"""

from typing import Protocol

from sfbot.constants.enums import Attribute, CharClass
from sfbot.simulate.constants import (
    ARMOR_MULTIPLIER,
    BYPASS_DAMAGE_REDUCTION,
    MAX_DAMAGE_REDUCTION,
)

# Crit chance cap (same for dungeon and pet combat)
MAX_CRIT_CHANCE = 0.50


class Combatant(Protocol):
    """Minimal interface shared by dungeon Fighter and PetFighter."""

    char_class: CharClass
    level: int
    armor: int
    luck: int

    def get_attr(self, attr: Attribute) -> int: ...


def calc_armor_reduction(attacker: Combatant, target: Combatant) -> float:
    """Calculate percentage armor damage reduction.

    Mages bypass armor entirely. Reduction is capped per class.
    """
    if attacker.char_class in BYPASS_DAMAGE_REDUCTION:
        return 0.0
    if target.armor == 0 or attacker.level == 0:
        return 0.0
    max_reduction = MAX_DAMAGE_REDUCTION[target.char_class]
    reduction = ARMOR_MULTIPLIER[target.char_class] * target.armor / attacker.level
    return min(reduction, float(max_reduction))


def calc_attribute_bonus(attacker: Combatant, target: Combatant) -> float:
    """Calculate main-attribute damage bonus multiplier.

    Bonus = 1 + max(main/2, main - target_main/2) / 10.
    """
    main_attr_type = attacker.char_class.main_attr
    attacker_main = attacker.get_attr(main_attr_type)
    target_main = target.get_attr(main_attr_type)
    effective = max(attacker_main // 2, attacker_main - target_main // 2)
    return 1.0 + effective / 10.0


def calc_crit_chance(attacker: Combatant, target: Combatant) -> float:
    """Calculate critical hit chance, capped at MAX_CRIT_CHANCE (50%).

    Formula: luck * 2.5 / target_level / 100.
    """
    if target.level == 0:
        return 0.0
    chance = attacker.luck * 2.5 / target.level / 100.0
    return min(chance, MAX_CRIT_CHANCE)
