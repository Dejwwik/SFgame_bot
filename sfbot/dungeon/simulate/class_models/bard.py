import random
from typing import override

from sfbot.dungeon.simulate.class_models.base import ClassModel, FightContext, TurnState
from sfbot.dungeon.simulate.constants import (
    BARD_CHANCES,
    BARD_DURATIONS,
    BARD_EFFECT_ROUNDS,
    BARD_VALUES,
    BYPASS_SPECIAL,
)


class BardModel(ClassModel):
    """Melody buff: every N turns, rolls a tiered damage multiplier lasting several turns."""

    def __init__(self) -> None:
        super().__init__()
        self.effect_round = BARD_EFFECT_ROUNDS
        self.melody_remaining = 0
        self.melody_mult = 1.0

    @override
    def before_attack(self, ctx: FightContext, ts: TurnState) -> None:
        """Roll a new melody every BARD_EFFECT_ROUNDS turns, apply damage buff.

        Mage defenders negate melody cycling (BYPASS_SPECIAL), but an
        already-active melody still applies its damage multiplier.
        """
        if ctx.defender_fighter.char_class not in BYPASS_SPECIAL:
            self.effect_round += 1
            if self.effect_round >= BARD_EFFECT_ROUNDS:
                self.effect_round = 0
                roll = random.random() * 100
                if roll < BARD_CHANCES[0]:
                    tier = 0
                elif roll < BARD_CHANCES[0] + BARD_CHANCES[1]:
                    tier = 1
                else:
                    tier = 2
                self.melody_remaining = BARD_DURATIONS[tier]
                self.melody_mult = 1.0 + BARD_VALUES[tier]

        if self.melody_remaining > 0:
            ts.dmg_min *= self.melody_mult
            ts.dmg_max *= self.melody_mult

    @override
    def end_turn(self, ctx: FightContext, ts: TurnState, rage: float) -> bool:
        """Tick down melody duration."""
        if self.melody_remaining > 0:
            self.melody_remaining -= 1
        return False
