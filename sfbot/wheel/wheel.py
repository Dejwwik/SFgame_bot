from dataclasses import dataclass
from datetime import datetime

from sfbot.constants import (
    CHARACTER_LEVEL_INDEX,
    VALUES_DELIMITER,
    Event,
)
from sfbot.exceptions import APIError
from sfbot.inventory import Inventory, InventorySlot
from sfbot.logging import get_main_logger
from sfbot.session import GameSession
from sfbot.state import PlayerState
from sfbot.utils import format_silver


def _find_wheel_result(result: dict[str, str]) -> str:
    # Sometime hits wheelresult and sometimes wheelresult(2) not sure why.
    for key, value in result.items():
        if key.startswith("wheelresult"):
            return value
    raise APIError(f"Wheel: no result in response (keys={list(result.keys())})")


# --- Wheel response field indices ---
WHEEL_SPINS_TODAY_INDEX = 1
WHEEL_NEXT_FREE_SPIN_INDEX = 2

# --- Wheel reward field indices ---
WHEEL_REWARD_TYPE_INDEX = 0
WHEEL_REWARD_AMOUNT_INDEX = 1

MAX_SPINS_PER_DAY = 20
MAX_SPINS_PER_DAY_EVENT = 40
LUCKY_COINS_PER_SPIN = 10


def get_max_spins_per_day(state: PlayerState) -> int:
    if state.has_event(Event.LUCKY_DAY):
        return MAX_SPINS_PER_DAY_EVENT
    return MAX_SPINS_PER_DAY


@dataclass(slots=True)
class SpinResult:
    """Parsed result of a wheel of fortune spin."""

    reward_type: int
    reward_amount: int


@dataclass(slots=True)
class WheelConfig:
    use_lucky_coins: bool = True
    use_mushrooms: bool = False


class Wheel:
    """Wheel of Fortune (Dr. Abawuwu)."""

    LUCKY_COINS = 0
    MUSHROOMS = 1
    FREE_TURN = 2

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self._parse()
        self.config = WheelConfig()

    def _parse(self) -> None:
        data = self.session.login_data
        wheel = data["wheel"].split(VALUES_DELIMITER)
        self.spins_today: int = int(wheel[WHEEL_SPINS_TODAY_INDEX])
        self.next_free_spin: int = int(wheel[WHEEL_NEXT_FREE_SPIN_INDEX])

    @property
    def is_upgraded(self) -> bool:
        character_data = self.session.login_data["ownplayersavecharacter"].split(
            VALUES_DELIMITER
        )
        character_values = [int(x) for x in character_data if x]
        level = character_values[CHARACTER_LEVEL_INDEX] & 0xFFFF
        has_pets = any(key.startswith("pets") for key in self.session.login_data)
        has_underworld = any(
            key.startswith("underworld") for key in self.session.login_data
        )
        return level >= 95 and has_pets and has_underworld

    @property
    def is_free(self) -> bool:
        """True if a free spin is available (accounting for server time offset)."""
        if self.spins_today == 0:
            return True
        if self.next_free_spin <= 0:
            return False
        return self.next_free_spin <= self.session.server_time()

    def is_completed(self, state: PlayerState) -> bool:
        if self.is_free:
            return False

        if self.config.use_lucky_coins and state.lucky_coins >= LUCKY_COINS_PER_SPIN:
            return False

        if self.config.use_mushrooms and state.mushrooms > 0:
            return False

        return True

    def refresh(self) -> None:
        self._parse()

    def status(self) -> None:
        print(f"  Spins today: {self.spins_today}")
        print(f"  Free spin available: {self.is_free}")
        if self.next_free_spin > 0:
            local_ts = self.next_free_spin - self.session.server_time_diff
            print(f"  Next free spin: {datetime.fromtimestamp(local_ts)}")

    def describe_reward(self, result: SpinResult) -> str:
        reward_type = result.reward_type
        amount = result.reward_amount

        if reward_type == 0:
            return f"{amount:,} mushrooms"
        if reward_type == 1:
            resource_name = "arcane" if self.is_upgraded else "wood"
            return f"{amount:,} {resource_name}"
        if reward_type == 2:
            return f"{amount:,} experience (XL)"
        if reward_type == 3:
            return "pet item" if self.is_upgraded else f"{amount:,} stone"
        if reward_type == 4:
            return f"{format_silver(amount)} (XL)"
        if reward_type == 5:
            return "item"
        if reward_type == 6:
            return f"{amount:,} wood (XL)"
        if reward_type == 7:
            return f"{amount:,} experience"
        if reward_type == 8:
            return f"{amount:,} stone (XL)"
        if reward_type == 9:
            return f"{amount:,} souls" if self.is_upgraded else format_silver(amount)
        return f"type={reward_type}, amount={amount}"

    async def spin_async(self, state: PlayerState, inventory: Inventory) -> None:
        """Async version of spin."""

        # Prefer free turn, then lucky coins, then mushrooms.
        if self.is_free:
            payment = self.FREE_TURN
        elif self.config.use_lucky_coins and state.lucky_coins >= LUCKY_COINS_PER_SPIN:
            payment = self.LUCKY_COINS
        elif self.config.use_mushrooms and state.mushrooms > 0:
            payment = self.MUSHROOMS
        else:
            raise ValueError(
                "Wheel spin is not free and no eligible payment is available"
            )

        # Snapshot occupied slot indices before spin
        old_slots, _ = inventory.get_backpack()

        result = await self.session.request_and_update_async(
            "WheelOfFortune", str(payment)
        )

        raw = _find_wheel_result(result)
        vals = list(map(int, raw.split(VALUES_DELIMITER)))

        logger = get_main_logger()

        spin = SpinResult(
            reward_type=vals[WHEEL_REWARD_TYPE_INDEX],
            reward_amount=vals[WHEEL_REWARD_AMOUNT_INDEX],
        )

        # If the reward is an item, lets log what actually was won
        # Its not neccesary but its nice to know what you got from the spin
        if spin.reward_type == 5:
            new_slot = self._find_new_item(inventory, old_slots)
            if new_slot and new_slot.item:
                logger.info(f"Wheel: won {new_slot.item.format()}")
            else:
                logger.info("Wheel: won item")
        else:
            logger.info(f"Wheel: won {self.describe_reward(spin)}")

    @staticmethod
    def _find_new_item(
        inventory: Inventory, old_slots: list[InventorySlot]
    ) -> InventorySlot | None:
        """Find the slot that became occupied after the spin."""
        slots, _ = inventory.get_backpack()

        for new_slot, old_slot in zip(slots, old_slots):
            if new_slot.item and not old_slot.item:
                return new_slot

        return None
