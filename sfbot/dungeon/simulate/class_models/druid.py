import random
from typing import override

from sfbot.dungeon.simulate.class_models.base import ClassModel, FightContext, TurnState
from sfbot.dungeon.simulate.combat import calc_hit_damage, will_skip
from sfbot.dungeon.simulate.constants import (
    BYPASS_SPECIAL,
    DRUID_RAGE_CRIT_BONUS,
    DRUID_RAGE_CRIT_CHANCE,
    DRUID_RAGE_CRIT_MULT,
    DRUID_SWOOP_CHANCE,
    DRUID_SWOOP_INCREMENT,
    DRUID_SWOOP_MAX,
    DRUID_SWOOP_MULTIPLIER,
    SKIP_TYPE_DEFAULT,
)
from sfbot.simulate.constants import CRIT_BASE


class DruidModel(ClassModel):
    """Eagle swoop (bonus attack) and bear rage form (crit boost on dodge)."""

    def __init__(self) -> None:
        super().__init__()
        self.request_rage = False
        self.in_rage = False
        self.swoop_chance = DRUID_SWOOP_CHANCE

    @override
    def before_attack(self, ctx: FightContext, ts: TurnState) -> None:
        """Activate or deactivate bear rage. In rage: boosted crit chance and multiplier.

        Bear rage lasts exactly one turn after being triggered by a dodge.
        """
        if self.request_rage:
            self.request_rage = False
            self.in_rage = True
        elif self.in_rage:
            self.in_rage = False

        if self.in_rage:
            ts.crit_chance = min(
                DRUID_RAGE_CRIT_CHANCE,
                ctx.attacker_stats.crit_chance + DRUID_RAGE_CRIT_BONUS,
            )
            ts.crit_mult = (
                (CRIT_BASE + DRUID_RAGE_CRIT_MULT)
                * ctx.attacker_stats.crit_mult
                / CRIT_BASE
            )

    @override
    def control(self, ctx: FightContext, ts: TurnState, rage: float) -> bool | None:
        """Attempt eagle swoop: a bonus attack with boosted damage.

        Skipped during bear rage and against Mages (BYPASS_SPECIAL).
        Swoop chance increases with each successful swoop, capped at DRUID_SWOOP_MAX.
        """
        if self.in_rage:
            return None
        if ctx.defender_fighter.char_class in BYPASS_SPECIAL:
            return None
        if self.swoop_chance <= 0 or random.random() >= self.swoop_chance:
            return None

        self.swoop_chance = min(
            self.swoop_chance + DRUID_SWOOP_INCREMENT, DRUID_SWOOP_MAX
        )
        swoop_rage = ctx.get_rage()
        swoop_dmg_min = ts.dmg_min * DRUID_SWOOP_MULTIPLIER
        swoop_dmg_max = ts.dmg_max * DRUID_SWOOP_MULTIPLIER

        skipped = will_skip(
            ctx.defender_fighter,
            ctx.attacker_fighter,
            SKIP_TYPE_DEFAULT,
            override_skip_chance=ts.defender_skip_override,
        )
        if skipped:
            return None

        dmg = calc_hit_damage(
            swoop_dmg_min, swoop_dmg_max, swoop_rage, ts.crit_chance, ts.crit_mult
        )
        dmg *= ts.dmg_mult
        if not ctx.deal_damage_to_defender(dmg):
            return False
        return None

    @override
    def on_dodge(self, ctx: FightContext, ts: TurnState, rage: float) -> None:
        """Request bear rage form for next turn when attack is dodged.

        Disabled against Mages (BYPASS_SPECIAL).
        """
        if ctx.attacker_fighter.char_class not in BYPASS_SPECIAL:
            self.request_rage = True
