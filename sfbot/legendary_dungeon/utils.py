from enum import IntEnum
from typing import TypeVar

from sfbot.legendary_dungeon.constants import (
    BARRELS_PER_SECTION,
    BASE_ESCAPE_RATE,
    BLESSING_VALUE,
    BOSS_DMG,
    CHESTS_PER_SECTION,
    ESCAPES_PER_SECTION,
    FIGHT_DMG,
    FIGHTS_PER_SECTION,
    KEY_SAVE_RATE,
    SAC_CHEST_DMG,
    SAC_CHESTS_PER_SECTION,
    SAC_DOOR_DMG,
    SAC_DOORS_PER_SECTION,
    TRAP_DMG,
    TRAPS_PER_SECTION,
)
from sfbot.legendary_dungeon.models import (
    GemEffect,
    GemOfFate,
    GemSpecial,
)

_E = TypeVar("_E", bound=IntEnum)


def safe_enum(cls: type[_E], val: int) -> _E | None:
    try:
        return cls(val)
    except ValueError:
        return None


# Return the remaining section indices and boss floors from the current gem-pick floor.
# e.g. pick_floor=25 -> sections [1,2,3], bosses [50,75,100] (section 0 is already done).
def remaining_context(pick_floor: int) -> tuple[list[int], list[int]]:
    start = pick_floor // 25
    return list(range(start, 4)), [b for b in (25, 50, 75, 100) if b > pick_floor]


# Calculate HP saved (% of max) by a single gem effect over the remaining dungeon.
# Positive = HP saved (advantage), negative = HP lost (disadvantage).
# pwr_abs is the raw effect power (e.g. 20 means 20%); we convert to fraction (p).
def effect_hp_impact(
    effect: GemEffect,
    pwr_abs: float,
    sections: list[int],
    bosses: list[int],
) -> float:
    p = pwr_abs / 100
    n = len(sections)

    total_fight_dmg = sum(FIGHTS_PER_SECTION * FIGHT_DMG[s] for s in sections)
    total_boss_dmg = sum(BOSS_DMG[b] for b in bosses)
    total_fights = n * FIGHTS_PER_SECTION
    avg_fight_dmg = total_fight_dmg / max(total_fights, 1)
    total_escapes = n * ESCAPES_PER_SECTION
    total_barrels = n * BARRELS_PER_SECTION
    total_chests = n * CHESTS_PER_SECTION

    if effect == GemEffect.DAMAGE_FROM_MONSTERS:
        return (total_fight_dmg + total_boss_dmg) * p
    if effect == GemEffect.DAMAGE_FROM_TRAPS:
        return n * TRAPS_PER_SECTION * TRAP_DMG * p
    if effect == GemEffect.DAMAGE_FROM_SAC_DOORS:
        return n * SAC_DOORS_PER_SECTION * SAC_DOOR_DMG * p
    if effect == GemEffect.DAMAGE_FROM_CHESTS:
        return n * SAC_CHESTS_PER_SECTION * SAC_CHEST_DMG * p
    if effect == GemEffect.DAMAGE_FROM_ESCAPE:
        fail_dmg = sum(ESCAPES_PER_SECTION * FIGHT_DMG[s] for s in sections)
        return fail_dmg * (1 - BASE_ESCAPE_RATE) * p
    if effect == GemEffect.HEALING_FROM_BLESSINGS:
        return n * 25.0 * p
    if effect == GemEffect.CHANCE_OF_KEYS:
        return total_fights * p * avg_fight_dmg * KEY_SAVE_RATE
    if effect == GemEffect.CHANCE_OF_KEY_AFTER_ESCAPE:
        return total_escapes * p * avg_fight_dmg * KEY_SAVE_RATE
    if effect == GemEffect.ESCAPE_CHANCE:
        escape_fight_dmg = sum(ESCAPES_PER_SECTION * FIGHT_DMG[s] for s in sections)
        return escape_fight_dmg * p
    if effect == GemEffect.CHANCE_OF_BLESSING_AFTER_FIGHT:
        return total_fights * p * BLESSING_VALUE
    if effect == GemEffect.CHANCE_OF_CURSE_AFTER_FIGHT:
        return total_fights * p * BLESSING_VALUE * 0.5
    if effect == GemEffect.CHANCE_OF_CURSE_AFTER_ESCAPE:
        return total_escapes * p * BLESSING_VALUE * 0.3
    if effect == GemEffect.BLESSING_OR_CURSE_AFTER_REVIVE:
        return BLESSING_VALUE * p * 0.3
    if effect == GemEffect.DURATION_OF_BLESSINGS:
        return n * 2 * 3.0 * p
    if effect == GemEffect.DURATION_OF_CURSES:
        return n * 1.5 * 2.0 * p
    if effect == GemEffect.CHANCE_OF_STRONGER_CURSES:
        return n * 1.5 * 3.0 * p
    if effect == GemEffect.BLESSINGS_IN_BARRELS_CHESTS_CORPSES:
        return (total_barrels + total_chests) * p * BLESSING_VALUE * 0.3
    if effect == GemEffect.CHANCE_OF_BLESSINGS_IN_BARRELS:
        return total_barrels * p * BLESSING_VALUE * 0.3
    if effect == GemEffect.CHANCE_OF_BETTER_BLESSINGS_IN_BARRELS:
        return total_barrels * p * BLESSING_VALUE * 0.2
    return 0.0


# Calculate HP impact (% of max) from a gem's special property.
# Positive = beneficial, negative = harmful.  Estimates extra encounters
# or reduced encounters per remaining section (n).
def special_hp_impact(
    special: GemSpecial,
    sections: list[int],
) -> float:
    n = len(sections)
    total_fight_dmg = sum(FIGHTS_PER_SECTION * FIGHT_DMG[s] for s in sections)
    avg_fight_dmg = total_fight_dmg / max(n * FIGHTS_PER_SECTION, 1)

    if special == GemSpecial.WEAKER_MONSTERS_SPAWN:
        return total_fight_dmg * 0.10
    if special == GemSpecial.STRONGER_MONSTERS_SPAWN:
        return -total_fight_dmg * 0.10
    if special == GemSpecial.MONSTERS_BEHIND_DOORS:
        return -n * 2 * avg_fight_dmg
    if special == GemSpecial.MORE_TRAPS_SPAWN:
        return -n * 2 * TRAP_DMG
    if special == GemSpecial.ALWAYS_ONE_TRAP:
        return -n * 2 * TRAP_DMG
    if special == GemSpecial.TRAPS_INFLICT_CURSE:
        return -n * TRAPS_PER_SECTION * 0.5 * 5.0
    if special == GemSpecial.MORE_SAC_DOORS:
        return -n * 1 * SAC_DOOR_DMG
    if special == GemSpecial.FEWER_SAC_DOORS:
        return n * 1 * SAC_DOOR_DMG * 0.5
    if special == GemSpecial.SAC_CHESTS_BEHIND_CLOSED_DOORS:
        return -n * 1 * SAC_CHEST_DMG * 0.5
    if special == GemSpecial.MORE_CURSED_DOORS:
        return -n * 1 * 5.0
    if special == GemSpecial.FEWER_CURSED_DOORS:
        return n * 1 * 5.0 * 0.5
    if special == GemSpecial.CURSED_CHESTS_BEHIND_CLOSED_DOORS:
        return -n * 1 * 5.0 * 0.3
    if special == GemSpecial.CHANCE_OF_UNLOCKED_DOORS:
        return n * 2 * avg_fight_dmg * 0.3
    if special == GemSpecial.CHANCE_OF_DOUBLE_LOCKED_DOOR:
        return -n * avg_fight_dmg * 0.3
    if special == GemSpecial.ALWAYS_ONE_LOCK:
        return -n * avg_fight_dmg * 0.2
    if special == GemSpecial.CHANCE_OF_EPIC_DOORS:
        return n * 3.0
    if special == GemSpecial.NO_MORE_EPIC_CHESTS:
        return -n * 2.0
    if special == GemSpecial.MORE_MYSTERIOUS_ROOMS:
        return -n * 1.0
    if special == GemSpecial.FEWER_MYSTERIOUS_ROOMS:
        return n * 1.0
    return 0.0


# Score a gem's net HP impact (% of max HP saved) from the current floor onward.
# Sums advantage (positive), disadvantage (negative), and special property.
def score_gem(gem: GemOfFate, current_floor: int) -> float:
    sections, bosses = remaining_context(current_floor)
    score = 0.0
    if gem.advantage is not None and gem.advantage_pwr != 0:
        score += effect_hp_impact(
            gem.advantage, abs(gem.advantage_pwr), sections, bosses
        )
    if gem.disadvantage is not None and gem.disadvantage_pwr != 0:
        score -= effect_hp_impact(
            gem.disadvantage, abs(gem.disadvantage_pwr), sections, bosses
        )
    if gem.special is not None:
        score += special_hp_impact(gem.special, sections)
    return score


# Pick the gem with the highest score from available choices.
# Returns (index, gem, score), or None if the list is empty.
def pick_best_gem(
    gems: list[GemOfFate], current_floor: int
) -> tuple[int, GemOfFate, float] | None:
    if not gems:
        return None
    scored = [(i, gem, score_gem(gem, current_floor)) for i, gem in enumerate(gems)]
    return max(scored, key=lambda x: x[2])
