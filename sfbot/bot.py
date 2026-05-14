import time
from dataclasses import dataclass

from sfbot.arena import Arena
from sfbot.arena_manager import ArenaManager
from sfbot.attributes import Attributes
from sfbot.character import Character
from sfbot.constants import (
    CHARACTER_STATUS_ACTION_INDEX,
    CHARACTER_STATUS_BUSY_UNTIL_INDEX,
    CHARACTER_STATUS_SECONDS_INDEX,
    VALUES_DELIMITER,
    Action,
    Attribute,
    CompanionClass,
    HabitatType,
    PotionAttributeType,
)
from sfbot.constants.enums import GemAttr
from sfbot.constants.limits import SMITH_UNLOCK_LEVEL, TOILET_UNLOCK_LEVEL
from sfbot.dice import DiceGame
from sfbot.dungeon import Dungeon as DungeonSystem
from sfbot.dungeon.constants import FLOORS_PER_DUNGEON, PORTAL_FLOORS, TOWER_FLOORS
from sfbot.events import Events
from sfbot.fortress import Fortress
from sfbot.fortress.fortress import BuildingType
from sfbot.gems.utils import calc_average_gem_attribute
from sfbot.guard import Guard
from sfbot.guild import Guild
from sfbot.inventory import Inventory
from sfbot.inventory.inventory import (
    get_max_potion_size,
)
from sfbot.items.comparison import ComparisonProfile
from sfbot.legendary_dungeon import LegendaryDungeon
from sfbot.logging import get_main_logger
from sfbot.mount import Mounts
from sfbot.persistence import load_opponents, remove_opponent
from sfbot.persistence.accounts import connect_async, upsert_character_stats_async
from sfbot.pets import Pets
from sfbot.pets.pet_reqs import PetRequirement
from sfbot.resources import Resources
from sfbot.reward import CalendarReward, DailyReward, EventReward, MailReward
from sfbot.scrapbook import Scrapbook
from sfbot.session import GameSession
from sfbot.shop import Shop
from sfbot.smith import Smith
from sfbot.state import PlayerState
from sfbot.tavern import Tavern
from sfbot.toilet import Toilet
from sfbot.underworld import Underworld
from sfbot.wheel import Wheel
from sfbot.witch import Witch
from sfbot.world_boss import WorldBoss
from sfbot.expedition import Expedition


@dataclass
class ActionState:
    action: Action
    """Action type id (see :class:`Action` enum: IDLE, GUARD, QUEST, …)."""
    seconds: int
    """Action-specific duration/param (guard hours, quest number, …)."""
    busy_until: int
    """Server unix timestamp when the action finishes."""
    server_time_diff: int
    """Offset to add to local time to get server time."""

    @property
    def is_idle(self) -> bool:
        return self.action == Action.IDLE

    @property
    def _server_now(self) -> int:
        return int(time.time()) + self.server_time_diff

    @property
    def remaining(self) -> int:
        """Seconds remaining until the action finishes (0 if already done)."""
        return max(0, self.busy_until - self._server_now)

    @property
    def is_finished(self) -> bool:
        return self.busy_until <= self._server_now


def parse_ratios(raw: dict[str, float]) -> dict[Attribute, float]:
    return {Attribute[k]: v for k, v in raw.items()}


def parse_companions(
    raw: dict[str, dict[str, float]],
) -> dict[CompanionClass, dict[Attribute, float]]:
    return {CompanionClass[k]: parse_ratios(v) for k, v in raw.items()}


class Bot:
    """Main bot class that composes all game subsystems."""

    def __init__(
        self,
        username: str,
        password_hash: str,
        server: str,
        character_id: str,
        base_attrs_target_ratios: dict[Attribute, float],
        equipment_target_ratios: dict[Attribute, float],
        gem_target_ratios: dict[Attribute, float],
        companion_equipment_ratios: dict[CompanionClass, dict[Attribute, float]],
        companion_gem_ratios: dict[CompanionClass, dict[Attribute, float]],
    ) -> None:
        self.session = GameSession(
            username,
            password_hash,
            server,
            character_id=character_id,
        )
        self.base_attrs_target_ratios: dict[Attribute, float] = base_attrs_target_ratios
        self.equipment_target_ratios: dict[Attribute, float] = equipment_target_ratios
        self.gem_target_ratios: dict[Attribute, float] = gem_target_ratios
        self.companion_equipment_ratios: dict[
            CompanionClass, dict[Attribute, float]
        ] = companion_equipment_ratios
        self.companion_gem_ratios: dict[CompanionClass, dict[Attribute, float]] = (
            companion_gem_ratios
        )

    @classmethod
    def from_db_config(
        cls,
        username: str,
        password_hash: str,
        server: str,
        character_id: str,
        config: dict,
    ) -> "Bot":
        """Create a Bot from a raw JSON config dict (as stored in account_data/)."""
        equip_cfg = config["equipment_attrs_target_ratios"]
        gem_cfg = config["gems_attrs_target_ratios"]
        return cls(
            username,
            password_hash,
            server=server,
            character_id=character_id,
            base_attrs_target_ratios=parse_ratios(config["base_attrs_target_ratios"]),
            equipment_target_ratios=parse_ratios(equip_cfg["main"]),
            gem_target_ratios=parse_ratios(gem_cfg["main"]),
            companion_equipment_ratios=parse_companions(equip_cfg["companions"]),
            companion_gem_ratios=parse_companions(gem_cfg["companions"]),
        )

    async def login_async(self) -> "Bot":
        """Async login and subsystem initialization."""
        await self.session.login_async()
        self.character = Character(self.session)
        self.resources = Resources(self.session)
        self.attributes = Attributes(self.session)
        self.inventory = Inventory(self.session)
        self.tavern = Tavern(self.session)
        self.events = Events(self.session)
        self.guard = Guard(self.session)
        self.shop = Shop(self.session)
        self.witch = Witch(self.session)
        self.guild = Guild(self.session)
        self.arena = Arena(self.session)
        self.mounts = Mounts(self.session)
        self.pets = Pets(self.session)
        self.toilet = Toilet(self.session)
        self.smith = Smith(self.session)
        self.dice = DiceGame(self.session)
        self.dungeon = DungeonSystem(self.session)
        self.wheel = Wheel(self.session)
        self.fortress = Fortress(self.session)
        self.underworld = Underworld(self.session)
        self.legendary_dungeon = LegendaryDungeon(self.session, self.inventory)
        self.calendar_reward = CalendarReward(self.session)
        self.daily_reward = DailyReward(self.session)
        self.event_reward = EventReward(self.session)
        self.mail_reward = MailReward(self.session)
        self.arena_manager = ArenaManager(self.session)
        self.scrapbook = Scrapbook(self.session)
        self.world_boss = WorldBoss(self.session)
        self.expedition = Expedition(self.session)
        self._parse_pending_unlocks()
        return self

    async def poll_async(self) -> None:
        """Async poll server and refresh all subsystems."""
        await self.session.poll_async()
        try:
            self.refresh()
        except KeyError:
            get_main_logger().warning("Session stale, re-logging in")
            await self.session.login_async()
            self.refresh()

    def _parse_pending_unlocks(self) -> None:
        raw = self.session.login_data.get("unlockfeature", "")
        vals = [int(x) for x in raw.split(VALUES_DELIMITER) if x]
        self.pending_unlocks: list[tuple[int, int]] = []
        for i in range(0, len(vals), 2):
            main_id = vals[i]
            sub_id = vals[i + 1] if i + 1 < len(vals) else 0
            if main_id != 0:
                self.pending_unlocks.append((main_id, sub_id))

    async def unlock_feature_async(self, main_ident: int, sub_ident: int) -> None:
        await self.session.request_and_update_async(
            "UnlockFeature", f"{main_ident}/{sub_ident}"
        )

    def refresh(self) -> None:
        """Refresh all subsystems from current login_data."""
        self.character.refresh()
        self.resources.refresh()
        self.events.refresh()
        self.arena.refresh()
        self.tavern.refresh()
        self.witch.refresh()
        self.guild.refresh()
        self.toilet.refresh()
        self.smith.refresh()
        self.wheel.refresh()
        self.dice.refresh()
        self.dungeon.refresh()
        self.mounts.refresh()
        self.pets.refresh()
        self.fortress.refresh()
        self.underworld.refresh()
        self.legendary_dungeon.refresh()
        self.calendar_reward.refresh()
        self.daily_reward.refresh()
        self.event_reward.refresh()
        self.arena_manager.refresh()
        self.scrapbook.parse()
        self.world_boss.refresh()
        self.expedition.refresh()
        self._parse_pending_unlocks()

    def status(self) -> None:
        """Show full status of all subsystems."""
        self.character.show()
        self.resources.show()
        self.tavern.status()

    async def load_arena_opponents_async(self) -> list[str]:
        return await load_opponents(self.session.character_id)

    async def remove_arena_opponent_async(self, name: str) -> None:
        await remove_opponent(self.session.character_id, name)

    def get_action_state(self) -> ActionState:
        """Parse current player action from *characterstatus*."""
        char_status = self.session.login_data["characterstatus"].split(VALUES_DELIMITER)
        values = [int(x) for x in char_status if x]
        return ActionState(
            action=Action(values[CHARACTER_STATUS_ACTION_INDEX]),
            seconds=values[CHARACTER_STATUS_SECONDS_INDEX],
            busy_until=values[CHARACTER_STATUS_BUSY_UNTIL_INDEX],
            server_time_diff=self.session.server_time_diff,
        )

    def get_player_state(self) -> PlayerState:
        return PlayerState(
            events=frozenset(self.events.active),
            silver_total=self.resources.silver_total,
            mushrooms=self.resources.mushrooms,
            lucky_coins=self.resources.lucky_coins,
            hourglasses=self.resources.hourglasses,
        )

    def meets_special_condition(self, req: PetRequirement) -> bool:
        pid = req.pet_id

        # Pet 16: arena rank ≤ 1000 or honor ≥ 50000 — not available on bot
        # Pet 35: guild rank ≤ 100 or guild honor ≥ 2500 — not available on bot
        # Pet 95: pet rank ≤ 100 or pet honor ≥ 4000 — not available on bot

        # Shadow dungeon 12 floor 10
        if pid == 19:
            return self.dungeon.shadow_progress.get(12, 0) >= FLOORS_PER_DUNGEON

        # Pet dungeon 0 (Shadow habitat fully explored)
        if pid == 20:
            return self.pets.habitats[HabitatType.SHADOW].is_explored

        # Tower = 100
        if pid == 39:
            return self.dungeon.light_progress.get(14, 0) >= TOWER_FLOORS

        # Pet dungeon 1 (Light habitat fully explored)
        if pid == 40:
            return self.pets.habitats[HabitatType.LIGHT].is_explored

        # Fortress rank ≤ 100 or fortress honor ≥ 2500
        if pid == 58:
            return self.fortress.rank <= 100 or self.fortress.honor >= 2500

        # Pet dungeon 2 (Earth habitat fully explored)
        if pid == 60:
            return self.pets.habitats[HabitatType.EARTH].is_explored

        # Portal = 50
        if pid == 79:
            return self.dungeon.portal_finished >= PORTAL_FLOORS

        # Pet dungeon 3 (Fire habitat fully explored)
        if pid == 80:
            return self.pets.habitats[HabitatType.FIRE].is_explored

        # Light dungeon 24 floor 10
        if pid == 99:
            return self.dungeon.light_progress.get(24, 0) >= FLOORS_PER_DUNGEON

        # Pet dungeon 4 (Water habitat fully explored)
        if pid == 100:
            return self.pets.habitats[HabitatType.WATER].is_explored

        return True

    def build_comparison_profiles(self) -> list[ComparisonProfile]:
        """Build ComparisonProfile list for main character and companions."""

        profiles: list[ComparisonProfile] = [
            ComparisonProfile(
                self.character.char_class,
                self.character.main_attr,
                self.equipment_target_ratios,
                self.gem_target_ratios,
                base_attrs=self.character.base_attrs,
            ),
        ]

        if not self.character.has_unlocked_companions:
            return profiles

        for companion_class, info in self.character.companions.items():
            # Companions base attrs are mirrored from character but with main attrs swapped.
            # E.g. if main is Mage (INT) and companion is Bert (Warrior/STR),
            # we swap INT↔STR so our INT goes into his STR slot and vice versa.
            base_attrs = self.character.base_attrs.copy()
            if info.char_class.main_attr != self.character.main_attr:
                (
                    base_attrs[info.char_class.main_attr],
                    base_attrs[self.character.main_attr],
                ) = (
                    base_attrs[self.character.main_attr],
                    base_attrs[info.char_class.main_attr],
                )
            profiles.append(
                ComparisonProfile(
                    info.char_class,
                    info.char_class.main_attr,
                    self.companion_equipment_ratios[companion_class],
                    self.companion_gem_ratios[companion_class],
                    companion=companion_class,
                    base_attrs=base_attrs,
                )
            )
        return profiles

    async def ensure_best_items_are_equipped(self):
        from sfbot.inventory.tasks import ensure_best_items_are_equipped as task

        if task.should_run(self):
            await task.run(self)

        await self.poll_async()

    async def ensure_best_gems_are_equipped(self):
        from sfbot.inventory.tasks import ensure_best_gems_are_equipped as task

        if task.should_run(self):
            await task.run(self)

        await self.poll_async()

    async def ensure_free_slot(self):
        if self.inventory.has_free_slot():
            return

        logger = get_main_logger()

        logger.info("Inventory: no free slot, need to free one")
        logger.info("  equipping best items")
        await self.ensure_best_items_are_equipped()

        logger.info("  equipping best gems")
        await self.ensure_best_gems_are_equipped()

        if self.inventory.has_free_slot():
            logger.info("Inventory: freed slot via equipping")
            return

        level = self.character.level
        mine_level = self.fortress.building_levels.get(BuildingType.GEM_MINE, 0)
        total_knights = (
            self.guild.total_knights
            if self.guild.is_in_guild
            else self.fortress.hok_level
        )
        average_single_attr_gem = calc_average_gem_attribute(
            level, total_knights, mine_level
        )

        smith = self.smith if level >= SMITH_UNLOCK_LEVEL else None
        toilet = self.toilet if level >= TOILET_UNLOCK_LEVEL else None

        await self.inventory.ensure_free_slot_async(
            main_potion_attr=PotionAttributeType(self.character.main_attr.value),
            max_potion_size=get_max_potion_size(level),
            smith=smith,
            toilet=toilet,
            keep_gem_attrs={
                GemAttr[self.character.char_class.main_attr.name],
                GemAttr.CONSTITUTION,
                GemAttr.BLACK,
            },
            average_single_attr_gem=average_single_attr_gem,
            profiles=self.build_comparison_profiles(),
            character=self.character,
        )

    async def save_stats(self) -> None:
        """Persist current character stats to DB."""
        conn = await connect_async()
        try:
            await upsert_character_stats_async(
                conn,
                character_id=self.session.character_id,
                level=self.character.level,
                silver_total=self.resources.silver_total,
                mushrooms=self.resources.mushrooms,
                lucky_coins=self.resources.lucky_coins,
            )
        finally:
            await conn.close()
