from sfbot.fortress.fortress import MAX_BUILDING_LEVEL, BuildingType, Fortress, UnitType
from sfbot.fortress.tests.conftest import (
    UNLIMITED,
    B,
    all_at_zero,
    free_costs,
    levels,
    make_fortress,
    pick_upgrade,
)

# ═══════════════════════════════════════════════════════════════════════════
# Maxed Building Detection
# ═══════════════════════════════════════════════════════════════════════════


class TestMaxedBuildingDetection:
    def test_fortress_is_maxed_at_level_20(self):
        fortress = make_fortress(building_levels=levels(FORTRESS=20))
        assert fortress.is_building_maxed(B.FORTRESS) is True
        assert (
            fortress.can_upgrade(B.FORTRESS, UNLIMITED, UNLIMITED, UNLIMITED) is False
        )

    def test_laborers_quarters_is_maxed_at_level_15(self):
        fortress = make_fortress(
            building_levels=levels(FORTRESS=20, LABORERS_QUARTERS=15)
        )
        assert fortress.is_building_maxed(B.LABORERS_QUARTERS) is True

    def test_gem_mine_is_maxed_at_level_100(self):
        fortress = make_fortress(building_levels=levels(FORTRESS=20, GEM_MINE=100))
        assert fortress.is_building_maxed(B.GEM_MINE) is True

    def test_gem_mine_is_not_maxed_at_level_99(self):
        fortress = make_fortress(building_levels=levels(FORTRESS=20, GEM_MINE=99))
        assert fortress.is_building_maxed(B.GEM_MINE) is False

    def test_treasury_is_maxed_at_level_45(self):
        fortress = make_fortress(building_levels=levels(FORTRESS=20, TREASURY=45))
        assert fortress.is_building_maxed(B.TREASURY) is True

    def test_all_buildings_at_max_pick_upgrade_returns_none(
        self, maxed_fortress: Fortress
    ):
        assert maxed_fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED) is None


# ═══════════════════════════════════════════════════════════════════════════
# Fortress Properties
# ═══════════════════════════════════════════════════════════════════════════


class TestFortressProperties:
    def test_populated_levels_reports_unlocked(self, fresh_fortress: Fortress):
        assert fresh_fortress.is_unlocked is True

    def test_empty_levels_reports_not_unlocked(self, unlocked_empty_fortress: Fortress):
        assert unlocked_empty_fortress.is_unlocked is False

    def test_fortress_level_reads_fortress_building(self):
        fortress = make_fortress(building_levels=levels(FORTRESS=12))
        assert fortress.fortress_level == 12

    def test_smithy_level_reads_smithy_building(self):
        fortress = make_fortress(building_levels=levels(SMITHY=7))
        assert fortress.smithy_level == 7

    def test_no_upgrade_target_reports_not_upgrading(self, fresh_fortress: Fortress):
        assert fresh_fortress.is_upgrading is False

    def test_upgrade_target_set_reports_is_upgrading(
        self, upgrading_fortress: Fortress
    ):
        assert upgrading_fortress.is_upgrading is True


# ═══════════════════════════════════════════════════════════════════════════
# Extreme / Impossible Game States
# ═══════════════════════════════════════════════════════════════════════════


class TestExtremeStates:
    def test_fortress_above_max_level_reports_maxed(self):
        fortress = make_fortress(building_levels=levels(FORTRESS=25))
        assert fortress.is_building_maxed(B.FORTRESS) is True
        assert (
            fortress.can_upgrade(B.FORTRESS, UNLIMITED, UNLIMITED, UNLIMITED) is False
        )

    def test_all_buildings_above_max_returns_none(self):
        building_levels = {bt: MAX_BUILDING_LEVEL[bt] + 10 for bt in BuildingType}
        assert pick_upgrade(building_levels) is None

    def test_negative_resources_returns_none(self):
        nonzero_costs = {bt: (0, 1, 1, 1) for bt in BuildingType}
        fortress = make_fortress(
            building_levels=all_at_zero(), building_costs=nonzero_costs
        )
        assert fortress.pick_upgrade(-1, -1, -1) is None

    def test_zero_cost_buildings_upgradable_with_zero_resources(self):
        fortress = make_fortress(
            building_levels=all_at_zero(), building_costs=free_costs()
        )
        assert fortress.pick_upgrade(0, 0, 0) == B.FORTRESS

    def test_fortress_at_max_all_others_at_zero_picks_lq(self):
        assert pick_upgrade(levels(FORTRESS=20)) == B.LABORERS_QUARTERS

    def test_treasury_at_absurd_level_reports_maxed(self):
        fortress = make_fortress(building_levels=levels(FORTRESS=1, TREASURY=999))
        assert fortress.is_building_maxed(B.TREASURY) is True

    def test_hok_above_max_reports_maxed(self):
        fortress = make_fortress(building_levels=all_at_zero(), hok_level=99)
        assert fortress.is_hok_maxed is True
        assert fortress.can_upgrade_hok(UNLIMITED, UNLIMITED, UNLIMITED) is False

    def test_unit_level_above_smithy_cannot_upgrade(self):
        fortress = make_fortress(
            building_levels=levels(SMITHY=5),
            unit_levels={
                UnitType.SOLDIER: 10,
                UnitType.MAGICIAN: 0,
                UnitType.ARCHER: 0,
            },
        )
        assert fortress.can_upgrade_unit(UnitType.SOLDIER) is False
