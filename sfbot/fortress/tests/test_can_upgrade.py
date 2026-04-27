import pytest

from sfbot.fortress.fortress import (
    MAX_BUILDING_LEVEL,
    REQUIRED_FORTRESS_LEVEL,
    UNCAPPED_BY_FORTRESS,
    BuildingType,
    Fortress,
)
from sfbot.fortress.tests.conftest import (
    STAGE2_COMPLETE,
    UNLIMITED,
    B,
    all_at_zero,
    expensive_costs,
    levels,
    make_fortress,
)

# ═══════════════════════════════════════════════════════════════════════════
# Fortress Not Unlocked (Empty State)
# ═══════════════════════════════════════════════════════════════════════════


class TestFortressNotUnlocked:
    def test_empty_levels_reports_not_unlocked(self, unlocked_empty_fortress: Fortress):
        assert unlocked_empty_fortress.is_unlocked is False

    def test_empty_levels_still_picks_fortress_because_get_defaults_to_zero(
        self, unlocked_empty_fortress: Fortress
    ):
        assert (
            unlocked_empty_fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED)
            == B.FORTRESS
        )

    def test_empty_levels_reports_fortress_level_as_zero(
        self, unlocked_empty_fortress: Fortress
    ):
        assert unlocked_empty_fortress.fortress_level == 0

    def test_empty_levels_returns_zero_for_every_building(
        self, unlocked_empty_fortress: Fortress
    ):
        for building_type in BuildingType:
            assert unlocked_empty_fortress.building_level(building_type) == 0

    def test_empty_levels_allows_fortress_upgrade_since_no_prerequisites(
        self, unlocked_empty_fortress: Fortress
    ):
        assert (
            unlocked_empty_fortress.can_upgrade(
                B.FORTRESS, UNLIMITED, UNLIMITED, UNLIMITED
            )
            is True
        )

    def test_empty_levels_blocks_lq_and_academy_due_to_fortress_requirement(
        self, unlocked_empty_fortress: Fortress
    ):
        assert (
            unlocked_empty_fortress.can_upgrade(
                B.LABORERS_QUARTERS, UNLIMITED, UNLIMITED, UNLIMITED
            )
            is False
        )
        assert (
            unlocked_empty_fortress.can_upgrade(
                B.ACADEMY, UNLIMITED, UNLIMITED, UNLIMITED
            )
            is False
        )


# ═══════════════════════════════════════════════════════════════════════════
# No Resources Available
# ═══════════════════════════════════════════════════════════════════════════


class TestInsufficientResources:
    def test_zero_wood_with_wood_cost_returns_none(self):
        wood_cost_only = {bt: (0, 0, 100, 0) for bt in BuildingType}
        fortress = make_fortress(
            building_levels=all_at_zero(), building_costs=wood_cost_only
        )
        assert fortress.pick_upgrade(0, UNLIMITED, UNLIMITED) is None

    def test_zero_stone_with_stone_cost_returns_none(self):
        stone_cost_only = {bt: (0, 0, 0, 100) for bt in BuildingType}
        fortress = make_fortress(
            building_levels=all_at_zero(), building_costs=stone_cost_only
        )
        assert fortress.pick_upgrade(UNLIMITED, 0, UNLIMITED) is None

    def test_zero_silver_with_silver_cost_returns_none(self):
        silver_cost_only = {bt: (0, 100, 0, 0) for bt in BuildingType}
        fortress = make_fortress(
            building_levels=all_at_zero(), building_costs=silver_cost_only
        )
        assert fortress.pick_upgrade(UNLIMITED, UNLIMITED, 0) is None

    def test_all_resources_zero_with_nonzero_costs_returns_none(self):
        nonzero_costs = {bt: (0, 10, 10, 10) for bt in BuildingType}
        fortress = make_fortress(
            building_levels=all_at_zero(), building_costs=nonzero_costs
        )
        assert fortress.pick_upgrade(0, 0, 0) is None

    def test_only_fortress_affordable_picks_fortress(self):
        costs = expensive_costs()
        costs[B.FORTRESS] = (0, 0, 0, 0)
        fortress = make_fortress(building_levels=all_at_zero(), building_costs=costs)
        assert fortress.pick_upgrade(100, 100, 100) == B.FORTRESS

    def test_no_cost_data_at_all_returns_none(self):
        fortress = make_fortress(building_levels=all_at_zero(), building_costs={})
        assert fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED) is None


# ═══════════════════════════════════════════════════════════════════════════
# Fortress Level Cap & Building Prerequisites
# ═══════════════════════════════════════════════════════════════════════════


class TestFortressLevelCapAndPrerequisites:
    def test_lq_at_fortress_level_is_capped_upgrades_fortress_instead(self):
        building_levels = levels(
            FORTRESS=3,
            LABORERS_QUARTERS=3,
            WOODCUTTER=3,
            QUARRY=3,
            BARRACKS=3,
            GEM_MINE=1,
        )
        fortress = make_fortress(building_levels=building_levels)
        assert fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED) == B.FORTRESS

    def test_quarry_below_fortress_level_upgrades_quarry_directly(self):
        building_levels = levels(
            FORTRESS=2,
            LABORERS_QUARTERS=2,
            WOODCUTTER=2,
            QUARRY=1,
            BARRACKS=1,
            GEM_MINE=1,
        )
        fortress = make_fortress(building_levels=building_levels)
        assert fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED) == B.QUARRY

    def test_barracks_blocked_at_fortress_3_picks_gemmine_instead(self):
        building_levels = levels(
            FORTRESS=3, LABORERS_QUARTERS=1, WOODCUTTER=1, QUARRY=1
        )
        fortress = make_fortress(building_levels=building_levels)
        assert fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED) == B.GEM_MINE

    def test_archery_guild_blocked_below_fortress_5(self):
        building_levels = levels(FORTRESS=4, ARCHERY_GUILD=0)
        fortress = make_fortress(building_levels=building_levels)
        assert (
            fortress.can_upgrade(B.ARCHERY_GUILD, UNLIMITED, UNLIMITED, UNLIMITED)
            is False
        )

    def test_archery_guild_allowed_at_fortress_5(self):
        building_levels = levels(FORTRESS=5, ARCHERY_GUILD=0)
        fortress = make_fortress(building_levels=building_levels)
        assert (
            fortress.can_upgrade(B.ARCHERY_GUILD, UNLIMITED, UNLIMITED, UNLIMITED)
            is True
        )

    def test_academy_blocked_below_fortress_6(self):
        building_levels = levels(FORTRESS=5)
        fortress = make_fortress(building_levels=building_levels)
        assert fortress.can_upgrade(B.ACADEMY, UNLIMITED, UNLIMITED, UNLIMITED) is False

    def test_academy_allowed_at_fortress_6(self):
        building_levels = levels(FORTRESS=6)
        fortress = make_fortress(building_levels=building_levels)
        assert fortress.can_upgrade(B.ACADEMY, UNLIMITED, UNLIMITED, UNLIMITED) is True

    def test_mages_tower_blocked_below_fortress_7(self):
        building_levels = levels(FORTRESS=6)
        fortress = make_fortress(building_levels=building_levels)
        assert (
            fortress.can_upgrade(B.MAGES_TOWER, UNLIMITED, UNLIMITED, UNLIMITED)
            is False
        )

    def test_mages_tower_allowed_at_fortress_7(self):
        building_levels = levels(FORTRESS=7)
        fortress = make_fortress(building_levels=building_levels)
        assert (
            fortress.can_upgrade(B.MAGES_TOWER, UNLIMITED, UNLIMITED, UNLIMITED) is True
        )

    def test_gem_mine_at_10_with_fortress_5_is_uncapped(self):
        building_levels = levels(FORTRESS=5, GEM_MINE=10)
        fortress = make_fortress(building_levels=building_levels)
        assert fortress.can_upgrade(B.GEM_MINE, UNLIMITED, UNLIMITED, UNLIMITED) is True

    def test_treasury_at_10_with_fortress_5_is_uncapped(self):
        building_levels = levels(FORTRESS=5, TREASURY=10)
        fortress = make_fortress(building_levels=building_levels)
        assert fortress.can_upgrade(B.TREASURY, UNLIMITED, UNLIMITED, UNLIMITED) is True

    def test_woodcutter_at_fortress_level_is_capped(self):
        building_levels = levels(FORTRESS=5, WOODCUTTER=5)
        fortress = make_fortress(building_levels=building_levels)
        assert (
            fortress.can_upgrade(B.WOODCUTTER, UNLIMITED, UNLIMITED, UNLIMITED) is False
        )

    def test_fortress_is_never_capped_by_own_level(self):
        building_levels = levels(FORTRESS=10)
        fortress = make_fortress(building_levels=building_levels)
        assert fortress.can_upgrade(B.FORTRESS, UNLIMITED, UNLIMITED, UNLIMITED) is True

    def test_all_candidates_capped_falls_back_to_fortress(self):
        fortress = make_fortress(building_levels=STAGE2_COMPLETE)
        assert fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED) == B.FORTRESS


# ═══════════════════════════════════════════════════════════════════════════
# Upgrade Already In Progress
# ═══════════════════════════════════════════════════════════════════════════


class TestUpgradeInProgress:
    def test_can_upgrade_returns_false_for_any_building_while_upgrading(
        self, upgrading_fortress: Fortress
    ):
        assert (
            upgrading_fortress.can_upgrade(B.FORTRESS, UNLIMITED, UNLIMITED, UNLIMITED)
            is False
        )
        assert (
            upgrading_fortress.can_upgrade(
                B.LABORERS_QUARTERS, UNLIMITED, UNLIMITED, UNLIMITED
            )
            is False
        )

    def test_pick_upgrade_returns_none_while_upgrading(
        self, upgrading_fortress: Fortress
    ):
        assert upgrading_fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED) is None


# ═══════════════════════════════════════════════════════════════════════════
# can_upgrade Edge Cases
# ═══════════════════════════════════════════════════════════════════════════


class TestCanUpgradeEdgeCases:
    def test_every_building_at_max_reports_cannot_upgrade(self):
        for building_type in BuildingType:
            building_levels = levels(FORTRESS=20)
            building_levels[building_type] = MAX_BUILDING_LEVEL[building_type]
            fortress = make_fortress(building_levels=building_levels)
            assert (
                fortress.can_upgrade(building_type, UNLIMITED, UNLIMITED, UNLIMITED)
                is False
            )

    def test_every_building_at_zero_with_high_fortress_reports_can_upgrade(self):
        for building_type in BuildingType:
            required = REQUIRED_FORTRESS_LEVEL.get(building_type, 0)
            building_levels = {b: 0 for b in BuildingType}
            if building_type == B.FORTRESS:
                building_levels[B.FORTRESS] = 0
            else:
                building_levels[B.FORTRESS] = max(
                    required, MAX_BUILDING_LEVEL[building_type]
                )
            fortress = make_fortress(building_levels=building_levels)
            assert (
                fortress.can_upgrade(building_type, UNLIMITED, UNLIMITED, UNLIMITED)
                is True
            )

    def test_exact_resource_match_allows_upgrade(self):
        building_levels = levels(FORTRESS=5)
        costs = {bt: (0, 100, 200, 300) for bt in BuildingType}
        fortress = make_fortress(building_levels=building_levels, building_costs=costs)
        assert fortress.can_upgrade(B.WOODCUTTER, 200, 300, 100) is True

    def test_one_wood_short_blocks_upgrade(self):
        building_levels = levels(FORTRESS=5)
        costs = {bt: (0, 100, 200, 300) for bt in BuildingType}
        fortress = make_fortress(building_levels=building_levels, building_costs=costs)
        assert fortress.can_upgrade(B.WOODCUTTER, 199, 300, 100) is False

    def test_one_stone_short_blocks_upgrade(self):
        building_levels = levels(FORTRESS=5)
        costs = {bt: (0, 100, 200, 300) for bt in BuildingType}
        fortress = make_fortress(building_levels=building_levels, building_costs=costs)
        assert fortress.can_upgrade(B.WOODCUTTER, 200, 299, 100) is False

    def test_one_silver_short_blocks_upgrade(self):
        building_levels = levels(FORTRESS=5)
        costs = {bt: (0, 100, 200, 300) for bt in BuildingType}
        fortress = make_fortress(building_levels=building_levels, building_costs=costs)
        assert fortress.can_upgrade(B.WOODCUTTER, 200, 300, 99) is False

    def test_active_upgrade_blocks_all_buildings(self):
        building_levels = levels(FORTRESS=20)
        fortress = make_fortress(building_levels=building_levels, upgrading=B.WALL)
        for building_type in BuildingType:
            assert (
                fortress.can_upgrade(building_type, UNLIMITED, UNLIMITED, UNLIMITED)
                is False
            )


# ═══════════════════════════════════════════════════════════════════════════
# Required Fortress Level Boundaries (parametrized)
# ═══════════════════════════════════════════════════════════════════════════

_BUILDINGS_WITH_FORTRESS_REQUIREMENT = [
    (bt, lvl) for bt, lvl in REQUIRED_FORTRESS_LEVEL.items() if lvl > 0
]


class TestRequiredFortressLevelBoundaries:
    @pytest.mark.parametrize(
        "building,required_level", _BUILDINGS_WITH_FORTRESS_REQUIREMENT
    )
    def test_one_below_required_fortress_level_blocks_upgrade(
        self, building: BuildingType, required_level: int
    ):
        building_levels = levels(FORTRESS=required_level - 1)
        fortress = make_fortress(building_levels=building_levels)
        assert fortress.can_upgrade(building, UNLIMITED, UNLIMITED, UNLIMITED) is False

    @pytest.mark.parametrize(
        "building,required_level", _BUILDINGS_WITH_FORTRESS_REQUIREMENT
    )
    def test_at_required_fortress_level_allows_upgrade(
        self, building: BuildingType, required_level: int
    ):
        building_levels = levels(FORTRESS=required_level)
        fortress = make_fortress(building_levels=building_levels)
        assert fortress.can_upgrade(building, UNLIMITED, UNLIMITED, UNLIMITED) is True


# ═══════════════════════════════════════════════════════════════════════════
# Fortress Level Cap Boundaries (parametrized)
# ═══════════════════════════════════════════════════════════════════════════

_CAPPED_BUILDINGS = [
    bt for bt in BuildingType if bt != B.FORTRESS and bt not in UNCAPPED_BY_FORTRESS
]


class TestFortressLevelCapBoundaries:
    @pytest.mark.parametrize("capped_building", _CAPPED_BUILDINGS)
    def test_building_at_fortress_level_is_capped(self, capped_building: BuildingType):
        required = REQUIRED_FORTRESS_LEVEL.get(capped_building, 0)
        fortress_level = max(required, 5)
        building_levels = levels(FORTRESS=fortress_level)
        building_levels[capped_building] = fortress_level
        fortress = make_fortress(building_levels=building_levels)
        assert (
            fortress.can_upgrade(capped_building, UNLIMITED, UNLIMITED, UNLIMITED)
            is False
        )

    @pytest.mark.parametrize("capped_building", _CAPPED_BUILDINGS)
    def test_building_one_below_fortress_level_is_not_capped(
        self, capped_building: BuildingType
    ):
        required = REQUIRED_FORTRESS_LEVEL.get(capped_building, 0)
        fortress_level = max(required, 5)
        building_levels = levels(FORTRESS=fortress_level)
        building_levels[capped_building] = fortress_level - 1
        fortress = make_fortress(building_levels=building_levels)
        assert (
            fortress.can_upgrade(capped_building, UNLIMITED, UNLIMITED, UNLIMITED)
            is True
        )


# ═══════════════════════════════════════════════════════════════════════════
# Resource Boundary Conditions
# ═══════════════════════════════════════════════════════════════════════════


class TestResourceBoundaryConditions:
    def test_exact_resources_allows_can_upgrade(self):
        building_levels = levels(FORTRESS=5)
        costs = {bt: (0, 50, 100, 200) for bt in BuildingType}
        fortress = make_fortress(building_levels=building_levels, building_costs=costs)
        assert fortress.can_upgrade(B.WOODCUTTER, 100, 200, 50) is True

    def test_one_wood_short_blocks_can_upgrade(self):
        building_levels = levels(FORTRESS=5)
        costs = {bt: (0, 50, 100, 200) for bt in BuildingType}
        fortress = make_fortress(building_levels=building_levels, building_costs=costs)
        assert fortress.can_upgrade(B.WOODCUTTER, 99, 200, 50) is False

    def test_one_stone_short_blocks_can_upgrade(self):
        building_levels = levels(FORTRESS=5)
        costs = {bt: (0, 50, 100, 200) for bt in BuildingType}
        fortress = make_fortress(building_levels=building_levels, building_costs=costs)
        assert fortress.can_upgrade(B.WOODCUTTER, 100, 199, 50) is False

    def test_one_silver_short_blocks_can_upgrade(self):
        building_levels = levels(FORTRESS=5)
        costs = {bt: (0, 50, 100, 200) for bt in BuildingType}
        fortress = make_fortress(building_levels=building_levels, building_costs=costs)
        assert fortress.can_upgrade(B.WOODCUTTER, 100, 200, 49) is False

    def test_expensive_first_candidate_blocks_cheaper_second(self):
        building_levels = levels(
            FORTRESS=10,
            LABORERS_QUARTERS=3,
            WOODCUTTER=3,
            QUARRY=4,
            BARRACKS=4,
            GEM_MINE=1,
        )
        costs = expensive_costs()
        costs[B.WOODCUTTER] = (0, 0, 0, 0)
        costs[B.QUARRY] = (0, 0, 0, 0)
        fortress = make_fortress(building_levels=building_levels, building_costs=costs)
        # LQ at level 3 is first candidate (lowest idx at same level), too expensive → stop
        assert fortress.pick_upgrade(100, 100, 100) is None

    def test_hok_exact_cost_boundary(self):
        hok_cost = (0, 100, 200, 300)
        fortress = make_fortress(
            building_levels=levels(FORTRESS=10), hok_level=5, hok_cost=hok_cost
        )
        assert fortress.can_upgrade_hok(200, 300, 100) is True
        assert fortress.can_upgrade_hok(200, 300, 99) is False
