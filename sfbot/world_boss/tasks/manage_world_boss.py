from sfbot import Bot
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    return True


async def run(bot: Bot) -> None:
    try:
        await bot.world_boss.manage_async()
    except APIError as exc:
        get_main_logger().warning(f"World Boss: {exc}")
