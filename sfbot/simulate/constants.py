from sfbot.constants.enums import CharClass

# --- Core class configuration tables (shared by dungeon and pet simulation) ---

HEALTH_MULTIPLIER: dict[CharClass, float] = {
    CharClass.WARRIOR: 5.0,
    CharClass.MAGE: 2.0,
    CharClass.SCOUT: 4.0,
    CharClass.ASSASSIN: 4.0,
    CharClass.BATTLE_MAGE: 5.0,
    CharClass.BERSERKER: 4.0,
    CharClass.DEMON_HUNTER: 4.0,
    CharClass.DRUID: 5.0,
    CharClass.BARD: 2.0,
    CharClass.NECROMANCER: 4.0,
    CharClass.PALADIN: 6.0,
    CharClass.PLAGUE_DOCTOR: 4.0,
}

WEAPON_MULTIPLIER: dict[CharClass, float] = {
    CharClass.WARRIOR: 2.0,
    CharClass.MAGE: 4.5,
    CharClass.SCOUT: 2.5,
    CharClass.ASSASSIN: 2.0,
    CharClass.BATTLE_MAGE: 2.0,
    CharClass.BERSERKER: 2.0,
    CharClass.DEMON_HUNTER: 2.5,
    CharClass.DRUID: 4.5,
    CharClass.BARD: 4.5,
    CharClass.NECROMANCER: 4.5,
    CharClass.PALADIN: 2.0,
    CharClass.PLAGUE_DOCTOR: 2.0,
}

DAMAGE_MULTIPLIER: dict[CharClass, float] = {
    CharClass.WARRIOR: 1.0,
    CharClass.MAGE: 1.0,
    CharClass.SCOUT: 1.0,
    CharClass.ASSASSIN: 0.625,
    CharClass.BATTLE_MAGE: 1.0,
    CharClass.BERSERKER: 1.25,
    CharClass.DEMON_HUNTER: 1.0,
    CharClass.DRUID: 1.0 / 3.0,
    CharClass.BARD: 1.125,
    CharClass.NECROMANCER: 5.0 / 9.0,
    CharClass.PALADIN: 0.833,
    CharClass.PLAGUE_DOCTOR: 1.25,
}

ARMOR_MULTIPLIER: dict[CharClass, float] = {
    CharClass.WARRIOR: 1.0,
    CharClass.MAGE: 1.0,
    CharClass.SCOUT: 1.0,
    CharClass.ASSASSIN: 1.0,
    CharClass.BATTLE_MAGE: 5.0,
    CharClass.BERSERKER: 0.5,
    CharClass.DEMON_HUNTER: 1.0,
    CharClass.DRUID: 1.0,
    CharClass.BARD: 2.0,
    CharClass.NECROMANCER: 2.0,
    CharClass.PALADIN: 1.0,
    CharClass.PLAGUE_DOCTOR: 2.0,
}

MAX_DAMAGE_REDUCTION: dict[CharClass, int] = {
    CharClass.WARRIOR: 50,
    CharClass.MAGE: 10,
    CharClass.SCOUT: 25,
    CharClass.ASSASSIN: 25,
    CharClass.BATTLE_MAGE: 50,
    CharClass.BERSERKER: 25,
    CharClass.DEMON_HUNTER: 50,
    CharClass.DRUID: 25,
    CharClass.BARD: 50,
    CharClass.NECROMANCER: 20,
    CharClass.PALADIN: 45,
    CharClass.PLAGUE_DOCTOR: 20,
}

SKIP_CHANCE: dict[CharClass, float] = {
    CharClass.WARRIOR: 0.25,
    CharClass.MAGE: 0.0,
    CharClass.SCOUT: 0.50,
    CharClass.ASSASSIN: 0.50,
    CharClass.BATTLE_MAGE: 0.0,
    CharClass.BERSERKER: 0.50,
    CharClass.DEMON_HUNTER: 0.0,
    CharClass.DRUID: 0.35,
    CharClass.BARD: 0.0,
    CharClass.NECROMANCER: 0.0,
    CharClass.PALADIN: 0.0,
    CharClass.PLAGUE_DOCTOR: 0.20,
}

BYPASS_DAMAGE_REDUCTION: frozenset[CharClass] = frozenset({CharClass.MAGE})

BYPASS_SKIP_CHANCE: frozenset[CharClass] = frozenset({CharClass.MAGE})

# Crit constants (sf-tools CONFIG.General)
CRIT_BASE = 2.0
CRIT_GLADIATOR_BONUS = 0.11

# Wings (life potion) HP multiplier
WINGS_HP_MULTIPLIER = 1.25

# Companion health multiplier override (Warrior companion has bonus HP)
COMPANION_HEALTH_MULTIPLIER: dict[CharClass, float] = {
    CharClass.WARRIOR: 6.1,
}
