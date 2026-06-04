import asyncio
import random
from datetime import datetime, time
from typing import Protocol

from sfbot import Bot
from sfbot.arena.tasks import fight_arena as arena_task
from sfbot.arena.tasks import fight_opponent as fight_opponent_task
from sfbot.arena_manager.tasks import buy_merchant_bonus as arena_manager_buy_task
from sfbot.arena_manager.tasks import sacrifice_runes as arena_manager_sacrifice_task
from sfbot.arena_manager.tasks import upgrade_buildings as arena_manager_upgrade_task
from sfbot.attributes.tasks import upgrade_attributes as upgrade_attributes_task
from sfbot.dice.tasks import play_dice as dice_task
from sfbot.dungeon.tasks import fight_dungeon as dungeon_task
from sfbot.dungeon.tasks import fight_portal as dungeon_portal_task
from sfbot.exceptions import (
    GemExtractedAlert,
    InventoryFullError,
    InventoryStuckError,
    KnownAPIError,
    LoginError,
)
from sfbot.fortress.tasks import attack_fortress as fortress_attack_task
from sfbot.fortress.tasks import collect_resources as fortress_collect_task
from sfbot.fortress.tasks import search_gems as fortress_mine_gems_task
from sfbot.fortress.tasks import (
    train_defence_units as fortress_train_defence_units_task,
)
from sfbot.fortress.tasks import train_soldiers as fortress_train_soldiers_task
from sfbot.fortress.tasks import upgrade_building as fortress_building_upgrade_task
from sfbot.fortress.tasks import upgrade_units as fortress_upgrade_units_task
from sfbot.guard.tasks import collect_guard as collect_guard_task
from sfbot.guard.tasks import start_guard as start_guard_task
from sfbot.guild.tasks import do_guild_fights as guild_task
from sfbot.guild.tasks import fight_portal as guild_portal_task
from sfbot.guild.tasks import upgrade_buildings as guild_upgrade_task
from sfbot.inventory.tasks import (
    ensure_best_gems_are_equipped as ensure_best_gems_are_equipped,
)
from sfbot.inventory.tasks import (
    ensure_best_items_are_equipped as ensure_best_items_are_equipped,
)
from sfbot.legendary_dungeon.tasks import run_dungeon as legendary_dungeon_task
from sfbot.logging import BotLogContext, get_bot_main_logger, get_main_logger
from sfbot.mount.tasks import ensure_mount as mount_task
from sfbot.persistence.accounts import (
    connect_async,
    get_all_enabled_characters_async,
    init_db,
    is_character_running_async,
    load_config_json,
)
from sfbot.pets.tasks import feed_pet as feed_pet_task
from sfbot.pets.tasks import fight_pet_dungeon as fight_pet_dungeon_task
from sfbot.pets.tasks import fight_pets as fight_pets_task
from sfbot.pets.tasks import unlock_features as unlock_features_task
from sfbot.potions.tasks import drink_potions as drink_potions_task
from sfbot.potions.tasks import prepare_elixirs_for_dungeons as prepare_elixirs_task
from sfbot.reward.tasks import claim_calendar as calendar_task
from sfbot.reward.tasks import claim_daily_task as daily_reward_task
from sfbot.reward.tasks import claim_event as event_reward_task
from sfbot.reward.tasks import claim_pending as mail_reward_task
from sfbot.scrapbook.tasks import update_queue as scrapbook_task
from sfbot.shop.tasks import buy_and_equip_better_item as buy_better_items_task
from sfbot.shop.tasks import buy_special_items as buy_special_items_task
from sfbot.smith.tasks import dismantle_item as dismantle_item_task
from sfbot.smith.tasks import extract_gems as extract_gems_task
from sfbot.smith.tasks import upgrade_items as upgrade_items_task
from sfbot.tavern.tasks import collect_quest as collect_quest_task
from sfbot.tavern.tasks import start_quest as start_quest_task
from sfbot.toilet.tasks import flush_toilet as toilet_flush_task
from sfbot.toilet.tasks import sacrifice_toilet as toilet_sacrifice_task
from sfbot.underworld.tasks import collect_resources as underworld_collect_task
from sfbot.underworld.tasks import collect_thirst as underworld_thirst_task
from sfbot.underworld.tasks import lure_hero as underworld_lure_task
from sfbot.underworld.tasks import upgrade_building as underworld_building_task
from sfbot.underworld.tasks import upgrade_fighters as underworld_fighters_task
from sfbot.wheel.tasks import spin_wheel as wheel_task
from sfbot.witch.tasks import buy_enchantments as enchantments_task
from sfbot.hellevator.tasks import run_hellevator as hellevator_task
from sfbot.world_boss.tasks import manage_world_boss as world_boss_task
from sfbot.session import init_server_map_async

LOOP_SLEEP = 180
JITTER_MAX = 60
ERROR_RETRY_DELAY = 60
ACTIONS_DELAY = 1
RUNNING_CHECK_INTERVAL = 300
NIGHT_START = time(2, 0)
NIGHT_END = time(8, 0)


class Task(Protocol):
    def should_run(self, bot: Bot) -> bool: ...
    async def run(self, bot: Bot) -> None: ...


def night_sleep_seconds() -> tuple[bool, int]:
    now = datetime.now()
    if NIGHT_START <= now.time() < NIGHT_END:
        wake_up = datetime.combine(now.date(), NIGHT_END)
        return True, int((wake_up - now).total_seconds()) + random.randint(
            0, JITTER_MAX * 5
        )
    return False, 0


async def run_task(bot: Bot, task: Task) -> None:
    """Run a task if should_run returns True, then poll + delay."""
    if task.should_run(bot):
        await task.run(bot)
    await bot.poll_async()
    await asyncio.sleep(ACTIONS_DELAY)


async def run_task_with_free_slot(bot: Bot, task: Task) -> None:
    """Ensure a free slot, run a task if should_run, then poll + delay."""
    if task.should_run(bot):
        await bot.ensure_free_slot()
        await task.run(bot)
    await bot.poll_async()
    await asyncio.sleep(ACTIONS_DELAY)


async def night_sleep() -> bool:
    """Sleep if in night window. Returns True if slept."""
    should_sleep, sleep_secs = night_sleep_seconds()
    if should_sleep:
        get_main_logger().info(f"Night mode: sleeping until 08:00 ({sleep_secs}s)")
        await asyncio.sleep(sleep_secs)
        return True
    return False


async def check_running(character_id: str) -> bool:
    """Check if the character is still marked as running in DB."""
    conn = await connect_async()
    try:
        return await is_character_running_async(conn, character_id)
    finally:
        await conn.close()


async def run_account(bot: Bot) -> None:
    character_id = bot.session.character_id
    token = BotLogContext.set(character_id)
    logger = get_main_logger()
    try:
        # Initial login with retries
        while True:
            try:
                await bot.login_async()
                break
            except (KnownAPIError, LoginError) as e:
                logger.warning(f"Login failed: {e}")
                await asyncio.sleep(ERROR_RETRY_DELAY)
            except Exception:
                logger.exception("Login failed")
                await asyncio.sleep(ERROR_RETRY_DELAY)

        logger.info(
            f"Logged in as {bot.session.player_name} (ID: {bot.session.pg_player})"
        )

        while True:
            try:
                # Check if still running
                if not await check_running(character_id):
                    logger.info("Paused by user")
                    while not await check_running(character_id):
                        await asyncio.sleep(RUNNING_CHECK_INTERVAL)
                    logger.info("Resumed by user")

                await bot.save_stats()

                if await night_sleep():
                    continue

                await bot.poll_async()

                # Tasks that need a free slot before running
                await run_task_with_free_slot(bot, collect_quest_task)
                await run_task_with_free_slot(bot, wheel_task)
                await run_task_with_free_slot(bot, toilet_flush_task)
                await run_task_with_free_slot(bot, buy_special_items_task)
                await run_task_with_free_slot(bot, fortress_mine_gems_task)
                await run_task_with_free_slot(bot, calendar_task)

                # Ensure best items/gems are equipped
                await bot.ensure_best_items_are_equipped()
                await bot.poll_async()
                await asyncio.sleep(ACTIONS_DELAY)

                await bot.ensure_best_gems_are_equipped()
                await bot.poll_async()
                await asyncio.sleep(ACTIONS_DELAY)

                # Tasks that need best items equipped first
                await run_task(bot, extract_gems_task)
                await run_task(bot, dismantle_item_task)
                await run_task(bot, buy_better_items_task)
                await run_task(bot, toilet_sacrifice_task)
                await run_task(bot, enchantments_task)
                await run_task(bot, upgrade_items_task)

                # Dungeon needs free slot
                await run_task_with_free_slot(bot, dungeon_task)

                # Standard tasks
                await run_task(bot, collect_guard_task)
                await run_task(bot, guild_task)
                await run_task(bot, guild_portal_task)
                await run_task(bot, guild_upgrade_task)
                await run_task(bot, fortress_collect_task)

                # MAKE SURE BUILDING UPGRADE IS BEFORE TRAINING
                # If we want upgrade building which is training, we cannot do so.
                # To avoid solving this, assume after the guard, there will be no training.
                # So we can just upgrade it with assumption that there is no training after guard.
                await run_task(bot, fortress_building_upgrade_task)
                await run_task(bot, fortress_upgrade_units_task)
                await run_task(bot, fortress_attack_task)
                await run_task(bot, fortress_train_soldiers_task)
                await run_task(bot, fortress_train_defence_units_task)

                await run_task(bot, underworld_collect_task)
                await run_task(bot, underworld_thirst_task)
                await run_task(bot, underworld_building_task)
                await run_task(bot, underworld_lure_task)
                await run_task(bot, underworld_fighters_task)

                await run_task(bot, arena_manager_sacrifice_task)
                await run_task(bot, arena_manager_upgrade_task)
                await run_task(bot, arena_manager_buy_task)

                await run_task(bot, prepare_elixirs_task)
                await run_task(bot, drink_potions_task)
                await run_task(bot, mount_task)
                await run_task(bot, upgrade_attributes_task)
                await run_task(bot, start_quest_task)
                await run_task(bot, arena_task)
                await run_task(bot, scrapbook_task)
                await run_task(bot, fight_opponent_task)
                await run_task(bot, dice_task)
                await run_task(bot, dungeon_portal_task)
                await run_task(bot, unlock_features_task)
                await run_task(bot, fight_pets_task)
                await run_task(bot, fight_pet_dungeon_task)
                await run_task(bot, feed_pet_task)
                await run_task(bot, legendary_dungeon_task)
                await run_task(bot, world_boss_task)
                await run_task(bot, hellevator_task)
                await run_task(bot, start_guard_task)
                await run_task(bot, daily_reward_task)
                await run_task(bot, event_reward_task)
                await run_task(bot, mail_reward_task)

                delay = LOOP_SLEEP + random.randint(0, JITTER_MAX)
                await asyncio.sleep(delay)

            except InventoryFullError:
                logger.warning("Inventory: could not free a slot, restarting loop")
            except InventoryStuckError:
                logger.error("Inventory: completely stuck, sleeping before retry")
                await asyncio.sleep(ERROR_RETRY_DELAY)
            except GemExtractedAlert:
                logger.info("Inventory: gem extracted, restarting loop")
            except KnownAPIError as e:
                logger.error(str(e))
                logger.info(f"retrying in {ERROR_RETRY_DELAY}s")
                await asyncio.sleep(ERROR_RETRY_DELAY)
            except LoginError as e:
                logger.warning(f"Login failed: {e}")
                logger.info(f"retrying in {ERROR_RETRY_DELAY}s")
                await asyncio.sleep(ERROR_RETRY_DELAY)
            except Exception:
                logger.exception("ERROR")
                logger.info(f"retrying in {ERROR_RETRY_DELAY}s")

                await asyncio.sleep(ERROR_RETRY_DELAY)
    finally:
        await bot.session.close()
        BotLogContext.reset(token)


POLL_NEW_CHARACTERS_INTERVAL = 60


async def main() -> None:
    logger = get_bot_main_logger()
    await init_server_map_async()
    active_tasks: dict[str, asyncio.Task] = {}  # character_id -> task

    try:
        while True:
            conn = await connect_async()
            try:
                characters = await get_all_enabled_characters_async(conn)
                if not characters:
                    logger.info("No enabled characters found. Retrying...")

            finally:
                await conn.close()

            for char in characters:
                cid = char["character_id"]
                if cid in active_tasks and not active_tasks[cid].done():
                    continue

                config = load_config_json(cid)
                if not config:
                    logger.warning(
                        f"Skipping {char['name']} ({char['server']}): no config file"
                    )
                    continue

                bot = Bot.from_db_config(
                    char["username"],
                    char["password_hash"],
                    server=char["server"],
                    character_id=cid,
                    config=config,
                )
                logger.info(f"Spawning task for {char['name']} ({char['server']})")
                active_tasks[cid] = asyncio.create_task(run_account(bot))

            await asyncio.sleep(POLL_NEW_CHARACTERS_INTERVAL)
    except asyncio.CancelledError:
        pass
    finally:
        for t in active_tasks.values():
            t.cancel()
        await asyncio.gather(*active_tasks.values(), return_exceptions=True)
        logger.info("Stopped.")


if __name__ == "__main__":
    init_db()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        get_main_logger().info("Stopped by user.")
