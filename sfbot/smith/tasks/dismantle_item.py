from sfbot import Bot
from sfbot.constants import BLACK_GEM_ATTR_RATIO, SMITH_UNLOCK_LEVEL
from sfbot.fortress.fortress import BuildingType
from sfbot.gems.utils import calc_average_gem_attribute
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    if bot.character.level < SMITH_UNLOCK_LEVEL:
        return False
    return not bot.smith.is_completed


async def run(bot: Bot) -> None:
    logger = get_main_logger()

    level = bot.character.level
    mine_level = bot.fortress.building_levels.get(BuildingType.GEM_MINE, 0)
    total_knights = (
        bot.guild.total_knights if bot.guild.is_in_guild else bot.fortress.hok_level
    )

    black_gem_threshold = (
        calc_average_gem_attribute(level, total_knights, mine_level)
        * BLACK_GEM_ATTR_RATIO
    )
    slot = bot.inventory.get_item_to_dismantle(black_gem_threshold)
    if slot and slot.item:
        item = slot.item
        cost = bot.smith.dismantle_cost(item.item_type)
        if bot.smith.dismantles_left < cost:
            return
        success = await bot.smith.dismantle_slot_async(
            slot.wire, item.item_type, item.model, item.cost.silver, item.cost.mushrooms
        )
        if success:
            logger.info(f"Smith: dismantled {item.format()}")
        else:
            logger.warning(f"Smith: dismantle failed {item.format()}")
