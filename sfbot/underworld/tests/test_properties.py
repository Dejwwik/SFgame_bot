from unittest.mock import MagicMock

from sfbot.underworld.constants import (
    MAX_BUILDING_LEVEL,
    BuildingType,
    UnitType,
)
from sfbot.underworld.tests.conftest import (
    UNLIMITED,
    B,
    all_at_max,
    all_at_zero,
    levels,
    make_underworld,
)
from sfbot.underworld.underworld import Underworld

# ═══════════════════════════════════════════════════════════════════════════
# Maxed Building Detection
# ═══════════════════════════════════════════════════════════════════════════


class TestMaxedBuildingDetection:
    def test_heart_is_maxed_at_level_15(self):
        uw = make_underworld(building_levels=levels(HEART_OF_DARKNESS=15))
        assert uw.is_building_maxed(B.HEART_OF_DARKNESS) is True
        assert uw.can_upgrade(B.HEART_OF_DARKNESS, UNLIMITED, UNLIMITED) is False

    def test_gold_pit_is_maxed_at_level_100(self):
        uw = make_underworld(building_levels=levels(HEART_OF_DARKNESS=15, GOLD_PIT=100))
        assert uw.is_building_maxed(B.GOLD_PIT) is True

    def test_gold_pit_is_not_maxed_at_level_99(self):
        uw = make_underworld(building_levels=levels(HEART_OF_DARKNESS=15, GOLD_PIT=99))
        assert uw.is_building_maxed(B.GOLD_PIT) is False

    def test_all_buildings_at_max_pick_upgrade_returns_none(self):
        uw = make_underworld(building_levels=all_at_max())
        assert uw.pick_upgrade(UNLIMITED, UNLIMITED) is None


# ═══════════════════════════════════════════════════════════════════════════
# Underworld Properties
# ═══════════════════════════════════════════════════════════════════════════


class TestUnderworldProperties:
    def test_populated_levels_reports_unlocked(self, fresh_underworld: Underworld):
        assert fresh_underworld.is_unlocked is True

    def test_empty_levels_reports_not_unlocked(self):
        uw = make_underworld()
        assert uw.is_unlocked is False

    def test_heart_level_reads_heart_building(self):
        uw = make_underworld(building_levels=levels(HEART_OF_DARKNESS=12))
        assert uw.heart_level == 12

    def test_no_upgrade_target_reports_not_upgrading(
        self, fresh_underworld: Underworld
    ):
        assert fresh_underworld.is_upgrading is False

    def test_upgrade_target_set_reports_is_upgrading(self):
        uw = make_underworld(
            building_levels=all_at_zero(), upgrading=B.HEART_OF_DARKNESS
        )
        assert uw.is_upgrading is True

    def test_upgrade_finished_when_time_passed(self):
        uw = make_underworld(
            building_levels=all_at_zero(),
            upgrading=B.HEART_OF_DARKNESS,
            upgrade_finish=0,
        )
        mock_session: MagicMock = uw.session  # type: ignore[assignment]
        mock_session.server_time.return_value = 100
        assert uw.upgrade_is_finished is True

    def test_upgrade_not_finished_when_time_not_passed(self):
        uw = make_underworld(
            building_levels=all_at_zero(),
            upgrading=B.HEART_OF_DARKNESS,
            upgrade_finish=200,
        )
        mock_session: MagicMock = uw.session  # type: ignore[assignment]
        mock_session.server_time.return_value = 100
        assert uw.upgrade_is_finished is False


# ═══════════════════════════════════════════════════════════════════════════
# Lure Properties
# ═══════════════════════════════════════════════════════════════════════════


class TestLureProperties:
    def test_can_lure_when_gate_built_and_under_limit(self):
        uw = make_underworld(building_levels=levels(GATE=5), lured_today=0)
        assert uw.can_lure is True

    def test_cannot_lure_when_at_limit(self):
        uw = make_underworld(building_levels=levels(GATE=5), lured_today=5)
        assert uw.can_lure is False

    def test_cannot_lure_without_gate(self):
        uw = make_underworld(building_levels=all_at_zero(), lured_today=0)
        assert uw.can_lure is False

    def test_max_lures_capped_by_gate_level(self):
        uw = make_underworld(building_levels=levels(GATE=2), lured_today=0)
        assert uw.max_lures == 2
        assert uw.can_lure is True

    def test_max_lures_capped_at_five(self):
        uw = make_underworld(building_levels=levels(GATE=100), lured_today=0)
        assert uw.max_lures == 5


# ═══════════════════════════════════════════════════════════════════════════
# Unit Upgrade
# ═══════════════════════════════════════════════════════════════════════════


class TestUnitUpgrade:
    def test_can_upgrade_unit_with_building_and_cost(self):
        uw = make_underworld(
            building_levels=levels(GOBLIN_PIT=1),
            unit_upgrade_costs={UnitType.GOBLIN: (2, 100, 50)},
        )
        assert uw.can_upgrade_unit(UnitType.GOBLIN) is True

    def test_cannot_upgrade_unit_without_building(self):
        uw = make_underworld(
            building_levels=all_at_zero(),
            unit_upgrade_costs={UnitType.GOBLIN: (2, 100, 50)},
        )
        assert uw.can_upgrade_unit(UnitType.GOBLIN) is False

    def test_cannot_upgrade_unit_without_cost_data(self):
        uw = make_underworld(building_levels=levels(GOBLIN_PIT=1))
        assert uw.can_upgrade_unit(UnitType.GOBLIN) is False

    def test_cannot_upgrade_unit_at_next_level_zero(self):
        uw = make_underworld(
            building_levels=levels(GOBLIN_PIT=1),
            unit_upgrade_costs={UnitType.GOBLIN: (0, 0, 0)},
        )
        assert uw.can_upgrade_unit(UnitType.GOBLIN) is False


# ═══════════════════════════════════════════════════════════════════════════
# Extreme / Impossible Game States
# ═══════════════════════════════════════════════════════════════════════════


class TestExtremeStates:
    def test_heart_above_max_level_reports_maxed(self):
        uw = make_underworld(building_levels=levels(HEART_OF_DARKNESS=25))
        assert uw.is_building_maxed(B.HEART_OF_DARKNESS) is True

    def test_all_buildings_above_max_returns_none(self):
        building_levels = {bt: MAX_BUILDING_LEVEL[bt] + 10 for bt in BuildingType}
        uw = make_underworld(building_levels=building_levels)
        assert uw.pick_upgrade(UNLIMITED, UNLIMITED) is None

    def test_negative_resources_returns_none(self):
        nonzero_costs = {bt: (0, 1, 1) for bt in BuildingType}
        uw = make_underworld(
            building_levels=all_at_zero(), building_costs=nonzero_costs
        )
        assert uw.pick_upgrade(-1, -1) is None
