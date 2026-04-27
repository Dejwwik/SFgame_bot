from dataclasses import dataclass
from math import ceil

from sfbot.constants.enums import Attribute, CharClass
from sfbot.dungeon.enums import RuneType
from sfbot.simulate.constants import (
    COMPANION_HEALTH_MULTIPLIER,
    HEALTH_MULTIPLIER,
    WINGS_HP_MULTIPLIER,
)


@dataclass(slots=True)
class Monster:
    name: str
    char_class: CharClass
    level: int
    strength: int
    dexterity: int
    intelligence: int
    constitution: int
    luck: int
    armor: int
    min_dmg: int | None
    max_dmg: int | None
    health: int
    rune_type: int
    rune_damage: int
    fire_resistance: int
    cold_resistance: int
    lightning_resistance: int
    is_mirror: bool = False


@dataclass(slots=True)
class Fighter:
    char_class: CharClass
    level: int
    strength: int
    dexterity: int
    intelligence: int
    constitution: int
    luck: int
    armor: int
    min_dmg: float
    max_dmg: float
    # Assassin second weapon damage (0 = use primary weapon stats)
    min_dmg2: float = 0.0
    max_dmg2: float = 0.0
    # Weapon rune
    rune_type: RuneType = RuneType.NONE
    rune_value: int = 0
    # Elemental resistances (0-75)
    fire_resistance: int = 0
    cold_resistance: int = 0
    lightning_resistance: int = 0
    # Portal bonuses (percentage, 0-50)
    portal_hp_bonus: int = 0
    portal_dmg_bonus: int = 0
    # Rune health bonus (percentage, 0-15)
    rune_health: int = 0
    # Gladiator level (0-15)
    gladiator: int = 0
    # Weapon enchantment: Sword of Vengeance (+5% crit damage)
    has_sword_of_vengeance: bool = False
    # Gloves enchantment: Shadow of the Cowboy (attack first)
    has_shadow_of_cowboy: bool = False
    # Wings active (25% HP bonus)
    has_life_potion: bool = False
    # Pre-computed HP (monsters have fixed life from JSON; 0 means calculate)
    health: int = 0
    # Companion mode (different HP multiplier, no Warrior block)
    is_companion: bool = False

    def get_main_attr(self) -> int:
        return self.get_attr(self.char_class.main_attr)

    def get_attr(self, attr: Attribute) -> int:
        match attr:
            case Attribute.STRENGTH:
                return self.strength
            case Attribute.DEXTERITY:
                return self.dexterity
            case Attribute.INTELLIGENCE:
                return self.intelligence
            case _:
                return self.strength

    def get_total_health(self) -> float:
        if self.health > 0:
            return float(self.health)
        if self.is_companion and self.char_class in COMPANION_HEALTH_MULTIPLIER:
            hp_multiplier = COMPANION_HEALTH_MULTIPLIER[self.char_class]
        else:
            hp_multiplier = HEALTH_MULTIPLIER[self.char_class]
        base_hp = self.constitution * hp_multiplier * (self.level + 1)
        if self.has_life_potion:
            base_hp = ceil(base_hp * WINGS_HP_MULTIPLIER)
        base_hp = ceil(base_hp * (1 + self.portal_hp_bonus / 100))
        base_hp = ceil(base_hp * (1 + self.rune_health / 100))
        return float(base_hp)
