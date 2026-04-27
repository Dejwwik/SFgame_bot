from sfbot import Bot
from sfbot.constants import TOILET_UNLOCK_LEVEL
from sfbot.exceptions import APIError
from sfbot.items.comparison import ITEM_TYPE_TO_EQUIP_SLOT, ComparisonProfile
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    slots, _ = bot.inventory.get_backpack()
    for slot in slots:
        item = slot.item
        if not item:
            continue
        if item.item_type in ITEM_TYPE_TO_EQUIP_SLOT:
            return True
    return False


async def ensure_best_inventory_items_equipped(
    bot: Bot, profiles: list[ComparisonProfile]
) -> bool:
    """Try equipping inventory items until no more improvements. Returns True if anything equipped."""
    any_equipped = False
    equipped_wires: set[str] = set()
    while True:
        equip_wire = await bot.inventory.equip_best_item_async(
            bot.character.level, profiles, equipped_wires
        )
        if equip_wire is None:
            break
        equipped_wires.add(equip_wire)
        any_equipped = True
    return any_equipped


async def wash_inventory_items(bot: Bot) -> bool:
    """Wash all non-washed equippable items in inventory via toilet."""
    logger = get_main_logger()
    washed_any = False
    for slot in bot.inventory.get_washable_items():
        item = slot.item
        if not item:
            continue
        if item.char_class is not None and item.char_class != bot.character.char_class:
            continue
        try:
            await bot.toilet.wash_async(slot.wire)
        except APIError as exc:
            logger.warning(
                f"Equip: could not wash {item.item_type.name}: {exc} — {item.format()}"
            )
            continue
        class_label = item.char_class.name.lower() if item.char_class else "everyone"
        logger.info(f"Equip: washed {item.item_type.name} for {class_label}")
        logger.info(f"\t{item.format()}")
        washed_any = True
    return washed_any


# This function ensures all the best items are equipped and inventory items (equippable) are useless
# Then we can sell them or dismantle them or extract gem from it.


async def run(bot: Bot) -> None:
    profiles = bot.build_comparison_profiles()

    # Phase 1: Equip all beneficial items from inventory
    await ensure_best_inventory_items_equipped(bot, profiles)

    # Phase 2: Wash-equip cycle (requires toilet)
    if bot.character.level < TOILET_UNLOCK_LEVEL:
        return

    while True:
        washed_any = await wash_inventory_items(bot)
        if not washed_any:
            break

        bot.refresh()

        equipped_any = await ensure_best_inventory_items_equipped(bot, profiles)
        if not equipped_any:
            break
