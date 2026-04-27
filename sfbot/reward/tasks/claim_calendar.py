from sfbot import Bot
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    return not bot.calendar_reward.is_completed


async def run(bot: Bot) -> None:
    try:
        await bot.calendar_reward.claim_async()
        get_main_logger().info("Calendar: claimed")
    except APIError as exc:
        get_main_logger().warning(f"Calendar: {exc}")
