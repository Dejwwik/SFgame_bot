"""Game enums, types, and lookup tables."""

from dataclasses import dataclass
from enum import IntEnum, StrEnum


class Rarity(StrEnum):
    NORMAL = "Normal"
    EPIC = "Epic"
    LEGENDARY = "Legendary"


class GemSlot(StrEnum):
    NONE = "None"
    EMPTY = "Empty"
    FILLED = "Filled"


# --- Equipment slot display names ---
EQUIPMENT_SLOT_NAMES = [
    "Weapon",
    "Shield",
    "Breastplate",
    "Footwear",
    "Gloves",
    "Hat",
    "Belt",
    "Amulet",
    "Ring",
    "Talisman",
]


class ShopType(IntEnum):
    WEAPON_SHOP = 3
    MAGIC_SHOP = 4


class ItemType(IntEnum):
    WEAPON = 1
    SHIELD = 2
    BREASTPLATE = 3
    FOOTWEAR = 4
    GLOVES = 5
    HAT = 6
    BELT = 7
    AMULET = 8
    RING = 9
    TALISMAN = 10
    SPECIAL = 11
    POTION = 12
    SCRAPBOOK = 13
    EPIC_ITEM_BAG = 14
    GEM = 15
    PET_ITEM = 16
    QUICK_SAND_GLASS = 17
    HEART_OF_DARKNESS = 18
    WHEEL_OF_FORTUNE = 19
    MANNEQUIN = 20


class AttributeCategory(StrEnum):
    SINGLE = "single"
    ALL = "all"
    TRIPLE = "triple"


class ItemAttributeType(IntEnum):
    STRENGTH = 1
    DEXTERITY = 2
    INTELLIGENCE = 3
    CONSTITUTION = 4
    LUCK = 5
    ALL = 6
    STR_CON_LUCK = 21
    DEX_CON_LUCK = 22
    INT_CON_LUCK = 23

    @property
    def category(self) -> AttributeCategory:
        if self.value <= 5:
            return AttributeCategory.SINGLE
        if self.value == 6:
            return AttributeCategory.ALL
        return AttributeCategory.TRIPLE


class Attribute(IntEnum):
    STRENGTH = 1
    DEXTERITY = 2
    INTELLIGENCE = 3
    CONSTITUTION = 4
    LUCK = 0

    @property
    def server_value(self) -> int:
        """Server protocol index: STR=1, DEX=2, INT=3, CON=4, LCK=5."""
        return self.value if self.value != 0 else 5


class PotionAttributeType(IntEnum):
    """Potion attribute, including HP/Wings as a special case."""

    LUCK = 0
    STRENGTH = 1
    DEXTERITY = 2
    INTELLIGENCE = 3
    CONSTITUTION = 4
    HP = 99


class PotionSize(IntEnum):
    SMALL = 1  # 10%
    MEDIUM = 2  # 15%
    LARGE = 3  # 25%


POTION_NAMES = {
    1: "Strength Small (10%)",
    2: "Dexterity Small (10%)",
    3: "Intelligence Small (10%)",
    4: "Constitution Small (10%)",
    5: "Luck Small (10%)",
    6: "Strength Medium (15%)",
    7: "Dexterity Medium (15%)",
    8: "Intelligence Medium (15%)",
    9: "Constitution Medium (15%)",
    10: "Luck Medium (15%)",
    11: "Strength Large (25%)",
    12: "Dexterity Large (25%)",
    13: "Intelligence Large (25%)",
    14: "Constitution Large (25%)",
    15: "Luck Large (25%)",
    16: "Eternal Life (Wings/HP)",
}


class CharClass(IntEnum):
    """Character classes (0-based, as used in item model: model_info // 1000)."""

    WARRIOR = 0
    MAGE = 1
    SCOUT = 2
    ASSASSIN = 3
    BATTLE_MAGE = 4
    BERSERKER = 5
    DEMON_HUNTER = 6
    DRUID = 7
    BARD = 8
    NECROMANCER = 9
    PALADIN = 10
    PLAGUE_DOCTOR = 11

    @property
    def main_attr(self) -> "Attribute":
        return _CLASS_TO_MAIN_ATTR[self]

    @classmethod
    def main_attr_index(cls, class_id: int) -> int:
        return _CLASS_TO_MAIN_ATTR[cls(class_id)].value


_CLASS_TO_MAIN_ATTR: dict[CharClass, Attribute] = {
    CharClass.WARRIOR: Attribute.STRENGTH,
    CharClass.MAGE: Attribute.INTELLIGENCE,
    CharClass.SCOUT: Attribute.DEXTERITY,
    CharClass.ASSASSIN: Attribute.DEXTERITY,
    CharClass.BATTLE_MAGE: Attribute.STRENGTH,
    CharClass.BERSERKER: Attribute.STRENGTH,
    CharClass.DEMON_HUNTER: Attribute.DEXTERITY,
    CharClass.DRUID: Attribute.INTELLIGENCE,
    CharClass.BARD: Attribute.INTELLIGENCE,
    CharClass.NECROMANCER: Attribute.INTELLIGENCE,
    CharClass.PALADIN: Attribute.STRENGTH,
    CharClass.PLAGUE_DOCTOR: Attribute.DEXTERITY,
}


class CompanionClass(IntEnum):
    """Tower companions (Bert/Mark/Kunigunde).

    Wire section for companion equip = value + 101.
    """

    WARRIOR = 0  # Bert
    MAGE = 1  # Mark
    SCOUT = 2  # Kunigunde

    @property
    def display_name(self) -> str:
        match self:
            case CompanionClass.WARRIOR:
                return "Bert"
            case CompanionClass.MAGE:
                return "Mark"
            case _:
                return "Kunigunde"

    @property
    def char_class(self) -> CharClass:
        return _COMPANION_TO_CLASS[self]

    @property
    def wire_section(self) -> int:
        """Wire section ID for PlayerItemMove commands."""
        return self.value + 101


_COMPANION_TO_CLASS: dict[CompanionClass, CharClass] = {
    CompanionClass.WARRIOR: CharClass.WARRIOR,
    CompanionClass.MAGE: CharClass.MAGE,
    CompanionClass.SCOUT: CharClass.SCOUT,
}


class Race(IntEnum):
    """Races (1-based, from ownplayersavecharacter[18])."""

    HUMAN = 1
    ELF = 2
    DWARF = 3
    GNOME = 4
    ORC = 5
    DARK_ELF = 6
    GOBLIN = 7
    DEMON = 8


class Mount(IntEnum):
    NONE = 0
    COW = 1
    HORSE = 2
    TIGER = 3
    DRAGON = 4


class HabitatType(IntEnum):
    SHADOW = 0  # pet IDs 1-20, typ_id=1, → Constitution
    LIGHT = 1  # pet IDs 21-40, typ_id=2, → Dexterity
    EARTH = 2  # pet IDs 41-60, typ_id=3, → Intelligence
    FIRE = 3  # pet IDs 61-80, typ_id=4, → Luck
    WATER = 4  # pet IDs 81-100, typ_id=5, → Strength


class EquipmentSlot(IntEnum):
    """Equipment slots (wire position 1-10)."""

    HAT = 1
    BREASTPLATE = 2
    GLOVES = 3
    FOOTWEAR = 4
    AMULET = 5
    BELT = 6
    RING = 7
    TALISMAN = 8
    WEAPON = 9
    SHIELD = 10


class RuneType(IntEnum):
    QUEST_GOLD = 31
    EPIC_CHANCE = 32
    ITEM_QUALITY = 33
    QUEST_XP = 34
    EXTRA_HP = 35
    FIRE_RES = 36
    COLD_RES = 37
    LIGHTNING_RES = 38
    TOTAL_RES = 39
    FIRE_DMG = 40
    COLD_DMG = 41
    LIGHTNING_DMG = 42


class Enchantment(IntEnum):
    SWORD_OF_VENGEANCE = 11
    MARIOS_BEARD = 31
    MANY_FEET_BOOTS = 41
    SHADOW_OF_COWBOY = 51
    ARCHAEOLOGICAL_AURA = 61
    THIRSTY_WANDERER = 71
    UNHOLY_ACQUISITIVENESS = 81
    GRAVE_ROBBERS_PRAYER = 91
    ROBBER_BARON_RITUAL = 101


class Location(IntEnum):
    SPRAWLING_JUNGLE = 1
    SKULL_ISLAND = 2
    EVERNIGHT_FOREST = 3
    STUMBLE_STEPPE = 4
    SHADOWROCK_MOUNTAIN = 5
    SPLIT_CANYON = 6
    BLACK_WATER_SWAMP = 7
    FLOODED_CALDWELL = 8
    TUSK_MOUNTAIN = 9
    MOLDY_FOREST = 10
    NEVERMOOR = 11
    BUSTED_LANDS = 12
    EROGENION = 13
    MAGMARON = 14
    SUNBURN_DESERT = 15
    GNAROGRIM = 16
    NORTHRUNT = 17
    BLACK_FOREST = 18
    MAERWYNN = 19
    PLAINS_OF_OZ_KORR = 20
    ROTTEN_LANDS = 21


class TimeOfDay(IntEnum):
    DAY = 0
    NIGHT = 1
    MIDNIGHT = 2  # hours 0-1, special subset of night


class Weekday(IntEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class Season(StrEnum):
    SPRING = "Spring"
    SUMMER = "Summer"
    FALL = "Fall"
    WINTER = "Winter"


class DicePayment(IntEnum):
    FREE = 0
    MUSHROOMS = 1
    HOURGLASS = 2


class DiceType(IntEnum):
    REROLL = 0
    SILVER = 1
    STONE = 2
    WOOD = 3
    SOULS = 4
    ARCANE = 5
    HOURGLASS = 6


class GemAttr(IntEnum):
    STRENGTH = 0
    DEXTERITY = 1
    INTELLIGENCE = 2
    CONSTITUTION = 3
    LUCK = 4
    BLACK = 5
    LEGENDARY = 6


class Action(IntEnum):
    IDLE = 0
    GUARD = 1
    QUEST = 2
    EXPEDITION = 4


class Event(IntEnum):
    EXCEPTIONAL_XP = 0
    GLORIOUS_GOLD_GALORE = 1
    TIDY_TOILET_TIME = 2
    ASSEMBLY_OF_AWESOME_ANIMALS = 3
    FANTASTIC_FORTRESS_FESTIVITY = 4
    DAYS_OF_DOOMED_SOULS = 5
    WITCHES_DANCE = 6
    SANDS_OF_TIME_SPECIAL = 7
    FORGE_FRENZY_FESTIVAL = 8
    EPIC_SHOPPING_SPREE = 9
    EPIC_QUEST_EXTRAVAGANZA = 10
    EPIC_GOOD_LUCK = 11
    ONE_BEER_TWO_BEER_FREE_BEER = 12
    PIECEWORK_PARTY = 13
    LUCKY_DAY = 14
    CRAZY_MUSHROOM_HARVEST = 15
    HOLIDAY_SALE = 16
    RUMBLE_FOR_RICHES = 17
    BLACK_GEM_RUSH = 18
    VALENTINES_BLESSING = 19


@dataclass(slots=True, frozen=True)
class Cost:
    """Gold and mushroom cost for a purchase."""

    silver: int = 0
    mushrooms: int = 0

    def format(self) -> str:
        if self.mushrooms > 0:
            return f"{self.mushrooms} mush"
        return f"{self.silver // 100:,}g {self.silver % 100}s"
