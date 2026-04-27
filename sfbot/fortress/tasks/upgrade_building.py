from sfbot import Bot
from sfbot.fortress.fortress import UNLOCK_LEVEL


def should_run(bot: Bot) -> bool:
    if bot.character.level < UNLOCK_LEVEL:
        return False
    if not bot.fortress.is_unlocked:
        return False
    f = bot.fortress
    if f.upgrade_is_finished:
        return True
    if not f.is_upgrading:
        if f.pick_upgrade(
            bot.resources.wood, bot.resources.stone, bot.resources.silver_total
        ) is not None:
            return True
    if f.can_upgrade_hok(
        bot.resources.wood, bot.resources.stone, bot.resources.silver_total
    ):
        return True
    return False


async def run(bot: Bot) -> None:
    f = bot.fortress

    # Finish pending building upgrade
    if f.upgrade_is_finished:
        await f.finish_upgrade_async()

    f.refresh()

    # Start next building upgrade
    if not f.is_upgrading:
        building = f.pick_upgrade(
            bot.resources.wood, bot.resources.stone, bot.resources.silver_total
        )
        if building is not None:
            await f.upgrade_building_async(building)

    # HoK uses a separate command and doesn't block building upgrades
    if f.can_upgrade_hok(
        bot.resources.wood, bot.resources.stone, bot.resources.silver_total
    ):
        await f.upgrade_hok_async()
