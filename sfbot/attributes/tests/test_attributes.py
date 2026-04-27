from sfbot.attributes.attributes import Attributes
from sfbot.constants import Attribute


class TestFindMostDeficient:
    """Attributes.find_most_deficient picks the attribute furthest below target."""

    @staticmethod
    def _find(
        base_attrs: dict[Attribute, int], weights: dict[Attribute, float]
    ) -> Attribute:
        attrs = Attributes.__new__(Attributes)
        return attrs.find_most_deficient(base_attrs, weights)

    def test_main_attr_below_target(self):
        base = {
            Attribute.STRENGTH: 100,
            Attribute.DEXTERITY: 100,
            Attribute.INTELLIGENCE: 400,
            Attribute.CONSTITUTION: 300,
            Attribute.LUCK: 100,
        }
        weights = {
            Attribute.INTELLIGENCE: 0.45,
            Attribute.CONSTITUTION: 0.30,
            Attribute.LUCK: 0.15,
            Attribute.STRENGTH: 0.05,
            Attribute.DEXTERITY: 0.05,
        }
        assert self._find(base, weights) == Attribute.INTELLIGENCE

    def test_con_below_target(self):
        base = {
            Attribute.STRENGTH: 50,
            Attribute.DEXTERITY: 50,
            Attribute.INTELLIGENCE: 500,
            Attribute.CONSTITUTION: 250,
            Attribute.LUCK: 150,
        }
        weights = {
            Attribute.INTELLIGENCE: 0.45,
            Attribute.CONSTITUTION: 0.30,
            Attribute.LUCK: 0.15,
            Attribute.STRENGTH: 0.05,
            Attribute.DEXTERITY: 0.05,
        }
        assert self._find(base, weights) == Attribute.CONSTITUTION

    def test_all_on_target_returns_first(self):
        base = {
            Attribute.STRENGTH: 50,
            Attribute.DEXTERITY: 50,
            Attribute.INTELLIGENCE: 450,
            Attribute.CONSTITUTION: 300,
            Attribute.LUCK: 150,
        }
        weights = {
            Attribute.INTELLIGENCE: 0.45,
            Attribute.CONSTITUTION: 0.30,
            Attribute.LUCK: 0.15,
            Attribute.STRENGTH: 0.05,
            Attribute.DEXTERITY: 0.05,
        }
        result = self._find(base, weights)
        assert result == Attribute.INTELLIGENCE

    def test_overinvested_skipped(self):
        base = {
            Attribute.STRENGTH: 200,
            Attribute.DEXTERITY: 50,
            Attribute.INTELLIGENCE: 400,
            Attribute.CONSTITUTION: 250,
            Attribute.LUCK: 100,
        }
        weights = {
            Attribute.INTELLIGENCE: 0.45,
            Attribute.CONSTITUTION: 0.30,
            Attribute.LUCK: 0.10,
            Attribute.STRENGTH: 0.05,
            Attribute.DEXTERITY: 0.10,
        }
        # STR at 20% vs target 5% → negative deficit, should not be picked
        result = self._find(base, weights)
        assert result != Attribute.STRENGTH

    def test_two_attrs_equal_weight(self):
        base = {
            Attribute.STRENGTH: 100,
            Attribute.INTELLIGENCE: 50,
        }
        weights = {
            Attribute.STRENGTH: 0.50,
            Attribute.INTELLIGENCE: 0.50,
        }
        assert self._find(base, weights) == Attribute.INTELLIGENCE

    def test_single_weight(self):
        base = {Attribute.STRENGTH: 500}
        weights = {Attribute.STRENGTH: 1.0}
        assert self._find(base, weights) == Attribute.STRENGTH

    def test_luck_most_deficient(self):
        base = {
            Attribute.STRENGTH: 100,
            Attribute.DEXTERITY: 100,
            Attribute.INTELLIGENCE: 400,
            Attribute.CONSTITUTION: 300,
            Attribute.LUCK: 10,
        }
        weights = {
            Attribute.INTELLIGENCE: 0.40,
            Attribute.CONSTITUTION: 0.30,
            Attribute.LUCK: 0.15,
            Attribute.STRENGTH: 0.10,
            Attribute.DEXTERITY: 0.05,
        }
        assert self._find(base, weights) == Attribute.LUCK

    def test_repeated_calls_converge(self):
        """Simulating multiple upgrades should spread points toward target."""
        base = {
            Attribute.INTELLIGENCE: 0,
            Attribute.CONSTITUTION: 0,
            Attribute.LUCK: 0,
        }
        weights = {
            Attribute.INTELLIGENCE: 0.50,
            Attribute.CONSTITUTION: 0.30,
            Attribute.LUCK: 0.20,
        }
        working = dict(base)
        for _ in range(100):
            attr = self._find(working, weights)
            working[attr] += 1

        total = sum(working.values())
        assert working[Attribute.INTELLIGENCE] / total > 0.45
        assert working[Attribute.CONSTITUTION] / total > 0.25
        assert working[Attribute.LUCK] / total > 0.15
