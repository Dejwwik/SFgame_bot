from typing import override

from sfbot.dungeon.simulate.class_models.base import ClassModel, FightContext, TurnState
from sfbot.dungeon.simulate.combat import calc_hit_damage, will_skip
from sfbot.dungeon.simulate.constants import SKIP_TYPE_DEFAULT


class AssassinModel(ClassModel):
    """Dual-wield: strikes with off-hand weapon after each successful hit."""

    @override
    def after_hit(self, ctx: FightContext, ts: TurnState, rage: float) -> bool:
        """Strike with second weapon. Defender can dodge the off-hand attack."""
        skipped = will_skip(
            ctx.defender_fighter,
            ctx.attacker_fighter,
            SKIP_TYPE_DEFAULT,
            override_skip_chance=ts.defender_skip_override,
        )
        if skipped:
            return False
        hit_dmg = calc_hit_damage(
            ctx.attacker_stats.dmg_min2,
            ctx.attacker_stats.dmg_max2,
            rage,
            ts.crit_chance,
            ts.crit_mult,
        )
        hit_dmg *= ts.dmg_mult
        return not ctx.deal_damage_to_defender(hit_dmg)
