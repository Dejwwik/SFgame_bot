from sfbot import Bot
from sfbot.fortress.fortress import (
    ATTACK_MAX_CAPACITY_RATIO,
    ATTACK_ROI_THRESHOLD,
    ATTACK_SOLDIER_BUFFER,
    UNLOCK_LEVEL,
)
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    if bot.character.level < UNLOCK_LEVEL:
        return False
    if not bot.fortress.is_unlocked:
        return False
    if bot.fortress.soldiers_after_training < 1:
        return False
    return bot.fortress.has_attack_target


async def run(bot: Bot) -> None:
    logger = get_main_logger()
    f = bot.fortress

    info = await f.fetch_opponent_info_async()
    if info is None:
        return
    advice, raid_wood, raid_stone = info

    soldiers_needed = advice + ATTACK_SOLDIER_BUFFER if advice > 1 else 1
    cost_wood = f.soldier_cost_wood * soldiers_needed
    cost_stone = f.soldier_cost_stone * soldiers_needed
    tag = f"advice={advice} raid={raid_wood}/{raid_stone} cost={cost_wood}/{cost_stone}"

    wood_ok = raid_wood >= cost_wood * ATTACK_ROI_THRESHOLD
    stone_ok = raid_stone >= cost_stone * ATTACK_ROI_THRESHOLD
    too_hard = soldiers_needed > f.soldier_max_capacity * ATTACK_MAX_CAPACITY_RATIO

    if too_hard or not (wood_ok or stone_ok):
        reason = "too hard" if too_hard else "low ROI"
        logger.info(f"Fortress: skip ({reason}) {tag}")
        if f.can_free_reroll:
            await f.reroll_opponent_async()
        return

    if f.available_soldiers < soldiers_needed:
        logger.info(
            f"Fortress: waiting ({f.available_soldiers}/{soldiers_needed} soldiers) {tag}"
        )
        return

    won = await f.attack_async(soldiers=soldiers_needed)
    if won is None:
        return
    if won:
        logger.info(f"Fortress: won {tag}")
    else:
        logger.info(f"Fortress: lost {tag}")
