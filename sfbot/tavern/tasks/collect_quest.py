from sfbot import Bot
from sfbot.constants import Action
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    state = bot.get_action_state()
    return state.action == Action.QUEST and state.is_finished


async def run(bot: Bot) -> None:
    await bot.ensure_free_slot()
    try:
        await bot.tavern.quests.collect_quest_async()
        get_main_logger().info("Quest: collected reward")
    except APIError as exc:
        get_main_logger().warning(f"Quest collect: {exc}")
