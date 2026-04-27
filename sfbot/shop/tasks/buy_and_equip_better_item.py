from sfbot import Bot
from sfbot.items.comparison import ComparisonProfile
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    return not bot.shop.is_done("better_items")


async def run(bot: Bot) -> None:
    profiles: list[ComparisonProfile] = bot.build_comparison_profiles()
    better_item = bot.shop.find_satisfable_best_item(
        bot.character.level,
        profiles,
        bot.resources.mushrooms,
        bot.resources.silver_total,
    )
    if not better_item:
        get_main_logger().info("Shop: no better items found in either shop")
        bot.shop.mark_done("better_items")
        return

    await bot.ensure_free_slot()

    bought = await bot.shop.buy_and_equip_item_async(bot.inventory, better_item)
    if bought:
        await bot.ensure_best_items_are_equipped()
        await bot.ensure_best_gems_are_equipped()
