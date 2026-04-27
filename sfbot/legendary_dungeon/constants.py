from sfbot.legendary_dungeon.models import (
    DoorType,
    DungeonEffectType,
    RoomEncounterType,
    RoomType,
)

# ── Gem scoring (encounter-based model) ──────────────────────────────────────
#
# Dungeon layout:
#   Floors 1-24:  section 0 -> boss at 25 -> gem pick 1
#   Floors 26-49: section 1 -> boss at 50 -> gem pick 2
#   Floors 51-74: section 2 -> boss at 75 -> gem pick 3
#   Floors 76-99: section 3 -> final boss at 100 (no gem pick)
#
# All damage is %-based (of max HP); character level is irrelevant.
# Final boss max ~52.5% HP -- need roughly 53%+ HP entering floor 100.
# Scores are in units of "% of max HP saved" -- directly comparable.
#
# Key mechanics:
#   - Failed escape deals the SAME damage as a fight (not reduced).
#   - Successful escape = 0 damage.
#   - Bosses cannot be escaped.
#   - Traps: 10% HP.  Sacrifice door: 12%.  Sacrifice chest: 15%.
#   - Lava: 10%.  Rainbow Rack: 20%.  RPS lose: 10%.
#   - Poison curse: 5% per room.
#   - Broken Armor curse: +50% dmg (fights & escapes only, NOT bosses).

BROKEN_ARMOR_MULTIPLIER = 1.5

FIGHTS_PER_SECTION = 7
TRAPS_PER_SECTION = 4
ESCAPES_PER_SECTION = 3
SAC_DOORS_PER_SECTION = 1.5
SAC_CHESTS_PER_SECTION = 1.5
BARRELS_PER_SECTION = 2
CHESTS_PER_SECTION = 3
BASE_ESCAPE_RATE = 0.5

# Max regular monster damage (% HP) by section -- from LD Gadget worst-case
FIGHT_DMG = [14.4, 20.57, 23.25, 25.71]

# Max boss damage (% HP) -- LD Gadget worst-case
BOSS_DMG: dict[int, float] = {25: 19.6, 50: 28.05, 75: 28.05, 100: 52.5}

TRAP_DMG = 10.0
SAC_DOOR_DMG = 12.0
SAC_CHEST_DMG = 15.0

BLESSING_VALUE = 15.0
KEY_SAVE_RATE = 0.3

# Key targets per section (section 0 = floors 1-24, section 1 = 25-49, section 2 = 50-74).
# Section 3 (floors 75+) is the last section — keys are not needed for locked doors.
KEYS_TARGET = [6, 4, 4]
HEAL_THRESHOLD = 70.0
START_HP_THRESHOLD = 99.0
URGENT_HP_THRESHOLD = 20.0
URGENT_TIME_REMAINING = 7200
MAX_STEPS = 300

# Number of wire ints per gem entry
GEM_FIELDS = 6
# First 3 gem slots in the wire are the player's owned gems
OWNED_GEM_SLOTS = 3


# ── Door scoring sets ───────────────────────────────────────────────────────

MONSTER_DOOR_TYPES = {
    DoorType.MONSTER_1,
    DoorType.MONSTER_2,
    DoorType.MONSTER_3,
}
GOOD_DOOR_TYPES = {
    DoorType.OPEN_DOOR,
    DoorType.EPIC_DOOR,
    DoorType.GOLDEN_DOOR,
    DoorType.BLESSING_DOOR,
    DoorType.KEY_MASTER_SHOP,
}
RESOURCE_DOOR_TYPES = {
    DoorType.WOOD,
    DoorType.STONE,
    DoorType.SOULS,
    DoorType.METAL,
    DoorType.ARCANE,
    DoorType.SAND_WATCHES,
    DoorType.WHEEL,
}
TRIAL_DOOR_TYPES = {
    DoorType.TRIAL_ROOM_1,
    DoorType.TRIAL_ROOM_2,
    DoorType.TRIAL_ROOM_3,
    DoorType.TRIAL_ROOM_4,
    DoorType.TRIAL_ROOM_5,
    DoorType.TRIAL_ROOM_EXIT,
}

# ── Room classification sets ────────────────────────────────────────────────

SAFE_ROOMS = {
    RoomType.FOUNTAIN_OF_LIFE,
    RoomType.DUNGEON_NARRATOR,
    RoomType.PILE_OF_ROCKS,
    RoomType.PILE_OF_WOOD,
    RoomType.SOUL_BATH,
    RoomType.ARCANE_SPLINTERS_CAVE,
    RoomType.UNLOCKED_SARCOPHAGUS,
    RoomType.SEWERS,
    RoomType.LOCKER_ROOM,
    RoomType.AUCTION_HOUSE,
    RoomType.WISHING_WELL,
    RoomType.WEAPON_ROOM,
}
SKIP_ROOMS = {
    RoomType.WHEEL_OF_FORTUNE,
    RoomType.UNDEAD_FIEND,
    RoomType.FLYING_TUBE,
    RoomType.BETA_ROOM,
    RoomType.RAINBOW_ROOM,
    RoomType.PIG_ROOM,
    RoomType.VALARAUKAR,
    RoomType.ROCK_PAPER_SCISSORS,
    RoomType.SPIDER_WEB,
    RoomType.THE_FLOOR_IS_LAVA,
    RoomType.FLOODED_ROOM,
    RoomType.HOLE_IN_THE_FLOOR,
    RoomType.KEY_TO_FAILURE_SHOP,
}
SAFE_ENCOUNTERS = {
    RoomEncounterType.BRONZE_CHEST,
    RoomEncounterType.SILVER_CHEST,
    RoomEncounterType.EPIC_CHEST,
    RoomEncounterType.CRATE_1,
    RoomEncounterType.CRATE_2,
    RoomEncounterType.CRATE_3,
    RoomEncounterType.PRIZE_CHEST,
    RoomEncounterType.SATED_CHEST,
    RoomEncounterType.BARREL,
}
# ── Key Master's Shop ───────────────────────────────────────────────────────
#
# Only buy (priority order):
#   ONE_HIT_WONDER:   instant kill for 4|8 rooms -> 2|4 keys
#   ESCAPE_ASSISTANT: +80% escape for 5|10 rooms -> 3|6 keys
#   ROAD_TO_RECOVERY: heal 10%|20%/room for 3|6  -> 1|3 keys
#   ELIXIR_OF_LIFE:   heal 25%|50% instantly      -> 1|3 keys

SHOP_ITEMS: list[tuple[DungeonEffectType, int, int]] = [
    (DungeonEffectType.ONE_HIT_WONDER, 2, 4),
    (DungeonEffectType.ESCAPE_ASSISTANT, 3, 6),
    (DungeonEffectType.ROAD_TO_RECOVERY, 1, 3),
    (DungeonEffectType.ELIXIR_OF_LIFE, 1, 3),
]
INSTA_HEAL_EFFECT = {DungeonEffectType.ELIXIR_OF_LIFE}
