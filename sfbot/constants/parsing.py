"""Field index constants for parsing server responses."""

# --- Common delimiter ---
VALUES_DELIMITER = "/"

# --- Item field count per item ---
ITEM_FIELD_COUNT = 19

# --- Item field indices (within the 19-field chunk) ---
ITEM_FIELD_TYPE = 0  # & 0xFF → ItemType
ITEM_FIELD_GEM_SLOT = 1
ITEM_FIELD_ENCHANTMENT = 2
ITEM_FIELD_MODEL = 3  # & 0xFFFF → full model (class_id * 1000 + model_id)
ITEM_FIELD_MIN_DAMAGE = 5
ITEM_FIELD_MAX_DAMAGE = 6
ITEM_FIELD_ATTR_TYPE_0 = 7  # +0,+1,+2 for 3 attr type slots
ITEM_FIELD_ATTR_VALUE_0 = 10  # +0,+1,+2 for 3 attr value slots
ITEM_FIELD_PRICE = 13  # sell_raw (gold*100 + silver)
ITEM_FIELD_MUSHROOM_PRICE = 14
ITEM_FIELD_UPGRADES = 15
ITEM_FIELD_GEM_POWER = 16
ITEM_FIELD_QUALITY = 17
ITEM_FIELD_WASHED = 18

# --- Wire format constants ---
MAIN_BACKPACK_SLOT_COUNT = 5  # indices 0-4 → "2/{i+1}"
WEAPON_EQUIPMENT_SLOT = 8  # 0-indexed equipment slot for weapon
WIRE_EQUIPMENT = "1"
WIRE_MAIN_BACKPACK = "2"
WIRE_EXTENDED_BACKPACK = "5"

# --- Model decomposition ---
MODEL_CLASS_DIVISOR = 1000  # model_info // 1000 → class, model_info % 1000 → model_id

# --- Character data indices (ownplayersavecharacter / otherplayersavecharacter) ---
CHARACTER_LEVEL_INDEX = 3  # & 0xFFFF → character level
CHARACTER_XP_INDEX = 4
CHARACTER_XP_NEXT_INDEX = 5
CHARACTER_HONOR_INDEX = 6
CHARACTER_RANK_INDEX = 7
CHARACTER_RACE_INDEX = 18
CHARACTER_CLASS_INDEX = 20  # 1-based (subtract 1 for CharClass enum)
CHARACTER_MOUNT_INDEX = 21  # & 0xFF → mount id
CHARACTER_ARMOR_INDEX = 23
CHARACTER_MIN_DAMAGE_INDEX = 24
CHARACTER_MAX_DAMAGE_INDEX = 25
CHARACTER_PORTAL_DMG_BONUS_INDEX = 26
CHARACTER_PORTAL_HP_BONUS_INDEX = 28
CHARACTER_MOUNT_END_INDEX = 29  # unix timestamp when mount expires
CHARACTER_BASE_ATTR_INDEX = 30  # [30:35] → Str, Dex, Int, Con, Luck (base)
CHARACTER_BONUS_ATTR_INDEX = 35  # [35:40] → Str, Dex, Int, Con, Luck (bonus)
CHARACTER_BOUGHT_ATTR_INDEX = 40  # [40:45] → times-bought per attribute
CHARACTER_MIN_FIELDS = 45  # minimum field count for a valid character
CHARACTER_ATTR_COUNT = 5  # number of attributes per group (Str, Dex, Int, Con, Luck)

# --- characterstatus field indices ---
CHARACTER_STATUS_ACTION_INDEX = 1
CHARACTER_STATUS_SECONDS_INDEX = 2
CHARACTER_STATUS_BUSY_UNTIL_INDEX = 3
CHARACTER_STATUS_BEER_MAX_INDEX = 5
CHARACTER_STATUS_THIRST_INDEX = 6
CHARACTER_STATUS_BEER_DRUNK_INDEX = 7
CHARACTER_STATUS_PET_EXPLORATION_TIMER_INDEX = 20
CHARACTER_STATUS_DUNGEON_NEXT_FREE_FIGHT_INDEX = 21

# --- resources field indices ---
RESOURCE_MUSHROOMS_INDEX = 1
RESOURCE_SILVER_RAW_INDEX = 2  # gold = val // 100, silver = val % 100
RESOURCE_LUCKY_COINS_INDEX = 3
RESOURCE_HOURGLASSES_INDEX = 4
RESOURCE_WOOD_INDEX = 5
RESOURCE_STONE_INDEX = 7
RESOURCE_METAL_INDEX = 9
RESOURCE_ARCANE_INDEX = 10
RESOURCE_SOULS_INDEX = 11
RESOURCE_FRUITS_BASE_INDEX = 12  # fruit counts per element at [12..16]

# --- pet field indices (ownpets array) ---
PET_LEVEL_BASE = 2  # pet levels at [pet_id + 1], pet_id 1-based → indices 2..101
PET_FRUITS_TODAY_BASE = 110  # fruits fed today at [pet_id + 109] → indices 110..209
PET_TOTAL_COLLECTED_INDEX = 103
PET_EXPLORED_BASE = 210  # explored per element at [210 + e], e=0..4
PET_BATTLED_OPPONENT_BASE = 223  # 1 if fought PvP today per element [223 + e]
PET_OPPONENT_ID_INDEX = 231
PET_OPPONENT_NEXT_FREE_BATTLE_INDEX = 232
PET_RANK_INDEX = 233
PET_HONOR_INDEX = 234
PET_OPPONENT_PET_COUNT_INDEX = 235
PET_OPPONENT_LEVEL_TOTAL_INDEX = 236
PET_OPPONENT_REROLL_DATE_INDEX = 237
PET_NEXT_FIGHT_LEVEL_BASE = 238  # next fight level per element [238 + e]
PET_ATR_BONUS_BASE = 250  # attribute bonuses at [250..254]

# --- owngroupsave.groupSave field indices ---
GUILD_PORTAL_LIFE_INDEX = 6  # >> 16
GUILD_PORTAL_DEFEATED_INDEX = 7  # >> 16
GUILD_FINISHED_RAIDS_INDEX = 8
GUILD_ATTACK_GUILD_INDEX = 364
GUILD_ATTACK_TIME_INDEX = 365
GUILD_DEFEND_GUILD_INDEX = 366
GUILD_DEFEND_TIME_INDEX = 367
GUILD_HYDRA_LIFE_INDEX = 383
GUILD_HYDRA_MAX_LIFE_INDEX = 384
GUILD_MEMBER_COUNT_INDEX = 3
GUILD_MEMBER_RANK_BASE_INDEX = 314  # + offset
GUILD_MEMBER_BATTLES_BASE_INDEX = 445  # + offset, % 100
GUILD_MEMBER_PORTAL_FOUGHT_BASE_INDEX = 164  # + offset, timestamp
GUILD_RANK_LEADER = 1
GUILD_RANK_OFFICER = 2
GUILD_RANK_MEMBER = 3

# --- charactergroup field indices ---
CHARACTER_GROUP_TREASURE_SKILL_INDEX = 0
CHARACTER_GROUP_INSTRUCTOR_SKILL_INDEX = 1
CHARACTER_GROUP_HYDRA_NEXT_BATTLE_INDEX = 2
CHARACTER_GROUP_HYDRA_REMAINING_INDEX = 3
CHARACTER_GROUP_PET_SKILL_INDEX = 4
CHARACTER_GROUP_JOINED_INDEX = 5

# --- ownplayersavepotions field indices ---
POTION_ID_START_INDEX = 1  # potion IDs at indices 1, 2, 3
POTION_EXPIRY_START_INDEX = 4  # expiry timestamps at indices 4, 5, 6
POTION_SLOT_COUNT = 3

# --- owntower companion data ---
# Each companion block is 148 values apart.  Layout per companion (22 values):
#   [+0] level, [+1..+3] skip, [+4..+8] base attrs, [+9..+13] bonus attrs,
#   [+14..+18] purchased attrs, [+19] armor, [+20] min_dmg, [+21] max_dmg
COMPANION_TOWER_STRIDE = 148
COMPANION_TOWER_FIRST = 3  # Bert starts at index 3
COMPANION_BASE_ATTR_OFFSET = 4
COMPANION_BONUS_ATTR_OFFSET = 9
COMPANION_ARMOR_OFFSET = 19
COMPANION_MIN_DMG_OFFSET = 20
COMPANION_MAX_DMG_OFFSET = 21

# --- owntower field indices (underworld buildings at offset 448) ---
GLADIATOR_TRAINER_INDEX = 454  # 448 + GladiatorTrainer(6)
