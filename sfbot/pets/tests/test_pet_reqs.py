from collections import Counter

import pytest

from sfbot.constants import Event, Location, Season, TimeOfDay, Weekday
from sfbot.pets.pet_reqs import (
    PET_REQUIREMENTS,
    PetRequirement,
    _matches_time_of_day,
    get_season,
)
from sfbot.pets.tests.conftest import make_params

# ── Helper to find trigger(s) by pet_id ──


def get_requirements(pet_id: int) -> list[PetRequirement]:
    return [r for r in PET_REQUIREMENTS if r.pet_id == pet_id]


def get_requirement(pet_id: int) -> PetRequirement:
    triggers = get_requirements(pet_id)
    assert len(triggers) == 1, (
        f"Expected 1 trigger for pet {pet_id}, got {len(triggers)}"
    )
    return triggers[0]


class TestGetSeason:
    def test_winter_early_jan(self):
        assert get_season(1, 1) == Season.WINTER

    def test_winter_march_19(self):
        assert get_season(3, 19) == Season.WINTER

    def test_spring_march_20(self):
        assert get_season(3, 20) == Season.SPRING

    def test_spring_june_20(self):
        assert get_season(6, 20) == Season.SPRING

    def test_summer_june_21(self):
        assert get_season(6, 21) == Season.SUMMER

    def test_summer_sept_22(self):
        assert get_season(9, 22) == Season.SUMMER

    def test_fall_sept_23(self):
        assert get_season(9, 23) == Season.FALL

    def test_fall_dec_20(self):
        assert get_season(12, 20) == Season.FALL

    def test_winter_dec_21(self):
        assert get_season(12, 21) == Season.WINTER

    def test_winter_dec_31(self):
        assert get_season(12, 31) == Season.WINTER


# ═══════════════════════════════════════════════════════════════
# _matches_time_of_day tests
# ═══════════════════════════════════════════════════════════════


class TestMatchesTimeOfDay:
    @pytest.mark.parametrize("hour", [6, 12, 17])
    def test_day_matches(self, hour: int):
        assert _matches_time_of_day(TimeOfDay.DAY, hour) is True

    @pytest.mark.parametrize("hour", [0, 5, 18, 23])
    def test_day_rejects(self, hour: int):
        assert _matches_time_of_day(TimeOfDay.DAY, hour) is False

    @pytest.mark.parametrize("hour", [0, 3, 5, 18, 22, 23])
    def test_night_matches(self, hour: int):
        assert _matches_time_of_day(TimeOfDay.NIGHT, hour) is True

    @pytest.mark.parametrize("hour", [6, 12, 17])
    def test_night_rejects(self, hour: int):
        assert _matches_time_of_day(TimeOfDay.NIGHT, hour) is False

    @pytest.mark.parametrize("hour", [0])
    def test_midnight_matches(self, hour: int):
        assert _matches_time_of_day(TimeOfDay.MIDNIGHT, hour) is True

    @pytest.mark.parametrize("hour", [1, 2, 6, 12, 23])
    def test_midnight_rejects(self, hour: int):
        assert _matches_time_of_day(TimeOfDay.MIDNIGHT, hour) is False


class TestSpecialDateYearHandling:
    def test_special_date_without_year_matches_every_year(self):
        req = PetRequirement(
            999,
            Location.NEVERMOOR,
            1,
            special_date=(5, 24),
        )

        assert req.check(**make_params(month=5, day=24, year=2026))
        assert req.check(**make_params(month=5, day=24, year=2027))
        assert not req.check(**make_params(month=5, day=25, year=2026))

    def test_special_date_with_year_matches_only_specific_year(self):
        req = PetRequirement(
            999,
            Location.NEVERMOOR,
            1,
            special_date=(5, 24, 2026),
        )

        assert req.check(**make_params(month=5, day=24, year=2026))
        assert not req.check(**make_params(month=5, day=24, year=2027))
        assert not req.check(**make_params(month=5, day=24))


# ═══════════════════════════════════════════════════════════════
# Shadow habitat (pet_id 1–20)
# ═══════════════════════════════════════════════════════════════


class TestShadow:
    def test_pet_1_slurp_nevermoor_day(self):
        req = get_requirement(1)
        assert req.location == Location.MOLDY_FOREST
        assert req.check(**make_params())
        assert not req.check(**make_params(hour=22))

    def test_pet_2_digmol_maerwynn_night(self):
        req = get_requirement(2)
        assert req.location == Location.ROTTEN_LANDS
        assert req.check(**make_params())

    def test_pet_3_toothey_sprawling_jungle_night(self):
        req = get_requirement(3)
        assert req.location == Location.SPRAWLING_JUNGLE
        assert req.check(**make_params())

    def test_pet_4_okultacle_split_canyon_night(self):
        req = get_requirement(4)
        assert req.location == Location.MOLDY_FOREST
        assert req.check(**make_params())

    def test_pet_5_spidor_black_forest_monday_night(self):
        req = get_requirement(5)
        assert req.location == Location.ROTTEN_LANDS
        # Monday night
        assert req.check(**make_params(weekday=Weekday.MONDAY))
        assert not req.check(**make_params(weekday=Weekday.TUESDAY))

    def test_pet_6_jackobu_black_water_swamp_midnight(self):
        req = get_requirement(6)
        assert req.location == Location.BLACK_WATER_SWAMP
        assert req.check(**make_params(hour=0))
        assert not req.check(**make_params(hour=1))

    def test_pet_7_shrimpfly_evernight_forest_summer_day(self):
        req = get_requirement(7)
        assert req.location == Location.SPRAWLING_JUNGLE
        assert req.check(**make_params(month=7, day=15))
        assert not req.check(**make_params(month=7, day=15, hour=22))
        assert not req.check(**make_params(month=1, day=15))

    def test_pet_8_reaprim_skull_island_winter_day(self):
        req = get_requirement(8)
        assert req.location == Location.ROTTEN_LANDS
        assert req.check(**make_params(month=1, day=10))
        assert not req.check(**make_params(month=1, day=10, hour=22))
        assert not req.check(**make_params(month=7, day=10))

    def test_pet_9_petdacat_shadowrock_mountain_friday_night(self):
        req = get_requirement(9)
        assert req.location == Location.SHADOWROCK_MOUNTAIN
        assert req.check(**make_params(weekday=Weekday.FRIDAY))
        assert not req.check(**make_params(weekday=Weekday.MONDAY))

    def test_pet_10_mykon_moldy_forest_fall_day(self):
        req = get_requirement(10)
        assert req.location == Location.MOLDY_FOREST
        assert req.check(**make_params(month=10, day=1))
        assert not req.check(**make_params(month=10, day=1, hour=22))
        assert not req.check(**make_params(month=4, day=1))

    def test_pet_11_fishorr_flooded_caldwell_monday_night(self):
        req = get_requirement(11)
        assert req.location == Location.BLACK_WATER_SWAMP
        assert req.check(**make_params(weekday=Weekday.MONDAY))
        assert not req.check(**make_params(weekday=Weekday.SUNDAY))

    def test_pet_12_cuckooly_tusk_mountain_tuesday_night(self):
        req = get_requirement(12)
        assert req.location == Location.ROTTEN_LANDS
        assert req.check(**make_params(weekday=Weekday.TUESDAY))
        assert not req.check(**make_params(weekday=Weekday.WEDNESDAY))

    def test_pet_13_battlutter_erogenion_wednesday_night(self):
        req = get_requirement(13)
        assert req.location == Location.SHADOWROCK_MOUNTAIN
        assert req.check(**make_params(weekday=Weekday.WEDNESDAY))
        assert not req.check(**make_params(weekday=Weekday.THURSDAY))

    def test_pet_14_pinklynx_stumble_steppe_thursday_day(self):
        req = get_requirement(14)
        assert req.location == Location.SHADOWROCK_MOUNTAIN
        assert req.check(**make_params(weekday=Weekday.THURSDAY))
        assert not req.check(**make_params(weekday=Weekday.THURSDAY, hour=22))
        assert not req.check(**make_params(weekday=Weekday.FRIDAY))

    def test_pet_15_pharamumm_halloween_crazy_mushroom(self):
        req = get_requirement(15)
        assert req.location == Location.ROTTEN_LANDS
        events_active = frozenset({Event.CRAZY_MUSHROOM_HARVEST})
        # Halloween with event
        assert req.check(**make_params(month=10, day=31, events=events_active))
        # Halloween without event
        assert not req.check(**make_params(month=10, day=31))
        # Event active but wrong date
        assert not req.check(**make_params(month=10, day=30, events=events_active))

    def test_pet_17_luchtablong_busted_lands_exceptional_xp(self):
        req = get_requirement(17)
        assert req.location == Location.SHADOWROCK_MOUNTAIN
        events_active = frozenset({Event.EXCEPTIONAL_XP})
        assert req.check(**make_params(events=events_active))
        assert not req.check(**make_params())

    def test_pet_16_always_available(self):
        req = get_requirement(16)
        assert req.location == Location.BLACK_WATER_SWAMP
        assert req.check(**make_params())
        assert req.check(**make_params(weekday=Weekday.FRIDAY, month=1, day=1))

    def test_pet_18_angrack_rotten_lands_friday_13th(self):
        triggers = get_requirements(18)
        assert len(triggers) == 5
        for t in triggers:
            assert t.location == Location.ROTTEN_LANDS
        # Day 11 Wed, 12 Thu, 13 Fri, 14 Sat, 15 Sun all match
        assert any(
            t.check(**make_params(weekday=Weekday.WEDNESDAY, day=11)) for t in triggers
        )
        assert any(
            t.check(**make_params(weekday=Weekday.THURSDAY, day=12)) for t in triggers
        )
        assert any(
            t.check(**make_params(weekday=Weekday.FRIDAY, day=13)) for t in triggers
        )
        assert any(
            t.check(**make_params(weekday=Weekday.SATURDAY, day=14)) for t in triggers
        )
        assert any(
            t.check(**make_params(weekday=Weekday.SUNDAY, day=15)) for t in triggers
        )
        # Wrong weekday for day 13
        assert not any(
            t.check(**make_params(weekday=Weekday.THURSDAY, day=13)) for t in triggers
        )
        # Wrong day for Friday
        assert not any(
            t.check(**make_params(weekday=Weekday.FRIDAY, day=12)) for t in triggers
        )

    def test_pet_19_always_available(self):
        req = get_requirement(19)
        assert req.location == Location.BLACK_WATER_SWAMP
        assert req.check(**make_params())

    def test_pet_20_always_available(self):
        req = get_requirement(20)
        assert req.location == Location.SPRAWLING_JUNGLE
        assert req.check(**make_params())


# ═══════════════════════════════════════════════════════════════
# Light habitat (pet_id 21–40)
# ═══════════════════════════════════════════════════════════════


class TestLight:
    def test_pet_21_shaggyll_stumble_steppe_day(self):
        req = get_requirement(21)
        assert req.location == Location.PLAINS_OF_OZ_KORR
        assert req.check(**make_params())
        assert not req.check(**make_params(hour=22))

    def test_pet_22_jellclops_moldy_forest_night(self):
        req = get_requirement(22)
        assert req.location == Location.BUSTED_LANDS
        assert req.check(**make_params())

    def test_pet_23_tinck_erogenion_day(self):
        req = get_requirement(23)
        assert req.location == Location.MAERWYNN
        assert req.check(**make_params())
        assert not req.check(**make_params(hour=22))

    def test_pet_24_cloudning_shadowrock_mountain_day(self):
        req = get_requirement(24)
        assert req.location == Location.BUSTED_LANDS
        assert req.check(**make_params())
        assert not req.check(**make_params(hour=22))

    def test_pet_25_nevorfull_sprawling_jungle_spring_night(self):
        req = get_requirement(25)
        assert req.location == Location.MAERWYNN
        assert req.check(**make_params(month=4, day=15))
        assert not req.check(**make_params(month=7, day=15))

    def test_pet_26_plutoid_nevermoor_saturday_day(self):
        req = get_requirement(26)
        assert req.location == Location.BUSTED_LANDS
        assert req.check(**make_params(weekday=Weekday.SATURDAY))
        assert not req.check(**make_params(weekday=Weekday.SATURDAY, hour=22))
        assert not req.check(**make_params(weekday=Weekday.SUNDAY))

    def test_pet_27_djinntonic_sunburn_desert_summer_day(self):
        req = get_requirement(27)
        assert req.location == Location.SUNBURN_DESERT
        assert req.check(**make_params(month=7, day=10))
        assert not req.check(**make_params(month=7, day=10, hour=22))
        assert not req.check(**make_params(month=1, day=10))

    def test_pet_28_blaxta_flooded_caldwell_fall_day(self):
        req = get_requirement(28)
        assert req.location == Location.PLAINS_OF_OZ_KORR
        assert req.check(**make_params(month=10, day=5))
        assert not req.check(**make_params(month=10, day=5, hour=22))
        assert not req.check(**make_params(month=4, day=5))

    def test_pet_29_lampcess_skull_island_monday_night(self):
        req = get_requirement(29)
        assert req.location == Location.SUNBURN_DESERT
        assert req.check(**make_params(weekday=Weekday.MONDAY))
        assert not req.check(**make_params(weekday=Weekday.TUESDAY))

    def test_pet_30_teslarr_busted_lands_tuesday_day(self):
        req = get_requirement(30)
        assert req.location == Location.BUSTED_LANDS
        assert req.check(**make_params(weekday=Weekday.TUESDAY))
        assert not req.check(**make_params(weekday=Weekday.TUESDAY, hour=22))
        assert not req.check(**make_params(weekday=Weekday.WEDNESDAY))

    def test_pet_31_sunnya_tusk_mountain_sunday_day(self):
        req = get_requirement(31)
        assert req.location == Location.SUNBURN_DESERT
        assert req.check(**make_params(weekday=Weekday.SUNDAY))
        assert not req.check(**make_params(weekday=Weekday.SUNDAY, hour=22))
        assert not req.check(**make_params(weekday=Weekday.MONDAY))

    def test_pet_32_buckfoxion_northrunt_wednesday_night(self):
        req = get_requirement(32)
        assert req.location == Location.MAERWYNN
        assert req.check(**make_params(weekday=Weekday.WEDNESDAY))
        assert not req.check(**make_params(weekday=Weekday.THURSDAY))

    def test_pet_33_birdychirp_evernight_forest_thursday_day(self):
        req = get_requirement(33)
        assert req.location == Location.PLAINS_OF_OZ_KORR
        assert req.check(**make_params(weekday=Weekday.THURSDAY))
        assert not req.check(**make_params(weekday=Weekday.THURSDAY, hour=22))
        assert not req.check(**make_params(weekday=Weekday.FRIDAY))

    def test_pet_34_eyeorwhat_black_water_swamp_friday_day(self):
        req = get_requirement(34)
        assert req.location == Location.BUSTED_LANDS
        assert req.check(**make_params(weekday=Weekday.FRIDAY))
        assert not req.check(**make_params(weekday=Weekday.FRIDAY, hour=22))
        assert not req.check(**make_params(weekday=Weekday.SATURDAY))

    def test_pet_36_antlar_shadowrock_mountain_december_day(self):
        req = get_requirement(36)
        assert req.location == Location.SHADOWROCK_MOUNTAIN
        # December
        assert req.check(**make_params(month=12, day=1))
        assert req.check(**make_params(month=12, day=25))
        # Not December
        assert not req.check(**make_params(month=11, day=30))
        assert not req.check(**make_params(month=1, day=1))

    def test_pet_37_liphant_busted_lands_april_fools(self):
        triggers = get_requirements(37)
        assert len(triggers) == 7
        for req in triggers:
            assert req.location == Location.BUSTED_LANDS

        # ±3 days around April 1: Mar 29 – Apr 4
        for month, day in [(3, 29), (3, 30), (3, 31), (4, 1), (4, 2), (4, 3), (4, 4)]:
            assert any(
                req.check(**make_params(month=month, day=day)) for req in triggers
            )

        for month, day in [(3, 28), (4, 5)]:
            assert not any(
                req.check(**make_params(month=month, day=day)) for req in triggers
            )

    def test_pet_35_always_available(self):
        req = get_requirement(35)
        assert req.location == Location.SUNBURN_DESERT
        assert req.check(**make_params())

    def test_pet_38_knilight_erogenion_epic_quest_extravaganza(self):
        req = get_requirement(38)
        assert req.location == Location.PLAINS_OF_OZ_KORR
        events_active = frozenset({Event.EPIC_QUEST_EXTRAVAGANZA})
        assert req.check(**make_params(events=events_active))
        assert not req.check(**make_params())

    def test_pet_39_always_available(self):
        req = get_requirement(39)
        assert req.location == Location.MAERWYNN
        assert req.check(**make_params())

    def test_pet_40_always_available(self):
        req = get_requirement(40)
        assert req.location == Location.PLAINS_OF_OZ_KORR
        assert req.check(**make_params())


# ═══════════════════════════════════════════════════════════════
# Earth habitat (pet_id 41–60)
# ═══════════════════════════════════════════════════════════════


class TestEarth:
    def test_pet_41_mamoton_stumble_steppe_day(self):
        req = get_requirement(41)
        assert req.location == Location.GNAROGRIM
        assert req.check(**make_params())
        assert not req.check(**make_params(hour=22))

    def test_pet_42_monkorrage_gnarogrim_night(self):
        req = get_requirement(42)
        assert req.location == Location.SPRAWLING_JUNGLE
        assert req.check(**make_params())

    def test_pet_43_smaponyck_erogenion_day(self):
        req = get_requirement(43)
        assert req.location == Location.MAERWYNN
        assert req.check(**make_params())
        assert not req.check(**make_params(hour=22))

    def test_pet_44_bittnutz_black_forest_day(self):
        req = get_requirement(44)
        assert req.location == Location.PLAINS_OF_OZ_KORR
        assert req.check(**make_params())
        assert not req.check(**make_params(hour=22))

    def test_pet_45_roarear_northrunt_night(self):
        req = get_requirement(45)
        assert req.location == Location.GNAROGRIM
        assert req.check(**make_params())

    def test_pet_46_muscudon_tusk_mountain_summer_day(self):
        req = get_requirement(46)
        assert req.location == Location.PLAINS_OF_OZ_KORR
        assert req.check(**make_params(month=7, day=10))
        assert not req.check(**make_params(month=7, day=10, hour=22))
        assert not req.check(**make_params(month=1, day=10))

    def test_pet_47_apstick_black_water_swamp_fall_day(self):
        req = get_requirement(47)
        assert req.location == Location.SPRAWLING_JUNGLE
        assert req.check(**make_params(month=10, day=5))
        assert not req.check(**make_params(month=10, day=5, hour=22))
        assert not req.check(**make_params(month=4, day=5))

    def test_pet_48_horrnington_split_canyon_winter_day(self):
        req = get_requirement(48)
        assert req.location == Location.GNAROGRIM
        assert req.check(**make_params(month=1, day=10))
        assert not req.check(**make_params(month=1, day=10, hour=22))
        assert not req.check(**make_params(month=7, day=10))

    def test_pet_49_boaringg_magmaron_spring_day(self):
        req = get_requirement(49)
        assert req.location == Location.MAERWYNN
        assert req.check(**make_params(month=4, day=15))
        assert not req.check(**make_params(month=4, day=15, hour=22))
        assert not req.check(**make_params(month=7, day=15))

    def test_pet_50_mameloth_nevermoor_sunday_night(self):
        req = get_requirement(50)
        assert req.location == Location.SPRAWLING_JUNGLE
        assert req.check(**make_params(weekday=Weekday.SUNDAY))
        assert not req.check(**make_params(weekday=Weekday.MONDAY))

    def test_pet_51_rheynooh_maerwynn_monday_day(self):
        req = get_requirement(51)
        assert req.location == Location.MAERWYNN
        assert req.check(**make_params(weekday=Weekday.MONDAY))
        assert not req.check(**make_params(weekday=Weekday.MONDAY, hour=22))
        assert not req.check(**make_params(weekday=Weekday.TUESDAY))

    def test_pet_52_rockastonn_busted_lands_tuesday_night(self):
        req = get_requirement(52)
        assert req.location == Location.GNAROGRIM
        assert req.check(**make_params(weekday=Weekday.TUESDAY))
        assert not req.check(**make_params(weekday=Weekday.WEDNESDAY))

    def test_pet_53_redwoofox_evernight_forest_wednesday_day(self):
        req = get_requirement(53)
        assert req.location == Location.MAERWYNN
        assert req.check(**make_params(weekday=Weekday.WEDNESDAY))
        assert not req.check(**make_params(weekday=Weekday.WEDNESDAY, hour=22))
        assert not req.check(**make_params(weekday=Weekday.THURSDAY))

    def test_pet_54_lilbeatzup_rotten_lands_thursday_day(self):
        req = get_requirement(54)
        assert req.location == Location.PLAINS_OF_OZ_KORR
        assert req.check(**make_params(weekday=Weekday.THURSDAY))
        assert not req.check(**make_params(weekday=Weekday.THURSDAY, hour=22))
        assert not req.check(**make_params(weekday=Weekday.FRIDAY))

    def test_pet_55_forror_maerwynn_easter_event(self):
        req = get_requirement(55)
        assert req.location == Location.MAERWYNN
        events_active = frozenset({Event.ASSEMBLY_OF_AWESOME_ANIMALS})
        assert req.check(**make_params(events=events_active))
        assert not req.check(**make_params())

    def test_pet_56_nipprabs_sprawling_jungle_pentecost_dates(self):
        triggers = get_requirements(56)
        assert len(triggers) == 5
        for req in triggers:
            assert req.location == Location.SPRAWLING_JUNGLE

        # Must match the explicit year-specific Pentecost dates.
        assert any(
            req.check(**make_params(month=5, day=24, year=2026)) for req in triggers
        )
        assert any(
            req.check(**make_params(month=5, day=16, year=2027)) for req in triggers
        )
        assert any(
            req.check(**make_params(month=6, day=4, year=2028)) for req in triggers
        )
        assert any(
            req.check(**make_params(month=5, day=20, year=2029)) for req in triggers
        )
        assert any(
            req.check(**make_params(month=6, day=9, year=2030)) for req in triggers
        )

        # Wrong date/year combos must not match.
        assert not any(
            req.check(**make_params(month=5, day=24, year=2027)) for req in triggers
        )
        assert not any(
            req.check(**make_params(month=5, day=16, year=2026)) for req in triggers
        )
        assert not any(req.check(**make_params(month=5, day=24)) for req in triggers)

    def test_pet_57_armoruck_plains_oz_korr_glorious_gold(self):
        req = get_requirement(57)
        assert req.location == Location.PLAINS_OF_OZ_KORR
        events_active = frozenset({Event.GLORIOUS_GOLD_GALORE})
        assert req.check(**make_params(events=events_active))
        assert not req.check(**make_params())

    def test_pet_58_always_available(self):
        req = get_requirement(58)
        assert req.location == Location.GNAROGRIM
        assert req.check(**make_params())

    def test_pet_60_always_available(self):
        req = get_requirement(60)
        assert req.location == Location.SPRAWLING_JUNGLE
        assert req.check(**make_params())


# ═══════════════════════════════════════════════════════════════
# Fire habitat (pet_id 61–80)
# ═══════════════════════════════════════════════════════════════


class TestFire:
    def test_pet_61_firimp_nevermoor_day(self):
        req = get_requirement(61)
        assert req.location == Location.MOLDY_FOREST
        assert req.check(**make_params())
        assert not req.check(**make_params(hour=22))

    def test_pet_62_gullps_flooded_caldwell_night(self):
        req = get_requirement(62)
        assert req.location == Location.MAGMARON
        assert req.check(**make_params())

    def test_pet_63_pyrophibus_black_water_swamp_night(self):
        req = get_requirement(63)
        assert req.location == Location.BLACK_WATER_SWAMP
        assert req.check(**make_params())

    def test_pet_64_flamechirr_tusk_mountain_day(self):
        req = get_requirement(64)
        assert req.location == Location.SUNBURN_DESERT
        assert req.check(**make_params())
        assert not req.check(**make_params(hour=22))

    def test_pet_65_tectospit_busted_lands_tuesday_night(self):
        req = get_requirement(65)
        assert req.location == Location.MAGMARON
        assert req.check(**make_params(weekday=Weekday.TUESDAY))
        assert not req.check(**make_params(weekday=Weekday.WEDNESDAY))

    def test_pet_66_pyroplant_moldy_forest_fall_night(self):
        req = get_requirement(66)
        assert req.location == Location.MOLDY_FOREST
        assert req.check(**make_params(month=10, day=5))
        assert not req.check(**make_params(month=4, day=5))

    def test_pet_67_kokofire_split_canyon_monday_day(self):
        req = get_requirement(67)
        assert req.location == Location.MAGMARON
        assert req.check(**make_params(weekday=Weekday.MONDAY))
        assert not req.check(**make_params(weekday=Weekday.MONDAY, hour=22))
        assert not req.check(**make_params(weekday=Weekday.TUESDAY))

    def test_pet_68_peppryon_sunburn_desert_spring_day(self):
        req = get_requirement(68)
        assert req.location == Location.SUNBURN_DESERT
        assert req.check(**make_params(month=4, day=10))
        assert not req.check(**make_params(month=4, day=10, hour=22))
        assert not req.check(**make_params(month=7, day=10))

    def test_pet_69_boomywoomy_plains_oz_korr_winter_day(self):
        req = get_requirement(69)
        assert req.location == Location.MAGMARON
        assert req.check(**make_params(month=1, day=10))
        assert not req.check(**make_params(month=1, day=10, hour=22))
        assert not req.check(**make_params(month=7, day=10))

    def test_pet_70_tikiricky_sprawling_jungle_wednesday_night(self):
        req = get_requirement(70)
        assert req.location == Location.SPRAWLING_JUNGLE
        assert req.check(**make_params(weekday=Weekday.WEDNESDAY))
        assert not req.check(**make_params(weekday=Weekday.THURSDAY))

    def test_pet_71_matchlit_stumble_steppe_thursday_day(self):
        req = get_requirement(71)
        assert req.location == Location.SUNBURN_DESERT
        assert req.check(**make_params(weekday=Weekday.THURSDAY))
        assert not req.check(**make_params(weekday=Weekday.THURSDAY, hour=22))
        assert not req.check(**make_params(weekday=Weekday.FRIDAY))

    def test_pet_72_birblazey_black_forest_summer_day(self):
        req = get_requirement(72)
        assert req.location == Location.SUNBURN_DESERT
        assert req.check(**make_params(month=7, day=10))
        assert not req.check(**make_params(month=7, day=10, hour=22))
        assert not req.check(**make_params(month=1, day=10))

    def test_pet_73_infernox_magmaron_friday_day(self):
        req = get_requirement(73)
        assert req.location == Location.MAGMARON
        assert req.check(**make_params(weekday=Weekday.FRIDAY))
        assert not req.check(**make_params(weekday=Weekday.FRIDAY, hour=22))
        assert not req.check(**make_params(weekday=Weekday.SATURDAY))

    def test_pet_74_humbuzzish_evernight_forest_saturday_night(self):
        req = get_requirement(74)
        assert req.location == Location.SPRAWLING_JUNGLE
        assert req.check(**make_params(weekday=Weekday.SATURDAY))
        assert not req.check(**make_params(weekday=Weekday.SUNDAY))

    def test_pet_76_mantiflame_maerwynn_tidy_toilet(self):
        req = get_requirement(76)
        assert req.location == Location.SUNBURN_DESERT
        events_active = frozenset({Event.TIDY_TOILET_TIME})
        assert req.check(**make_params(events=events_active))
        assert not req.check(**make_params())

    def test_pet_77_finnettle_magmaron_valentines(self):
        triggers = get_requirements(77)
        assert len(triggers) == 7
        for t in triggers:
            assert t.location == Location.MAGMARON
        # Feb 11-17 all match
        for day in range(11, 18):
            assert any(t.check(**make_params(month=2, day=day)) for t in triggers)
        # Outside range
        assert not any(t.check(**make_params(month=2, day=10)) for t in triggers)
        assert not any(t.check(**make_params(month=2, day=18)) for t in triggers)
        assert not any(t.check(**make_params(month=3, day=14)) for t in triggers)

    def test_pet_78_etrock_plains_oz_korr_new_years(self):
        triggers = get_requirements(78)
        assert len(triggers) == 8
        for t in triggers:
            assert t.location == Location.PLAINS_OF_OZ_KORR
        # Dec 28-31, Jan 1-4 all match
        for day in [28, 29, 30, 31]:
            assert any(t.check(**make_params(month=12, day=day)) for t in triggers)
        for day in [1, 2, 3, 4]:
            assert any(t.check(**make_params(month=1, day=day)) for t in triggers)
        # Outside range
        assert not any(t.check(**make_params(month=12, day=27)) for t in triggers)
        assert not any(t.check(**make_params(month=1, day=5)) for t in triggers)

    def test_pet_79_always_available(self):
        req = get_requirement(79)
        assert req.location == Location.MAGMARON
        assert req.check(**make_params())

    def test_pet_80_always_available(self):
        req = get_requirement(80)
        assert req.location == Location.GNAROGRIM
        assert req.check(**make_params())


# ═══════════════════════════════════════════════════════════════
# Water habitat (pet_id 81–100)
# ═══════════════════════════════════════════════════════════════


class TestWater:
    def test_pet_81_goldy_magmaron_day(self):
        req = get_requirement(81)
        assert req.location == Location.SKULL_ISLAND
        assert req.check(**make_params())
        assert not req.check(**make_params(hour=22))

    def test_pet_82_orcahle_skull_island_day(self):
        req = get_requirement(82)
        assert req.location == Location.SKULL_ISLAND
        assert req.check(**make_params())
        assert not req.check(**make_params(hour=22))

    def test_pet_83_ocodile_evernight_forest_night(self):
        req = get_requirement(83)
        assert req.location == Location.BLACK_WATER_SWAMP
        assert req.check(**make_params())

    def test_pet_84_penguwater_northrunt_day(self):
        req = get_requirement(84)
        assert req.location == Location.SHADOWROCK_MOUNTAIN
        assert req.check(**make_params())
        assert not req.check(**make_params(hour=22))

    def test_pet_85_walrophin_rotten_lands_monday_day(self):
        req = get_requirement(85)
        assert req.location == Location.SHADOWROCK_MOUNTAIN
        assert req.check(**make_params(weekday=Weekday.MONDAY))
        assert not req.check(**make_params(weekday=Weekday.MONDAY, hour=22))
        assert not req.check(**make_params(weekday=Weekday.TUESDAY))

    def test_pet_86_colsnail_tusk_mountain_tuesday_night(self):
        req = get_requirement(86)
        assert req.location == Location.MOLDY_FOREST
        assert req.check(**make_params(weekday=Weekday.TUESDAY))
        assert not req.check(**make_params(weekday=Weekday.WEDNESDAY))

    def test_pet_87_aquaphant_split_canyon_wednesday_day(self):
        req = get_requirement(87)
        assert req.location == Location.MOLDY_FOREST
        assert req.check(**make_params(weekday=Weekday.WEDNESDAY))
        assert not req.check(**make_params(weekday=Weekday.WEDNESDAY, hour=22))
        assert not req.check(**make_params(weekday=Weekday.THURSDAY))

    def test_pet_88_naar_flooded_caldwell_winter_day(self):
        req = get_requirement(88)
        assert req.location == Location.SHADOWROCK_MOUNTAIN
        assert req.check(**make_params(month=1, day=10))
        assert not req.check(**make_params(month=1, day=10, hour=22))
        assert not req.check(**make_params(month=7, day=10))

    def test_pet_89_octoboss_moldy_forest_thursday_night(self):
        req = get_requirement(89)
        assert req.location == Location.MOLDY_FOREST
        assert req.check(**make_params(weekday=Weekday.THURSDAY))
        assert not req.check(**make_params(weekday=Weekday.FRIDAY))

    def test_pet_90_ewilgryn_skull_island_friday_day(self):
        req = get_requirement(90)
        assert req.location == Location.SKULL_ISLAND
        assert req.check(**make_params(weekday=Weekday.FRIDAY))
        assert not req.check(**make_params(weekday=Weekday.FRIDAY, hour=22))
        assert not req.check(**make_params(weekday=Weekday.SATURDAY))

    def test_pet_91_seapard_black_water_swamp_saturday_day(self):
        req = get_requirement(91)
        assert req.location == Location.SKULL_ISLAND
        assert req.check(**make_params(weekday=Weekday.SATURDAY))
        assert not req.check(**make_params(weekday=Weekday.SATURDAY, hour=22))
        assert not req.check(**make_params(weekday=Weekday.SUNDAY))

    def test_pet_92_shellzy_erogenion_fall_night(self):
        req = get_requirement(92)
        assert req.location == Location.SKULL_ISLAND
        assert req.check(**make_params(month=10, day=5))
        assert not req.check(**make_params(month=4, day=5))

    def test_pet_93_mingho_sprawling_jungle_summer_day(self):
        req = get_requirement(93)
        assert req.location == Location.BLACK_WATER_SWAMP
        assert req.check(**make_params(month=7, day=10))
        assert not req.check(**make_params(month=7, day=10, hour=22))
        assert not req.check(**make_params(month=1, day=10))

    def test_pet_94_angbite_shadowrock_mountain_sunday_night(self):
        req = get_requirement(94)
        assert req.location == Location.SHADOWROCK_MOUNTAIN
        assert req.check(**make_params(weekday=Weekday.SUNDAY))
        assert not req.check(**make_params(weekday=Weekday.MONDAY))

    def test_pet_95_always_available(self):
        req = get_requirement(95)
        assert req.location == Location.SKULL_ISLAND
        assert req.check(**make_params())

    def test_pet_97_cannoturtle_skull_island_birthday(self):
        req = get_requirement(97)
        assert req.location == Location.SKULL_ISLAND
        assert req.check(**make_params(month=6, day=22))
        assert not req.check(**make_params(month=6, day=23))
        assert not req.check(**make_params(month=7, day=22))

    def test_pet_99_always_available(self):
        req = get_requirement(99)
        assert req.location == Location.MOLDY_FOREST
        assert req.check(**make_params())

    def test_pet_100_always_available(self):
        req = get_requirement(100)
        assert req.location == Location.BLACK_WATER_SWAMP
        assert req.check(**make_params())


# ═══════════════════════════════════════════════════════════════
# Structural / integrity tests
# ═══════════════════════════════════════════════════════════════


class TestStructure:
    def test_total_trigger_count(self):
        """123 triggers total (unique pets + extra date entries for 18, 37, 56, 77, 78)."""
        assert len(PET_REQUIREMENTS) == 123

    def test_all_pet_ids_in_valid_range(self):
        for req in PET_REQUIREMENTS:
            assert 1 <= req.pet_id <= 100, f"pet_id {req.pet_id} out of range"

    def test_shadow_pet_ids(self):
        shadow_ids = {r.pet_id for r in PET_REQUIREMENTS if 1 <= r.pet_id <= 20}
        expected = {
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            12,
            13,
            14,
            15,
            16,
            17,
            18,
            19,
            20,
        }
        assert shadow_ids == expected

    def test_light_pet_ids(self):
        light_ids = {r.pet_id for r in PET_REQUIREMENTS if 21 <= r.pet_id <= 40}
        expected = {
            21,
            22,
            23,
            24,
            25,
            26,
            27,
            28,
            29,
            30,
            31,
            32,
            33,
            34,
            35,
            36,
            37,
            38,
            39,
            40,
        }
        assert light_ids == expected

    def test_earth_pet_ids(self):
        earth_ids = {r.pet_id for r in PET_REQUIREMENTS if 41 <= r.pet_id <= 60}
        expected = {
            41,
            42,
            43,
            44,
            45,
            46,
            47,
            48,
            49,
            50,
            51,
            52,
            53,
            54,
            55,
            56,
            57,
            58,
            60,
        }
        assert earth_ids == expected

    def test_fire_pet_ids(self):
        fire_ids = {r.pet_id for r in PET_REQUIREMENTS if 61 <= r.pet_id <= 80}
        expected = {
            61,
            62,
            63,
            64,
            65,
            66,
            67,
            68,
            69,
            70,
            71,
            72,
            73,
            74,
            76,
            77,
            78,
            79,
            80,
        }
        assert fire_ids == expected

    def test_water_pet_ids(self):
        water_ids = {r.pet_id for r in PET_REQUIREMENTS if 81 <= r.pet_id <= 100}
        expected = {
            81,
            82,
            83,
            84,
            85,
            86,
            87,
            88,
            89,
            90,
            91,
            92,
            93,
            94,
            95,
            97,
            99,
            100,
        }
        assert water_ids == expected

    def test_no_duplicate_triggers_except_multi_entry_pets(self):
        """Only pets 18, 37, 56, 77, and 78 should have multiple entries."""
        counts = Counter(r.pet_id for r in PET_REQUIREMENTS)
        multi_entry = {18: 5, 37: 7, 56: 5, 77: 7, 78: 8}
        for pet_id, count in counts.items():
            if pet_id in multi_entry:
                expected = multi_entry[pet_id]
                assert count == expected, (
                    f"pet {pet_id} should have {expected} entries, got {count}"
                )
            else:
                assert count == 1, f"pet {pet_id} has {count} entries, expected 1"


# ═══════════════════════════════════════════════════════════════
# Negative tests — verify no triggers match under wrong conditions
# ═══════════════════════════════════════════════════════════════


class TestNegative:
    """Verify that NO requirement matches when all conditions are wrong."""

    def test_no_match_summer_day_tuesday_no_events(self):
        """Tuesday summer day with no events — only specific pets should match."""
        params = make_params(weekday=Weekday.TUESDAY, month=7, day=15)
        matched = {r.pet_id for r in PET_REQUIREMENTS if r.check(**params)}
        # Only time_of_day=DAY pets with no day/season/event constraint,
        # or DAY+TUESDAY, or DAY+SUMMER should match.
        # Should NOT contain any night/midnight/other-day/other-season/event pets.
        for pet_id in matched:
            triggers = get_requirements(pet_id)
            for req in triggers:
                if req.check(**params):
                    if req.time_of_day is not None:
                        assert req.time_of_day in (TimeOfDay.DAY, TimeOfDay.NIGHT)
                    if req.day_of_week is not None:
                        assert req.day_of_week == Weekday.TUESDAY
                    if req.season is not None:
                        assert req.season == Season.SUMMER

    def test_no_match_winter_night_wednesday_no_events(self):
        """Wednesday winter night with no events."""
        params = make_params(weekday=Weekday.WEDNESDAY, month=1, day=15, hour=22)
        matched = {r.pet_id for r in PET_REQUIREMENTS if r.check(**params)}
        for pet_id in matched:
            for req in get_requirements(pet_id):
                if req.check(**params):
                    if req.time_of_day is not None:
                        assert req.time_of_day in (TimeOfDay.NIGHT, TimeOfDay.MIDNIGHT)
                    if req.day_of_week is not None:
                        assert req.day_of_week == Weekday.WEDNESDAY
                    if req.season is not None:
                        assert req.season == Season.WINTER

    def test_event_pets_never_match_without_event(self):
        """All event-gated pets must NOT match when no events are active."""
        params = make_params(month=10, day=31, weekday=Weekday.FRIDAY)
        event_pet_ids = {r.pet_id for r in PET_REQUIREMENTS if r.event is not None}
        for pet_id in event_pet_ids:
            for req in get_requirements(pet_id):
                if req.event is not None:
                    assert not req.check(**params), (
                        f"pet {pet_id} matched without event"
                    )

    def test_special_date_pets_never_match_on_wrong_date(self):
        """All special_date pets must NOT match on a random date."""
        params = make_params(month=6, day=15)
        special_pet_ids = {
            r.pet_id for r in PET_REQUIREMENTS if r.special_date is not None
        }
        for pet_id in special_pet_ids:
            for req in get_requirements(pet_id):
                if req.special_date is not None:
                    assert not req.check(**params), (
                        f"pet {pet_id} matched on wrong date"
                    )

    def test_day_of_month_pet_never_matches_on_wrong_combo(self):
        """Pet 18 (Friday the 13th) must NOT match on wrong day+weekday combos."""
        triggers = get_requirements(18)
        # Friday the 12th — no entry for that combo
        assert not any(
            t.check(**make_params(weekday=Weekday.FRIDAY, day=12)) for t in triggers
        )
        # Thursday the 13th — no entry for that combo
        assert not any(
            t.check(**make_params(weekday=Weekday.THURSDAY, day=13)) for t in triggers
        )

    def test_month_pet_never_matches_outside_month(self):
        """Pet 36 (December) must NOT match in any other month."""
        req = get_requirement(36)
        for m in range(1, 12):
            assert not req.check(**make_params(month=m, day=15)), (
                f"pet 36 matched in month {m}"
            )

    def test_midnight_pet_matches_at_midnight(self):
        req = get_requirement(6)
        assert req.check(**make_params(hour=0))
        assert not req.check(**make_params(hour=1))

    def test_no_match_at_all_on_impossible_scenario(self):
        """Mar 25, 10pm Wednesday, spring, no events — only unconstrained night pets match."""
        params = make_params(weekday=Weekday.WEDNESDAY, month=3, day=25, hour=22)
        matched_ids = {r.pet_id for r in PET_REQUIREMENTS if r.check(**params)}
        # All matched must be night-compatible and wednesday-compatible and spring-compatible
        for pid in matched_ids:
            for req in get_requirements(pid):
                if req.check(**params):
                    if req.time_of_day is not None:
                        assert req.time_of_day == TimeOfDay.NIGHT
                    if req.day_of_week is not None:
                        assert req.day_of_week == Weekday.WEDNESDAY
                    if req.season is not None:
                        assert req.season == Season.SPRING
