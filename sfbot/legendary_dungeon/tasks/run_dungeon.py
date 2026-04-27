from sfbot import Bot
from sfbot.constants import LEGENDARY_DUNGEON_UNLOCK_LEVEL
from sfbot.exceptions import APIError
from sfbot.legendary_dungeon.constants import (
    START_HP_THRESHOLD,
    URGENT_HP_THRESHOLD,
    URGENT_TIME_REMAINING,
)
from sfbot.legendary_dungeon.models import DungeonStage
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    if bot.character.level < LEGENDARY_DUNGEON_UNLOCK_LEVEL:
        return False
    ld = bot.legendary_dungeon
    if not ld.is_active:
        return False
    if ld.dungeon is None:
        return False
    d = ld.dungeon
    if d.stage == DungeonStage.COMPLETED:
        return False
    if d.stage == DungeonStage.NOT_ENTERED:
        return True
    if not d.is_alive:
        healed = ld.healing_pct()
        if healed >= START_HP_THRESHOLD:
            return True
        time_left = ld.end_ts - ld.session.server_time()
        if time_left < URGENT_TIME_REMAINING and healed >= URGENT_HP_THRESHOLD:
            return True
        return False
    return True


async def run(bot: Bot) -> None:
    await bot.ensure_free_slot()
    try:
        await bot.legendary_dungeon.run_async()
    except APIError as exc:
        get_main_logger().warning(f"Dungeon: {exc}")
