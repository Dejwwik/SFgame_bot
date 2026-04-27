from sfbot.fortress.fortress import (
    BUILD_QUEUE,
    MAX_BUILDING_LEVEL,
    REQUIRED_FORTRESS_LEVEL,
    BuildingType,
)
from sfbot.fortress.tests.conftest import QUEUE_TARGET, B

# ═══════════════════════════════════════════════════════════════════════════
# BUILD_QUEUE Structural Integrity
# ═══════════════════════════════════════════════════════════════════════════


class TestBuildQueueStructuralIntegrity:
    def test_every_queue_building_has_a_max_level_entry(self):
        for target_level, buildings_in_stage in BUILD_QUEUE:
            for building in buildings_in_stage:
                assert building in MAX_BUILDING_LEVEL, (
                    f"{building.name} missing from MAX_BUILDING_LEVEL"
                )

    def test_no_stage_target_exceeds_building_max_level(self):
        for target_level, buildings_in_stage in BUILD_QUEUE:
            for building in buildings_in_stage:
                assert target_level <= MAX_BUILDING_LEVEL[building], (
                    f"Stage targets {building.name} at {target_level}, "
                    f"but max is {MAX_BUILDING_LEVEL[building]}"
                )

    def test_every_building_type_appears_in_queue_at_least_once(self):
        buildings_in_queue = set()
        for _, buildings_in_stage in BUILD_QUEUE:
            buildings_in_queue.update(buildings_in_stage)
        for building_type in BuildingType:
            assert building_type in buildings_in_queue, (
                f"{building_type.name} never appears in BUILD_QUEUE"
            )

    def test_highest_queue_target_matches_queue_target_dict(self):
        highest_target: dict[BuildingType, int] = {}
        for target_level, buildings_in_stage in BUILD_QUEUE:
            for building in buildings_in_stage:
                highest_target[building] = max(
                    highest_target.get(building, 0), target_level
                )
        for building_type in BuildingType:
            assert (
                highest_target.get(building_type, 0) == QUEUE_TARGET[building_type]
            ), (
                f"{building_type.name}: queue reaches "
                f"{highest_target.get(building_type, 0)}, expected "
                f"{QUEUE_TARGET[building_type]}"
            )

    def test_f2p_buildings_intentionally_not_reaching_max(self):
        assert QUEUE_TARGET[B.WOODCUTTER] < MAX_BUILDING_LEVEL[B.WOODCUTTER]
        assert QUEUE_TARGET[B.QUARRY] < MAX_BUILDING_LEVEL[B.QUARRY]

    def test_required_fortress_levels_are_valid_building_types(self):
        for building_type in REQUIRED_FORTRESS_LEVEL:
            assert building_type in BuildingType.__members__.values()
