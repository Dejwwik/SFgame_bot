from sfbot import Bot
from sfbot.constants import GUARD_UNLOCK_LEVEL
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger

GUARD_HOURS = 1


def should_run(bot: Bot) -> bool:
    if bot.character.level < GUARD_UNLOCK_LEVEL:
        return False

    state = bot.get_action_state()
    if not state.is_idle:
        return False

    return bot.tavern.is_completed(bot.get_player_state())


async def run(bot: Bot) -> None:
    try:
        await bot.guard.start_async(hours=GUARD_HOURS)
        get_main_logger().info(f"Guard: started {GUARD_HOURS}h shift")
    except APIError as exc:
        get_main_logger().warning(f"Guard: {exc}")
