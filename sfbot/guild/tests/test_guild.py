from sfbot.constants import Cost
from sfbot.guild.guild import get_upgrade_cost


class TestGetUpgradeCost:
    def test_level_0(self):
        assert get_upgrade_cost(0) == Cost(silver=5_00)

    def test_level_1(self):
        assert get_upgrade_cost(1) == Cost(silver=10_00)

    def test_level_2(self):
        assert get_upgrade_cost(2) == Cost(silver=25_00)

    def test_level_3(self):
        assert get_upgrade_cost(3) == Cost(silver=100_00)

    def test_level_4(self):
        assert get_upgrade_cost(4) == Cost(silver=250_00)

    def test_level_5_costs_mushrooms(self):
        assert get_upgrade_cost(5) == Cost(mushrooms=1)

    def test_high_level_costs_mushrooms(self):
        assert get_upgrade_cost(99) == Cost(mushrooms=1)
