from datetime import datetime, timezone

from sfbot.constants import (
    CHARACTER_STATUS_DUNGEON_NEXT_FREE_FIGHT_INDEX,
    VALUES_DELIMITER,
)
from sfbot.dungeon.constants import (
    CONTINUOUS_LOOP_FLOORS,
    FLOORS_PER_DUNGEON,
    LOCKED,
    MIRROR_WIN_CHANCE,
    PORTAL_FLOORS,
    SANDSTORM_FLOORS,
    SIMULATION_ITERATIONS,
    TOWER_FLOORS,
    TWISTER_FLOORS,
)
from sfbot.dungeon.enums import DungeonKind, LightDungeon, ShadowDungeon
from sfbot.dungeon.models import Fighter
from sfbot.dungeon.monsters import get_monster_at
from sfbot.dungeon.simulate import (
    fighter_from_monster,
    simulate_fight,
    simulate_sequential_fight,
)
from sfbot.fight import FightResult, parse_fight_result
from sfbot.logging import get_main_logger
from sfbot.session import GameSession


def parse_progress(values: list[int]) -> dict[int, int]:
    return {dungeon_id: floor for dungeon_id, floor in enumerate(values)}


def is_finished_light(dungeon_id: int, progress: int) -> bool:
    if dungeon_id == LightDungeon.TOWER:
        return progress >= TOWER_FLOORS
    if dungeon_id == LightDungeon.SANDSTORM:
        return progress >= SANDSTORM_FLOORS
    return progress >= FLOORS_PER_DUNGEON


def is_finished_shadow(dungeon_id: int, progress: int) -> bool:
    if dungeon_id == ShadowDungeon.TWISTER:
        return progress >= TWISTER_FLOORS
    if dungeon_id == ShadowDungeon.CONTINUOUS_LOOP_OF_IDOLS:
        return progress >= CONTINUOUS_LOOP_FLOORS
    return progress >= FLOORS_PER_DUNGEON


def is_companion_dungeon(dungeon: LightDungeon | ShadowDungeon) -> bool:
    """Return True if this dungeon uses sequential 4v1 companion fights."""
    if isinstance(dungeon, ShadowDungeon):
        return dungeon != ShadowDungeon.TWISTER
    return dungeon == LightDungeon.TOWER


def simulate_dungeon_fight(
    player: Fighter,
    dungeon: LightDungeon | ShadowDungeon,
    progress: int,
    companions: list[Fighter],
) -> float | None:
    monster = get_monster_at(dungeon, progress)
    if monster is None:
        return None
    if monster.is_mirror:
        return MIRROR_WIN_CHANCE

    monster_fighter = fighter_from_monster(monster)

    if companions and is_companion_dungeon(dungeon):
        fighters = companions + [player]
        return simulate_sequential_fight(
            fighters, monster_fighter, SIMULATION_ITERATIONS
        )

    return simulate_fight(player, monster_fighter, SIMULATION_ITERATIONS)


class Dungeon:
    """Regular dungeon system — light dungeons, shadow dungeons, and portal."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self.light_progress: dict[int, int] = {}
        self.shadow_progress: dict[int, int] = {}
        self.next_free_fight: int = 0
        self.portal_finished: int = 0
        self.portal_enemy_hp: int = 0
        self.portal_last_fight_day: int = 0
        self.parse()

    def parse(self) -> None:
        light_raw = self.session.login_data.get("dungeonprogresslight(37)", "")
        if light_raw:
            light_vals = [int(x) for x in light_raw.split(VALUES_DELIMITER) if x]
            self.light_progress = parse_progress(light_vals)
        else:
            self.light_progress = {}

        shadow_raw = self.session.login_data.get("dungeonprogressshadow(37)", "")
        if shadow_raw:
            shadow_vals = [int(x) for x in shadow_raw.split(VALUES_DELIMITER) if x]
            self.shadow_progress = parse_progress(shadow_vals)
        else:
            self.shadow_progress = {}

        char_status_raw = self.session.login_data.get("characterstatus", "")
        if char_status_raw:
            status_vals = [int(x) for x in char_status_raw.split(VALUES_DELIMITER) if x]
            if len(status_vals) > CHARACTER_STATUS_DUNGEON_NEXT_FREE_FIGHT_INDEX:
                self.next_free_fight = status_vals[
                    CHARACTER_STATUS_DUNGEON_NEXT_FREE_FIGHT_INDEX
                ]
            else:
                self.next_free_fight = 0
        else:
            self.next_free_fight = 0

        portal_raw = self.session.login_data.get("portalprogress(3)", "")
        if portal_raw:
            portal_vals = [int(x) for x in portal_raw.split(VALUES_DELIMITER) if x]
            self.portal_finished = portal_vals[0] if len(portal_vals) > 0 else 0
            self.portal_enemy_hp = portal_vals[1] if len(portal_vals) > 1 else 0
            self.portal_last_fight_day = portal_vals[2] if len(portal_vals) > 2 else 0
        else:
            self.portal_finished = 0
            self.portal_enemy_hp = 0
            self.portal_last_fight_day = 0

    def refresh(self) -> None:
        self.parse()

    @property
    def is_free(self) -> bool:
        return self.next_free_fight <= self.session.server_time()

    def get_fightable_light_dungeons(self) -> list[LightDungeon]:
        result: list[LightDungeon] = []
        for member in LightDungeon:
            dungeon_id = member.value
            progress = self.light_progress.get(dungeon_id, LOCKED)
            if progress == LOCKED or is_finished_light(dungeon_id, progress):
                continue
            if member == LightDungeon.TOWER:
                continue
            result.append(member)
        return result

    def get_fightable_shadow_dungeons(self) -> list[ShadowDungeon]:
        result: list[ShadowDungeon] = []
        for member in ShadowDungeon:
            dungeon_id = member.value
            progress = self.shadow_progress.get(dungeon_id, LOCKED)
            if progress == LOCKED or is_finished_shadow(dungeon_id, progress):
                continue
            if member == ShadowDungeon.TWISTER:
                continue
            result.append(member)
        return result

    def get_best_dungeon(
        self,
        player: Fighter,
        companions: list[Fighter],
    ) -> tuple[DungeonKind | None, LightDungeon | ShadowDungeon | None, float]:
        """Find the best dungeon to fight using battle simulation.

        Returns (kind, dungeon, win_chance). Returns (None, None, 0.0)
        if nothing is fightable.
        """
        best_kind: DungeonKind | None = None
        best_dungeon: LightDungeon | ShadowDungeon | None = None
        best_chance: float = 0.0

        for light_dungeon in self.get_fightable_light_dungeons():
            progress = self.light_progress.get(light_dungeon.value, 0)
            chance = simulate_dungeon_fight(player, light_dungeon, progress, companions)
            if chance is not None and chance > best_chance:
                best_kind = DungeonKind.LIGHT
                best_dungeon = light_dungeon
                best_chance = chance

        if self.is_tower_fightable:
            chance = simulate_dungeon_fight(
                player, LightDungeon.TOWER, self.tower_progress, companions
            )
            if chance is not None and chance > best_chance:
                best_kind = DungeonKind.TOWER
                best_dungeon = LightDungeon.TOWER
                best_chance = chance

        for shadow_dungeon in self.get_fightable_shadow_dungeons():
            progress = self.shadow_progress.get(shadow_dungeon.value, 0)
            chance = simulate_dungeon_fight(
                player, shadow_dungeon, progress, companions
            )
            if chance is not None and chance > best_chance:
                best_kind = DungeonKind.SHADOW
                best_dungeon = shadow_dungeon
                best_chance = chance

        if self.is_twister_fightable:
            chance = simulate_dungeon_fight(
                player, ShadowDungeon.TWISTER, self.twister_progress, companions
            )
            if chance is not None and chance > best_chance:
                best_kind = DungeonKind.TWISTER
                best_dungeon = ShadowDungeon.TWISTER
                best_chance = chance

        return best_kind, best_dungeon, best_chance

    @property
    def tower_progress(self) -> int:
        return self.light_progress.get(LightDungeon.TOWER, LOCKED)

    @property
    def is_tower_fightable(self) -> bool:
        progress = self.tower_progress
        return progress != LOCKED and progress < TOWER_FLOORS

    @property
    def twister_progress(self) -> int:
        return self.shadow_progress.get(ShadowDungeon.TWISTER, LOCKED)

    @property
    def is_twister_fightable(self) -> bool:
        progress = self.twister_progress
        return progress != LOCKED and progress < TWISTER_FLOORS

    @property
    def is_portal_finished(self) -> bool:
        return self.portal_finished >= PORTAL_FLOORS

    @property
    def can_fight_portal(self) -> bool:
        if self.is_portal_finished:
            return False
        if self.portal_enemy_hp <= 0 and self.portal_finished > 0:
            return False
        server_now = self.session.server_time()
        current_day = (
            datetime.fromtimestamp(server_now, tz=timezone.utc).timetuple().tm_yday
        )
        return self.portal_last_fight_day != current_day

    async def update_async(self) -> None:
        await self.session.request_and_update_async("PlayerDungeonOpen")
        self.refresh()

    async def fight_light_async(self, dungeon: LightDungeon) -> FightResult:
        if dungeon == LightDungeon.TOWER:
            raise ValueError("Use fight_tower_async() for the Tower")
        floor = self.light_progress.get(dungeon.value, 0) + 1
        wire_id = dungeon.value + 1
        result = await self.session.request_and_update_async(
            "PlayerDungeonBattle", f"{wire_id}/0"
        )
        self.refresh()
        fight = parse_fight_result(result)
        outcome = "won" if fight.won else "lost"
        get_main_logger().info(
            f"Dungeon: {outcome} {dungeon.name} (light) floor {floor} +{fight.xp:,} XP"
        )
        return fight

    async def fight_shadow_async(self, dungeon: ShadowDungeon) -> FightResult:
        floor = self.shadow_progress.get(dungeon.value, 0) + 1
        if dungeon == ShadowDungeon.TWISTER:
            wire_id = ShadowDungeon.TWISTER.value + 1
            result = await self.session.request_and_update_async(
                "PlayerDungeonBattle", f"{wire_id}/0"
            )
        else:
            wire_id = dungeon.value + 1
            result = await self.session.request_and_update_async(
                "PlayerShadowBattle", f"{wire_id}/0"
            )
        self.refresh()
        fight = parse_fight_result(result)
        outcome = "won" if fight.won else "lost"
        get_main_logger().info(
            f"Dungeon: {outcome} {dungeon.name} (shadow) floor {floor} +{fight.xp:,} XP"
        )
        return fight

    async def fight_tower_async(self) -> FightResult:
        progress = self.tower_progress
        if not self.is_tower_fightable:
            raise ValueError("Tower is not fightable")
        result = await self.session.request_and_update_async(
            "PlayerTowerBattle", f"{progress + 1}/0"
        )
        self.refresh()
        fight = parse_fight_result(result)
        outcome = "won" if fight.won else "lost"
        get_main_logger().info(
            f"Dungeon: {outcome} Tower floor {progress + 1} +{fight.xp:,} XP"
        )
        return fight

    async def fight_portal_async(self) -> FightResult:
        result = await self.session.request_and_update_async("PlayerPortalBattle")
        self.refresh()
        fight = parse_fight_result(result)
        outcome = "won" if fight.won else "lost"
        get_main_logger().info(
            f"Portal: {outcome} enemy {self.portal_finished}/{PORTAL_FLOORS}"
        )
        return fight
