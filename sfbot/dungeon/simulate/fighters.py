"""Fighter construction and pre-computed combat calculation functions.

Port of HafisCZ's sf-tools simulator (js/sim/base.js).
"""

from sfbot.constants.enums import Attribute, CharClass
from sfbot.dungeon.enums import RuneType
from sfbot.dungeon.models import Fighter, Monster
from sfbot.dungeon.simulate.class_models.base import CombatStats
from sfbot.dungeon.simulate.combat import estimate_weapon_damage
from sfbot.dungeon.simulate.constants import (
    CLASS_DAMAGE_BONUS,
    CRIT_ENCHANTMENT_BONUS,
    MAX_RUNE_DAMAGE,
    MAX_RUNE_RESISTANCE,
    NECROMANCER_DH_BONUS,
)
from sfbot.simulate.combat import (
    calc_armor_reduction,
    calc_attribute_bonus,
    calc_crit_chance,
)
from sfbot.simulate.constants import (
    CRIT_BASE,
    CRIT_GLADIATOR_BONUS,
    DAMAGE_MULTIPLIER,
)


def fighter_from_monster(monster: Monster) -> Fighter:
    if monster.min_dmg is None or monster.max_dmg is None:
        min_dmg, max_dmg = estimate_weapon_damage(monster.level, monster.char_class)
    else:
        min_dmg, max_dmg = float(monster.min_dmg), float(monster.max_dmg)
    return Fighter(
        char_class=monster.char_class,
        level=monster.level,
        strength=monster.strength,
        dexterity=monster.dexterity,
        intelligence=monster.intelligence,
        constitution=monster.constitution,
        luck=monster.luck,
        armor=monster.armor,
        min_dmg=min_dmg,
        max_dmg=max_dmg,
        health=monster.health,
        rune_type=RuneType(monster.rune_type) if monster.rune_type else RuneType.NONE,
        rune_value=monster.rune_damage,
        fire_resistance=monster.fire_resistance,
        cold_resistance=monster.cold_resistance,
        lightning_resistance=monster.lightning_resistance,
    )


def fighter_from_character(
    char_class: CharClass,
    level: int,
    total_attrs: dict[Attribute, int],
    armor: int,
    min_dmg: int | float,
    max_dmg: int | float,
    portal_hp_bonus: int = 0,
    portal_dmg_bonus: int = 0,
    rune_type: RuneType = RuneType.NONE,
    rune_value: int = 0,
    fire_resistance: int = 0,
    cold_resistance: int = 0,
    lightning_resistance: int = 0,
    rune_health: int = 0,
    gladiator: int = 0,
    has_sword_of_vengeance: bool = False,
    has_shadow_of_cowboy: bool = False,
    has_life_potion: bool = False,
    is_companion: bool = False,
    min_dmg2: int | float = 0,
    max_dmg2: int | float = 0,
) -> Fighter:
    return Fighter(
        char_class=char_class,
        level=level,
        strength=total_attrs[Attribute.STRENGTH],
        dexterity=total_attrs[Attribute.DEXTERITY],
        intelligence=total_attrs[Attribute.INTELLIGENCE],
        constitution=total_attrs[Attribute.CONSTITUTION],
        luck=total_attrs[Attribute.LUCK],
        armor=armor,
        min_dmg=float(min_dmg),
        max_dmg=float(max_dmg),
        min_dmg2=float(min_dmg2),
        max_dmg2=float(max_dmg2),
        rune_type=rune_type,
        rune_value=rune_value,
        fire_resistance=fire_resistance,
        cold_resistance=cold_resistance,
        lightning_resistance=lightning_resistance,
        portal_hp_bonus=portal_hp_bonus,
        portal_dmg_bonus=portal_dmg_bonus,
        rune_health=rune_health,
        gladiator=gladiator,
        has_sword_of_vengeance=has_sword_of_vengeance,
        has_shadow_of_cowboy=has_shadow_of_cowboy,
        has_life_potion=has_life_potion,
        is_companion=is_companion,
    )


# --- Dungeon-specific combat calculations ---


def calc_rune_bonus(attacker: Fighter, target: Fighter) -> float:
    if attacker.rune_type == RuneType.NONE or attacker.rune_value == 0:
        return 0.0

    rune_damage = min(MAX_RUNE_DAMAGE, attacker.rune_value)
    match attacker.rune_type:
        case RuneType.FIRE:
            resistance = min(MAX_RUNE_RESISTANCE, target.fire_resistance)
        case RuneType.COLD:
            resistance = min(MAX_RUNE_RESISTANCE, target.cold_resistance)
        case RuneType.LIGHTNING:
            resistance = min(MAX_RUNE_RESISTANCE, target.lightning_resistance)

    return (1.0 - resistance / 100.0) * (rune_damage / 100.0)


def calc_class_multiplier(attacker: Fighter, target: Fighter) -> float:
    base = DAMAGE_MULTIPLIER[attacker.char_class]

    if (
        attacker.char_class == CharClass.NECROMANCER
        and target.char_class == CharClass.DEMON_HUNTER
    ):
        return base + NECROMANCER_DH_BONUS

    bonus = CLASS_DAMAGE_BONUS.get((attacker.char_class, target.char_class))
    if bonus is not None:
        return base * bonus

    return base


def calc_damage_range(attacker: Fighter, target: Fighter) -> tuple[float, float]:
    portal_multiplier = 1.0 + attacker.portal_dmg_bonus / 100.0
    attribute_bonus = calc_attribute_bonus(attacker, target)
    armor_reduction = 1.0 - calc_armor_reduction(attacker, target) / 100.0
    rune_bonus = 1.0 + calc_rune_bonus(attacker, target)
    class_multiplier = calc_class_multiplier(attacker, target)

    total = (
        portal_multiplier
        * attribute_bonus
        * armor_reduction
        * rune_bonus
        * class_multiplier
    )
    return attacker.min_dmg * total, attacker.max_dmg * total


def calc_crit_multiplier(attacker: Fighter, target: Fighter) -> float:
    multiplier = CRIT_BASE
    if attacker.has_sword_of_vengeance:
        multiplier += CRIT_ENCHANTMENT_BONUS
    gladiator_advantage = max(0, attacker.gladiator - target.gladiator)
    multiplier += CRIT_GLADIATOR_BONUS * gladiator_advantage
    return multiplier


# --- Pre-computed per-fighter combat state ---


def precompute_combat_stats(a: Fighter, b: Fighter) -> CombatStats:
    dmg_min, dmg_max = calc_damage_range(a, b)
    # Assassin second weapon: compute damage range using the same total multiplier
    if a.char_class == CharClass.ASSASSIN and a.max_dmg2 > 0:
        portal_multiplier = 1.0 + a.portal_dmg_bonus / 100.0
        attribute_bonus = calc_attribute_bonus(a, b)
        armor_reduction = 1.0 - calc_armor_reduction(a, b) / 100.0
        rune_bonus = 1.0 + calc_rune_bonus(a, b)
        class_multiplier = calc_class_multiplier(a, b)
        total = (
            portal_multiplier
            * attribute_bonus
            * armor_reduction
            * rune_bonus
            * class_multiplier
        )
        dmg_min2, dmg_max2 = a.min_dmg2 * total, a.max_dmg2 * total
    else:
        dmg_min2, dmg_max2 = dmg_min, dmg_max
    return CombatStats(
        dmg_min=dmg_min,
        dmg_max=dmg_max,
        dmg_min2=dmg_min2,
        dmg_max2=dmg_max2,
        crit_chance=calc_crit_chance(a, b),
        crit_mult=calc_crit_multiplier(a, b),
        total_hp=a.get_total_health(),
        fighter=a,
    )
