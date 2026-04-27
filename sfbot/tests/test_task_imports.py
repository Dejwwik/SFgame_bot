"""Verify every task module imports cleanly and exposes should_run / run.

This catches stale method references across domain boundaries — e.g. a task
calling `bot.inventory.find_item_to_dismantle()` after it was renamed to
`get_item_to_dismantle()`.
"""

import asyncio
import importlib
import inspect

import pytest

TASK_MODULES = [
    "sfbot.arena.tasks.fight_arena",
    "sfbot.arena.tasks.fight_opponent",
    "sfbot.attributes.tasks.upgrade_attributes",
    "sfbot.dice.tasks.play_dice",
    "sfbot.fortress.tasks.attack_fortress",
    "sfbot.fortress.tasks.collect_resources",
    "sfbot.fortress.tasks.search_gems",
    "sfbot.fortress.tasks.train_defence_units",
    "sfbot.fortress.tasks.train_soldiers",
    "sfbot.fortress.tasks.upgrade_building",
    "sfbot.fortress.tasks.upgrade_units",
    "sfbot.guard.tasks.collect_guard",
    "sfbot.guard.tasks.start_guard",
    "sfbot.guild.tasks.do_guild_fights",
    "sfbot.guild.tasks.fight_portal",
    "sfbot.guild.tasks.upgrade_buildings",
    "sfbot.inventory.tasks.ensure_best_gems_are_equipped",
    "sfbot.inventory.tasks.ensure_best_items_are_equipped",
    "sfbot.mount.tasks.ensure_mount",
    "sfbot.pets.tasks.feed_pet",
    "sfbot.pets.tasks.fight_pet_dungeon",
    "sfbot.pets.tasks.fight_pets",
    "sfbot.pets.tasks.unlock_features",
    "sfbot.potions.tasks.drink_potions",
    "sfbot.reward.tasks.claim_calendar",
    "sfbot.reward.tasks.claim_daily_task",
    "sfbot.reward.tasks.claim_event",
    "sfbot.reward.tasks.claim_pending",
    "sfbot.shop.tasks.buy_and_equip_better_item",
    "sfbot.shop.tasks.buy_special_items",
    "sfbot.smith.tasks.dismantle_item",
    "sfbot.smith.tasks.upgrade_items",
    "sfbot.tavern.tasks.collect_quest",
    "sfbot.tavern.tasks.start_quest",
    "sfbot.toilet.tasks.flush_toilet",
    "sfbot.toilet.tasks.sacrifice_toilet",
    "sfbot.underworld.tasks.collect_resources",
    "sfbot.underworld.tasks.collect_thirst",
    "sfbot.underworld.tasks.lure_hero",
    "sfbot.underworld.tasks.upgrade_building",
    "sfbot.underworld.tasks.upgrade_fighters",
    "sfbot.wheel.tasks.spin_wheel",
    "sfbot.witch.tasks.buy_enchantments",
]


@pytest.mark.parametrize("module_path", TASK_MODULES)
class TestTaskModule:
    def test_imports_cleanly(self, module_path: str) -> None:
        importlib.import_module(module_path)

    def test_has_should_run(self, module_path: str) -> None:
        mod = importlib.import_module(module_path)
        assert hasattr(mod, "should_run"), f"{module_path} missing should_run()"
        sig = inspect.signature(mod.should_run)
        params = list(sig.parameters)
        assert params == ["bot"], (
            f"{module_path}.should_run has params {params}, expected ['bot']"
        )

    def test_has_run(self, module_path: str) -> None:
        mod = importlib.import_module(module_path)
        assert hasattr(mod, "run"), f"{module_path} missing run()"
        assert asyncio.iscoroutinefunction(mod.run), f"{module_path}.run must be async"
        sig = inspect.signature(mod.run)
        params = list(sig.parameters)
        assert params == ["bot"], (
            f"{module_path}.run has params {params}, expected ['bot']"
        )
