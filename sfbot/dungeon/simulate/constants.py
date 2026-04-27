from sfbot.constants.enums import CharClass

# --- Max fight rounds safety limit ---
MAX_ROUNDS = 500

# Mage negates all special class abilities (fireball, revive, forms, etc.)
BYPASS_SPECIAL: frozenset[CharClass] = frozenset({CharClass.MAGE})

# Class vs class special damage multipliers (sf-tools CONFIG)
CLASS_DAMAGE_BONUS: dict[tuple[CharClass, CharClass], float] = {
    (CharClass.MAGE, CharClass.PALADIN): 1.5,
    (CharClass.PALADIN, CharClass.MAGE): 1.5,
    (CharClass.DRUID, CharClass.MAGE): 4.0 / 3.0,
    (CharClass.DRUID, CharClass.DEMON_HUNTER): 1.15,
    (CharClass.BARD, CharClass.PLAGUE_DOCTOR): 1.05,
    (CharClass.PLAGUE_DOCTOR, CharClass.DEMON_HUNTER): 1.065,
}

# Necromancer vs DH is additive, not multiplicative
NECROMANCER_DH_BONUS = 0.1

# Crit constants (dungeon-specific additions)
CRIT_ENCHANTMENT_BONUS = 0.05

# Rune caps (sf-tools getDamageBase)
MAX_RUNE_DAMAGE = 60
MAX_RUNE_RESISTANCE = 75

# Hand damage estimation for monsters without weapon damage (Twister)
HAND_DAMAGE_MULTIPLIER = 0.7
HAND_DAMAGE_MIN_RATIO = 2.0 / 3.0
HAND_DAMAGE_MAX_RATIO = 4.0 / 3.0

# --- Twister weapon damage per level ---
# Observed damage-per-level ratios for the three base weapon classes.
# Hybrid classes map to their weapon-base class via TWISTER_WEAPON_BASE_CLASS.
TWISTER_DAMAGE_PER_LEVEL: dict[CharClass, float] = {
    CharClass.WARRIOR: 2.78,
    CharClass.MAGE: 5.87,
    CharClass.SCOUT: 3.46,
}

# Hybrid class → weapon base class for Twister damage estimation
TWISTER_WEAPON_BASE_CLASS: dict[CharClass, CharClass] = {
    CharClass.WARRIOR: CharClass.WARRIOR,
    CharClass.MAGE: CharClass.MAGE,
    CharClass.SCOUT: CharClass.SCOUT,
    CharClass.ASSASSIN: CharClass.WARRIOR,
    CharClass.BATTLE_MAGE: CharClass.WARRIOR,
    CharClass.BERSERKER: CharClass.WARRIOR,
    CharClass.PALADIN: CharClass.WARRIOR,
    CharClass.PLAGUE_DOCTOR: CharClass.WARRIOR,
    CharClass.DEMON_HUNTER: CharClass.SCOUT,
    CharClass.NECROMANCER: CharClass.MAGE,
    CharClass.BARD: CharClass.MAGE,
    CharClass.DRUID: CharClass.MAGE,
}

# --- Class ability constants ---

# Skip types: DEFAULT = normal dodge/block, CONTROL = Berserker chain (attacker loses turn)
SKIP_TYPE_DEFAULT = 0
SKIP_TYPE_CONTROL = 1

SKIP_TYPE: dict[CharClass, int] = {
    CharClass.WARRIOR: SKIP_TYPE_DEFAULT,
    CharClass.MAGE: SKIP_TYPE_DEFAULT,
    CharClass.SCOUT: SKIP_TYPE_DEFAULT,
    CharClass.ASSASSIN: SKIP_TYPE_DEFAULT,
    CharClass.BATTLE_MAGE: SKIP_TYPE_DEFAULT,
    CharClass.BERSERKER: SKIP_TYPE_CONTROL,
    CharClass.DEMON_HUNTER: SKIP_TYPE_DEFAULT,
    CharClass.DRUID: SKIP_TYPE_DEFAULT,
    CharClass.BARD: SKIP_TYPE_DEFAULT,
    CharClass.NECROMANCER: SKIP_TYPE_DEFAULT,
    CharClass.PALADIN: SKIP_TYPE_DEFAULT,
    CharClass.PLAGUE_DOCTOR: SKIP_TYPE_DEFAULT,
}

# Berserker: chain attacks (up to 15 consecutive = 1 initial + 14 chains)
BERSERKER_SKIP_LIMIT = 14

# BattleMage: fireball damage = min(target_hp/3, player_hp × ratio × target_hp_mult)
FIREBALL_HP_RATIO = 0.05

# DemonHunter: revive on death
DH_REVIVE_CHANCE = 0.44
DH_REVIVE_DECAY = 0.11
DH_REVIVE_HP = 0.9
DH_REVIVE_HP_DECAY = 0.1
DH_REVIVE_HP_MIN = 0.1

# Druid: eagle swoop + bear rage form
DRUID_SWOOP_CHANCE = 0.15
DRUID_SWOOP_INCREMENT = 0.05
DRUID_SWOOP_MAX = 0.50
DRUID_SWOOP_BONUS = 0.8
DRUID_SWOOP_MULTIPLIER = (1.0 / 3.0 + DRUID_SWOOP_BONUS) / (1.0 / 3.0)
DRUID_RAGE_CRIT_CHANCE = 0.75
DRUID_RAGE_CRIT_BONUS = 0.1
DRUID_RAGE_CRIT_MULT = 4.0

# Bard: melody buff every N turns
BARD_EFFECT_ROUNDS = 4
BARD_DURATIONS: list[int] = [3, 3, 4]
BARD_CHANCES: list[int] = [25, 50, 25]
BARD_VALUES: list[float] = [0.2, 0.4, 0.6]

# Necromancer: minion summons
NECRO_SUMMON_CHANCE = 0.5

NECRO_SKELETON = 0
NECRO_ZOMBIE = 1
NECRO_SPECTRE = 2

NECRO_SUMMON_DURATION: list[int] = [3, 2, 4]
NECRO_SUMMON_DMG_BONUS: list[float] = [0.25, 1.0, 0.0]
NECRO_SUMMON_CRIT_CHANCE: list[float] = [0.5, 0.6, 0.5]
NECRO_SUMMON_CRIT_BONUS: list[float] = [0.0, 0.5, 0.0]
NECRO_SUMMON_CRIT_CHANCE_BONUS: list[float] = [0.0, 0.1, 0.0]
NECRO_SUMMON_SKIP_CHANCE: list[float] = [0.0, 0.0, 0.25]
NECRO_SKELETON_REVIVE_COUNT = 1
NECRO_SKELETON_REVIVE_DURATION = 1
NECRO_SKELETON_REVIVE_CHANCE = 0.5

# Paladin: stance cycling
PALADIN_STANCE_NEUTRAL = 0
PALADIN_STANCE_DEFENSIVE = 1
PALADIN_STANCE_OFFENSIVE = 2
PALADIN_STANCE_COUNT = 3
PALADIN_STANCE_CHANGE_CHANCE = 0.5

PALADIN_STANCE_SKIP: list[float] = [0.30, 0.50, 0.25]
PALADIN_STANCE_DMG_BONUS: list[float] = [0.0, -0.265, 0.42]
PALADIN_STANCE_MAX_RED_BONUS: list[int] = [0, 0, -25]
PALADIN_DEFENSIVE_HEAL_MULT = 0.3

# PlagueDoctor: tincture poison
PD_TINCTURE_CHANCE = 0.5
PD_TINCTURE_TOTAL_ROUNDS = 3
PD_TINCTURE_DMG_BONUS: list[float] = [-0.9, -0.55, -0.2]
PD_TINCTURE_SKIP_CHANCE: list[float] = [0.35, 0.50, 0.65]
