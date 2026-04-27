"""Guild management - fights, portal battles, hydra."""

from datetime import datetime, timezone

from sfbot.constants import (
    CHARACTER_GROUP_HYDRA_NEXT_BATTLE_INDEX,
    CHARACTER_GROUP_HYDRA_REMAINING_INDEX,
    CHARACTER_GROUP_INSTRUCTOR_SKILL_INDEX,
    CHARACTER_GROUP_JOINED_INDEX,
    CHARACTER_GROUP_PET_SKILL_INDEX,
    CHARACTER_GROUP_TREASURE_SKILL_INDEX,
    GUILD_ATTACK_GUILD_INDEX,
    GUILD_ATTACK_TIME_INDEX,
    GUILD_DEFEND_GUILD_INDEX,
    GUILD_DEFEND_TIME_INDEX,
    GUILD_FINISHED_RAIDS_INDEX,
    GUILD_HYDRA_LIFE_INDEX,
    GUILD_HYDRA_MAX_LIFE_INDEX,
    GUILD_MEMBER_BATTLES_BASE_INDEX,
    GUILD_MEMBER_COUNT_INDEX,
    GUILD_MEMBER_PORTAL_FOUGHT_BASE_INDEX,
    GUILD_MEMBER_RANK_BASE_INDEX,
    GUILD_PORTAL_DEFEATED_INDEX,
    GUILD_PORTAL_LIFE_INDEX,
    GUILD_RANK_LEADER,
    GUILD_RANK_MEMBER,
    GUILD_RANK_OFFICER,
    VALUES_DELIMITER,
    Cost,
)
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger
from sfbot.session import GameSession
from sfbot.state import PlayerState

MAX_GUILD_PORTAL_ENEMIES = 50
MAX_GUILD_RAIDS = 50
GUILD_RAID_BATTLE_ID = 1_000_000
GOLD_ONLY_GUILD_SKILL_MAX_LEVEL = 5
GOLD_ONLY_PET_MAX_LEVEL = 10

GUILD_JOINED_RANKS = {GUILD_RANK_LEADER, GUILD_RANK_OFFICER, GUILD_RANK_MEMBER}

_UPGRADE_COSTS = {
    0: Cost(silver=5_00),
    1: Cost(silver=10_00),
    2: Cost(silver=25_00),
    3: Cost(silver=100_00),
    4: Cost(silver=250_00),
}


def get_upgrade_cost(level: int) -> Cost:
    return _UPGRADE_COSTS.get(level, Cost(mushrooms=1))


class Guild:
    """Guild fights, portal, and hydra management."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self.is_in_guild: bool = False
        self._parse()

    def _parse(self) -> None:
        data = self.session.login_data

        raw = data.get("owngroupsave.groupSave", "")
        group = raw.split(VALUES_DELIMITER)

        self.is_in_guild = bool(raw)

        if not self.is_in_guild:
            return

        self.guild_name: str = data.get("owngroupname.r", "")

        vals = [int(x) if x.lstrip("-").isdigit() else 0 for x in group if x]
        self.attacking_guild: int = vals[GUILD_ATTACK_GUILD_INDEX]
        self.attacking_time: int = vals[GUILD_ATTACK_TIME_INDEX]
        self.defending_guild: int = vals[GUILD_DEFEND_GUILD_INDEX]
        self.defending_time: int = vals[GUILD_DEFEND_TIME_INDEX]
        self.portal_life: int = vals[GUILD_PORTAL_LIFE_INDEX] >> 16

        self.portal_defeated: int = vals[GUILD_PORTAL_DEFEATED_INDEX] >> 16
        self.finished_raids: int = vals[GUILD_FINISHED_RAIDS_INDEX]
        self.hydra_life: int = vals[GUILD_HYDRA_LIFE_INDEX]
        self.hydra_max_life: int = vals[GUILD_HYDRA_MAX_LIFE_INDEX]

        cgroup = data.get("charactergroup", "").split(VALUES_DELIMITER)
        cvals = [int(x) for x in cgroup if x]
        self.own_treasure_skill: int = cvals[CHARACTER_GROUP_TREASURE_SKILL_INDEX]
        self.own_instructor_skill: int = cvals[CHARACTER_GROUP_INSTRUCTOR_SKILL_INDEX]
        self.own_pet_level: int = cvals[CHARACTER_GROUP_PET_SKILL_INDEX]
        self.hydra_next_battle: int = cvals[CHARACTER_GROUP_HYDRA_NEXT_BATTLE_INDEX]
        self.hydra_remaining_fights: int = cvals[CHARACTER_GROUP_HYDRA_REMAINING_INDEX]
        self.joined_timestamp: int = (
            cvals[CHARACTER_GROUP_JOINED_INDEX]
            if len(cvals) > CHARACTER_GROUP_JOINED_INDEX
            else 0
        )

        self.treasure_upgrade_cost: Cost = get_upgrade_cost(self.own_treasure_skill)
        self.instructor_upgrade_cost: Cost = get_upgrade_cost(self.own_instructor_skill)

        self.member_count: int = vals[GUILD_MEMBER_COUNT_INDEX]
        knights_raw = data.get("owngroupknights.r", "").strip(",")
        if knights_raw:
            knight_vals = [int(x) for x in knights_raw.split(",") if x.isdigit()]
            self.total_knights: int = sum(
                k
                for i, k in enumerate(knight_vals[: self.member_count])
                if vals[GUILD_MEMBER_RANK_BASE_INDEX + i] in GUILD_JOINED_RANKS
            )
        else:
            self.total_knights: int = 0

        member_names = data.get("owngroupmember.r", "").split(",")
        player_name = self.session.player_name
        self._own_member_idx: int | None = None
        for index, name in enumerate(member_names):
            if name == player_name:
                self._own_member_idx = index
                break

        self.attack_joined: bool = False
        self.defense_joined: bool = False
        self.portal_fought_today: bool = False

        if self._own_member_idx is not None:
            battles_raw = (
                vals[GUILD_MEMBER_BATTLES_BASE_INDEX + self._own_member_idx] % 100
            )
            self.attack_joined = battles_raw >= 10  # Attack=10, Both=11
            self.defense_joined = battles_raw % 10 == 1  # Defense=1, Both=11

            portal_ts = vals[
                GUILD_MEMBER_PORTAL_FOUGHT_BASE_INDEX + self._own_member_idx
            ]
            if portal_ts > 0:
                server_now = self.session.server_time()
                today = datetime.fromtimestamp(server_now, tz=timezone.utc).date()
                fought_date = datetime.fromtimestamp(portal_ts, tz=timezone.utc).date()
                self.portal_fought_today = fought_date == today

    def refresh(self) -> None:
        self._parse()

    @property
    def is_completed(self) -> bool:
        if not self.is_in_guild:
            return True
        return not (
            self.has_attack or self.has_defense or self.can_hydra or self.can_portal
        )

    @property
    def is_24h_member(self) -> bool:
        if not self.is_in_guild:
            return False
        if self.joined_timestamp <= 0:
            return True
        return self.session.server_time() - self.joined_timestamp >= 86400

    @property
    def has_attack(self) -> bool:
        if not self.is_in_guild:
            return False
        if self.attack_joined:
            return False
        return self.attacking_guild > 1

    @property
    def has_defense(self) -> bool:
        if not self.is_in_guild:
            return False
        if self.defense_joined:
            return False
        return self.defending_guild > 1

    @property
    def can_raid(self) -> bool:
        if not self.is_in_guild:
            return False
        if self.finished_raids >= MAX_GUILD_RAIDS:
            return False
        if self.attacking_guild > 1 or self.defending_guild > 1:
            return False
        server_now = self.session.server_time()
        if self.attacking_time > 0 and self.attacking_time > server_now:
            return False
        return True

    @property
    def can_portal(self) -> bool:
        if not self.is_in_guild:
            return False
        if self.portal_fought_today:
            return False
        if self.portal_defeated >= MAX_GUILD_PORTAL_ENEMIES:
            return False
        return self.portal_life > 0

    @property
    def can_hydra(self) -> bool:
        if not self.is_in_guild:
            return False
        if self.hydra_remaining_fights <= 0:
            return False
        if self.hydra_life <= 0:
            return False
        now = self.session.server_time()
        if self.hydra_next_battle > 0 and self.hydra_next_battle > now:
            return False
        return True

    async def join_attack_async(self) -> None:
        """Join an active guild attack."""
        await self.session.request_and_update_async("GroupReadyAttack", "")

    async def join_defense_async(self) -> None:
        """Join an active guild defense."""
        await self.session.request_and_update_async("GroupReadyDefense", "")

    async def portal_battle_async(self) -> None:
        """Enter the guild portal battle."""
        await self.session.request_and_update_async("GroupPortalBattle", "")

    async def hydra_battle_async(self) -> None:
        """Fight the guild hydra."""
        await self.session.request_and_update_async("GroupPetBattle", "0")

    async def upgrade_treasure_async(self) -> None:
        await self.session.request_and_update_async(
            "GroupSkillIncrease", f"0/{self.own_treasure_skill}"
        )

    async def upgrade_instructor_async(self) -> None:
        await self.session.request_and_update_async(
            "GroupSkillIncrease", f"1/{self.own_instructor_skill}"
        )

    async def upgrade_pet_async(self) -> None:
        await self.session.request_and_update_async(
            "GroupSkillIncrease", f"2/{self.own_pet_level}"
        )

    def should_upgrade_treasure(self, state: PlayerState) -> bool:
        if not self.is_in_guild:
            return False
        if self.own_treasure_skill >= GOLD_ONLY_GUILD_SKILL_MAX_LEVEL:
            return False
        cost = self.treasure_upgrade_cost
        if cost.mushrooms > 0:
            return False
        return state.silver_total >= cost.silver

    def should_upgrade_instructor(self, state: PlayerState) -> bool:
        if not self.is_in_guild:
            return False
        if self.own_instructor_skill >= GOLD_ONLY_GUILD_SKILL_MAX_LEVEL:
            return False
        cost = self.instructor_upgrade_cost
        if cost.mushrooms > 0:
            return False
        return state.silver_total >= cost.silver

    def should_upgrade_pet(self, state: PlayerState) -> bool:
        if not self.is_in_guild:
            return False
        if self.own_pet_level >= GOLD_ONLY_PET_MAX_LEVEL:
            return False
        cost = get_upgrade_cost(self.own_pet_level)
        if cost.mushrooms > 0:
            return False
        return state.silver_total >= cost.silver

    def should_upgrade_skills(self, state: PlayerState) -> bool:
        return (
            self.should_upgrade_instructor(state)
            or self.should_upgrade_treasure(state)
            or self.should_upgrade_pet(state)
        )

    async def upgrade_skills_async(self, state: PlayerState) -> None:
        logger = get_main_logger()

        if self.should_upgrade_instructor(state):
            try:
                await self.upgrade_instructor_async()
                self.refresh()
                logger.info(
                    f"Guild instructor: upgraded to {self.own_instructor_skill}"
                )
            except APIError as exc:
                logger.warning(f"Guild instructor: {exc}")

        if self.should_upgrade_treasure(state):
            try:
                await self.upgrade_treasure_async()
                self.refresh()
                logger.info(f"Guild treasure: upgraded to {self.own_treasure_skill}")
            except APIError as exc:
                logger.warning(f"Guild treasure: {exc}")

        if self.should_upgrade_pet(state):
            try:
                await self.upgrade_pet_async()
                self.refresh()
                logger.info(f"Guild pet: upgraded to {self.own_pet_level}")
            except APIError as exc:
                logger.warning(f"Guild pet: {exc}")

    async def run_daily_async(self) -> None:
        """Join attack/defense and fight hydra/portal if available."""
        logger = get_main_logger()
        self.refresh()

        if self.has_attack:
            try:
                await self.join_attack_async()
                logger.info("Guild attack: registered")
            except APIError as exc:
                logger.warning(f"Guild attack: {exc}")

        if self.has_defense:
            try:
                await self.join_defense_async()
                logger.info("Guild defense: registered")
            except APIError as exc:
                logger.warning(f"Guild defense: {exc}")

        if self.can_hydra:
            try:
                await self.hydra_battle_async()
                logger.info("Hydra: done")
            except APIError as exc:
                logger.warning(f"Hydra: {exc}")

    async def run_portal_async(self) -> None:
        """Fight the guild portal if available."""
        if not self.can_portal:
            return
        try:
            await self.portal_battle_async()
            get_main_logger().info("Portal: done")
        except APIError as exc:
            get_main_logger().warning(f"Portal: {exc}")

    def status(self) -> None:
        if not self.is_in_guild:
            print("Not in a guild")
            return

        print(f"\n=== Guild: {self.guild_name} ===")
        print(f"  Raids completed: {self.finished_raids}/{MAX_GUILD_RAIDS}")
        if self.has_attack:
            print(f"  Attack active: guild #{self.attacking_guild}")
        else:
            print("  No active attack")
        if self.has_defense:
            print(f"  Defense active: guild #{self.defending_guild}")
        else:
            print("  No active defense")
        print(f"  Portal: {self.portal_life}% HP, {self.portal_defeated} defeated")
        if self.hydra_max_life > 0:
            print(
                f"  Hydra: {self.hydra_life:,}/{self.hydra_max_life:,} HP, {self.hydra_remaining_fights} fights left"
            )
        else:
            print("  Hydra: not available")
