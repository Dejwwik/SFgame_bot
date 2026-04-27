from unittest.mock import MagicMock

from sfbot.fortress.fortress import UNLOCK_LEVEL, BuildingType, Fortress, UnitType
from sfbot.fortress.tasks import train_defence_units as task
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

    def test_no_buildings_skips(self):
        fortress = make_fortress(
            building_levels={B.FORTRESS: 10, B.ARCHERY_GUILD: 0, B.MAGES_TOWER: 0},
        )
        bot = make_bot(fortress=fortress)
        assert task.should_run(bot) is False

    def test_both_training_but_have_slots_runs(self):
        fortress = make_fortress(
            building_levels={B.FORTRESS: 10, B.ARCHERY_GUILD: 5, B.MAGES_TOWER: 5},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 5, U.ARCHER: 5},
            unit_training_finish={U.SOLDIER: 0, U.MAGICIAN: 9999, U.ARCHER: 9999},
        )
        bot = make_bot(fortress=fortress)
        assert task.should_run(bot) is True

    def test_both_training_all_slots_full_skips(self):
        fortress = make_fortress(
            building_levels={B.FORTRESS: 10, B.ARCHERY_GUILD: 5, B.MAGES_TOWER: 5},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 10, U.ARCHER: 10},
            unit_training_finish={U.SOLDIER: 0, U.MAGICIAN: 9999, U.ARCHER: 9999},
        )
        bot = make_bot(fortress=fortress)
        assert task.should_run(bot) is False

    def test_all_slots_full_skips(self):
        fortress = make_fortress(
            building_levels={B.FORTRESS: 10, B.ARCHERY_GUILD: 5, B.MAGES_TOWER: 5},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 10, U.ARCHER: 10},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        bot = make_bot(fortress=fortress)
        assert task.should_run(bot) is False

    def test_archers_available_runs(self):
        fortress = make_fortress(
            building_levels={B.FORTRESS: 10, B.ARCHERY_GUILD: 5, B.MAGES_TOWER: 0},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 3},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        bot = make_bot(fortress=fortress)
        assert task.should_run(bot) is True

    def test_mages_available_runs(self):
        fortress = make_fortress(
            building_levels={B.FORTRESS: 10, B.ARCHERY_GUILD: 0, B.MAGES_TOWER: 5},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        bot = make_bot(fortress=fortress)
        assert task.should_run(bot) is True

    def test_both_available_runs(self):
        fortress = make_fortress(
            building_levels={B.FORTRESS: 10, B.ARCHERY_GUILD: 5, B.MAGES_TOWER: 5},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        bot = make_bot(fortress=fortress)
        assert task.should_run(bot) is True

    def test_ignores_soldiers(self):
        fortress = make_fortress(
            building_levels={
                B.FORTRESS: 10,
                B.BARRACKS: 5,
                B.ARCHERY_GUILD: 0,
                B.MAGES_TOWER: 0,
            },
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        bot = make_bot(fortress=fortress)
        assert task.should_run(bot) is False

    def test_one_training_one_available(self):
        fortress = make_fortress(
            building_levels={B.FORTRESS: 10, B.ARCHERY_GUILD: 5, B.MAGES_TOWER: 5},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 5},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 5, U.ARCHER: 0},
            unit_training_finish={U.SOLDIER: 0, U.MAGICIAN: 9999, U.ARCHER: 0},
        )
        bot = make_bot(fortress=fortress)
        # Mages training, archers have trainable slots
        assert task.should_run(bot) is True


class TestCanTrainArcher:
    def test_no_archery_guild(self):
        f = make_fortress(
            building_levels={B.ARCHERY_GUILD: 0},
        )
        assert f.can_train(U.ARCHER) is False

    def test_currently_training_still_has_slots(self):
        f = make_fortress(
            building_levels={B.ARCHERY_GUILD: 5},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 5},
            unit_training_finish={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 9999},
        )
        assert f.can_train(U.ARCHER) is True

    def test_currently_training_all_slots_full(self):
        f = make_fortress(
            building_levels={B.ARCHERY_GUILD: 5},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 10},
            unit_training_finish={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 9999},
        )
        assert f.can_train(U.ARCHER) is False

    def test_at_max(self):
        f = make_fortress(
            building_levels={B.ARCHERY_GUILD: 5},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 10},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        assert f.can_train(U.ARCHER) is False

    def test_can_train(self):
        f = make_fortress(
            building_levels={B.ARCHERY_GUILD: 5},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 2},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        assert f.can_train(U.ARCHER) is True


class TestCanTrainMage:
    def test_no_mages_tower(self):
        f = make_fortress(
            building_levels={B.MAGES_TOWER: 0},
        )
        assert f.can_train(U.MAGICIAN) is False

    def test_currently_training_still_has_slots(self):
        f = make_fortress(
            building_levels={B.MAGES_TOWER: 10},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 5, U.ARCHER: 0},
            unit_training_finish={U.SOLDIER: 0, U.MAGICIAN: 9999, U.ARCHER: 0},
        )
        assert f.can_train(U.MAGICIAN) is True

    def test_currently_training_all_slots_full(self):
        f = make_fortress(
            building_levels={B.MAGES_TOWER: 5},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 5, U.ARCHER: 0},
            unit_training_finish={U.SOLDIER: 0, U.MAGICIAN: 9999, U.ARCHER: 0},
        )
        assert f.can_train(U.MAGICIAN) is False

    def test_at_max(self):
        f = make_fortress(
            building_levels={B.MAGES_TOWER: 5},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 5, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        assert f.can_train(U.MAGICIAN) is False

    def test_can_train(self):
        f = make_fortress(
            building_levels={B.MAGES_TOWER: 5},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 4, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        assert f.can_train(U.MAGICIAN) is True


class TestTrainableCount:
    def test_archer_empty(self):
        f = make_fortress(
            building_levels={B.ARCHERY_GUILD: 5},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        assert f.trainable_count(U.ARCHER) == 10

    def test_mage_partial(self):
        f = make_fortress(
            building_levels={B.MAGES_TOWER: 20},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 5, U.ARCHER: 0},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 7, U.ARCHER: 0},
        )
        assert f.trainable_count(U.MAGICIAN) == 8

    def test_archer_at_max(self):
        f = make_fortress(
            building_levels={B.ARCHERY_GUILD: 15},
            unit_counts={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 30},
            unit_in_training={U.SOLDIER: 0, U.MAGICIAN: 0, U.ARCHER: 0},
        )
        assert f.trainable_count(U.ARCHER) == 0
