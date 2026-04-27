import random
from typing import override

from sfbot.dungeon.simulate.class_models.base import ClassModel, FightContext, TurnState
from sfbot.dungeon.simulate.combat import calc_hit_damage, will_skip
from sfbot.dungeon.simulate.constants import (
    BYPASS_SPECIAL,
    PD_TINCTURE_CHANCE,
    PD_TINCTURE_SKIP_CHANCE,
    PD_TINCTURE_TOTAL_ROUNDS,
    SKIP_TYPE_DEFAULT,
)


class PlagueDoctorModel(ClassModel):
    """Tincture poison: debuffs enemy damage and dodge chance over multiple rounds."""

    @override
    def control(self, ctx: FightContext, ts: TurnState, rage: float) -> bool | None:
        """Apply poison tick if tincture active, otherwise attempt to throw a new one.

        Entire control is skipped against Mages (BYPASS_SPECIAL).
        Active tincture deals damage each round and suppresses defender dodge.
        """
        if ctx.defender_fighter.char_class in BYPASS_SPECIAL:
            return None

        tincture = ctx.tincture_on_defender
        if tincture > 0:
            poison_dmg = calc_hit_damage(
                ts.dmg_min, ts.dmg_max, rage, ts.crit_chance, ts.crit_mult
            )
            poison_dmg *= ts.dmg_mult
            alive = ctx.deal_damage_to_defender(poison_dmg)

            new_tincture = tincture - 1
            ctx.tincture_on_defender = new_tincture
            if new_tincture > 0:
                ts.defender_skip_override = PD_TINCTURE_SKIP_CHANCE[new_tincture - 1]
            else:
                ts.defender_skip_override = None

            if not alive:
                return False
            return None

        if random.random() >= PD_TINCTURE_CHANCE:
            return None

        skipped = will_skip(
            ctx.defender_fighter,
            ctx.attacker_fighter,
            SKIP_TYPE_DEFAULT,
            override_skip_chance=ts.defender_skip_override,
        )
        throw_dmg = calc_hit_damage(
            ts.dmg_min, ts.dmg_max, rage, ts.crit_chance, ts.crit_mult
        )
        throw_dmg *= ts.dmg_mult

        if skipped:
            return True

        ctx.tincture_on_defender = PD_TINCTURE_TOTAL_ROUNDS
        alive = ctx.deal_damage_to_defender(throw_dmg)
        return alive
