from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from sfbot.constants import Event, Location, Season, TimeOfDay, Weekday


class TimeStatus(Enum):
    ACTIVE = 0
    UPCOMING = 1
    MISSED = 2


@dataclass(slots=True, frozen=True)
class PetRequirement:
    pet_id: int
    location: Location
    days_per_year: int
    time_of_day: TimeOfDay | None = None
    day_of_week: Weekday | None = None
    season: Season | None = None
    event: Event | None = None
    # (month, day) -> every year, (month, day, year) -> exact year only
    special_date: tuple[int, int] | tuple[int, int, int] | None = None
    day_of_month: int | None = None
    month: int | None = None

    def check(self, events: frozenset[Event], server_time: int) -> bool:
        if self.get_time_status(server_time) == TimeStatus.MISSED:
            return False
        dt = datetime.fromtimestamp(server_time, tz=timezone.utc)
        if self.day_of_week is not None and self.day_of_week != Weekday(dt.weekday()):
            return False
        if self.season is not None and self.season != get_season(dt.month, dt.day):
            return False
        if self.event is not None and self.event not in events:
            return False
        if self.special_date is not None:
            if len(self.special_date) == 2:
                if self.special_date != (dt.month, dt.day):
                    return False
            elif self.special_date != (dt.month, dt.day, dt.year):
                return False
        if self.day_of_month is not None and self.day_of_month != dt.day:
            return False
        if self.month is not None and self.month != dt.month:
            return False
        return True

    def get_time_status(self, server_time: int) -> TimeStatus:
        if self.time_of_day is None:
            return TimeStatus.ACTIVE

        hour = datetime.fromtimestamp(server_time, tz=timezone.utc).hour

        if self.time_of_day == TimeOfDay.DAY:
            if 6 <= hour < 18:
                return TimeStatus.ACTIVE
            if hour < 6:
                return TimeStatus.UPCOMING
            return TimeStatus.MISSED
        if self.time_of_day == TimeOfDay.NIGHT:
            if hour < 6 or hour >= 18:
                return TimeStatus.ACTIVE
            return TimeStatus.UPCOMING
        if self.time_of_day == TimeOfDay.MIDNIGHT:
            if hour == 0:
                return TimeStatus.ACTIVE
            return TimeStatus.MISSED
        return TimeStatus.ACTIVE


def get_season(month: int, day: int) -> Season:
    md = month * 100 + day
    if 320 <= md <= 620:
        return Season.SPRING
    if 621 <= md <= 922:
        return Season.SUMMER
    if 923 <= md <= 1220:
        return Season.FALL
    return Season.WINTER


def _matches_time_of_day(time_of_day: TimeOfDay, hour: int) -> bool:
    """Check if the given hour matches the time of day requirement (DAY/NIGHT/MIDNIGHT)."""
    if time_of_day == TimeOfDay.DAY:
        return 6 <= hour < 18
    if time_of_day == TimeOfDay.NIGHT:
        return hour < 6 or hour >= 18
    if time_of_day == TimeOfDay.MIDNIGHT:
        return hour == 0


PET_REQUIREMENTS: list[PetRequirement] = [
    # ── Shadow (pet_id 1–20) ──
    PetRequirement(
        1,
        Location.MOLDY_FOREST,
        365,
        time_of_day=TimeOfDay.DAY,
    ),
    PetRequirement(
        2,
        Location.ROTTEN_LANDS,
        365,
        time_of_day=TimeOfDay.NIGHT,
    ),
    PetRequirement(
        3,
        Location.SPRAWLING_JUNGLE,
        365,
        time_of_day=TimeOfDay.NIGHT,
    ),
    PetRequirement(
        4,
        Location.MOLDY_FOREST,
        365,
        time_of_day=TimeOfDay.NIGHT,
    ),
    PetRequirement(
        5,
        Location.ROTTEN_LANDS,
        52,
        time_of_day=TimeOfDay.NIGHT,
        day_of_week=Weekday.MONDAY,
    ),
    PetRequirement(
        6,
        Location.BLACK_WATER_SWAMP,
        365,
        time_of_day=TimeOfDay.MIDNIGHT,
    ),
    PetRequirement(
        7,
        Location.SPRAWLING_JUNGLE,
        94,
        time_of_day=TimeOfDay.DAY,
        season=Season.SUMMER,
    ),
    PetRequirement(
        8,
        Location.ROTTEN_LANDS,
        89,
        time_of_day=TimeOfDay.DAY,
        season=Season.WINTER,
    ),
    PetRequirement(
        9,
        Location.SHADOWROCK_MOUNTAIN,
        52,
        time_of_day=TimeOfDay.NIGHT,
        day_of_week=Weekday.FRIDAY,
    ),
    PetRequirement(
        10,
        Location.MOLDY_FOREST,
        89,
        time_of_day=TimeOfDay.DAY,
        season=Season.FALL,
    ),
    PetRequirement(
        11,
        Location.BLACK_WATER_SWAMP,
        52,
        time_of_day=TimeOfDay.NIGHT,
        day_of_week=Weekday.MONDAY,
    ),
    PetRequirement(
        12,
        Location.ROTTEN_LANDS,
        52,
        time_of_day=TimeOfDay.NIGHT,
        day_of_week=Weekday.TUESDAY,
    ),
    PetRequirement(
        13,
        Location.SHADOWROCK_MOUNTAIN,
        52,
        time_of_day=TimeOfDay.NIGHT,
        day_of_week=Weekday.WEDNESDAY,
    ),
    PetRequirement(
        14,
        Location.SHADOWROCK_MOUNTAIN,
        52,
        time_of_day=TimeOfDay.DAY,
        day_of_week=Weekday.THURSDAY,
    ),
    PetRequirement(
        15,
        Location.ROTTEN_LANDS,
        1,
        event=Event.CRAZY_MUSHROOM_HARVEST,
        special_date=(10, 31),
    ),
    PetRequirement(
        16,
        Location.BLACK_WATER_SWAMP,
        365,
    ),  # rank ≤ 1000 or honor ≥ 50000
    PetRequirement(
        17,
        Location.SHADOWROCK_MOUNTAIN,
        39,
        event=Event.EXCEPTIONAL_XP,
    ),
    # Pet 18: Friday the 13th ±2 days — Wed 11 through Sun 15
    PetRequirement(
        18,
        Location.ROTTEN_LANDS,
        12,
        day_of_week=Weekday.WEDNESDAY,
        day_of_month=11,
    ),
    PetRequirement(
        18,
        Location.ROTTEN_LANDS,
        12,
        day_of_week=Weekday.THURSDAY,
        day_of_month=12,
    ),
    PetRequirement(
        18,
        Location.ROTTEN_LANDS,
        12,
        day_of_week=Weekday.FRIDAY,
        day_of_month=13,
    ),
    PetRequirement(
        18,
        Location.ROTTEN_LANDS,
        12,
        day_of_week=Weekday.SATURDAY,
        day_of_month=14,
    ),
    PetRequirement(
        18,
        Location.ROTTEN_LANDS,
        12,
        day_of_week=Weekday.SUNDAY,
        day_of_month=15,
    ),
    PetRequirement(
        19,
        Location.BLACK_WATER_SWAMP,
        365,
    ),  # shadow dungeon 12 floor 10
    PetRequirement(
        20,
        Location.SPRAWLING_JUNGLE,
        365,
    ),  # pet dungeon 0 floor 20
    # ── Light (pet_id 21–40) ──
    PetRequirement(
        21,
        Location.PLAINS_OF_OZ_KORR,
        365,
        time_of_day=TimeOfDay.DAY,
    ),
    PetRequirement(
        22,
        Location.BUSTED_LANDS,
        365,
        time_of_day=TimeOfDay.NIGHT,
    ),
    PetRequirement(
        23,
        Location.MAERWYNN,
        365,
        time_of_day=TimeOfDay.DAY,
    ),
    PetRequirement(
        24,
        Location.BUSTED_LANDS,
        365,
        time_of_day=TimeOfDay.DAY,
    ),
    PetRequirement(
        25,
        Location.MAERWYNN,
        93,
        time_of_day=TimeOfDay.NIGHT,
        season=Season.SPRING,
    ),
    PetRequirement(
        26,
        Location.BUSTED_LANDS,
        52,
        time_of_day=TimeOfDay.DAY,
        day_of_week=Weekday.SATURDAY,
    ),
    PetRequirement(
        27,
        Location.SUNBURN_DESERT,
        94,
        time_of_day=TimeOfDay.DAY,
        season=Season.SUMMER,
    ),
    PetRequirement(
        28,
        Location.PLAINS_OF_OZ_KORR,
        89,
        time_of_day=TimeOfDay.DAY,
        season=Season.FALL,
    ),
    PetRequirement(
        29,
        Location.SUNBURN_DESERT,
        52,
        time_of_day=TimeOfDay.NIGHT,
        day_of_week=Weekday.MONDAY,
    ),
    PetRequirement(
        30,
        Location.BUSTED_LANDS,
        52,
        time_of_day=TimeOfDay.DAY,
        day_of_week=Weekday.TUESDAY,
    ),
    PetRequirement(
        31,
        Location.SUNBURN_DESERT,
        52,
        time_of_day=TimeOfDay.DAY,
        day_of_week=Weekday.SUNDAY,
    ),
    PetRequirement(
        32,
        Location.MAERWYNN,
        52,
        time_of_day=TimeOfDay.NIGHT,
        day_of_week=Weekday.WEDNESDAY,
    ),
    PetRequirement(
        33,
        Location.PLAINS_OF_OZ_KORR,
        52,
        time_of_day=TimeOfDay.DAY,
        day_of_week=Weekday.THURSDAY,
    ),
    PetRequirement(
        34,
        Location.BUSTED_LANDS,
        52,
        time_of_day=TimeOfDay.DAY,
        day_of_week=Weekday.FRIDAY,
    ),
    PetRequirement(
        35,
        Location.SUNBURN_DESERT,
        365,
    ),  # guild rank ≤ 100 or guild honor ≥ 2500
    PetRequirement(
        36,
        Location.SHADOWROCK_MOUNTAIN,
        31,
        time_of_day=TimeOfDay.DAY,
        month=12,
    ),
    # Pet 37: April Fools ±3 days — Mar 29 through Apr 4
    PetRequirement(
        37,
        Location.BUSTED_LANDS,
        7,
        special_date=(3, 29),
    ),
    PetRequirement(
        37,
        Location.BUSTED_LANDS,
        7,
        special_date=(3, 30),
    ),
    PetRequirement(
        37,
        Location.BUSTED_LANDS,
        7,
        special_date=(3, 31),
    ),
    PetRequirement(
        37,
        Location.BUSTED_LANDS,
        7,
        special_date=(4, 1),
    ),
    PetRequirement(
        37,
        Location.BUSTED_LANDS,
        7,
        special_date=(4, 2),
    ),
    PetRequirement(
        37,
        Location.BUSTED_LANDS,
        7,
        special_date=(4, 3),
    ),
    PetRequirement(
        37,
        Location.BUSTED_LANDS,
        7,
        special_date=(4, 4),
    ),
    PetRequirement(
        38,
        Location.PLAINS_OF_OZ_KORR,
        39,
        event=Event.EPIC_QUEST_EXTRAVAGANZA,
    ),
    PetRequirement(
        39,
        Location.MAERWYNN,
        365,
    ),  # tower = 100
    PetRequirement(
        40,
        Location.PLAINS_OF_OZ_KORR,
        365,
    ),  # pet dungeon 1 floor 20
    # ── Earth (pet_id 41–60) ──
    PetRequirement(
        41,
        Location.GNAROGRIM,
        365,
        time_of_day=TimeOfDay.DAY,
    ),
    PetRequirement(
        42,
        Location.SPRAWLING_JUNGLE,
        365,
        time_of_day=TimeOfDay.NIGHT,
    ),
    PetRequirement(
        43,
        Location.MAERWYNN,
        365,
        time_of_day=TimeOfDay.DAY,
    ),
    PetRequirement(
        44,
        Location.PLAINS_OF_OZ_KORR,
        365,
        time_of_day=TimeOfDay.DAY,
    ),
    PetRequirement(
        45,
        Location.GNAROGRIM,
        365,
        time_of_day=TimeOfDay.NIGHT,
    ),
    PetRequirement(
        46,
        Location.PLAINS_OF_OZ_KORR,
        94,
        time_of_day=TimeOfDay.DAY,
        season=Season.SUMMER,
    ),
    PetRequirement(
        47,
        Location.SPRAWLING_JUNGLE,
        89,
        time_of_day=TimeOfDay.DAY,
        season=Season.FALL,
    ),
    PetRequirement(
        48,
        Location.GNAROGRIM,
        89,
        time_of_day=TimeOfDay.DAY,
        season=Season.WINTER,
    ),
    PetRequirement(
        49,
        Location.MAERWYNN,
        93,
        time_of_day=TimeOfDay.DAY,
        season=Season.SPRING,
    ),
    PetRequirement(
        50,
        Location.SPRAWLING_JUNGLE,
        52,
        time_of_day=TimeOfDay.NIGHT,
        day_of_week=Weekday.SUNDAY,
    ),
    PetRequirement(
        51,
        Location.MAERWYNN,
        52,
        time_of_day=TimeOfDay.DAY,
        day_of_week=Weekday.MONDAY,
    ),
    PetRequirement(
        52,
        Location.GNAROGRIM,
        52,
        time_of_day=TimeOfDay.NIGHT,
        day_of_week=Weekday.TUESDAY,
    ),
    PetRequirement(
        53,
        Location.MAERWYNN,
        52,
        time_of_day=TimeOfDay.DAY,
        day_of_week=Weekday.WEDNESDAY,
    ),
    PetRequirement(
        54,
        Location.PLAINS_OF_OZ_KORR,
        52,
        time_of_day=TimeOfDay.DAY,
        day_of_week=Weekday.THURSDAY,
    ),
    PetRequirement(
        55,
        Location.MAERWYNN,
        1,
        event=Event.ASSEMBLY_OF_AWESOME_ANIMALS,
    ),
    # Pet 56: Pentecost / Whitsun — 1 day/year (year-specific)
    PetRequirement(
        56,
        Location.SPRAWLING_JUNGLE,
        1,
        special_date=(5, 24, 2026),
    ),
    PetRequirement(
        56,
        Location.SPRAWLING_JUNGLE,
        1,
        special_date=(5, 16, 2027),
    ),
    PetRequirement(
        56,
        Location.SPRAWLING_JUNGLE,
        1,
        special_date=(6, 4, 2028),
    ),
    PetRequirement(
        56,
        Location.SPRAWLING_JUNGLE,
        1,
        special_date=(5, 20, 2029),
    ),
    PetRequirement(
        56,
        Location.SPRAWLING_JUNGLE,
        1,
        special_date=(6, 9, 2030),
    ),
    PetRequirement(
        57,
        Location.PLAINS_OF_OZ_KORR,
        39,
        event=Event.GLORIOUS_GOLD_GALORE,
    ),
    PetRequirement(
        58,
        Location.GNAROGRIM,
        365,
    ),  # fortress rank ≤ 100 or fort honor ≥ 2500
    # Pet 59: GEM_MINE — skipped (non-expedition location)
    PetRequirement(
        60,
        Location.SPRAWLING_JUNGLE,
        365,
    ),  # pet dungeon 2 floor 20
    # ── Fire (pet_id 61–80) ──
    PetRequirement(
        61,
        Location.MOLDY_FOREST,
        365,
        time_of_day=TimeOfDay.DAY,
    ),
    PetRequirement(
        62,
        Location.MAGMARON,
        365,
        time_of_day=TimeOfDay.NIGHT,
    ),
    PetRequirement(
        63,
        Location.BLACK_WATER_SWAMP,
        365,
        time_of_day=TimeOfDay.NIGHT,
    ),
    PetRequirement(
        64,
        Location.SUNBURN_DESERT,
        365,
        time_of_day=TimeOfDay.DAY,
    ),
    PetRequirement(
        65,
        Location.MAGMARON,
        52,
        time_of_day=TimeOfDay.NIGHT,
        day_of_week=Weekday.TUESDAY,
    ),
    PetRequirement(
        66,
        Location.MOLDY_FOREST,
        89,
        time_of_day=TimeOfDay.NIGHT,
        season=Season.FALL,
    ),
    PetRequirement(
        67,
        Location.MAGMARON,
        52,
        time_of_day=TimeOfDay.DAY,
        day_of_week=Weekday.MONDAY,
    ),
    PetRequirement(
        68,
        Location.SUNBURN_DESERT,
        93,
        time_of_day=TimeOfDay.DAY,
        season=Season.SPRING,
    ),
    PetRequirement(
        69,
        Location.MAGMARON,
        89,
        time_of_day=TimeOfDay.DAY,
        season=Season.WINTER,
    ),
    PetRequirement(
        70,
        Location.SPRAWLING_JUNGLE,
        52,
        time_of_day=TimeOfDay.NIGHT,
        day_of_week=Weekday.WEDNESDAY,
    ),
    PetRequirement(
        71,
        Location.SUNBURN_DESERT,
        52,
        time_of_day=TimeOfDay.DAY,
        day_of_week=Weekday.THURSDAY,
    ),
    PetRequirement(
        72,
        Location.SUNBURN_DESERT,
        94,
        time_of_day=TimeOfDay.DAY,
        season=Season.SUMMER,
    ),
    PetRequirement(
        73,
        Location.MAGMARON,
        52,
        time_of_day=TimeOfDay.DAY,
        day_of_week=Weekday.FRIDAY,
    ),
    PetRequirement(
        74,
        Location.SPRAWLING_JUNGLE,
        52,
        time_of_day=TimeOfDay.NIGHT,
        day_of_week=Weekday.SATURDAY,
    ),
    # Pet 75: WEAPON_SHOP — skipped (non-expedition location)
    PetRequirement(
        76,
        Location.SUNBURN_DESERT,
        39,
        event=Event.TIDY_TOILET_TIME,
    ),
    # Pet 77: Valentine's Day ±3 days — Feb 11 through Feb 17
    PetRequirement(
        77,
        Location.MAGMARON,
        7,
        special_date=(2, 11),
    ),
    PetRequirement(
        77,
        Location.MAGMARON,
        7,
        special_date=(2, 12),
    ),
    PetRequirement(
        77,
        Location.MAGMARON,
        7,
        special_date=(2, 13),
    ),
    PetRequirement(
        77,
        Location.MAGMARON,
        7,
        special_date=(2, 14),
    ),
    PetRequirement(
        77,
        Location.MAGMARON,
        7,
        special_date=(2, 15),
    ),
    PetRequirement(
        77,
        Location.MAGMARON,
        7,
        special_date=(2, 16),
    ),
    PetRequirement(
        77,
        Location.MAGMARON,
        7,
        special_date=(2, 17),
    ),
    # Pet 78: New Year's ±3 days — Dec 28 through Jan 4
    PetRequirement(
        78,
        Location.PLAINS_OF_OZ_KORR,
        8,
        special_date=(12, 28),
    ),
    PetRequirement(
        78,
        Location.PLAINS_OF_OZ_KORR,
        8,
        special_date=(12, 29),
    ),
    PetRequirement(
        78,
        Location.PLAINS_OF_OZ_KORR,
        8,
        special_date=(12, 30),
    ),
    PetRequirement(
        78,
        Location.PLAINS_OF_OZ_KORR,
        8,
        special_date=(12, 31),
    ),
    PetRequirement(
        78,
        Location.PLAINS_OF_OZ_KORR,
        8,
        special_date=(1, 1),
    ),
    PetRequirement(
        78,
        Location.PLAINS_OF_OZ_KORR,
        8,
        special_date=(1, 2),
    ),
    PetRequirement(
        78,
        Location.PLAINS_OF_OZ_KORR,
        8,
        special_date=(1, 3),
    ),
    PetRequirement(
        78,
        Location.PLAINS_OF_OZ_KORR,
        8,
        special_date=(1, 4),
    ),
    PetRequirement(
        79,
        Location.MAGMARON,
        365,
    ),  # portal = 50
    PetRequirement(
        80,
        Location.GNAROGRIM,
        365,
    ),  # pet dungeon 3 floor 20
    # ── Water (pet_id 81–100) ──
    PetRequirement(
        81,
        Location.SKULL_ISLAND,
        365,
        time_of_day=TimeOfDay.DAY,
    ),
    PetRequirement(
        82,
        Location.SKULL_ISLAND,
        365,
        time_of_day=TimeOfDay.DAY,
    ),
    PetRequirement(
        83,
        Location.BLACK_WATER_SWAMP,
        365,
        time_of_day=TimeOfDay.NIGHT,
    ),
    PetRequirement(
        84,
        Location.SHADOWROCK_MOUNTAIN,
        365,
        time_of_day=TimeOfDay.DAY,
    ),
    PetRequirement(
        85,
        Location.SHADOWROCK_MOUNTAIN,
        52,
        time_of_day=TimeOfDay.DAY,
        day_of_week=Weekday.MONDAY,
    ),
    PetRequirement(
        86,
        Location.MOLDY_FOREST,
        52,
        time_of_day=TimeOfDay.NIGHT,
        day_of_week=Weekday.TUESDAY,
    ),
    PetRequirement(
        87,
        Location.MOLDY_FOREST,
        52,
        time_of_day=TimeOfDay.DAY,
        day_of_week=Weekday.WEDNESDAY,
    ),
    PetRequirement(
        88,
        Location.SHADOWROCK_MOUNTAIN,
        89,
        time_of_day=TimeOfDay.DAY,
        season=Season.WINTER,
    ),
    PetRequirement(
        89,
        Location.MOLDY_FOREST,
        52,
        time_of_day=TimeOfDay.NIGHT,
        day_of_week=Weekday.THURSDAY,
    ),
    PetRequirement(
        90,
        Location.SKULL_ISLAND,
        52,
        time_of_day=TimeOfDay.DAY,
        day_of_week=Weekday.FRIDAY,
    ),
    PetRequirement(
        91,
        Location.SKULL_ISLAND,
        52,
        time_of_day=TimeOfDay.DAY,
        day_of_week=Weekday.SATURDAY,
    ),
    PetRequirement(
        92,
        Location.SKULL_ISLAND,
        89,
        time_of_day=TimeOfDay.NIGHT,
        season=Season.FALL,
    ),
    PetRequirement(
        93,
        Location.BLACK_WATER_SWAMP,
        94,
        time_of_day=TimeOfDay.DAY,
        season=Season.SUMMER,
    ),
    PetRequirement(
        94,
        Location.SHADOWROCK_MOUNTAIN,
        52,
        time_of_day=TimeOfDay.NIGHT,
        day_of_week=Weekday.SUNDAY,
    ),
    PetRequirement(
        95,
        Location.SKULL_ISLAND,
        365,
    ),  # pet rank ≤ 100 or pet honor ≥ 4000
    # Pet 96: MAGIC_SHOP — skipped (non-expedition location)
    # Pet 97: S&F anniversary — June 22 only
    PetRequirement(
        97,
        Location.SKULL_ISLAND,
        1,
        special_date=(6, 22),
    ),
    # Pet 98: TOILET — skipped (non-expedition location)
    PetRequirement(
        99,
        Location.MOLDY_FOREST,
        365,
    ),  # light dungeon 24 floor 10
    PetRequirement(
        100,
        Location.BLACK_WATER_SWAMP,
        365,
    ),  # pet dungeon 4 floor 20
]
