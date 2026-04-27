from sfbot import Bot
from sfbot.constants import PotionAttributeType, PotionSize
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    return bot.inventory.has_potions_for_dungeon(
        bot.character.main_attr,
        bot.character.dungeon_potion_credits,
    )


async def run(bot: Bot) -> None:
    main_attr = bot.character.main_attr
    main_potion_attr = PotionAttributeType(main_attr.value)

    # Kill active potions that aren't part of the dungeon set
    for active in list(bot.character.potions):
        p = active.potion
        keep = (
            p.attr == PotionAttributeType.HP
            or (
                p.attr == PotionAttributeType.CONSTITUTION
                and p.size == PotionSize.LARGE
            )
            or (p.attr == main_potion_attr and p.size == PotionSize.LARGE)
        )
        if not keep:
            await bot.character.kill_potion_async(active.slot)

    potions = bot.inventory.get_potions_for_dungeon(
        main_attr, bot.character.dungeon_potion_credits
    )

    for potion in potions:
        await bot.inventory.use_potion_async(potion.wire, potion.item)

    bot.character.refresh()
    if bot.character.is_dungeon_ready:
        get_main_logger().info("Elixir: dungeon potions are ready")
