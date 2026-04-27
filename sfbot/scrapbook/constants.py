"""Scrapbook constants — boundaries, position formulas, item count."""

# Scrapbook bitfield: positions 1..800 = monsters, 801..2396 = items
# Game percentage = (monsters_found + items_found) / SCRAPBOOK_COUNT
SCRAPBOOK_COUNT = 2396
MONSTER_POSITIONS = 800
ITEM_POSITIONS = SCRAPBOOK_COUNT - MONSTER_POSITIONS  # 1596

# Legendary items (model_id >= 90) are not tracked in the scrapbook
MAX_MODEL_ID = 90

# EquipmentIdent boundaries for scrapbook position calculation.
# Outer index = ColorClass (0=classless, 1=Warrior, 2=Mage, 3=Scout).
# Inner key = Type - 1 (0=Weapon, 1=Shield, 2=Breastplate, 3=Footwear,
#   4=Gloves, 5=Hat, 6=Belt, 7=Amulet, 8=Ring, 9=Talisman).
# Value = [normal_start, epic_start].
# From sf-tools models.js line 592 and Rust unlockables.rs.
SCRAPBOOK_BOUNDARIES: list[dict[int, list[int]]] = [
    # ColorClass 0 — classless accessories
    {7: [800, 1010], 8: [1050, 1210], 9: [1250, 1324]},
    # ColorClass 1 — Warrior
    {
        0: [1364, 1664],
        1: [1704, 1804],
        2: [1844, 1944],
        3: [1984, 2084],
        4: [2124, 2224],
        5: [2264, 2364],
        6: [2404, 2504],
    },
    # ColorClass 2 — Mage
    {
        0: [2544, 2644],
        2: [2684, 2784],
        3: [2824, 2924],
        4: [2964, 3064],
        5: [3104, 3204],
        6: [3244, 3344],
    },
    # ColorClass 3 — Scout
    {
        0: [3384, 3484],
        2: [3524, 3624],
        3: [3664, 3764],
        4: [3804, 3904],
        5: [3944, 4044],
        6: [4084, 4184],
    },
]

# How often the main bot re-scores opponents from the DB (seconds).
QUEUE_REFRESH_INTERVAL = 1800  # 1 hour

# Max results for crawled opponents queue
MAX_QUEUE_SIZE = 50

# HoF pagination — matches Rust reference: pos//above/below, 51 per page
PLAYERS_PER_PAGE = 51
PLAYERS_ABOVE = 25
PLAYERS_BELOW = 25
HOF_START_POSITION = 26  # first page center: 26 (ranks 1-51)

# Minimum player level to consider (skip inactive accounts)
MIN_PLAYER_LEVEL = 2

# How many ranks above the player's own rank to start crawling from
CRAWL_RANKS_ABOVE = 1000

# Delay between API requests (seconds)
PAGE_DELAY = 0.5
PLAYER_DELAY = 0.3
