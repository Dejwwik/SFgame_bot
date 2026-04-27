from sfbot.underworld.constants import (
    BUILD_QUEUE,
    MAX_BUILDING_LEVEL,
    BuildingType,
)
from sfbot.underworld.tests.conftest import (
    QUEUE_TARGET,
    UNLIMITED,
    B,
    all_at_max,
    all_at_zero,
    expensive_costs,
    levels,
    make_underworld,
    pick_upgrade,
    run_full_progression,
)

# ═══════════════════════════════════════════════════════════════════════════
# Fresh Start Progression (Stage-by-Stage)
# ═══════════════════════════════════════════════════════════════════════════


class TestFreshStartProgression:
    def test_all_buildings_at_zero_picks_heart_first(self):
        assert pick_upgrade(all_at_zero()) == B.HEART_OF_DARKNESS

    def test_heart_at_1_picks_soul_extractor(self):
        building_levels = levels(HEART_OF_DARKNESS=1)
        assert pick_upgrade(building_levels) == B.SOUL_EXTRACTOR

    def test_heart_and_extractor_at_1_picks_goblin_pit(self):
        building_levels = levels(HEART_OF_DARKNESS=1, SOUL_EXTRACTOR=1)
        assert pick_upgrade(building_levels) == B.GOBLIN_PIT

    def test_stage1_complete_advances_to_stage2_picks_heart_when_gate_capped(self):
        building_levels = levels(HEART_OF_DARKNESS=1, SOUL_EXTRACTOR=1, GOBLIN_PIT=1)
        # Gate requires Heart=2, so Heart must be upgraded first
        assert pick_upgrade(building_levels) == B.HEART_OF_DARKNESS

    def test_stage2_picks_lowest_level_building_first(self):
        building_levels = levels(
            HEART_OF_DARKNESS=3, SOUL_EXTRACTOR=2, GOBLIN_PIT=1, GATE=1
        )
        assert pick_upgrade(building_levels) == B.TORTURE_CHAMBER

    def test_stage2_complete_advances_to_stage3_keeper(self):
        building_levels = levels(
            HEART_OF_DARKNESS=5,
            SOUL_EXTRACTOR=5,
            GATE=5,
            TORTURE_CHAMBER=5,
            GOBLIN_PIT=1,
        )
        assert pick_upgrade(building_levels) == B.KEEPER

    def test_stage3_keeper_and_troll_at_1_advances_to_stage4(self):
        building_levels = levels(
            HEART_OF_DARKNESS=5,
            SOUL_EXTRACTOR=5,
            GATE=5,
            TORTURE_CHAMBER=5,
            GOBLIN_PIT=1,
            KEEPER=1,
            TROLL_BLOCK=1,
        )
        # Keeper at 1 is lowest in stage 4 and under Heart cap (5)
        assert pick_upgrade(building_levels) == B.KEEPER


# ═══════════════════════════════════════════════════════════════════════════
# Heart Gate Logic
# ═══════════════════════════════════════════════════════════════════════════


class TestHeartGate:
    def test_building_at_heart_level_falls_back_to_heart(self):
        building_levels = levels(
            HEART_OF_DARKNESS=5,
            SOUL_EXTRACTOR=5,
            GATE=5,
            TORTURE_CHAMBER=5,
            GOBLIN_PIT=1,
            KEEPER=5,
            TROLL_BLOCK=1,
        )
        # Stage 4 wants all to 10, but everything is capped at Heart=5
        # Should fall back to Heart
        assert pick_upgrade(building_levels) == B.HEART_OF_DARKNESS

    def test_gold_pit_is_uncapped_by_heart(self):
        building_levels = levels(HEART_OF_DARKNESS=15, GOLD_PIT=50)
        uw = make_underworld(building_levels=building_levels)
        # Gold Pit level 50 > Heart=15 but should still be upgradeable
        assert uw.can_upgrade(B.GOLD_PIT, UNLIMITED, UNLIMITED) is True

    def test_soul_extractor_capped_at_heart_level(self):
        building_levels = levels(HEART_OF_DARKNESS=5, SOUL_EXTRACTOR=5)
        uw = make_underworld(building_levels=building_levels)
        assert uw.can_upgrade(B.SOUL_EXTRACTOR, UNLIMITED, UNLIMITED) is False


# ═══════════════════════════════════════════════════════════════════════════
# Resource Gating
# ═══════════════════════════════════════════════════════════════════════════


class TestResourceGating:
    def test_no_resources_returns_none(self):
        uw = make_underworld(
            building_levels=all_at_zero(), building_costs=expensive_costs()
        )
        assert uw.pick_upgrade(0, 0) is None

    def test_expensive_costs_block_upgrade(self):
        uw = make_underworld(
            building_levels=all_at_zero(), building_costs=expensive_costs()
        )
        assert uw.pick_upgrade(100, 100) is None

    def test_already_upgrading_returns_none(self):
        uw = make_underworld(
            building_levels=all_at_zero(), upgrading=B.HEART_OF_DARKNESS
        )
        assert uw.pick_upgrade(UNLIMITED, UNLIMITED) is None


# ═══════════════════════════════════════════════════════════════════════════
# Full Progression
# ═══════════════════════════════════════════════════════════════════════════


class TestFullProgression:
    def test_full_run_reaches_queue_targets(self):
        uw = run_full_progression()
        for bt, target in QUEUE_TARGET.items():
            assert uw.building_level(bt) >= target, (
                f"{bt.name} should be at least {target}, got {uw.building_level(bt)}"
            )

    def test_full_run_gold_pit_reaches_100(self):
        uw = run_full_progression()
        assert uw.building_level(B.GOLD_PIT) == 100

    def test_all_at_max_pick_upgrade_returns_none(self):
        assert pick_upgrade(all_at_max()) is None


# ═══════════════════════════════════════════════════════════════════════════
# BUILD_QUEUE Integrity
# ═══════════════════════════════════════════════════════════════════════════


class TestBuildQueueIntegrity:
    def test_all_buildings_appear_in_queue(self):
        buildings_in_queue: set[BuildingType] = set()
        for _, buildings in BUILD_QUEUE:
            buildings_in_queue.update(buildings)
        for bt in BuildingType:
            assert bt in buildings_in_queue, f"{bt.name} missing from BUILD_QUEUE"

    def test_no_duplicate_buildings_within_a_stage(self):
        for target, buildings in BUILD_QUEUE:
            assert len(buildings) == len(set(buildings)), (
                f"Duplicate in stage target={target}"
            )

    def test_target_levels_within_max(self):
        for target, buildings in BUILD_QUEUE:
            for b in buildings:
                assert target <= MAX_BUILDING_LEVEL[b], (
                    f"{b.name} target={target} exceeds max={MAX_BUILDING_LEVEL[b]}"
                )
