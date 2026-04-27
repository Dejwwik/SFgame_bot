import random
from typing import override

from sfbot.dungeon.simulate.class_models.base import ClassModel, FightContext, TurnState
from sfbot.dungeon.simulate.combat import calc_hit_damage
from sfbot.dungeon.simulate.constants import (
    BYPASS_SPECIAL,
    PALADIN_DEFENSIVE_HEAL_MULT,
    PALADIN_STANCE_CHANGE_CHANCE,
    PALADIN_STANCE_COUNT,
    PALADIN_STANCE_DEFENSIVE,
    PALADIN_STANCE_DMG_BONUS,
    PALADIN_STANCE_NEUTRAL,
    PALADIN_STANCE_SKIP,
)


class PaladinModel(ClassModel):
    """Stance cycling (neutral/defensive/offensive) with dodge-based healing."""

    def __init__(self) -> None:
        super().__init__()
        self.stance = PALADIN_STANCE_NEUTRAL

    @override
    def before_attack(self, ctx: FightContext, ts: TurnState) -> None:
        """Cycle to the next stance with a random chance, then apply stance damage bonus.

        Stance cycling is disabled against Mages (BYPASS_SPECIAL),
        but the current stance's damage multiplier still applies.
        """
        if ctx.defender_fighter.char_class not in BYPASS_SPECIAL:
            if random.random() < PALADIN_STANCE_CHANGE_CHANCE:
                self.stance = (self.stance + 1) % PALADIN_STANCE_COUNT
        ts.dmg_mult *= 1.0 + PALADIN_STANCE_DMG_BONUS[self.stance]

    @override
    def get_skip_override(self, ctx: FightContext) -> float | None:
        """Return stance-specific skip chance applied to the defender."""
        return PALADIN_STANCE_SKIP[self.stance]

    @override
    def on_dodge(self, ctx: FightContext, ts: TurnState, rage: float) -> None:
        """Heal the defender when in DEFENSIVE stance and the attack is dodged.

        Heal amount is a fraction of the damage the hit would have dealt.
        """
        if self.stance != PALADIN_STANCE_DEFENSIVE:
            return
        would_dmg = calc_hit_damage(
            ts.dmg_min, ts.dmg_max, rage, ts.crit_chance, ts.crit_mult
        )
        would_dmg *= ts.dmg_mult
        heal = would_dmg * PALADIN_DEFENSIVE_HEAL_MULT
        max_heal = ctx.defender_stats.total_hp - ctx.defender_hp
        if max_heal > 0:
            ctx.defender_hp += min(heal, max_heal)
