"""Feature unlock levels, caps, and thresholds."""

# --- Feature unlock levels (player level required) ---
GUARD_UNLOCK_LEVEL = 12
LEGENDARY_DUNGEON_UNLOCK_LEVEL = 50
WITCH_UNLOCK_LEVEL = 66
PET_UNLOCK_LEVEL = 75
SMITH_UNLOCK_LEVEL = 90
PORTAL_UNLOCK_LEVEL = 99
DICE_UNLOCK_LEVEL = 100
TOILET_UNLOCK_LEVEL = 100

# --- Item rarity thresholds (based on model_id = model_info % 1000) ---
RARITY_EPIC_THRESHOLD = 50
RARITY_LEGENDARY_THRESHOLD = 90

# --- Rune type threshold ---
RUNE_TYPE_THRESHOLD = 31  # attribute types >= 31 are runes

# --- Potion size unlock thresholds ---
MEDIUM_POTION_LEVEL = 10
LARGE_POTION_LEVEL = 15

# --- Socket gate level (items without sockets rejected above this) ---
SOCKET_GATE_LEVEL = 25

# --- Gem value ratios ---
BLACK_GEM_ATTR_RATIO = 0.66
LEGENDARY_GEM_ATTR_RATIO = 0.65
BLACK_GEM_SELL_RATIO = 0.9  # sell threshold multiplier for black gems — matches GEM_KEEP_RATIO to close dead zone

# --- Smith upgrade multiplier ---
# Each smith upgrade increases the highest attribute(s) by this factor.
SMITH_UPGRADE_MULTIPLIER = 1.03

# --- Special item model ---
WINGS_MODEL_ID = 16

# --- Wings (life potion) HP bonus percentage ---
WINGS_HP_BONUS = 25
