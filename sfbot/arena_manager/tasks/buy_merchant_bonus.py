from sfbot import Bot
from sfbot.arena_manager.constants import ARENA_MANAGER_UNLOCK_LEVEL


def should_run(bot: Bot) -> bool:
    if bot.character.level < ARENA_MANAGER_UNLOCK_LEVEL:
        return False
    if not bot.arena_manager.is_unlocked:
        return False
    if not bot.arena_manager.has_merchant_offers:
        return False
    toilet_offers = bot.arena_manager.get_toilet_offers()
    if not toilet_offers:
        return False
    return any(offer.cost <= bot.resources.mushrooms for offer in toilet_offers)


async def run(bot: Bot) -> None:
    am = bot.arena_manager
    toilet_offers = am.get_toilet_offers()
    for offer in toilet_offers:
        if offer.cost <= bot.resources.mushrooms:
            await am.buy_merchant_offer_async(offer)
            break
