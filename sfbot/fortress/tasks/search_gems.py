from sfbot import Bot
from sfbot.fortress.fortress import UNLOCK_LEVEL, BuildingType


def should_run(bot: Bot) -> bool:
    if bot.character.level < UNLOCK_LEVEL:
        return False
    if not bot.fortress.is_unlocked:
        return False
    f = bot.fortress
    if f.building_level(BuildingType.GEM_MINE) < 1:
        return False
    if f.upgrade_target == BuildingType.GEM_MINE:
        return False
    if f.gem_search_is_finished:
        return True
    return not f.is_gem_searching


async def run(bot: Bot) -> None:
    f = bot.fortress
    if f.gem_search_is_finished:
        await f.finish_gem_search_async()

    f.refresh()
    if f.is_gem_searching:
        return

    # Don't start a new search if gem mine is next in the upgrade queue
    next_building = f.pick_upgrade(
        bot.resources.wood, bot.resources.stone, bot.resources.silver_total
    )
    if next_building == BuildingType.GEM_MINE:
        return

    await f.start_gem_search_async()
