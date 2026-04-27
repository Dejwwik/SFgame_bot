from sfbot import Bot
from sfbot.constants import Mount
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    return not bot.mounts.is_completed


async def run(bot: Bot) -> None:
    await bot.mounts.ensure_mount_async(
        Mount.TIGER,
        silver_total=bot.resources.silver_total,
        mushrooms=bot.resources.mushrooms,
    )
    get_main_logger().info("Mount: set")
