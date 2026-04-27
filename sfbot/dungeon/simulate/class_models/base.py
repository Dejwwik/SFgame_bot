from dataclasses import dataclass

from sfbot.dungeon.models import Fighter


@dataclass
class TurnState:
    """Mutable per-turn attacker state passed through hooks."""

    dmg_min: float
    dmg_max: float
    crit_chance: float
    crit_mult: float
    dmg_mult: float
    defender_skip_override: float | None


@dataclass
class CombatStats:
    """Pre-computed combat values for one fighter vs its opponent."""

    dmg_min: float
    dmg_max: float
    dmg_min2: float
    dmg_max2: float
    crit_chance: float
    crit_mult: float
    total_hp: float
    fighter: Fighter


class ClassModel:
    """Base class for class-specific combat models.

    Provides no-op defaults for all hooks. Subclasses override only
    the hooks they need.
    """

    def __init__(self) -> None:
        self.skip_count = 0

    def before(self, ctx: "FightContext") -> None:
        """Pre-combat ability, runs once before the fight loop starts.

        Used by: BattleMage (fireball).
        """
        pass

    def check_control_skip(self, ctx: "FightContext") -> bool:
        """Check if the defender forces the attacker to lose this turn.

        Returns True if the attacker's turn is skipped (swap without attacking).
        Used by: Berserker (chain-skip up to BERSERKER_SKIP_LIMIT consecutive turns).
        """
        return False

    def before_attack(self, ctx: "FightContext", ts: TurnState) -> None:
        """Modify attacker's turn state before the attack resolves.

        Used by: Paladin (stance damage bonus), Bard (melody damage buff),
        Druid (bear rage crit boost).
        """
        pass

    def get_skip_override(self, ctx: "FightContext") -> float | None:
        """Override the defender's dodge/skip chance for incoming attacks.

        Returns a float to override, or None to use the default.
        Used by: Paladin (stance-based skip chance), Necromancer (spectre skip).
        """
        return None

    def control(self, ctx: "FightContext", ts: TurnState, rage: float) -> bool | None:
        """Execute a control ability instead of a normal attack.

        Returns None to proceed with normal attack, True if the turn was
        consumed (swap), or False if the defender was killed.
        Used by: Druid (eagle swoop), PlagueDoctor (tincture throw/poison tick),
        Necromancer (summon minion + attack).
        """
        return None

    def on_dodge(self, ctx: "FightContext", ts: TurnState, rage: float) -> None:
        """React when the attacker's normal attack is dodged by the defender.

        Used by: Druid (enters bear rage form on next turn).
        """
        pass

    def after_hit(self, ctx: "FightContext", ts: TurnState, rage: float) -> bool:
        """Execute an ability after a successful normal hit.

        Returns True if the defender was killed.
        Used by: Assassin (second weapon strike with off-hand).
        """
        return False

    def end_turn(self, ctx: "FightContext", ts: TurnState, rage: float) -> bool:
        """End-of-turn ability after the attack phase completes.

        Returns True if the defender was killed.
        Used by: Necromancer (minion follow-up attack), Bard (melody tick-down).
        """
        return False

    def on_death(self, ctx: "FightContext") -> bool:
        """React when this fighter is killed. Returns True if revived.

        Used by: DemonHunter (chance to revive with decaying HP).
        """
        return False


class FightContext:
    """Shared mutable fight state accessed by both class models."""

    def __init__(
        self,
        stats_a: CombatStats,
        stats_b: CombatStats,
        model_a: ClassModel,
        model_b: ClassModel,
    ) -> None:
        self.hp_a = stats_a.total_hp
        self.hp_b = stats_b.total_hp
        self.turn = 0
        self.a_is_attacker = True
        self.model_a = model_a
        self.model_b = model_b
        self.stats_a = stats_a
        self.stats_b = stats_b
        self.tincture_on_a = 0
        self.tincture_on_b = 0

    def get_rage(self) -> float:
        rage = 1.0 + self.turn / 6.0
        self.turn += 1
        return rage

    @property
    def attacker_hp(self) -> float:
        return self.hp_a if self.a_is_attacker else self.hp_b

    @attacker_hp.setter
    def attacker_hp(self, v: float) -> None:
        if self.a_is_attacker:
            self.hp_a = v
        else:
            self.hp_b = v

    @property
    def defender_hp(self) -> float:
        return self.hp_b if self.a_is_attacker else self.hp_a

    @defender_hp.setter
    def defender_hp(self, v: float) -> None:
        if self.a_is_attacker:
            self.hp_b = v
        else:
            self.hp_a = v

    @property
    def attacker_stats(self) -> CombatStats:
        return self.stats_a if self.a_is_attacker else self.stats_b

    @property
    def defender_stats(self) -> CombatStats:
        return self.stats_b if self.a_is_attacker else self.stats_a

    @property
    def attacker_model(self) -> ClassModel:
        return self.model_a if self.a_is_attacker else self.model_b

    @property
    def defender_model(self) -> ClassModel:
        return self.model_b if self.a_is_attacker else self.model_a

    @property
    def attacker_fighter(self) -> Fighter:
        return self.attacker_stats.fighter

    @property
    def defender_fighter(self) -> Fighter:
        return self.defender_stats.fighter

    @property
    def tincture_on_attacker(self) -> int:
        return self.tincture_on_a if self.a_is_attacker else self.tincture_on_b

    @tincture_on_attacker.setter
    def tincture_on_attacker(self, v: int) -> None:
        if self.a_is_attacker:
            self.tincture_on_a = v
        else:
            self.tincture_on_b = v

    @property
    def tincture_on_defender(self) -> int:
        return self.tincture_on_b if self.a_is_attacker else self.tincture_on_a

    @tincture_on_defender.setter
    def tincture_on_defender(self, v: int) -> None:
        if self.a_is_attacker:
            self.tincture_on_b = v
        else:
            self.tincture_on_a = v

    def deal_damage_to_defender(self, damage: float) -> bool:
        """Apply damage to defender. Returns True if alive (survived or revived)."""
        self.defender_hp -= damage
        if self.defender_hp <= 0:
            return self.defender_model.on_death(self)
        return True

    def swap(self) -> None:
        self.a_is_attacker = not self.a_is_attacker
