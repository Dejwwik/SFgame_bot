from sfbot.fortress.fortress import UnitType
from sfbot.fortress.tests.conftest import (
    UNLIMITED,
    all_at_zero,
    levels,
    make_fortress,
)

# ═══════════════════════════════════════════════════════════════════════════
# Hall of Knights
# ═══════════════════════════════════════════════════════════════════════════


class TestHallOfKnights:
    def test_hok_at_level_0_is_not_maxed(self):
        fortress = make_fortress(building_levels=all_at_zero(), hok_level=0)
        assert fortress.is_hok_maxed is False

    def test_hok_at_level_20_is_maxed(self):
        fortress = make_fortress(building_levels=all_at_zero(), hok_level=20)
        assert fortress.is_hok_maxed is True

    def test_hok_upgrade_allowed_with_sufficient_resources(self):
        hok_cost = (100, 50, 200, 300)  # time, silver, wood, stone
        fortress = make_fortress(
            building_levels=levels(FORTRESS=10), hok_level=5, hok_cost=hok_cost
        )
        assert fortress.can_upgrade_hok(200, 300, 50) is True

    def test_hok_upgrade_blocked_when_hok_equals_fortress(self):
        hok_cost = (100, 50, 200, 300)
        fortress = make_fortress(
            building_levels=levels(FORTRESS=5), hok_level=5, hok_cost=hok_cost
        )
        assert fortress.can_upgrade_hok(UNLIMITED, UNLIMITED, UNLIMITED) is False

    def test_hok_upgrade_blocked_without_cost_data(self):
        fortress = make_fortress(
            building_levels=all_at_zero(), hok_level=5, hok_cost=None
        )
        assert fortress.can_upgrade_hok(UNLIMITED, UNLIMITED, UNLIMITED) is False

    def test_hok_upgrade_blocked_when_already_maxed(self):
        hok_cost = (100, 50, 200, 300)
        fortress = make_fortress(
            building_levels=all_at_zero(), hok_level=20, hok_cost=hok_cost
        )
        assert fortress.can_upgrade_hok(UNLIMITED, UNLIMITED, UNLIMITED) is False

    def test_hok_upgrade_blocked_by_insufficient_wood(self):
        hok_cost = (100, 50, 200, 300)
        fortress = make_fortress(
            building_levels=levels(FORTRESS=10), hok_level=5, hok_cost=hok_cost
        )
        assert fortress.can_upgrade_hok(199, 300, 50) is False

    def test_hok_upgrade_blocked_by_insufficient_stone(self):
        hok_cost = (100, 50, 200, 300)
        fortress = make_fortress(
            building_levels=levels(FORTRESS=10), hok_level=5, hok_cost=hok_cost
        )
        assert fortress.can_upgrade_hok(200, 299, 50) is False

    def test_hok_upgrade_blocked_by_insufficient_silver(self):
        hok_cost = (100, 50, 200, 300)
        fortress = make_fortress(
            building_levels=all_at_zero(), hok_level=5, hok_cost=hok_cost
        )
        assert fortress.can_upgrade_hok(200, 300, 49) is False


# ═══════════════════════════════════════════════════════════════════════════
# Unit Upgrades
# ═══════════════════════════════════════════════════════════════════════════


class TestUnitUpgrades:
    def test_soldier_below_smithy_level_can_upgrade(self):
        fortress = make_fortress(
            building_levels=levels(SMITHY=10, BARRACKS=10),
            unit_levels={UnitType.SOLDIER: 5, UnitType.MAGICIAN: 0, UnitType.ARCHER: 0},
        )
        assert fortress.can_upgrade_unit(UnitType.SOLDIER) is True

    def test_soldier_at_smithy_level_cannot_upgrade(self):
        fortress = make_fortress(
            building_levels=levels(SMITHY=10, BARRACKS=15),
            unit_levels={
                UnitType.SOLDIER: 10,
                UnitType.MAGICIAN: 0,
                UnitType.ARCHER: 0,
            },
        )
        assert fortress.can_upgrade_unit(UnitType.SOLDIER) is False

    def test_soldier_above_barracks_level_can_still_upgrade(self):
        fortress = make_fortress(
            building_levels=levels(SMITHY=20, BARRACKS=5),
            unit_levels={UnitType.SOLDIER: 5, UnitType.MAGICIAN: 0, UnitType.ARCHER: 0},
        )
        assert fortress.can_upgrade_unit(UnitType.SOLDIER) is True

    def test_soldier_at_smithy_max_cannot_upgrade(self):
        fortress = make_fortress(
            building_levels=levels(SMITHY=20, BARRACKS=8),
            unit_levels={UnitType.SOLDIER: 20, UnitType.MAGICIAN: 0, UnitType.ARCHER: 0},
        )
        assert fortress.can_upgrade_unit(UnitType.SOLDIER) is False

    def test_all_units_below_smithy_level_can_upgrade(self):
        fortress = make_fortress(
            building_levels=levels(
                SMITHY=5, BARRACKS=5, ARCHERY_GUILD=5, MAGES_TOWER=5
            ),
            unit_levels={UnitType.SOLDIER: 3, UnitType.MAGICIAN: 4, UnitType.ARCHER: 2},
        )
        for unit_type in UnitType:
            assert fortress.can_upgrade_unit(unit_type) is True

    def test_no_unit_upgrades_when_smithy_at_zero(self):
        fortress = make_fortress(
            building_levels=levels(
                SMITHY=0, BARRACKS=5, ARCHERY_GUILD=5, MAGES_TOWER=5
            ),
            unit_levels={UnitType.SOLDIER: 0, UnitType.MAGICIAN: 0, UnitType.ARCHER: 0},
        )
        for unit_type in UnitType:
            assert fortress.can_upgrade_unit(unit_type) is False

    def test_no_training_building_cannot_upgrade(self):
        fortress = make_fortress(
            building_levels=levels(
                SMITHY=10, BARRACKS=0, ARCHERY_GUILD=0, MAGES_TOWER=0
            ),
            unit_levels={UnitType.SOLDIER: 0, UnitType.MAGICIAN: 0, UnitType.ARCHER: 0},
        )
        for unit_type in UnitType:
            assert fortress.can_upgrade_unit(unit_type) is False
