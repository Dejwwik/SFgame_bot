from sfbot import Bot
from sfbot.constants import SMITH_UNLOCK_LEVEL, EquipmentSlot
from sfbot.items.comparison import (
    get_equip_wire_position,
    profile_equipped_items,
)
from sfbot.logging import get_main_logger

MAX_UPGRADE_LEVEL = 3


def should_run(bot: Bot) -> bool:
    return bot.character.level >= SMITH_UNLOCK_LEVEL


async def run(bot: Bot) -> None:
    logger = get_main_logger()
    profiles = bot.build_comparison_profiles()

    for target_level in range(1, MAX_UPGRADE_LEVEL + 1):
        for profile in profiles:
            items = profile_equipped_items(bot.session, profile)
            for slot in EquipmentSlot:
                item = items[slot]
                if item is None:
                    continue
                if item.upgrades > MAX_UPGRADE_LEVEL:
                    continue
                if item.upgrades >= target_level:
                    continue

                wire = get_equip_wire_position(slot, profile)
                success = await bot.smith.upgrade_item_async(
                    wire,
                    item.item_type,
                    item.model,
                    item.cost.silver,
                    item.cost.mushrooms,
                )
                if success:
                    display_name = (
                        profile.companion.display_name
                        if profile.companion
                        else bot.session.player_name
                    )
                    logger.info(
                        f"Smith: upgraded {display_name} {slot.name} to level {target_level}"
                    )
                    await bot.poll_async()
                else:
                    return
