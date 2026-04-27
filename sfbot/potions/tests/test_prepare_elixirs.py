"""Edge-case tests for calc_dungeon_potion_credits covering boundary conditions."""

from sfbot.constants import PotionAttributeType, PotionSize
from sfbot.potions.potions import (
    ActivePotion,
    Potion,
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


class TestCreditsEdgeCases:
    def test_only_small_potions_give_zero_credits(self):
        potions = [
            _active(CON, PotionSize.SMALL, NOW + 200 * HOUR, slot=1),
            _active(STR, PotionSize.SMALL, NOW + 200 * HOUR, slot=2),
        ]
        c = calc_dungeon_potion_credits(potions, STR, False, NOW)
        assert c[CON] == 0
        assert c[STR] == 0

    def test_ready_with_asymmetric_expiry(self):
        """CON 12 days, main 6 days → base = main. CON excess = 6 days = 144h → 2 credits."""
        main_end = NOW + 144 * HOUR
        potions = [
            _active(HP, None, NOW + 500 * HOUR, slot=1),
            _active(CON, PotionSize.LARGE, NOW + 288 * HOUR, slot=2),
            _active(STR, PotionSize.LARGE, main_end, slot=3),
        ]
        c = calc_dungeon_potion_credits(potions, STR, True, NOW)
        assert c[CON] == 2  # (288-144)=144 → 144//72 = 2
        assert c[STR] == 0

    def test_not_ready_all_types_partial(self):
        """All active with partial coverage."""
        potions = [
            _active(HP, None, NOW + 100 * HOUR, slot=1),
            _active(CON, PotionSize.LARGE, NOW + 80 * HOUR, slot=2),
            _active(STR, PotionSize.LARGE, NOW + 150 * HOUR, slot=3),
        ]
        c = calc_dungeon_potion_credits(potions, STR, False, NOW)
        assert c[CON] == 1  # 80//72
        assert c[STR] == 2  # 150//72
        assert c[HP] == 0  # 100 < 144

    def test_credits_dict_uses_correct_main_attr_key(self):
        """Verify the dict key is the actual main_potion_attr, not STR."""
        INT = PotionAttributeType.INTELLIGENCE
        potions = [_active(INT, PotionSize.LARGE, NOW + 100 * HOUR)]
        c = calc_dungeon_potion_credits(potions, INT, False, NOW)
        assert c[INT] == 1
        assert STR not in c
