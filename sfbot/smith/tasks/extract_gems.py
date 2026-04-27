from sfbot import Bot
from sfbot.constants import SMITH_UNLOCK_LEVEL, GemAttr
from sfbot.fortress.fortress import BuildingType
from sfbot.gems.utils import calc_average_gem_attribute
from sfbot.logging import get_main_logger

EXTRACT_GEM_ATTRS: set[GemAttr] = {GemAttr.LEGENDARY, GemAttr.BLACK}


# Proactively extract valuable legendary/black gems from backpack items.
# Without this, gems stay trapped in junk items unless the free-slot chain
# reaches stage 14, which rarely happens when earlier stages free a slot.


def should_run(bot: Bot) -> bool:
    return bot.character.level >= SMITH_UNLOCK_LEVEL


async def run(bot: Bot) -> None:
    logger = get_main_logger()

    level = bot.character.level
    mine_level = bot.fortress.building_levels.get(BuildingType.GEM_MINE, 0)
    total_knights = (
        bot.guild.total_knights if bot.guild.is_in_guild else bot.fortress.hok_level
    )
    average_single_attr_gem = calc_average_gem_attribute(
        level, total_knights, mine_level
    )

    if not bot.inventory.get_items_with_gems():
        return

    while True:
        slot = bot.inventory.get_item_with_extractable_gem(
            average_single_attr_gem, EXTRACT_GEM_ATTRS
        )
        if not slot or not slot.item:
            return

        item = slot.item
        success = await bot.smith.extract_gem_from_slot_async(
            slot.wire, item.item_type, item.model, item.cost.silver, item.cost.mushrooms
        )
        if success:
            logger.info("Smith: extracted gem")
            logger.info(f"  Item: {item.format()}")
            logger.info(f"  Gem:  {item.inserted_gem.format()}")  # type: ignore
            await bot.poll_async()
        else:
            logger.warning(f"Smith: gem extraction failed for {item.format()}")
            return
