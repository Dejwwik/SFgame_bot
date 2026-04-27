from dataclasses import dataclass, field
from enum import IntEnum

# ── Enums ────────────────────────────────────────────────────────────────────


class EventTheme(IntEnum):
    DIABOLICAL_COMPANY_PARTY = 1
    LORD_OF_THE_THINGS = 2
    FANTASTIC_LEGENDARIES = 3
    SHADY_BIRTHDAY_BASH = 4
    MASSIVE_WINTER_SPECTACLE = 5
    ABYSS_OF_MADNESS = 6
    HUNT_FOR_BLAZING_EASTER_EGG = 7
    VILE_VACATION = 8


class DungeonStage(IntEnum):
    NOT_ENTERED = 0
    DOOR_SELECT = 1
    ROOM_ENTERED = 10
    ROOM_INTERACTED = 11
    ROOM_SPECIAL = 12
    ROOM_FINISHED = 100
    HEALING = 101
    COMPLETED = 102


class DungeonEffectType(IntEnum):
    # Blessings
    RAIDER = 1
    ONE_HIT_WONDER = 2
    ESCAPE_ASSISTANT = 3
    DISARM_TRAPS = 4
    LOCK_PICK = 5
    KEY_MOMENT = 6
    ELIXIR_OF_LIFE = 7
    ROAD_TO_RECOVERY = 8
    # Curses
    BROKEN_ARMOR = 101
    POISONED = 102
    PANDEROUS = 103
    GOLD_RUSH_HANGOVER = 104
    HARD_LOCK = 105


class DoorType(IntEnum):
    MONSTER_1 = 1
    MONSTER_2 = 2
    MONSTER_3 = 3
    BOSS_1 = 4
    BOSS_2 = 5
    BLOCKED = 1000
    MYSTERY_DOOR = 1001
    LOCKED_DOOR = 1002
    OPEN_DOOR = 1003
    EPIC_DOOR = 1004
    DOUBLE_LOCKED_DOOR = 1005
    GOLDEN_DOOR = 1006
    SACRIFICIAL_DOOR = 1007
    CURSED_DOOR = 1008
    KEY_MASTER_SHOP = 1009
    BLESSING_DOOR = 1010
    WHEEL = 1011
    WOOD = 1012
    STONE = 1013
    SOULS = 1014
    METAL = 1015
    ARCANE = 1016
    SAND_WATCHES = 1017
    TRIAL_ROOM_1 = 1018
    TRIAL_ROOM_2 = 1019
    TRIAL_ROOM_3 = 1020
    TRIAL_ROOM_4 = 1021
    TRIAL_ROOM_5 = 1022
    TRIAL_ROOM_EXIT = 1023


class DoorTrap(IntEnum):
    POISONED_DAGGERS = 1
    SWINGING_AXE = 2
    PAINT_BUCKET = 3
    BEAR_TRAP = 4
    GUILLOTINE = 5
    HAMMER_AMBUSH = 6
    TRIP_WIRE = 7
    TOP_SPIKES = 8
    SHARK = 9


class RoomType(IntEnum):
    GENERIC = 1
    BOSS_ROOM = 4
    ENCOUNTER = 100
    EMPTY = 200
    FOUNTAIN_OF_LIFE = 301
    HOLE_IN_THE_FLOOR = 302
    PILE_OF_ROCKS = 303
    THE_FLOOR_IS_LAVA = 304
    DUNGEON_NARRATOR = 305
    FLOODED_ROOM = 306
    WISHING_WELL = 307
    ROCK_PAPER_SCISSORS = 308
    SEWERS = 309
    UNDEAD_FIEND = 310
    LOCKER_ROOM = 311
    UNLOCKED_SARCOPHAGUS = 312
    VALARAUKAR = 313
    PILE_OF_WOOD = 314
    KEY_MASTER_SHOP = 315
    WHEEL_OF_FORTUNE = 316
    SPIDER_WEB = 317
    BETA_ROOM = 319
    FLYING_TUBE = 320
    SOUL_BATH = 321
    ARCANE_SPLINTERS_CAVE = 322
    KEY_TO_FAILURE_SHOP = 323
    RAINBOW_ROOM = 324
    PIG_ROOM = 325
    AUCTION_HOUSE = 326
    WEAPON_ROOM = 329


class RoomEncounterType(IntEnum):
    BRONZE_CHEST = 0
    SILVER_CHEST = 1
    EPIC_CHEST = 2
    CRATE_1 = 100
    CRATE_2 = 101
    CRATE_3 = 102
    MAGE_SKELETON = 300
    WARRIOR_SKELETON = 301
    BARREL = 400
    MIMIC_CHEST = 500
    SACRIFICIAL_CHEST = 600
    CURSE_CHEST = 601
    PRIZE_CHEST = 602
    SATED_CHEST = 603


class GemEffect(IntEnum):
    CHANCE_OF_KEYS = 1
    ESCAPE_CHANCE = 10
    DAMAGE_FROM_ESCAPE = 11
    CHANCE_OF_KEY_AFTER_ESCAPE = 12
    CHANCE_OF_CURSE_AFTER_ESCAPE = 13
    DURATION_OF_BLESSINGS = 30
    DURATION_OF_CURSES = 31
    CHANCE_OF_STRONGER_CURSES = 32
    DAMAGE_FROM_MONSTERS = 40
    CHANCE_OF_BLESSING_AFTER_FIGHT = 41
    CHANCE_OF_CURSE_AFTER_FIGHT = 42
    CHANCE_OF_BLESSINGS_IN_BARRELS = 50
    CHANCE_OF_BETTER_BLESSINGS_IN_BARRELS = 51
    DAMAGE_FROM_SAC_DOORS = 70
    DAMAGE_FROM_CHESTS = 71
    DAMAGE_FROM_TRAPS = 90
    BLESSING_OR_CURSE_AFTER_REVIVE = 100
    BLESSINGS_IN_BARRELS_CHESTS_CORPSES = 110
    HEALING_FROM_BLESSINGS = 130


class GemSpecial(IntEnum):
    WEAKER_MONSTERS_SPAWN = 1
    STRONGER_MONSTERS_SPAWN = 2
    MORE_TRAPS_SPAWN = 3
    SAC_CHESTS_BEHIND_CLOSED_DOORS = 6
    MORE_SAC_DOORS = 8
    FEWER_SAC_DOORS = 9
    CURSED_CHESTS_BEHIND_CLOSED_DOORS = 10
    MORE_CURSED_DOORS = 12
    FEWER_CURSED_DOORS = 13
    CHANCE_OF_EPIC_DOORS = 17
    CHANCE_OF_UNLOCKED_DOORS = 18
    CHANCE_OF_DOUBLE_LOCKED_DOOR = 19
    MORE_MYSTERIOUS_ROOMS = 20
    FEWER_MYSTERIOUS_ROOMS = 21
    ALWAYS_ONE_TRAP = 22
    ALWAYS_ONE_LOCK = 23
    MONSTERS_BEHIND_DOORS = 24
    NO_MORE_EPIC_CHESTS = 25
    TRAPS_INFLICT_CURSE = 26


class GemType(IntEnum):
    EYE_OF_THE_BULL = 1
    SOUL_OF_THE_RABBIT = 2
    BOULDER_OF_GREED = 3
    EMERALD_OF_THE_EXPLORER = 4
    PEARL_OF_THE_MASOCHIST = 5
    PENDANT_OF_THE_KEY_MASTER = 6
    PEBBLE_OF_DECEIT = 7
    GREASY_HEALING_STONE = 8
    SPYING_GEM = 9
    LODE_STONE = 10
    BOULDER_OF_THE_GAMBLER = 11
    OLD_SACRIFICIAL_STONE = 12
    BLOOD_DROP_OF_SACRIFICE = 13
    KIDNEY_STONE_OF_DETERMINATION = 14
    HOPE_OF_THE_THIRSTY_ONE = 15
    ERRATIC_BOULDER_OF_THE_HIP = 16
    SAPHIRE_OF_THE_MISADVENTURER = 17
    CURSED_MOONSTONE = 18
    DIAMOND_OF_THE_TIMETRAVELER = 19
    TREASURE_OF_THE_HERO = 20
    CROWN_JEWEL_OF_THE_DEVIL = 21
    CURSED_PEARL = 22
    RUSTY_HEALING_STONE = 23


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass(slots=True)
class MerchantOffer:
    typ: DungeonEffectType
    max_uses: int
    strength: int
    keys: int


@dataclass(slots=True)
class DungeonEffect:
    typ: DungeonEffectType
    remaining_uses: int
    max_uses: int
    strength: int


@dataclass(slots=True)
class Door:
    typ: DoorType
    trap: DoorTrap | None = None


@dataclass(slots=True)
class RoomEncounter:
    is_monster: bool = False
    monster_id: int = 0
    encounter_type: RoomEncounterType | None = None

    @staticmethod
    def parse(val: int) -> "RoomEncounter":
        if val < 0:
            return RoomEncounter(is_monster=True, monster_id=abs(val))
        try:
            return RoomEncounter(encounter_type=RoomEncounterType(val))
        except ValueError:
            return RoomEncounter()


@dataclass(slots=True)
class RunStats:
    items_found: int = 0
    epics_found: int = 0
    keys_found: int = 0
    silver_found: int = 0
    attempts: int = 0


@dataclass(slots=True)
class TotalStats:
    legendaries_found: int = 0
    best_run_attempts: int = 0
    enemies_defeated: int = 0
    epics_found: int = 0
    gold_found: int = 0


@dataclass(slots=True)
class GemOfFate:
    typ: GemType | None = None
    advantage: GemEffect | None = None
    advantage_pwr: int = 0
    disadvantage: GemEffect | None = None
    disadvantage_pwr: int = 0
    special: GemSpecial | None = None


@dataclass(slots=True)
class DungeonState:
    health_status: int = 0
    current_hp: int = 0
    pre_battle_hp: int = 0
    max_hp: int = 0
    blessings: list[DungeonEffect | None] = field(
        default_factory=lambda: [None, None, None]
    )
    curses: list[DungeonEffect | None] = field(
        default_factory=lambda: [None, None, None]
    )
    stage: DungeonStage = DungeonStage.NOT_ENTERED
    gem_count: int = 0
    current_floor: int = 0
    max_floor: int = 0
    doors: list[Door] = field(
        default_factory=lambda: [Door(DoorType.BLOCKED), Door(DoorType.BLOCKED)]
    )
    room_type: RoomType | None = None
    encounter: RoomEncounter = field(default_factory=RoomEncounter)
    keys: int = 0

    @property
    def is_alive(self) -> bool:
        return self.health_status != 1 and self.stage != DungeonStage.HEALING

    @property
    def is_healing(self) -> bool:
        return self.stage == DungeonStage.HEALING
