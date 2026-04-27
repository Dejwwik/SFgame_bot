from unittest.mock import MagicMock

from sfbot.fortress.fortress import UNLOCK_LEVEL, BuildingType, Fortress, UnitType
from sfbot.fortress.tasks import train_soldiers as task
from sfbot.fortress.tests.conftest import all_at_zero, make_fortress

B = BuildingType
U = UnitType


def make_bot(
    level: int = 100,
    fortress: Fortress | None = None,
) -> MagicMock:
    bot = MagicMock()
    bot.character.level = level
    bot.fortress = fortress or make_fortress(building_levels=all_at_zero())
    return bot


class TestShouldRun:
    def test_low_level_skips(self):
        bot = make_bot(level=UNLOCK_LEVEL - 1)
        assert task.should_run(bot) is False

    def test_fortress_not_unlocked_skips(self):
        fortress = make_fortress(building_levels={})
        bot = make_bot(fortress=fortress)
        assert task.should_run(bot) is False

    def test_no_barracks_skips(self):
        fortress = make_fortress(
            building_levels={B.FORTRESS: 5, B.BARRACKS: 0},
        )
        bot = make_bot(fortress=fortress)
        assert task.should_run(bot) is False

    def test_already_training_but_has_slots_runs(self):
        fortress = make_fortress(
            building_levels={B.FORTRESS: 5, B.BARRACKS: 5},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 5, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_training_finish={U.SOLDIER: 9999, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        bot = make_bot(fortress=fortress)
        assert task.should_run(bot) is True

    def test_already_training_all_slots_full_skips(self):
        fortress = make_fortress(
            building_levels={B.FORTRESS: 5, B.BARRACKS: 5},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 15, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_training_finish={U.SOLDIER: 9999, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        bot = make_bot(fortress=fortress)
        assert task.should_run(bot) is False

    def test_all_slots_full_skips(self):
        fortress = make_fortress(
            building_levels={B.FORTRESS: 5, B.BARRACKS: 5},
            unit_counts={U.SOLDIER: 15, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        bot = make_bot(fortress=fortress)
        assert task.should_run(bot) is False

    def test_has_trainable_slots_runs(self):
        fortress = make_fortress(
            building_levels={B.FORTRESS: 5, B.BARRACKS: 5},
            unit_counts={U.SOLDIER: 3, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        bot = make_bot(fortress=fortress)
        assert task.should_run(bot) is True

    def test_partial_training_still_has_slots(self):
        fortress = make_fortress(
            building_levels={B.FORTRESS: 5, B.BARRACKS: 15},
            unit_counts={U.SOLDIER: 5, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 10, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        bot = make_bot(fortress=fortress)
        # 45 - 5 - 10 = 30 trainable
        assert task.should_run(bot) is True

    def test_ignores_archers_and_mages(self):
        fortress = make_fortress(
            building_levels={
                B.FORTRESS: 10,
                B.BARRACKS: 5,
                B.ARCHERY_GUILD: 5,
                B.MAGES_TOWER: 5,
            },
            unit_counts={U.SOLDIER: 15, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        bot = make_bot(fortress=fortress)
        # Soldiers full, archers/mages available — but this task only handles soldiers
        assert task.should_run(bot) is False


class TestTrainableCount:
    def test_empty(self):
        f = make_fortress(
            building_levels={B.BARRACKS: 5},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        assert f.trainable_count(U.SOLDIER) == 15

    def test_some_existing_and_training(self):
        f = make_fortress(
            building_levels={B.BARRACKS: 15},
            unit_counts={U.SOLDIER: 5, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 10, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        assert f.trainable_count(U.SOLDIER) == 30

    def test_at_max(self):
        f = make_fortress(
            building_levels={B.BARRACKS: 15},
            unit_counts={U.SOLDIER: 45, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        assert f.trainable_count(U.SOLDIER) == 0

    def test_never_negative(self):
        f = make_fortress(
            building_levels={B.BARRACKS: 5},
            unit_counts={U.SOLDIER: 10, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 8, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        assert f.trainable_count(U.SOLDIER) == 0


class TestCanTrain:
    def test_no_building(self):
        f = make_fortress(
            building_levels={B.BARRACKS: 0},
        )
        assert f.can_train(U.SOLDIER) is False

    def test_currently_training_still_has_slots(self):
        f = make_fortress(
            building_levels={B.BARRACKS: 5},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 5, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_training_finish={U.SOLDIER: 9999, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        assert f.can_train(U.SOLDIER) is True

    def test_all_full(self):
        f = make_fortress(
            building_levels={B.BARRACKS: 5},
            unit_counts={U.SOLDIER: 15, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        assert f.can_train(U.SOLDIER) is False

    def test_can_train(self):
        f = make_fortress(
            building_levels={B.BARRACKS: 5},
            unit_counts={U.SOLDIER: 3, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        assert f.can_train(U.SOLDIER) is True
