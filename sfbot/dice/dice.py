from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from sfbot.constants import VALUES_DELIMITER, DicePayment, DiceType
from sfbot.session import GameSession

# --- Dice response field indices ---
DICE_NEXT_FREE_INDEX = 0
DICE_REMAINING_INDEX = 1

# --- Dice reward field indices ---
DICE_REWARD_TYPE_INDEX = 0
DICE_REWARD_AMOUNT_INDEX = 1

# --- Game constants ---
DICE_COUNT = 5


@dataclass(slots=True)
class DiceResult:
    """Parsed result of a dice roll."""

    reward_type: DiceType | None
    reward_amount: int


class DiceGame:
    """Dice game - roll 5 dice for resources."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self._parse_availability()

    def _parse_availability(self) -> None:
        data = self.session.login_data
        dice = data["dice"].split(VALUES_DELIMITER)
        self.next_free: int = int(dice[DICE_NEXT_FREE_INDEX])
        self.remaining: int = int(dice[DICE_REMAINING_INDEX])

    @property
    def is_completed(self) -> bool:
        """True when no dice games remain."""
        # Works correctly if there is 20 rolls on event, as there is 10 on normal day.
        return self.remaining <= 0

    @property
    def is_free(self) -> bool:
        if self.next_free <= 0:
            return self.remaining > 0
        return self.next_free <= self.session.server_time()

    def refresh(self) -> None:
        self._parse_availability()

    def status(self) -> None:
        print(f"  Games left: {self.remaining}")
        print(f"  Free roll: {self.is_free}")
        if self.next_free > 0:
            local_ts = self.next_free - self.session.server_time_diff
            print(f"  Next free: {datetime.fromtimestamp(local_ts)}")

    async def _send_roll_async(
        self, dice_params: list[int], payment: DicePayment
    ) -> dict[str, str]:
        params = VALUES_DELIMITER.join(
            [str(payment.value)] + [str(d) for d in dice_params]
        )
        result = await self.session.request_and_update_async("RollDice", params)
        self._parse_availability()
        return result

    @staticmethod
    def _parse_dice(result: dict[str, str]) -> list[DiceType]:
        status = result["dicestatus"].split(VALUES_DELIMITER)
        return [DiceType(int(status[i])) for i in range(DICE_COUNT)]

    @staticmethod
    def _parse_reward(result: dict[str, str]) -> DiceResult:
        if "dicereward" not in result:
            return DiceResult(reward_type=None, reward_amount=0)

        reward = result["dicereward"].split(VALUES_DELIMITER)
        raw_type = int(reward[DICE_REWARD_TYPE_INDEX])

        return DiceResult(
            reward_type=DiceType(raw_type - 1),
            reward_amount=int(reward[DICE_REWARD_AMOUNT_INDEX]),
        )

    async def play_async(
        self,
        prefer: DiceType | None = None,
        *,
        payment: DicePayment = DicePayment.FREE,
    ) -> DiceResult:
        """Async version of play."""
        if payment == DicePayment.FREE and not self.is_free:
            raise ValueError(
                "Dice roll is not free — pass payment=DicePayment.MUSHROOMS or HOURGLASS"
            )

        r1 = await self._send_roll_async([0] * DICE_COUNT, payment)
        dice = self._parse_dice(r1)

        dice_type: DiceType = prefer or Counter(dice).most_common(1)[0][0]
        keep_params = [d.value if d == dice_type else 0 for d in dice]

        r2 = await self._send_roll_async(keep_params, DicePayment.FREE)
        return self._parse_reward(r2)
