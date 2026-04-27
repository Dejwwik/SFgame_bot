from sfbot import Bot
from sfbot.constants import GUARD_UNLOCK_LEVEL, Action
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    if bot.character.level < GUARD_UNLOCK_LEVEL:
        return False
    state = bot.get_action_state()
    return state.action == Action.GUARD and state.is_finished


async def run(bot: Bot) -> None:
    try:
        await bot.guard.collect_async()
        get_main_logger().info("Guard: collected reward")
    except APIError as exc:
        get_main_logger().warning(f"Guard collect: {exc}")
