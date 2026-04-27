from sfbot import Bot
from sfbot.underworld.constants import UNLOCK_LEVEL


def should_run(bot: Bot) -> bool:
    if bot.character.level < UNLOCK_LEVEL:
        return False
    if not bot.underworld.is_unlocked:
        return False
    uw = bot.underworld
    if uw.upgrade_is_finished:
        return True
    if not uw.is_upgrading:
        if uw.pick_upgrade(bot.resources.silver_total, bot.resources.souls) is not None:
            return True
    return False


async def run(bot: Bot) -> None:
    uw = bot.underworld

    if uw.upgrade_is_finished:
        await uw.finish_upgrade_async()

    uw.refresh()

    if not uw.is_upgrading:
        building = uw.pick_upgrade(bot.resources.silver_total, bot.resources.souls)
        if building is not None:
            await uw.upgrade_building_async(building)
