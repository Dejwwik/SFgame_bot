import asyncio

from sfbot import Bot
from sfbot.arena_manager.constants import ARENA_MANAGER_UNLOCK_LEVEL, IdleBuildingType
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    if bot.character.level < ARENA_MANAGER_UNLOCK_LEVEL:
        return False
    if not bot.arena_manager.is_unlocked:
        return False
    return bot.arena_manager.get_next_upgrade() is not None


async def run(bot: Bot) -> None:
    am = bot.arena_manager
    idx = 0
    upgraded: dict[IdleBuildingType, tuple[int, int]] = {}
    while True:
        result = am.get_next_upgrade(idx)
        if result is None:
            break
        building_type, amount, idx = result
        if building_type not in upgraded:
            upgraded[building_type] = (am.buildings[building_type].level, 0)
        await am.upgrade_building_async(building_type, amount)
        await asyncio.sleep(0.02)
        start, inc = upgraded[building_type]
        upgraded[building_type] = (start, inc + amount.value)
    for bt, (start, inc) in upgraded.items():
        if inc:
            get_main_logger().info(f"Arena Manager: {bt.name} {start} -> {start + inc}")
    am.mark_post_upgrade_cycle()
