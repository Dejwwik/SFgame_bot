from sfbot.constants import VALUES_DELIMITER
from sfbot.constants.enums import ItemType
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger
from sfbot.session import GameSession

BLACKSMITH_ACTION_DISMANTLE = 201
BLACKSMITH_ACTION_GEM_EXTRACT = 203
BLACKSMITH_ACTION_UPGRADE = 204

DAILY_DISMANTLE_LIMIT = 5
EVENT_DISMANTLE_LIMIT = 15
WEAPON_DISMANTLE_COST = 2


class Smith:
    """Blacksmith — item dismantling for metal and arcane dust."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self._parse()

    def _parse(self) -> None:
        data = self.session.login_data
        smith_raw = data["smith"].split(VALUES_DELIMITER)
        self.dismantles_left: int = int(smith_raw[0])

    def refresh(self) -> None:
        self._parse()

    @property
    def is_completed(self) -> bool:
        return self.dismantles_left <= 0

    @property
    def can_dismantle(self) -> bool:
        return self.dismantles_left > 0

    def dismantle_cost(self, item_type: int) -> int:
        return WEAPON_DISMANTLE_COST if item_type == ItemType.WEAPON else 1

    async def dismantle_slot_async(
        self, wire: str, item_type: int, model: int, silver: int, mushrooms: int
    ) -> bool:
        logger = get_main_logger()
        ident = f"{item_type}/{model}/{silver}/{mushrooms}"
        params = f"{wire}/{BLACKSMITH_ACTION_DISMANTLE}/-1/{ident}"
        try:
            await self.session.request_and_update_async("PlayerItemMove", params)
            self._parse()
            return True
        except APIError as exc:
            logger.warning(f"Smith: {exc}")
            return False

    async def extract_gem_from_slot_async(
        self, wire: str, item_type: int, model: int, silver: int, mushrooms: int
    ) -> bool:
        logger = get_main_logger()
        ident = f"{item_type}/{model}/{silver}/{mushrooms}"
        params = f"{wire}/{BLACKSMITH_ACTION_GEM_EXTRACT}/-1/{ident}"
        try:
            await self.session.request_and_update_async("PlayerItemMove", params)
            return True
        except APIError as exc:
            logger.warning(f"Smith: gem extract failed: {exc}")
            return False

    async def upgrade_item_async(
        self, wire: str, item_type: int, model: int, silver: int, mushrooms: int
    ) -> bool:
        logger = get_main_logger()
        ident = f"{item_type}/{model}/{silver}/{mushrooms}"
        params = f"{wire}/{BLACKSMITH_ACTION_UPGRADE}/-1/{ident}"
        try:
            await self.session.request_and_update_async("PlayerItemMove", params)
            return True
        except APIError as exc:
            logger.warning(f"Smith: upgrade failed: {exc}")
            return False
