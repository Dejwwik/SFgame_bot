from sfbot import Bot
from sfbot.constants import PET_UNLOCK_LEVEL, ItemType
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger
from sfbot.pets.pet_reqs import TimeStatus


def should_run(bot: Bot) -> bool:
    state = bot.get_action_state()
    if not state.is_idle:
        return False

    return not bot.tavern.is_completed(bot.get_player_state())


async def run(bot: Bot) -> None:
    state = bot.get_action_state()
    if not state.is_idle:
        return

    player_state = bot.get_player_state()
    if bot.tavern.should_buy_beer(player_state):
        try:
            await bot.tavern.buy_beer_async()
            get_main_logger().info(
                f"Beer drunked, thirst={bot.tavern.thirst_seconds // 60}min"
            )
        except (ValueError, APIError) as exc:
            get_main_logger().warning(f"Beer: {exc}")

    pet_requirements = []
    if bot.character.level >= PET_UNLOCK_LEVEL:
        pet_requirements = bot.pets.get_todays_pet_requirements(
            player_state.events, bot.session.server_time()
        )
        pet_requirements = [
            r for r in pet_requirements if bot.meets_special_condition(r)
        ]

    # Prioritize pet quest — rarest pet first (sorted by days_per_year)
    egg_quest = None
    if pet_requirements:
        for req in pet_requirements:
            status = req.get_time_status(bot.session.server_time())
            if status == TimeStatus.UPCOMING:
                get_main_logger().info(f"  Pets: waiting for {req.time_of_day.name}")  # type: ignore
                return

            for quest in bot.tavern.quests.quests:
                if quest.item is None and quest.location == req.location:
                    egg_quest = quest
                    break
            if egg_quest:
                break

    # Prioritize epic item bag quest — always pick it
    epic_quest = None
    if not egg_quest:
        for quest in bot.tavern.quests.quests:
            if quest.item is not None and quest.item.item_type == ItemType.EPIC_ITEM_BAG:
                epic_quest = quest
                break

    # Prioritize special quest
    special_quest = None
    if not egg_quest and not epic_quest:
        for quest in bot.tavern.quests.quests:
            if quest.item is not None and quest.item.item_type == ItemType.SPECIAL:
                special_quest = quest
                break

    # Go for pet/epic/special quest if available, otherwise best quest based on preference
    best = egg_quest or epic_quest or special_quest or bot.tavern.quests.get_best_quest(player_state)
    mins, secs = divmod(best.base_length, 60)
    tag = " [egg]" if egg_quest else " [epic]" if epic_quest else " [special]" if special_quest else ""
    get_main_logger().info(
        f"  Quest: {best.location.name} ({mins}m{secs:02d}s, {best.base_silver // 100:,}g){tag}"
    )
    try:
        await bot.tavern.quests.start_quest_async(best.index + 1)
    except APIError as exc:
        get_main_logger().warning(f"Quest start: {exc}")
