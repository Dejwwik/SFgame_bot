from datetime import datetime, timezone

from sfbot import Bot
from sfbot.constants import DICE_UNLOCK_LEVEL, DicePayment, DiceType
from sfbot.dungeon.constants import LOCKED
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger

# Use hourglasses to finish remaining dice rolls within this many hours before midnight
HOURGLASS_HOURS_BEFORE_MIDNIGHT = 1


def _is_near_midnight(bot: Bot) -> bool:
    """True if server time is within HOURGLASS_HOURS_BEFORE_MIDNIGHT of midnight."""
    server_ts = bot.session.server_time()
    server_dt = datetime.fromtimestamp(server_ts, tz=timezone.utc)
    hours_left = 24 - server_dt.hour
    return hours_left <= HOURGLASS_HOURS_BEFORE_MIDNIGHT


def should_run(bot: Bot) -> bool:
    if bot.character.level < DICE_UNLOCK_LEVEL:
        return False
    if bot.dungeon.tower_progress == LOCKED:
        return False
    if bot.dice.is_completed:
        return False
    if bot.dice.is_free:
        return True
    # Near midnight: use hourglasses to finish remaining rolls
    if _is_near_midnight(bot) and bot.resources.hourglasses > 0:
        return True
    return False


async def run(bot: Bot) -> None:
    dice = bot.dice

    if dice.is_completed:
        return

    payment = DicePayment.FREE
    if not dice.is_free:
        if _is_near_midnight(bot) and bot.resources.hourglasses > 0:
            payment = DicePayment.HOURGLASS
        else:
            return

    epic_event = bot.events.epic_luck_event
    if epic_event:
        await bot.ensure_free_slot()

    try:
        # SOULS dice type becomes epic items during Epic Good Luck event
        prefer = DiceType.SOULS if epic_event else None
        result = await dice.play_async(prefer=prefer, payment=payment)
        if epic_event and result.reward_type == DiceType.SOULS:
            reward = "EPIC item"
        elif result.reward_type:
            reward = f"{result.reward_amount:,} {result.reward_type.name}"
        else:
            reward = "nothing"
        prefix = "Dice (hourglass)" if payment == DicePayment.HOURGLASS else "Dice"
        get_main_logger().info(f"{prefix}: won {reward}")

    except (ValueError, APIError) as exc:
        get_main_logger().warning(f"Dice: {exc}")
