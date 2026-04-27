from sfbot import Bot
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    return bot.daily_reward.has_claimable


async def run(bot: Bot) -> None:
    try:
        await bot.daily_reward.claim_all_async()
    except APIError as exc:
        get_main_logger().warning(f"Daily: {exc}")
