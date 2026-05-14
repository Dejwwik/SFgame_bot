from sfbot import Bot
from sfbot.constants import Action
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    if not bot.expedition.is_available:
        return False
    action = bot.get_action_state()
    if action.action == Action.EXPEDITION and not action.is_finished:
        return False
    if bot.expedition.is_waiting:
        return False
    return True


async def run(bot: Bot) -> None:
    try:
        await bot.expedition.run_expedition_async()
    except APIError as exc:
        get_main_logger().warning(f"Expedition: {exc}")
