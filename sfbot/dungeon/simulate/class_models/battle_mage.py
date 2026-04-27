from math import ceil
from typing import override

from sfbot.dungeon.models import Fighter
from sfbot.dungeon.simulate.class_models.base import ClassModel, FightContext
from sfbot.dungeon.simulate.constants import (
    BYPASS_SPECIAL,
    FIREBALL_HP_RATIO,
)
from sfbot.simulate.constants import HEALTH_MULTIPLIER


def calc_fireball_damage(
    attacker_hp: float, target_hp: float, target: Fighter
) -> float:
    """Calculate fireball damage: min(target_hp/3, attacker_hp * ratio * class_mult).

    Deals 0 against Mages (BYPASS_SPECIAL).
    """
    if target.char_class in BYPASS_SPECIAL:
        return 0.0
    multiplier = FIREBALL_HP_RATIO * HEALTH_MULTIPLIER[target.char_class]
    return min(ceil(target_hp / 3.0), ceil(attacker_hp * multiplier))


class BattleMageModel(ClassModel):
    """Pre-combat fireball that deals HP-ratio damage before the fight loop."""

    @override
    def before(self, ctx: FightContext) -> None:
        """Fire a fireball before combat begins. Skipped against Mages (BYPASS_SPECIAL)."""
        if ctx.defender_fighter.char_class in BYPASS_SPECIAL:
            return
        damage = calc_fireball_damage(
            ctx.attacker_hp, ctx.defender_hp, ctx.defender_fighter
        )
        ctx.turn += 1
        ctx.defender_hp -= damage
