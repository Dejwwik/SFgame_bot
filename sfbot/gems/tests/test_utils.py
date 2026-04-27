from sfbot.gems.utils import _calc_above_25, _calc_base, calc_average_gem_attribute


class TestCalcBase:
    """Tests for mine level <= 25 (linear formula)."""

    def test_mine_level_1_no_knights(self):
        # level=100, mine=1, knights=0: 100 * 0.25 * (1 + 0) = 25.0
        assert calc_average_gem_attribute(100, 0, 1) == 25.0

    def test_mine_level_1_with_knights(self):
        # level=100, mine=1, knights=30: 25.0 + 30/3 = 35.0
        assert calc_average_gem_attribute(100, 30, 1) == 35.0

    def test_mine_level_25_no_knights(self):
        # level=100, mine=25, knights=0: 100 * 0.25 * (1 + 0.25 * 24) = 100 * 0.25 * 7.0 = 175.0
        assert calc_average_gem_attribute(100, 0, 25) == 175.0

    def test_mine_level_10(self):
        # level=200, mine=10, knights=0: 200 * 0.25 * (1 + 0.25 * 9) = 50 * 3.25 = 162.5
        assert calc_average_gem_attribute(200, 0, 10) == 162.5

    def test_low_level(self):
        # level=1, mine=1, knights=0: 1 * 0.25 * 1 = 0.25
        assert calc_average_gem_attribute(1, 0, 1) == 0.25

    def test_knights_always_add_third(self):
        # Knights contribution is always total_knights / 3
        base = calc_average_gem_attribute(50, 0, 5)
        with_knights = calc_average_gem_attribute(50, 90, 5)
        assert with_knights - base == 30.0

    def test_mine_level_capped_at_25(self):
        # _calc_base clamps mine_level to 25, but calc_average_gem_attribute
        # switches to _calc_above_25 for mine > 25, so test at boundary
        assert calc_average_gem_attribute(100, 0, 25) == _calc_base(100, 25, 0)


class TestCalcAbove25:
    """Tests for mine level > 25 (polynomial regression)."""

    def test_uses_polynomial_for_mine_above_25(self):
        # Should use _calc_above_25, not _calc_base
        result = calc_average_gem_attribute(100, 0, 26)
        expected = _calc_above_25(100, 26, 0)
        assert result == expected

    def test_returns_float(self):
        result = calc_average_gem_attribute(300, 0, 30)
        assert isinstance(result, float)

    def test_increases_with_level(self):
        low = calc_average_gem_attribute(100, 0, 30)
        high = calc_average_gem_attribute(300, 0, 30)
        assert high > low

    def test_increases_with_mine(self):
        # Polynomial is fitted for high-level characters (mine > 25 = late game)
        low = calc_average_gem_attribute(500, 0, 26)
        high = calc_average_gem_attribute(500, 0, 40)
        assert high > low

    def test_knights_add_same_amount(self):
        base = calc_average_gem_attribute(200, 0, 30)
        with_knights = calc_average_gem_attribute(200, 60, 30)
        assert with_knights - base == 20.0


class TestBranchBoundary:
    """Tests for the mine_level == 25 / 26 boundary."""

    def test_mine_25_uses_base(self):
        assert calc_average_gem_attribute(100, 0, 25) == _calc_base(100, 25, 0)

    def test_mine_26_uses_above_25(self):
        assert calc_average_gem_attribute(100, 0, 26) == _calc_above_25(100, 26, 0)

    def test_mine_0_uses_base(self):
        # Edge case: mine level 0 (not unlocked)
        result = calc_average_gem_attribute(100, 0, 0)
        # 100 * 0.25 * (1 + 0.25 * (0 - 1)) = 100 * 0.25 * 0.75 = 18.75
        assert result == 18.75
