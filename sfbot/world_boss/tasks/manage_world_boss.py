from sfbot import Bot
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    return bot.world_boss.is_active


async def run(bot: Bot) -> None:
    try:
        await bot.world_boss.manage_async()
    except APIError as exc:
        get_main_logger().warning(f"World Boss: {exc}")
