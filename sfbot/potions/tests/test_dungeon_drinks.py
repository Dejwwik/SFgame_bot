from sfbot.constants import PotionAttributeType, PotionSize
from sfbot.potions.potions import (
    ActivePotion,
    Potion,
    _find_expires,
    calc_dungeon_potion_credits,
)

HOUR = 3600
NOW = 1_000_000

CON = PotionAttributeType.CONSTITUTION
STR = PotionAttributeType.STRENGTH
HP = PotionAttributeType.HP


def _active(
    attr: PotionAttributeType,
    size: PotionSize | None,
    expires: int,
    slot: int = 1,
) -> ActivePotion:
    return ActivePotion(potion=Potion(attr=attr, size=size), expires=expires, slot=slot)


# ── _find_expires ──


class TestFindExpires:
    def test_empty(self):
        assert _find_expires([], CON) == 0

    def test_large_con(self):
        potions = [_active(CON, PotionSize.LARGE, NOW + 5 * HOUR)]
        assert _find_expires(potions, CON) == NOW + 5 * HOUR

    def test_medium_con_skipped(self):
        potions = [_active(CON, PotionSize.MEDIUM, NOW + 5 * HOUR)]
        assert _find_expires(potions, CON) == 0

    def test_wings_any_size(self):
        potions = [_active(HP, None, NOW + 3 * HOUR)]
        assert _find_expires(potions, HP) == NOW + 3 * HOUR

    def test_wrong_attr(self):
        potions = [_active(STR, PotionSize.LARGE, NOW + 5 * HOUR)]
        assert _find_expires(potions, CON) == 0

    def test_first_match(self):
        potions = [
            _active(HP, None, NOW + 7 * HOUR, slot=1),
            _active(CON, PotionSize.LARGE, NOW + 4 * HOUR, slot=2),
            _active(STR, PotionSize.LARGE, NOW + 3 * HOUR, slot=3),
        ]
        assert _find_expires(potions, CON) == NOW + 4 * HOUR
        assert _find_expires(potions, STR) == NOW + 3 * HOUR
        assert _find_expires(potions, HP) == NOW + 7 * HOUR


# ── calc_dungeon_potion_credits — not dungeon-ready ──


class TestCreditsNotReady:
    """Not dungeon-ready: base = now, credits = remaining_hours // 72."""

    def test_no_active_potions(self):
        c = calc_dungeon_potion_credits([], STR, False, NOW)
        assert c[CON] == 0
        assert c[STR] == 0
        assert c[HP] == 0

    def test_large_con_5_days(self):
        """5 days = 120h → 120//72 = 1 credit."""
        potions = [_active(CON, PotionSize.LARGE, NOW + 120 * HOUR)]
        c = calc_dungeon_potion_credits(potions, STR, False, NOW)
        assert c[CON] == 1

    def test_large_con_3_days_exact(self):
        """72h exactly → 72//72 = 1 credit."""
        potions = [_active(CON, PotionSize.LARGE, NOW + 72 * HOUR)]
        c = calc_dungeon_potion_credits(potions, STR, False, NOW)
        assert c[CON] == 1

    def test_large_con_just_under_72h(self):
        """71h → 0 credits."""
        potions = [_active(CON, PotionSize.LARGE, NOW + 71 * HOUR)]
        c = calc_dungeon_potion_credits(potions, STR, False, NOW)
        assert c[CON] == 0

    def test_large_main_10_days(self):
        """10 days = 240h → 240//72 = 3 credits."""
        potions = [_active(STR, PotionSize.LARGE, NOW + 240 * HOUR)]
        c = calc_dungeon_potion_credits(potions, STR, False, NOW)
        assert c[STR] == 3

    def test_wings_over_144h(self):
        """Wings 200h remaining → 200 >= 144 → credit 1."""
        potions = [_active(HP, None, NOW + 200 * HOUR)]
        c = calc_dungeon_potion_credits(potions, STR, False, NOW)
        assert c[HP] == 1

    def test_wings_exactly_144h(self):
        """Wings 144h → 144 >= 144 → credit 1."""
        potions = [_active(HP, None, NOW + 144 * HOUR)]
        c = calc_dungeon_potion_credits(potions, STR, False, NOW)
        assert c[HP] == 1

    def test_wings_under_144h(self):
        """Wings 143h → credit 0."""
        potions = [_active(HP, None, NOW + 143 * HOUR)]
        c = calc_dungeon_potion_credits(potions, STR, False, NOW)
        assert c[HP] == 0

    def test_medium_con_ignored(self):
        potions = [_active(CON, PotionSize.MEDIUM, NOW + 200 * HOUR)]
        c = calc_dungeon_potion_credits(potions, STR, False, NOW)
        assert c[CON] == 0

    def test_full_dungeon_set_active(self):
        """All 3 active, not-ready flag (e.g. because server hasn't set flag)."""
        potions = [
            _active(HP, None, NOW + 160 * HOUR, slot=1),
            _active(CON, PotionSize.LARGE, NOW + 100 * HOUR, slot=2),
            _active(STR, PotionSize.LARGE, NOW + 80 * HOUR, slot=3),
        ]
        c = calc_dungeon_potion_credits(potions, STR, False, NOW)
        assert c[CON] == 1  # 100//72
        assert c[STR] == 1  # 80//72
        assert c[HP] == 1  # 160 >= 144

    def test_expired_potion_zero_credit(self):
        potions = [_active(CON, PotionSize.LARGE, NOW - HOUR)]
        c = calc_dungeon_potion_credits(potions, STR, False, NOW)
        assert c[CON] == 0


# ── calc_dungeon_potion_credits — dungeon-ready ──


class TestCreditsReady:
    """Dungeon-ready: base = min(con_expires, main_expires, wings_expires)."""

    def test_both_expire_same_time(self):
        """CON and main expire at same time → both excess = 0."""
        end = NOW + 100 * HOUR
        potions = [
            _active(HP, None, end + 200 * HOUR, slot=1),
            _active(CON, PotionSize.LARGE, end, slot=2),
            _active(STR, PotionSize.LARGE, end, slot=3),
        ]
        c = calc_dungeon_potion_credits(potions, STR, True, NOW)
        assert c[CON] == 0
        assert c[STR] == 0

    def test_con_longer_than_main(self):
        """CON 9 days, main 3 days → base = main end. CON excess = 6 days = 144h → 2 credits."""
        main_end = NOW + 72 * HOUR
        potions = [
            _active(HP, None, NOW + 500 * HOUR, slot=1),
            _active(CON, PotionSize.LARGE, NOW + 216 * HOUR, slot=2),
            _active(STR, PotionSize.LARGE, main_end, slot=3),
        ]
        c = calc_dungeon_potion_credits(potions, STR, True, NOW)
        # base = min(216h_from_now, 72h_from_now) = 72h_from_now (main_end)
        # CON excess = 216 - 72 = 144h → 144//72 = 2
        assert c[CON] == 2
        assert c[STR] == 0

    def test_main_longer_than_con(self):
        con_end = NOW + 72 * HOUR
        potions = [
            _active(HP, None, NOW + 500 * HOUR, slot=1),
            _active(CON, PotionSize.LARGE, con_end, slot=2),
            _active(STR, PotionSize.LARGE, NOW + 200 * HOUR, slot=3),
        ]
        c = calc_dungeon_potion_credits(potions, STR, True, NOW)
        assert c[CON] == 0
        assert c[STR] == 1  # (200-72) = 128h → 128//72 = 1

    def test_wings_excess_over_common_end(self):
        """Wings 200h past common end → 200 >= 144 → credit 1."""
        common = NOW + 100 * HOUR
        potions = [
            _active(HP, None, common + 200 * HOUR, slot=1),
            _active(CON, PotionSize.LARGE, common, slot=2),
            _active(STR, PotionSize.LARGE, common, slot=3),
        ]
        c = calc_dungeon_potion_credits(potions, STR, True, NOW)
        assert c[HP] == 1

    def test_wings_short_after_common_end(self):
        """Wings 100h past common end → 100 < 144 → credit 0."""
        common = NOW + 100 * HOUR
        potions = [
            _active(HP, None, common + 100 * HOUR, slot=1),
            _active(CON, PotionSize.LARGE, common, slot=2),
            _active(STR, PotionSize.LARGE, common, slot=3),
        ]
        c = calc_dungeon_potion_credits(potions, STR, True, NOW)
        assert c[HP] == 0

    def test_wings_exactly_144h_past_common(self):
        common = NOW + 100 * HOUR
        potions = [
            _active(HP, None, common + 144 * HOUR, slot=1),
            _active(CON, PotionSize.LARGE, common, slot=2),
            _active(STR, PotionSize.LARGE, common, slot=3),
        ]
        c = calc_dungeon_potion_credits(potions, STR, True, NOW)
        assert c[HP] == 1

    def test_different_main_attr(self):
        """Mage (INT) credits use INT as main."""
        INT = PotionAttributeType.INTELLIGENCE
        common = NOW + 72 * HOUR
        potions = [
            _active(HP, None, NOW + 500 * HOUR, slot=1),
            _active(CON, PotionSize.LARGE, common, slot=2),
            _active(INT, PotionSize.LARGE, NOW + 200 * HOUR, slot=3),
        ]
        c = calc_dungeon_potion_credits(potions, INT, True, NOW)
        assert c[CON] == 0
        assert c[INT] == 1  # (200-72)=128 → 128//72 = 1
        assert STR not in c  # STR is not a key

    def test_wings_earliest_expiry_sets_base(self):
        """Wings expire first → base = wings_expires. CON+main get excess credits."""
        potions = [
            _active(HP, None, NOW + 50 * HOUR, slot=1),
            _active(CON, PotionSize.LARGE, NOW + 200 * HOUR, slot=2),
            _active(STR, PotionSize.LARGE, NOW + 200 * HOUR, slot=3),
        ]
        c = calc_dungeon_potion_credits(potions, STR, True, NOW)
        # base = min(200, 200, 50) = 50 (wings)
        # CON = (200-50)=150h → 150//72 = 2
        # STR = (200-50)=150h → 150//72 = 2
        # Wings = (50-50)=0h → 0 < 144 → 0
        assert c[CON] == 2
        assert c[STR] == 2
        assert c[HP] == 0
