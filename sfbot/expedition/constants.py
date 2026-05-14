from enum import IntEnum


class FloorStage(IntEnum):
    CROSSROADS = 1
    BOSS = 2
    REWARDS = 3
    WAITING = 4


class ExpeditionThing(IntEnum):
    UNKNOWN = 0
    DUMMY1 = 1
    DUMMY2 = 2
    DUMMY3 = 3
    TOILET_PAPER = 11
    BAIT = 21
    DRAGON = 22
    CAMP_FIRE = 31
    PHOENIX = 32
    BURNT_CAMPFIRE = 33
    UNICORN_HORN = 41
    DONKEY = 42
    RAINBOW = 43
    UNICORN = 44
    CUP_CAKE = 51
    CAKE = 61
    SMALL_HURDLE = 71
    BIG_HURDLE = 72
    WINNERS_PODIUM = 73
    SOCKS = 81
    CLOTH_PILE = 82
    REVEALING_COUPLE = 83
    SWORD_IN_STONE = 91
    BENT_SWORD = 92
    BROKEN_SWORD = 93
    WELL = 101
    GIRL = 102
    BALLOONS = 103
    PRINCE = 111
    ROYAL_FROG = 112
    HAND = 121
    FEET = 122
    BODY = 123
    KLAUS = 124
    KEY = 131
    SUITCASE = 132
    FISHING_ROD = 141
    FISHING_BAIT = 142
    MERMAN = 143
    MUGS = 151
    DRAFT_BEER = 152
    BARKEEPER = 153
    CHICKEN = 161
    TIGER = 162
    RIDING_STAN = 163
    CUPID = 171
    LOVESTRUCK_SHAKES = 172
    LOVE_BIRDS = 173
    DUMMY_BOUNTY = 1000
    TOILET_PAPER_BOUNTY = 1001
    DRAGON_BOUNTY = 1002
    BURNT_CAMPFIRE_BOUNTY = 1003
    UNICORN_BOUNTY = 1004
    WINNER_PODIUM_BOUNTY = 1007
    REVEALING_COUPLE_BOUNTY = 1008
    BROKEN_SWORD_BOUNTY = 1009
    BALLOON_BOUNTY = 1010
    FROG_BOUNTY = 1011
    KLAUS_BOUNTY = 1012
    MERMAN_BOUNTY = 1014
    BARKEEPER_BOUNTY = 1015
    STAN_BOUNTY = 1016
    LOVE_BIRD_BOUNTY = 1017


# Target thing → matching bounty
TARGET_TO_BOUNTY: dict[int, int] = {
    ExpeditionThing.DUMMY1: ExpeditionThing.DUMMY_BOUNTY,
    ExpeditionThing.DUMMY2: ExpeditionThing.DUMMY_BOUNTY,
    ExpeditionThing.DUMMY3: ExpeditionThing.DUMMY_BOUNTY,
    ExpeditionThing.TOILET_PAPER: ExpeditionThing.TOILET_PAPER_BOUNTY,
    ExpeditionThing.DRAGON: ExpeditionThing.DRAGON_BOUNTY,
    ExpeditionThing.BURNT_CAMPFIRE: ExpeditionThing.BURNT_CAMPFIRE_BOUNTY,
    ExpeditionThing.UNICORN: ExpeditionThing.UNICORN_BOUNTY,
    ExpeditionThing.WINNERS_PODIUM: ExpeditionThing.WINNER_PODIUM_BOUNTY,
    ExpeditionThing.REVEALING_COUPLE: ExpeditionThing.REVEALING_COUPLE_BOUNTY,
    ExpeditionThing.BROKEN_SWORD: ExpeditionThing.BROKEN_SWORD_BOUNTY,
    ExpeditionThing.BALLOONS: ExpeditionThing.BALLOON_BOUNTY,
    ExpeditionThing.ROYAL_FROG: ExpeditionThing.FROG_BOUNTY,
    ExpeditionThing.KLAUS: ExpeditionThing.KLAUS_BOUNTY,
    ExpeditionThing.MERMAN: ExpeditionThing.MERMAN_BOUNTY,
    ExpeditionThing.BARKEEPER: ExpeditionThing.BARKEEPER_BOUNTY,
    ExpeditionThing.RIDING_STAN: ExpeditionThing.STAN_BOUNTY,
    ExpeditionThing.LOVE_BIRDS: ExpeditionThing.LOVE_BIRD_BOUNTY,
}

# Target thing → ordered chain of prerequisites (not including the target itself).
# Pick chain items in order to make the target appear. If multiple chain items are
# offered simultaneously, pick the one furthest along (highest index in list).
TARGET_CHAIN: dict[int, list[int]] = {
    ExpeditionThing.DRAGON: [ExpeditionThing.BAIT],
    ExpeditionThing.BURNT_CAMPFIRE: [ExpeditionThing.CAMP_FIRE, ExpeditionThing.PHOENIX],
    ExpeditionThing.UNICORN: [ExpeditionThing.UNICORN_HORN, ExpeditionThing.DONKEY, ExpeditionThing.RAINBOW],
    ExpeditionThing.WINNERS_PODIUM: [ExpeditionThing.SMALL_HURDLE, ExpeditionThing.BIG_HURDLE],
    ExpeditionThing.REVEALING_COUPLE: [ExpeditionThing.SOCKS, ExpeditionThing.CLOTH_PILE],
    ExpeditionThing.BROKEN_SWORD: [ExpeditionThing.SWORD_IN_STONE, ExpeditionThing.BENT_SWORD],
    ExpeditionThing.BALLOONS: [ExpeditionThing.WELL, ExpeditionThing.GIRL],
    ExpeditionThing.ROYAL_FROG: [ExpeditionThing.PRINCE],
    ExpeditionThing.KLAUS: [ExpeditionThing.HAND, ExpeditionThing.FEET, ExpeditionThing.BODY],
    ExpeditionThing.MERMAN: [ExpeditionThing.FISHING_ROD, ExpeditionThing.FISHING_BAIT],
    ExpeditionThing.BARKEEPER: [ExpeditionThing.MUGS, ExpeditionThing.DRAFT_BEER],
    ExpeditionThing.RIDING_STAN: [ExpeditionThing.CHICKEN, ExpeditionThing.TIGER],
    ExpeditionThing.LOVE_BIRDS: [ExpeditionThing.CUPID, ExpeditionThing.LOVESTRUCK_SHAKES],
}


class RewardType(IntEnum):
    HELLEVATOR_POINTS = 1
    HELLEVATOR_CARDS = 2
    MUSHROOMS = 3
    SILVER = 4
    LUCKY_COINS = 5
    WOOD = 6
    STONE = 7
    ARCANE = 8
    METAL = 9
    SOULS = 10
    FRUIT_SHADOW = 11
    FRUIT_LIGHT = 12
    FRUIT_EARTH = 13
    FRUIT_FIRE = 14
    FRUIT_WATER = 15
    LEGENDARY_GEM = 16
    GOLD_FIDGET = 17
    SILVER_FIDGET = 18
    BRONZE_FIDGET = 19
    GEM_1 = 20
    GEM_2 = 21
    GEM_3 = 22
    FRUIT_BASKET = 23
    XP = 24
    EGG = 25
    QUICKSAND_GLASS = 26
    HONOR = 27
    BEER = 28


# Higher = more valuable. Used to pick the best reward.
REWARD_PRIORITY: dict[int, int] = {
    RewardType.EGG: 100,
    RewardType.LEGENDARY_GEM: 90,
    RewardType.MUSHROOMS: 89,
    RewardType.LUCKY_COINS: 85,
    RewardType.QUICKSAND_GLASS: 80,
    RewardType.GEM_1: 70,
    RewardType.GEM_2: 70,
    RewardType.GEM_3: 70,
    RewardType.FRUIT_BASKET: 65,
    RewardType.BEER: 60,
    RewardType.HONOR: 55,
    RewardType.XP: 50,
    RewardType.GOLD_FIDGET: 45,
    RewardType.SILVER_FIDGET: 40,
    RewardType.BRONZE_FIDGET: 35,
    RewardType.SILVER: 30,
    RewardType.SOULS: 25,
    RewardType.ARCANE: 20,
    RewardType.WOOD: 15,
    RewardType.STONE: 15,
    RewardType.METAL: 15,
    RewardType.FRUIT_SHADOW: 10,
    RewardType.FRUIT_LIGHT: 10,
    RewardType.FRUIT_EARTH: 10,
    RewardType.FRUIT_FIRE: 10,
    RewardType.FRUIT_WATER: 10,
}


# expeditionstate field indices
ES_CURRENT_FLOOR = 0
ES_FLOOR_STAGE = 2
ES_TARGET_THING = 3
ES_TARGET_CURRENT = 7
ES_TARGET_AMOUNT = 8
ES_ITEMS_START = 9
ES_ITEMS_COUNT = 4
ES_HEROISM = 13
ES_BUSY_SINCE = 15
ES_BUSY_UNTIL = 16

# Available expeditions: chunks of 8
EXPEDITION_FIELDS = 8
AE_TARGET = 0
AE_LOCATION_1 = 4
AE_LOCATION_2 = 5
AE_THIRST_SEC = 6
AE_SPECIAL = 7

TOTAL_FLOORS = 10
