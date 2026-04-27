import pytest

from sfbot.fortress.fortress import (
    MAX_BUILDING_LEVEL,
    REQUIRED_FORTRESS_LEVEL,
    UNCAPPED_BY_FORTRESS,
    BuildingType,
    Fortress,
)
from sfbot.fortress.tests.conftest import (
    ENDGAME_ONLY_GEM_MINE_LEFT,
    QUEUE_TARGET,
    STAGE1_BUILDINGS,
    STAGE1_COMPLETE,
    STAGE2_COMPLETE,
    STAGE3_COMPLETE,
    STAGES_1_TO_7_COMPLETE,
    STAGES_1_TO_8_COMPLETE,
    UNLIMITED,
    B,
    all_at_max,
    all_at_queue_target,
    all_at_zero,
    expensive_costs,
    levels,
    make_fortress,
    pick_upgrade,
)

# ═══════════════════════════════════════════════════════════════════════════
# Fresh Start Progression (Stage-by-Stage)
# ═══════════════════════════════════════════════════════════════════════════


class TestFreshStartProgression:
    def test_all_buildings_at_zero_picks_fortress_first(self):
        assert pick_upgrade(all_at_zero()) == B.FORTRESS

    def test_only_fortress_at_1_picks_laborers_quarters_next(self):
        building_levels = levels(FORTRESS=1)
        assert pick_upgrade(building_levels) == B.LABORERS_QUARTERS

    def test_fortress_and_lq_at_1_picks_woodcutter_next(self):
        building_levels = levels(FORTRESS=1, LABORERS_QUARTERS=1)
        assert pick_upgrade(building_levels) == B.WOODCUTTER

    def test_stage1_complete_except_gemmine_falls_back_to_fortress_since_gemmine_needs_fortress_3(
        self,
    ):
        building_levels = levels(
            FORTRESS=1, LABORERS_QUARTERS=1, WOODCUTTER=1, QUARRY=1, BARRACKS=1
        )
        assert pick_upgrade(building_levels) == B.FORTRESS

    def test_stage1_gemmine_becomes_available_once_fortress_reaches_3(self):
        building_levels = levels(
            FORTRESS=3, LABORERS_QUARTERS=1, WOODCUTTER=1, QUARRY=1, BARRACKS=1
        )
        assert pick_upgrade(building_levels) == B.GEM_MINE

    def test_stage1_complete_advances_to_stage2_starting_with_fortress(self):
        assert pick_upgrade(STAGE1_COMPLETE) == B.FORTRESS

    def test_stage2_all_at_3_picks_fortress_as_first_in_list(self):
        building_levels = levels(
            FORTRESS=3,
            LABORERS_QUARTERS=3,
            WOODCUTTER=3,
            QUARRY=3,
            BARRACKS=3,
            GEM_MINE=1,
        )
        assert pick_upgrade(building_levels) == B.FORTRESS

    def test_stage2_complete_advances_to_stage3_picking_fortress(self):
        assert pick_upgrade(STAGE2_COMPLETE) == B.FORTRESS

    def test_stage3_complete_advances_to_stage4_picking_fortress(self):
        assert pick_upgrade(STAGE3_COMPLETE) == B.FORTRESS

    def test_stage4_fortress_ahead_of_lq_picks_lower_level_lq(self):
        building_levels = levels(
            FORTRESS=8,
            LABORERS_QUARTERS=6,
            WOODCUTTER=5,
            QUARRY=5,
            BARRACKS=6,
            GEM_MINE=1,
        )
        assert pick_upgrade(building_levels) == B.LABORERS_QUARTERS


# ═══════════════════════════════════════════════════════════════════════════
# Out-of-Order / Bad Sequences
# ═══════════════════════════════════════════════════════════════════════════


class TestOutOfOrderSequences:
    # --- Gem Mine ahead of schedule ---

    def test_gem_mine_at_100_fortress_at_1_resumes_core_upgrades(self):
        building_levels = levels(
            FORTRESS=1,
            GEM_MINE=100,
            LABORERS_QUARTERS=1,
            WOODCUTTER=1,
            QUARRY=1,
            BARRACKS=1,
        )
        assert pick_upgrade(building_levels) == B.FORTRESS

    def test_gem_mine_at_50_fortress_at_3_picks_lowest_stage2_building(self):
        building_levels = levels(
            FORTRESS=3,
            GEM_MINE=50,
            LABORERS_QUARTERS=1,
            WOODCUTTER=1,
            QUARRY=1,
            BARRACKS=1,
        )
        assert pick_upgrade(building_levels) == B.LABORERS_QUARTERS

    # --- Treasury ahead of schedule ---

    def test_treasury_at_45_fortress_at_5_continues_normal_stage3(self):
        building_levels = dict(STAGE2_COMPLETE)
        building_levels[B.TREASURY] = 45
        assert pick_upgrade(building_levels) == B.FORTRESS

    # --- Smithy maxed before its stage ---

    def test_smithy_at_20_with_stage2_complete_continues_stage3(self):
        building_levels = dict(STAGE2_COMPLETE)
        building_levels[B.SMITHY] = 20
        assert pick_upgrade(building_levels) == B.FORTRESS

    # --- Barracks ahead ---

    def test_barracks_maxed_at_15_gemmine_blocked_falls_back_to_fortress(self):
        building_levels = levels(
            FORTRESS=1,
            LABORERS_QUARTERS=1,
            WOODCUTTER=1,
            QUARRY=1,
            BARRACKS=15,
            GEM_MINE=0,
        )
        assert pick_upgrade(building_levels) == B.FORTRESS

    def test_barracks_maxed_at_15_satisfies_stage3_barracks_requirement(self):
        building_levels = dict(STAGE2_COMPLETE)
        building_levels[B.BARRACKS] = 15
        assert pick_upgrade(building_levels) == B.FORTRESS

    # --- LQ maxed early ---

    def test_lq_at_15_with_stage2_done_picks_fortress_for_stage3(self):
        building_levels = dict(STAGE2_COMPLETE)
        building_levels[B.LABORERS_QUARTERS] = 15
        assert pick_upgrade(building_levels) == B.FORTRESS

    # --- Academy maxed early ---

    def test_academy_at_20_with_treasury_at_0_picks_treasury(self):
        building_levels = dict(STAGES_1_TO_7_COMPLETE)
        building_levels[B.ACADEMY] = 20
        building_levels[B.TREASURY] = 0
        assert pick_upgrade(building_levels) == B.TREASURY

    # --- Wall / Archery / Mages ahead ---

    def test_wall_at_20_moves_to_archery_and_mages_stage(self):
        building_levels = dict(ENDGAME_ONLY_GEM_MINE_LEFT)
        building_levels[B.GEM_MINE] = 30
        building_levels[B.WALL] = 20
        building_levels[B.ARCHERY_GUILD] = 0
        building_levels[B.MAGES_TOWER] = 0
        result = pick_upgrade(building_levels)
        assert result in (B.ARCHERY_GUILD, B.MAGES_TOWER)

    def test_archery_and_mages_maxed_advances_to_final_gem_mine_stage(self):
        building_levels = dict(ENDGAME_ONLY_GEM_MINE_LEFT)
        building_levels[B.GEM_MINE] = 30
        assert pick_upgrade(building_levels) == B.GEM_MINE

    # --- Fortress at various mid-game levels ---

    def test_fortress_at_10_lq_never_built_picks_lq(self):
        building_levels = levels(FORTRESS=10, GEM_MINE=1)
        assert pick_upgrade(building_levels) == B.LABORERS_QUARTERS

    def test_fortress_at_20_all_others_zero_picks_lq(self):
        building_levels = levels(FORTRESS=20)
        assert pick_upgrade(building_levels) == B.LABORERS_QUARTERS

    def test_fortress_at_1_others_at_5_picks_fortress_as_lowest(self):
        building_levels = {bt: 5 for bt in BuildingType}
        building_levels[B.FORTRESS] = 1
        assert pick_upgrade(building_levels) == B.FORTRESS

    # --- Mid-game states ---

    def test_stages_1_to_7_done_picks_academy_as_lowest_in_stage8(self):
        result = pick_upgrade(STAGES_1_TO_7_COMPLETE)
        assert result == B.ACADEMY

    def test_stage8_treasury_lower_than_academy_picks_treasury(self):
        building_levels = dict(STAGES_1_TO_7_COMPLETE)
        building_levels[B.ACADEMY] = 5
        building_levels[B.TREASURY] = 3
        building_levels[B.BARRACKS] = 10
        assert pick_upgrade(building_levels) == B.TREASURY

    # --- Everything maxed except one ---

    def test_only_gem_mine_remaining_picks_gem_mine(self):
        building_levels = all_at_max()
        building_levels[B.GEM_MINE] = 50
        assert pick_upgrade(building_levels) == B.GEM_MINE

    def test_only_wall_remaining_picks_wall(self):
        building_levels = all_at_max()
        building_levels[B.WALL] = 10
        assert pick_upgrade(building_levels) == B.WALL

    def test_only_smithy_remaining_picks_smithy(self):
        building_levels = all_at_max()
        building_levels[B.SMITHY] = 5
        assert pick_upgrade(building_levels) == B.SMITHY

    def test_only_treasury_remaining_picks_treasury(self):
        building_levels = all_at_max()
        building_levels[B.TREASURY] = 20
        assert pick_upgrade(building_levels) == B.TREASURY

    def test_only_lq_remaining_picks_lq(self):
        building_levels = all_at_max()
        building_levels[B.LABORERS_QUARTERS] = 10
        assert pick_upgrade(building_levels) == B.LABORERS_QUARTERS

    def test_only_fortress_remaining_picks_fortress(self):
        building_levels = all_at_max()
        building_levels[B.FORTRESS] = 15
        assert pick_upgrade(building_levels) == B.FORTRESS

    # --- Specific bad combos ---

    def test_quarry_maxed_wc_zero_but_lq_also_zero_picks_lq_first(self):
        building_levels = levels(FORTRESS=20, QUARRY=20, WOODCUTTER=0)
        assert pick_upgrade(building_levels) == B.LABORERS_QUARTERS

    def test_wc_maxed_quarry_zero_but_lq_also_zero_picks_lq_first(self):
        building_levels = levels(FORTRESS=20, WOODCUTTER=20, QUARRY=0)
        assert pick_upgrade(building_levels) == B.LABORERS_QUARTERS

    def test_only_woodcutter_missing_in_stage1_picks_woodcutter(self):
        building_levels = levels(
            FORTRESS=20,
            LABORERS_QUARTERS=15,
            WOODCUTTER=0,
            QUARRY=20,
            BARRACKS=15,
            GEM_MINE=100,
        )
        assert pick_upgrade(building_levels) == B.WOODCUTTER

    def test_only_quarry_missing_in_stage1_picks_quarry(self):
        building_levels = levels(
            FORTRESS=20,
            LABORERS_QUARTERS=15,
            WOODCUTTER=20,
            QUARRY=0,
            BARRACKS=15,
            GEM_MINE=100,
        )
        assert pick_upgrade(building_levels) == B.QUARRY

    def test_only_barracks_missing_with_high_fortress_picks_barracks(self):
        building_levels = levels(
            FORTRESS=20,
            LABORERS_QUARTERS=15,
            WOODCUTTER=20,
            QUARRY=20,
            BARRACKS=0,
            GEM_MINE=1,
        )
        assert pick_upgrade(building_levels) == B.BARRACKS

    def test_gemmine_done_but_smithy_at_0_picks_smithy(self):
        building_levels = levels(
            FORTRESS=15,
            LABORERS_QUARTERS=15,
            WOODCUTTER=5,
            QUARRY=5,
            BARRACKS=6,
            GEM_MINE=10,
            WALL=1,
            ARCHERY_GUILD=1,
            MAGES_TOWER=1,
            SMITHY=0,
        )
        assert pick_upgrade(building_levels) == B.SMITHY

    def test_academy_and_treasury_both_maxed_skips_to_stage9(self):
        building_levels = dict(STAGES_1_TO_7_COMPLETE)
        building_levels[B.ACADEMY] = 20
        building_levels[B.TREASURY] = 45
        building_levels[B.BARRACKS] = 15
        assert pick_upgrade(building_levels) == B.FORTRESS

    def test_fortress_maxed_lq_at_12_picks_lq_for_stage9(self):
        building_levels = dict(STAGES_1_TO_7_COMPLETE)
        building_levels[B.FORTRESS] = 20
        building_levels[B.LABORERS_QUARTERS] = 12
        building_levels[B.ACADEMY] = 20
        building_levels[B.TREASURY] = 45
        building_levels[B.BARRACKS] = 15
        assert pick_upgrade(building_levels) == B.LABORERS_QUARTERS

    def test_uncapped_gem_mine_and_treasury_far_ahead_still_follows_stage3(self):
        building_levels = dict(STAGE2_COMPLETE)
        building_levels[B.GEM_MINE] = 80
        building_levels[B.TREASURY] = 40
        building_levels[B.SMITHY] = 15
        assert pick_upgrade(building_levels) == B.FORTRESS

    def test_military_buildings_maxed_but_early_buildings_low_picks_woodcutter(self):
        building_levels = levels(
            FORTRESS=7,
            LABORERS_QUARTERS=5,
            WOODCUTTER=3,
            QUARRY=3,
            BARRACKS=15,
            GEM_MINE=1,
            WALL=20,
            ARCHERY_GUILD=15,
            MAGES_TOWER=15,
            SMITHY=20,
        )
        assert pick_upgrade(building_levels) == B.WOODCUTTER

    def test_only_academy_behind_in_stage8_picks_academy(self):
        building_levels = dict(STAGES_1_TO_7_COMPLETE)
        building_levels[B.ACADEMY] = 3
        building_levels[B.TREASURY] = 10
        building_levels[B.BARRACKS] = 10
        assert pick_upgrade(building_levels) == B.ACADEMY

    def test_only_treasury_behind_in_stage8_picks_treasury(self):
        building_levels = dict(STAGES_1_TO_7_COMPLETE)
        building_levels[B.ACADEMY] = 10
        building_levels[B.TREASURY] = 7
        building_levels[B.BARRACKS] = 10
        assert pick_upgrade(building_levels) == B.TREASURY


# ═══════════════════════════════════════════════════════════════════════════
# Full Progression Simulation
# ═══════════════════════════════════════════════════════════════════════════


class TestFullProgressionSimulation:
    def test_progression_completes_without_stalling(
        self, completed_progression: Fortress
    ):
        for building_type in BuildingType:
            assert (
                completed_progression.building_level(building_type)
                >= QUEUE_TARGET[building_type]
            ), (
                f"{building_type.name} at {completed_progression.building_level(building_type)}, "
                f"expected {QUEUE_TARGET[building_type]}"
            )

    def test_total_upgrades_equals_sum_of_queue_targets(self):
        fortress = make_fortress(building_levels=all_at_zero())
        upgrade_count = 0
        for _ in range(2000):
            building = fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED)
            if building is None:
                break
            fortress.building_levels[building] = fortress.building_level(building) + 1
            upgrade_count += 1
        expected_total = sum(QUEUE_TARGET.values())
        assert upgrade_count == expected_total

    def test_capped_buildings_never_exceed_fortress_during_progression(self):
        fortress = make_fortress(building_levels=all_at_zero())
        for _ in range(2000):
            building = fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED)
            if building is None:
                break
            fortress.building_levels[building] = fortress.building_level(building) + 1
            for building_type in BuildingType:
                if building_type == B.FORTRESS or building_type in UNCAPPED_BY_FORTRESS:
                    continue
                assert (
                    fortress.building_level(building_type) <= fortress.fortress_level
                ), (
                    f"After upgrading {building.name}: {building_type.name} at "
                    f"{fortress.building_level(building_type)} > Fortress at "
                    f"{fortress.fortress_level}"
                )

    def test_required_fortress_levels_always_met_before_upgrade(self):
        fortress = make_fortress(building_levels=all_at_zero())
        for _ in range(2000):
            building = fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED)
            if building is None:
                break
            required = REQUIRED_FORTRESS_LEVEL.get(building, 0)
            assert fortress.fortress_level >= required, (
                f"Upgrading {building.name} with Fortress at "
                f"{fortress.fortress_level}, but requires {required}"
            )
            fortress.building_levels[building] = fortress.building_level(building) + 1


# ═══════════════════════════════════════════════════════════════════════════
# Partially Affordable Stages
# ═══════════════════════════════════════════════════════════════════════════


class TestPartiallyAffordableStages:
    def test_only_quarry_affordable_but_lq_blocks(self):
        building_levels = levels(
            FORTRESS=5,
            LABORERS_QUARTERS=1,
            WOODCUTTER=1,
            QUARRY=1,
            BARRACKS=1,
            GEM_MINE=1,
        )
        costs = expensive_costs()
        costs[B.QUARRY] = (0, 0, 0, 0)
        fortress = make_fortress(building_levels=building_levels, building_costs=costs)
        # LQ is first candidate (lowest idx at same level), too expensive → stop
        assert fortress.pick_upgrade(100, 100, 100) is None

    def test_only_lq_affordable_in_stage2_picks_lq(self):
        building_levels = levels(
            FORTRESS=2,
            LABORERS_QUARTERS=1,
            WOODCUTTER=1,
            QUARRY=1,
            BARRACKS=1,
            GEM_MINE=1,
        )
        costs = expensive_costs()
        costs[B.LABORERS_QUARTERS] = (0, 0, 0, 0)
        fortress = make_fortress(building_levels=building_levels, building_costs=costs)
        assert fortress.pick_upgrade(100, 100, 100) == B.LABORERS_QUARTERS

    def test_lowest_level_building_too_expensive_stops(self):
        building_levels = levels(
            FORTRESS=5,
            LABORERS_QUARTERS=2,
            WOODCUTTER=3,
            QUARRY=3,
            BARRACKS=3,
            GEM_MINE=1,
        )
        costs = expensive_costs()
        costs[B.WOODCUTTER] = (0, 0, 0, 0)
        fortress = make_fortress(building_levels=building_levels, building_costs=costs)
        # LQ at level 2 is first candidate (lowest level), too expensive → stop
        assert fortress.pick_upgrade(100, 100, 100) is None

    def test_lowest_level_building_affordable_picks_it(self):
        building_levels = levels(
            FORTRESS=5,
            LABORERS_QUARTERS=2,
            WOODCUTTER=3,
            QUARRY=3,
            BARRACKS=3,
            GEM_MINE=1,
        )
        costs = expensive_costs()
        costs[B.LABORERS_QUARTERS] = (0, 0, 0, 0)
        fortress = make_fortress(building_levels=building_levels, building_costs=costs)
        assert fortress.pick_upgrade(100, 100, 100) == B.LABORERS_QUARTERS

    def test_no_candidate_affordable_but_fortress_is_falls_back(self):
        costs = expensive_costs()
        costs[B.FORTRESS] = (0, 0, 0, 0)
        fortress = make_fortress(building_levels=STAGE2_COMPLETE, building_costs=costs)
        assert fortress.pick_upgrade(100, 100, 100) == B.FORTRESS


# ═══════════════════════════════════════════════════════════════════════════
# Stage Skipping
# ═══════════════════════════════════════════════════════════════════════════


class TestStageSkipping:
    def test_completed_early_stages_skip_to_first_incomplete(self):
        building_levels = levels(
            FORTRESS=20,
            LABORERS_QUARTERS=15,
            WOODCUTTER=5,
            QUARRY=5,
            BARRACKS=6,
            GEM_MINE=10,
            WALL=1,
            ARCHERY_GUILD=1,
            MAGES_TOWER=1,
            SMITHY=9,
            ACADEMY=0,
        )
        result = pick_upgrade(building_levels)
        assert result in (B.ACADEMY, B.TREASURY, B.BARRACKS)

    def test_all_queue_targets_met_returns_none(
        self, completed_queue_fortress: Fortress
    ):
        assert (
            completed_queue_fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED)
            is None
        )

    def test_only_last_stage_incomplete_picks_gem_mine(self):
        building_levels = all_at_queue_target()
        building_levels[B.GEM_MINE] = 50
        assert pick_upgrade(building_levels) == B.GEM_MINE

    def test_f2p_buildings_at_target_but_below_max_still_returns_none(self):
        building_levels = all_at_queue_target()
        assert pick_upgrade(building_levels) is None


# ═══════════════════════════════════════════════════════════════════════════
# Candidate Ordering Within Stage
# ═══════════════════════════════════════════════════════════════════════════


class TestCandidateOrderingWithinStage:
    def test_tied_levels_pick_earlier_building_in_stage_list(self):
        building_levels = levels(
            FORTRESS=5,
            LABORERS_QUARTERS=3,
            WOODCUTTER=3,
            QUARRY=3,
            BARRACKS=3,
            GEM_MINE=1,
        )
        assert pick_upgrade(building_levels) == B.LABORERS_QUARTERS

    def test_lower_level_building_picked_even_if_later_in_list(self):
        building_levels = levels(
            FORTRESS=5,
            LABORERS_QUARTERS=4,
            WOODCUTTER=2,
            QUARRY=3,
            BARRACKS=3,
            GEM_MINE=1,
        )
        assert pick_upgrade(building_levels) == B.WOODCUTTER

    def test_stage4_tied_fortress_and_lq_picks_fortress_as_first(self):
        building_levels = levels(
            FORTRESS=6,
            LABORERS_QUARTERS=6,
            WOODCUTTER=5,
            QUARRY=5,
            BARRACKS=6,
            GEM_MINE=1,
        )
        assert pick_upgrade(building_levels) == B.FORTRESS

    def test_stage8_all_tied_at_6_picks_academy_as_first_in_list(self):
        building_levels = dict(STAGES_1_TO_7_COMPLETE)
        building_levels[B.ACADEMY] = 6
        building_levels[B.TREASURY] = 6
        assert pick_upgrade(building_levels) == B.ACADEMY


# ═══════════════════════════════════════════════════════════════════════════
# Fortress Fallback Mechanism
# ═══════════════════════════════════════════════════════════════════════════


class TestFortressFallbackMechanism:
    def test_lq_capped_at_fortress_level_triggers_fortress_fallback(self):
        building_levels = levels(
            FORTRESS=8,
            LABORERS_QUARTERS=8,
            WOODCUTTER=5,
            QUARRY=5,
            BARRACKS=6,
            GEM_MINE=1,
        )
        assert pick_upgrade(building_levels) == B.FORTRESS

    def test_fortress_maxed_and_candidate_too_expensive_returns_none(self):
        building_levels = levels(FORTRESS=20, LABORERS_QUARTERS=12)
        fortress = make_fortress(
            building_levels=building_levels, building_costs=expensive_costs()
        )
        assert fortress.pick_upgrade(100, 100, 100) is None

    def test_gem_mine_directly_upgradable_no_fallback_needed(self):
        building_levels = levels(
            FORTRESS=9,
            LABORERS_QUARTERS=10,
            WOODCUTTER=5,
            QUARRY=5,
            BARRACKS=6,
            GEM_MINE=0,
        )
        assert pick_upgrade(building_levels) == B.GEM_MINE

    def test_barracks_and_gemmine_both_blocked_falls_back_to_fortress(self):
        building_levels = levels(
            FORTRESS=2,
            LABORERS_QUARTERS=1,
            WOODCUTTER=1,
            QUARRY=1,
            BARRACKS=0,
            GEM_MINE=0,
        )
        assert pick_upgrade(building_levels) == B.FORTRESS

    def test_all_candidates_and_fortress_too_expensive_returns_none(self):
        fortress = make_fortress(
            building_levels=STAGE2_COMPLETE,
            building_costs=expensive_costs(),
        )
        assert fortress.pick_upgrade(100, 100, 100) is None


# ═══════════════════════════════════════════════════════════════════════════
# Specific Game-State Snapshots
# ═══════════════════════════════════════════════════════════════════════════


class TestGameStateSnapshots:
    def test_brand_new_fortress_picks_fortress(self):
        assert pick_upgrade(all_at_zero()) == B.FORTRESS

    def test_after_first_upgrade_picks_laborers_quarters(self):
        assert pick_upgrade(levels(FORTRESS=1)) == B.LABORERS_QUARTERS

    def test_stage1_only_quarry_at_zero_picks_quarry(self):
        building_levels = levels(
            FORTRESS=3,
            LABORERS_QUARTERS=1,
            WOODCUTTER=1,
            QUARRY=0,
            BARRACKS=1,
            GEM_MINE=1,
        )
        assert pick_upgrade(building_levels) == B.QUARRY

    def test_stage1_barracks_blocked_at_fortress_3_falls_back(self):
        building_levels = levels(
            FORTRESS=3,
            LABORERS_QUARTERS=1,
            WOODCUTTER=1,
            QUARRY=1,
            GEM_MINE=1,
        )
        assert pick_upgrade(building_levels) == B.LABORERS_QUARTERS

    def test_endgame_gem_mine_at_50_picks_gem_mine(self):
        building_levels = all_at_queue_target()
        building_levels[B.GEM_MINE] = 50
        assert pick_upgrade(building_levels) == B.GEM_MINE

    def test_endgame_wall_at_10_picks_wall_before_archery_mages(self):
        building_levels = all_at_queue_target()
        building_levels[B.WALL] = 10
        building_levels[B.ARCHERY_GUILD] = 5
        building_levels[B.MAGES_TOWER] = 5
        building_levels[B.GEM_MINE] = 100
        assert pick_upgrade(building_levels) == B.WALL

    def test_endgame_archery_at_5_mages_at_10_picks_lower_archery(self):
        building_levels = all_at_queue_target()
        building_levels[B.ARCHERY_GUILD] = 5
        building_levels[B.MAGES_TOWER] = 10
        building_levels[B.GEM_MINE] = 100
        assert pick_upgrade(building_levels) == B.ARCHERY_GUILD

    def test_endgame_mages_at_8_archery_at_12_picks_lower_mages(self):
        building_levels = all_at_queue_target()
        building_levels[B.ARCHERY_GUILD] = 12
        building_levels[B.MAGES_TOWER] = 8
        building_levels[B.GEM_MINE] = 100
        assert pick_upgrade(building_levels) == B.MAGES_TOWER

    def test_mid_stage10_smithy_at_5_picks_smithy(self):
        building_levels = levels(
            FORTRESS=15,
            LABORERS_QUARTERS=15,
            WOODCUTTER=5,
            QUARRY=5,
            BARRACKS=6,
            GEM_MINE=10,
            WALL=1,
            ARCHERY_GUILD=1,
            MAGES_TOWER=1,
            SMITHY=5,
        )
        assert pick_upgrade(building_levels) == B.SMITHY

    def test_stage9_fortress_14_lq_13_picks_lower_level_lq(self):
        building_levels = dict(STAGES_1_TO_8_COMPLETE)
        building_levels[B.FORTRESS] = 14
        building_levels[B.LABORERS_QUARTERS] = 13
        assert pick_upgrade(building_levels) == B.LABORERS_QUARTERS

    def test_stage10_fortress_at_18_picks_fortress(self):
        building_levels = dict(STAGES_1_TO_8_COMPLETE)
        building_levels[B.FORTRESS] = 18
        building_levels[B.LABORERS_QUARTERS] = 15
        assert pick_upgrade(building_levels) == B.FORTRESS


# ═══════════════════════════════════════════════════════════════════════════
# Mixed Ahead/Behind States
# ═══════════════════════════════════════════════════════════════════════════


class TestMixedAheadBehindStates:
    def test_gem_mine_at_100_smithy_at_0_picks_smithy(self):
        building_levels = levels(
            FORTRESS=15,
            LABORERS_QUARTERS=15,
            WOODCUTTER=5,
            QUARRY=5,
            BARRACKS=6,
            GEM_MINE=100,
            WALL=1,
            ARCHERY_GUILD=1,
            MAGES_TOWER=1,
            SMITHY=0,
        )
        assert pick_upgrade(building_levels) == B.SMITHY

    def test_treasury_maxed_academy_at_0_picks_academy(self):
        building_levels = dict(STAGES_1_TO_7_COMPLETE)
        building_levels[B.ACADEMY] = 0
        building_levels[B.TREASURY] = 45
        assert pick_upgrade(building_levels) == B.ACADEMY

    def test_wall_at_15_not_yet_maxed_picks_wall(self):
        building_levels = all_at_queue_target()
        building_levels[B.WALL] = 15
        building_levels[B.ARCHERY_GUILD] = 10
        building_levels[B.MAGES_TOWER] = 12
        building_levels[B.GEM_MINE] = 100
        assert pick_upgrade(building_levels) == B.WALL

    def test_wall_done_archery_behind_mages_picks_archery(self):
        building_levels = all_at_queue_target()
        building_levels[B.WALL] = 20
        building_levels[B.ARCHERY_GUILD] = 7
        building_levels[B.MAGES_TOWER] = 12
        building_levels[B.GEM_MINE] = 100
        assert pick_upgrade(building_levels) == B.ARCHERY_GUILD

    def test_barracks_queue_target_is_15_and_queue_complete_returns_none(self):
        building_levels = all_at_queue_target()
        assert building_levels[B.BARRACKS] == 15
        assert pick_upgrade(building_levels) is None

    def test_smithy_ahead_of_its_stage_skips_to_next(self):
        building_levels = levels(
            FORTRESS=10,
            LABORERS_QUARTERS=10,
            WOODCUTTER=5,
            QUARRY=5,
            BARRACKS=6,
            GEM_MINE=10,
            WALL=1,
            ARCHERY_GUILD=1,
            MAGES_TOWER=1,
            SMITHY=20,
        )
        assert pick_upgrade(building_levels) == B.FORTRESS

    def test_fortress_behind_lq_ahead_picks_fortress(self):
        building_levels = levels(
            FORTRESS=6,
            LABORERS_QUARTERS=12,
            WOODCUTTER=5,
            QUARRY=5,
            BARRACKS=6,
            GEM_MINE=1,
        )
        assert pick_upgrade(building_levels) == B.FORTRESS


# ═══════════════════════════════════════════════════════════════════════════
# Each Stage-1 Building Missing (parametrized)
# ═══════════════════════════════════════════════════════════════════════════


class TestEachStage1BuildingMissing:
    @pytest.mark.parametrize("missing_building", STAGE1_BUILDINGS)
    def test_single_stage1_building_at_zero_gets_picked(
        self, missing_building: BuildingType
    ):
        building_levels = {bt: 0 for bt in BuildingType}
        building_levels[B.FORTRESS] = 20
        for stage1_building in STAGE1_BUILDINGS:
            if stage1_building != B.FORTRESS:
                building_levels[stage1_building] = 1
        building_levels[missing_building] = 0
        fortress = make_fortress(building_levels=building_levels)
        result = fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED)
        assert result == missing_building


# ═══════════════════════════════════════════════════════════════════════════
# Single Building Maxed, Rest at Zero (parametrized)
# ═══════════════════════════════════════════════════════════════════════════


class TestSingleBuildingMaxedOthersAtZero:
    @pytest.mark.parametrize("maxed_building", list(BuildingType))
    def test_one_building_maxed_rest_zero_still_picks_something(
        self, maxed_building: BuildingType
    ):
        building_levels = all_at_zero()
        building_levels[maxed_building] = MAX_BUILDING_LEVEL[maxed_building]
        fortress = make_fortress(building_levels=building_levels)
        result = fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED)
        assert result is not None

    @pytest.mark.parametrize("maxed_building", list(BuildingType))
    def test_one_building_over_target_rest_at_target_still_complete(
        self, maxed_building: BuildingType
    ):
        building_levels = all_at_queue_target()
        building_levels[maxed_building] = MAX_BUILDING_LEVEL[maxed_building]
        assert pick_upgrade(building_levels) is None


# ═══════════════════════════════════════════════════════════════════════════
# Progression Invariants
# ═══════════════════════════════════════════════════════════════════════════


class TestProgressionInvariants:
    def test_no_building_ever_exceeds_its_queue_target(self):
        fortress = make_fortress(building_levels=all_at_zero())
        for _ in range(2000):
            building = fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED)
            if building is None:
                break
            fortress.building_levels[building] = fortress.building_level(building) + 1
            assert fortress.building_level(building) <= QUEUE_TARGET[building], (
                f"{building.name} at {fortress.building_level(building)} exceeds "
                f"queue target {QUEUE_TARGET[building]}"
            )

    def test_barracks_stops_at_level_15(self, completed_progression: Fortress):
        assert completed_progression.building_level(B.BARRACKS) == 15

    def test_woodcutter_stops_at_level_15(self, completed_progression: Fortress):
        assert completed_progression.building_level(B.WOODCUTTER) == 15

    def test_quarry_stops_at_level_15(self, completed_progression: Fortress):
        assert completed_progression.building_level(B.QUARRY) == 15

    def test_gem_mine_reaches_level_100(self, completed_progression: Fortress):
        assert completed_progression.building_level(B.GEM_MINE) == 100

    def test_fortress_reaches_level_20(self, completed_progression: Fortress):
        assert completed_progression.building_level(B.FORTRESS) == 20

    def test_smithy_reaches_9_before_academy_or_treasury_reach_10(self):
        fortress = make_fortress(building_levels=all_at_zero())
        smithy_reached_9 = False
        for _ in range(2000):
            building = fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED)
            if building is None:
                break
            fortress.building_levels[building] = fortress.building_level(building) + 1
            if fortress.building_level(B.SMITHY) >= 9:
                smithy_reached_9 = True
            if not smithy_reached_9:
                assert fortress.building_level(B.ACADEMY) < 10, (
                    "Academy reached 10 before Smithy reached 9"
                )
                assert fortress.building_level(B.TREASURY) < 10, (
                    "Treasury reached 10 before Smithy reached 9"
                )

    def test_gem_mine_reaches_10_before_smithy_starts(self):
        fortress = make_fortress(building_levels=all_at_zero())
        gem_mine_reached_10 = False
        for _ in range(2000):
            building = fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED)
            if building is None:
                break
            fortress.building_levels[building] = fortress.building_level(building) + 1
            if fortress.building_level(B.GEM_MINE) >= 10:
                gem_mine_reached_10 = True
            if not gem_mine_reached_10:
                assert fortress.building_level(B.SMITHY) < 1, (
                    "Smithy started before GemMine reached 10"
                )

    def test_lq_reaches_15_before_fortress_exceeds_15(self):
        fortress = make_fortress(building_levels=all_at_zero())
        for _ in range(2000):
            building = fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED)
            if building is None:
                break
            fortress.building_levels[building] = fortress.building_level(building) + 1
            if fortress.building_level(B.FORTRESS) > 15:
                assert fortress.building_level(B.LABORERS_QUARTERS) >= 15, (
                    f"Fortress at {fortress.building_level(B.FORTRESS)} but LQ at "
                    f"{fortress.building_level(B.LABORERS_QUARTERS)}"
                )

    def test_barracks_reaches_6_before_fortress_exceeds_6(self):
        fortress = make_fortress(building_levels=all_at_zero())
        for _ in range(2000):
            building = fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED)
            if building is None:
                break
            fortress.building_levels[building] = fortress.building_level(building) + 1
            if fortress.building_level(B.FORTRESS) > 6:
                assert fortress.building_level(B.BARRACKS) >= 6, (
                    f"Fortress at {fortress.building_level(B.FORTRESS)} but Barracks at "
                    f"{fortress.building_level(B.BARRACKS)}"
                )

    def test_barracks_reaches_10_before_academy_exceeds_10(self):
        fortress = make_fortress(building_levels=all_at_zero())
        for _ in range(2000):
            building = fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED)
            if building is None:
                break
            fortress.building_levels[building] = fortress.building_level(building) + 1
            if fortress.building_level(B.ACADEMY) > 10:
                assert fortress.building_level(B.BARRACKS) >= 10, (
                    f"Academy at {fortress.building_level(B.ACADEMY)} but Barracks at "
                    f"{fortress.building_level(B.BARRACKS)}"
                )


# ═══════════════════════════════════════════════════════════════════════════
# Barracks Progression Through Stages
# ═══════════════════════════════════════════════════════════════════════════


class TestBarracksProgressionThroughStages:
    # --- Stage 3: Barracks joins Fortress+LQ升to level 6 ---

    def test_stage3_barracks_at_5_with_fortress_and_lq_at_5_picks_fortress(self):
        building_levels = levels(
            FORTRESS=5,
            LABORERS_QUARTERS=5,
            WOODCUTTER=5,
            QUARRY=5,
            BARRACKS=5,
            GEM_MINE=1,
        )
        assert pick_upgrade(building_levels) == B.FORTRESS

    def test_stage3_fortress_at_6_lq_at_6_barracks_still_at_5_picks_barracks(self):
        building_levels = levels(
            FORTRESS=6,
            LABORERS_QUARTERS=6,
            WOODCUTTER=5,
            QUARRY=5,
            BARRACKS=5,
            GEM_MINE=1,
        )
        assert pick_upgrade(building_levels) == B.BARRACKS

    # --- Stage 8: Barracks joins Academy+Treasury to level 10 ---

    def test_stage8_barracks_at_6_is_lowest_picked_before_academy_at_8(self):
        building_levels = dict(STAGES_1_TO_7_COMPLETE)
        building_levels[B.ACADEMY] = 8
        building_levels[B.TREASURY] = 8
        assert pick_upgrade(building_levels) == B.BARRACKS

    def test_stage8_barracks_at_8_academy_at_7_picks_academy(self):
        building_levels = dict(STAGES_1_TO_7_COMPLETE)
        building_levels[B.BARRACKS] = 8
        building_levels[B.ACADEMY] = 7
        building_levels[B.TREASURY] = 9
        assert pick_upgrade(building_levels) == B.ACADEMY

    def test_stage8_academy_and_treasury_at_10_barracks_at_6_picks_barracks(self):
        building_levels = dict(STAGES_1_TO_7_COMPLETE)
        building_levels[B.ACADEMY] = 10
        building_levels[B.TREASURY] = 10
        assert pick_upgrade(building_levels) == B.BARRACKS

    def test_stage8_all_three_at_10_advances_to_stage9(self):
        building_levels = dict(STAGES_1_TO_7_COMPLETE)
        building_levels[B.ACADEMY] = 10
        building_levels[B.TREASURY] = 10
        building_levels[B.BARRACKS] = 10
        assert pick_upgrade(building_levels) == B.FORTRESS

    def test_stage8_barracks_at_9_academy_at_9_treasury_at_9_picks_academy_first_in_list(
        self,
    ):
        building_levels = dict(STAGES_1_TO_7_COMPLETE)
        building_levels[B.ACADEMY] = 9
        building_levels[B.TREASURY] = 9
        building_levels[B.BARRACKS] = 9
        assert pick_upgrade(building_levels) == B.ACADEMY

    def test_stage8_only_barracks_behind_at_7_picks_barracks(self):
        building_levels = dict(STAGES_1_TO_7_COMPLETE)
        building_levels[B.ACADEMY] = 10
        building_levels[B.TREASURY] = 10
        building_levels[B.BARRACKS] = 7
        assert pick_upgrade(building_levels) == B.BARRACKS

    # --- Stage 12: Barracks+Woodcutter+Quarry to level 15 (after Fortress=20) ---

    def test_stage12_after_fortress_20_barracks_at_10_picks_barracks(self):
        building_levels = dict(STAGES_1_TO_8_COMPLETE)
        building_levels[B.FORTRESS] = 20
        building_levels[B.LABORERS_QUARTERS] = 15
        building_levels[B.WOODCUTTER] = 15
        building_levels[B.QUARRY] = 15
        assert pick_upgrade(building_levels) == B.BARRACKS

    def test_stage12_barracks_at_14_picks_barracks(self):
        building_levels = dict(STAGES_1_TO_8_COMPLETE)
        building_levels[B.FORTRESS] = 20
        building_levels[B.LABORERS_QUARTERS] = 15
        building_levels[B.WOODCUTTER] = 15
        building_levels[B.QUARRY] = 15
        building_levels[B.BARRACKS] = 14
        assert pick_upgrade(building_levels) == B.BARRACKS

    def test_stage12_all_at_15_advances_to_academy_stage(self):
        building_levels = dict(STAGES_1_TO_8_COMPLETE)
        building_levels[B.FORTRESS] = 20
        building_levels[B.LABORERS_QUARTERS] = 15
        building_levels[B.WOODCUTTER] = 15
        building_levels[B.QUARRY] = 15
        building_levels[B.BARRACKS] = 15
        assert pick_upgrade(building_levels) == B.ACADEMY

    # --- Barracks already ahead of schedule ---

    def test_barracks_already_at_10_in_stage8_skips_to_academy_and_treasury(self):
        building_levels = dict(STAGES_1_TO_7_COMPLETE)
        building_levels[B.BARRACKS] = 10
        result = pick_upgrade(building_levels)
        assert result in (B.ACADEMY, B.TREASURY)

    def test_barracks_already_at_15_in_stage8_picks_lowest_academy_or_treasury(self):
        building_levels = dict(STAGES_1_TO_7_COMPLETE)
        building_levels[B.BARRACKS] = 15
        result = pick_upgrade(building_levels)
        assert result in (B.ACADEMY, B.TREASURY)

    def test_barracks_maxed_with_stage12_done_skips_to_academy(self):
        building_levels = dict(STAGES_1_TO_8_COMPLETE)
        building_levels[B.FORTRESS] = 20
        building_levels[B.LABORERS_QUARTERS] = 15
        building_levels[B.WOODCUTTER] = 15
        building_levels[B.QUARRY] = 15
        building_levels[B.BARRACKS] = 15
        assert pick_upgrade(building_levels) == B.ACADEMY
