from sfbot import Bot
from sfbot.character import EquipmentRunes
from sfbot.dungeon.enums import DungeonKind, ShadowDungeon
from sfbot.dungeon.enums import RuneType as SimRuneType
from sfbot.dungeon.models import Fighter
from sfbot.dungeon.simulate import (
    estimate_hand_damage,
    fighter_from_character,
)
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger


def sim_rune_type(runes: EquipmentRunes) -> SimRuneType:
    if runes.weapon_rune_type is None or runes.weapon_rune_value <= 0:
        return SimRuneType.NONE
    return SimRuneType(runes.weapon_rune_type.value)


def build_companion_fighters(bot: Bot) -> list[Fighter]:
    character = bot.character
    if not character.companions:
        return []

    companions: list[Fighter] = []
    for info in character.companions.values():
        min_dmg: int | float = info.min_dmg
        max_dmg: int | float = info.max_dmg
        if min_dmg == 0 or max_dmg == 0:
            min_dmg, max_dmg = estimate_hand_damage(character.level, info.char_class)

        runes = info.runes
        companions.append(
            fighter_from_character(
                char_class=info.char_class,
                level=character.level,
                total_attrs=info.total_attrs,
                armor=info.armor,
                min_dmg=min_dmg,
                max_dmg=max_dmg,
                portal_hp_bonus=character.portal_hp_bonus,
                portal_dmg_bonus=character.portal_dmg_bonus,
                rune_type=sim_rune_type(runes),
                rune_value=runes.weapon_rune_value,
                fire_resistance=runes.fire_resistance,
                cold_resistance=runes.cold_resistance,
                lightning_resistance=runes.lightning_resistance,
                rune_health=runes.rune_health,
                gladiator=character.gladiator,
                has_sword_of_vengeance=runes.has_sword_of_vengeance,
                has_shadow_of_cowboy=runes.has_shadow_of_cowboy,
                has_life_potion=character.has_life_potion,
                is_companion=True,
            )
        )

    return companions


def build_player_fighter(bot: Bot) -> Fighter:
    character = bot.character
    runes = character.runes

    return fighter_from_character(
        char_class=character.char_class,
        level=character.level,
        total_attrs=character.total_attrs,
        armor=character.armor,
        min_dmg=character.min_dmg,
        max_dmg=character.max_dmg,
        portal_hp_bonus=character.portal_hp_bonus,
        portal_dmg_bonus=character.portal_dmg_bonus,
        rune_type=sim_rune_type(runes),
        rune_value=runes.weapon_rune_value,
        fire_resistance=runes.fire_resistance,
        cold_resistance=runes.cold_resistance,
        lightning_resistance=runes.lightning_resistance,
        rune_health=runes.rune_health,
        gladiator=character.gladiator,
        has_sword_of_vengeance=runes.has_sword_of_vengeance,
        has_shadow_of_cowboy=runes.has_shadow_of_cowboy,
        has_life_potion=character.has_life_potion,
        min_dmg2=character.min_dmg2,
        max_dmg2=character.max_dmg2,
    )


def should_run(bot: Bot) -> bool:
    return bot.dungeon.is_free


async def run(bot: Bot) -> None:
    logger = get_main_logger()
    dungeon = bot.dungeon

    try:
        await dungeon.update_async()
    except APIError as exc:
        logger.warning(f"Dungeon: update failed: {exc}")
        return

    player = build_player_fighter(bot)
    companions = build_companion_fighters(bot)

    kind, target, win_chance = dungeon.get_best_dungeon(player, companions)

    if kind is None or target is None:
        return

    logger.info(
        f"Dungeon: fighting {target.name} ({kind.value}), win chance {win_chance:.0%}"
    )

    try:
        match kind:
            case DungeonKind.TOWER:
                await dungeon.fight_tower_async()
            case DungeonKind.LIGHT:
                await dungeon.fight_light_async(target)  # type: ignore[arg-type]
            case DungeonKind.SHADOW:
                await dungeon.fight_shadow_async(target)  # type: ignore[arg-type]
            case DungeonKind.TWISTER:
                await dungeon.fight_shadow_async(ShadowDungeon.TWISTER)
    except APIError as exc:
        logger.warning(f"Dungeon: {kind.value} fight failed: {exc}")
