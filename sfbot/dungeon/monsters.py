"""Load dungeon monster data from dungeons.json."""

import json
from functools import lru_cache
from pathlib import Path

from sfbot.constants.enums import CharClass
from sfbot.dungeon.enums import LightDungeon, ShadowDungeon
from sfbot.dungeon.models import Monster

# --- JSON class name → CharClass enum (includes "WarMage" alias for BattleMage) ---
CLASS_NAME_MAP: dict[str, CharClass] = {
    "Warrior": CharClass.WARRIOR,
    "Mage": CharClass.MAGE,
    "Scout": CharClass.SCOUT,
    "Assassin": CharClass.ASSASSIN,
    "BattleMage": CharClass.BATTLE_MAGE,
    "WarMage": CharClass.BATTLE_MAGE,
    "Berserker": CharClass.BERSERKER,
    "DemonHunter": CharClass.DEMON_HUNTER,
    "Druid": CharClass.DRUID,
    "Bard": CharClass.BARD,
    "Necromancer": CharClass.NECROMANCER,
    "Paladin": CharClass.PALADIN,
    "PlagueDoctor": CharClass.PLAGUE_DOCTOR,
}

# --- JSON dungeon name → LightDungeon enum ---
LIGHT_NAME_MAP: dict[str, LightDungeon] = {
    "Desecrated_Catacombs": LightDungeon.DESECRATED_CATACOMBS,
    "Mines_of_Gloria": LightDungeon.MINES_OF_GLORIA,
    "Ruins_of_Gnark": LightDungeon.RUINS_OF_GNARK,
    "Cutthroat_Grotto": LightDungeon.CUTTHROAT_GROTTO,
    "Emerald_Scale_Altar": LightDungeon.EMERALD_SCALE_ALTAR,
    "Toxic_Tree": LightDungeon.TOXIC_TREE,
    "Magma_Stream": LightDungeon.MAGMA_STREAM,
    "Frost_Blood_Temple": LightDungeon.FROST_BLOOD_TEMPLE,
    "Pyramids_of_Madness": LightDungeon.PYRAMIDS_OF_MADNESS,
    "Black_Skull_Fortress": LightDungeon.BLACK_SKULL_FORTRESS,
    "Circus_of_Horror": LightDungeon.CIRCUS_OF_HORROR,
    "Hell": LightDungeon.HELL,
    "The_13th_Floor": LightDungeon.THE_13TH_FLOOR,
    "Osteros": LightDungeon.EASTEROS,
    "Tower": LightDungeon.TOWER,
    "Time_Honored_School_of_Magic": LightDungeon.TIME_HONORED_SCHOOL_OF_MAGIC,
    "Hemorridor": LightDungeon.HEMORRIDOR,
    "Nordic": LightDungeon.NORDIC_GODS,
    "Mount_Olympus": LightDungeon.MOUNT_OLYMPUS,
    "Tavern_of_the_Dark_Doppelgangers": LightDungeon.TAVERN_OF_THE_DARK_DOPPELGANGERS,
    "Dragons_Hoard": LightDungeon.DRAGONS_HOARD,
    "House_of_Horrors": LightDungeon.HOUSE_OF_HORRORS,
    "The_3rd_League_of_Superheroes": LightDungeon.THIRD_LEAGUE_OF_SUPERHEROES,
    "Dojo_of_Childhood_Heroes": LightDungeon.DOJO_OF_CHILDHOOD_HEROES,
    "Monster_Grotto": LightDungeon.MONSTER_GROTTO,
    "City_of_Intrigues": LightDungeon.CITY_OF_INTRIGUES,
    "School_of_magic_Express": LightDungeon.SCHOOL_OF_MAGIC_EXPRESS,
    "Ash_Mountain": LightDungeon.ASH_MOUNTAIN,
    "Playa_HQ": LightDungeon.PLAYA_GAMES_HQ,
    "Training_Camp": LightDungeon.TRAINING_CAMP,
    "Sandstorm": LightDungeon.SANDSTORM,
    "Arcade_of_the_Old_Pixel_Icons": LightDungeon.ARCADE_OF_THE_OLD_PIXEL_ICONS,
    "The_Server_Room": LightDungeon.THE_SERVER_ROOM,
    "Workshop_of_the_Hunters_of_the_Undead": LightDungeon.WORKSHOP_OF_THE_HUNTERS,
    "Retro_TV_Legends": LightDungeon.RETRO_TV_LEGENDS,
    "The_Meeting_Room": LightDungeon.MEETING_ROOM,
}

# --- JSON dungeon name → ShadowDungeon enum ---
SHADOW_NAME_MAP: dict[str, ShadowDungeon] = {
    "Shadow_Desecrated_Catacombs": ShadowDungeon.DESECRATED_CATACOMBS,
    "Shadow_Mines_of_Gloria": ShadowDungeon.MINES_OF_GLORIA,
    "Shadow_Ruins_of_Gnark": ShadowDungeon.RUINS_OF_GNARK,
    "Shadow_Cutthroat_Grotto": ShadowDungeon.CUTTHROAT_GROTTO,
    "Shadow_Emerald_Scale_Altar": ShadowDungeon.EMERALD_SCALE_ALTAR,
    "Shadow_Toxic_Tree": ShadowDungeon.TOXIC_TREE,
    "Shadow_Magma_Stream": ShadowDungeon.MAGMA_STREAM,
    "Shadow_Frost_Blood_Temple": ShadowDungeon.FROST_BLOOD_TEMPLE,
    "Shadow_Pyramids_of_Madness": ShadowDungeon.PYRAMIDS_OF_MADNESS,
    "Shadow_Black_Skull_Fortress": ShadowDungeon.BLACK_SKULL_FORTRESS,
    "Shadow_Circus_of_Horror": ShadowDungeon.CIRCUS_OF_HORROR,
    "Shadow_Hell": ShadowDungeon.HELL,
    "Shadow_The_13th_Floor": ShadowDungeon.THE_13TH_FLOOR,
    "Shadow_Osteros": ShadowDungeon.EASTEROS,
    "Twister": ShadowDungeon.TWISTER,
    "Shadow_Time_Honored_School_of_Magic": ShadowDungeon.TIME_HONORED_SCHOOL_OF_MAGIC,
    "Shadow_Hemorridor": ShadowDungeon.HEMORRIDOR,
    "Continuous_Loop_of_Idols": ShadowDungeon.CONTINUOUS_LOOP_OF_IDOLS,
    "Shadow_Nordic": ShadowDungeon.NORDIC_GODS,
    "Shadow_Mount_Olympus": ShadowDungeon.MOUNT_OLYMPUS,
    "Shadow_Tavern_of_the_Dark_Doppelgangers": ShadowDungeon.TAVERN_OF_THE_DARK_DOPPELGANGERS,
    "Shadow_Dragons_Hoard": ShadowDungeon.DRAGONS_HOARD,
    "Shadow_House_of_Horrors": ShadowDungeon.HOUSE_OF_HORRORS,
    "Shadow_The_3rd_League_of_Superheroes": ShadowDungeon.THIRD_LEAGUE_OF_SUPERHEROES,
    "Shadow_Dojo_of_Childhood_Heroes": ShadowDungeon.DOJO_OF_CHILDHOOD_HEROES,
    "Shadow_Monster_Grotto": ShadowDungeon.MONSTER_GROTTO,
    "Shadow_City_of_Intrigues": ShadowDungeon.CITY_OF_INTRIGUES,
    "Shadow_School_of_magic_Express": ShadowDungeon.SCHOOL_OF_MAGIC_EXPRESS,
    "Shadow_Ash_Mountain": ShadowDungeon.ASH_MOUNTAIN,
    "Shadow_Playa_HQ": ShadowDungeon.PLAYA_GAMES_HQ,
    "Shadow_Arcade_of_the_Old_Pixel_Icons": ShadowDungeon.ARCADE_OF_THE_OLD_PIXEL_ICONS,
    "Shadow_The_Server_Room": ShadowDungeon.THE_SERVER_ROOM,
    "Shadow_Workshop_of_the_Hunters_of_the_Undead": ShadowDungeon.WORKSHOP_OF_THE_HUNTERS,
    "Shadow_Retro_TV_Legends": ShadowDungeon.RETRO_TV_LEGENDS,
    "Shadow_The_Meeting_Room": ShadowDungeon.MEETING_ROOM,
}

DUNGEONS_JSON_PATH = Path(__file__).resolve().parent / "dungeons.json"


@lru_cache(maxsize=1)
def load_dungeons_json() -> dict:
    with open(DUNGEONS_JSON_PATH) as f:
        return json.load(f)


def parse_monster(data: dict) -> Monster:
    if data.get("special") == "mirror":
        return Monster(
            name="Mirror",
            char_class=CharClass.WARRIOR,
            level=0,
            strength=0,
            dexterity=0,
            intelligence=0,
            constitution=0,
            luck=0,
            armor=0,
            min_dmg=None,
            max_dmg=None,
            health=0,
            rune_type=0,
            rune_damage=0,
            fire_resistance=0,
            cold_resistance=0,
            lightning_resistance=0,
            is_mirror=True,
        )

    runes = data.get("runes", {})
    resistances = runes.get("res", [0, 0, 0])
    return Monster(
        name=data.get("name", ""),
        char_class=CLASS_NAME_MAP[data["class"]],
        level=data["level"],
        strength=data["strength"],
        dexterity=data["dexterity"],
        intelligence=data["intelligence"],
        constitution=data["constitution"],
        luck=data["luck"],
        armor=data.get("armor", 0),
        min_dmg=data["min_dmg"],
        max_dmg=data["max_dmg"],
        health=data["life"],
        rune_type=runes.get("type", 0),
        rune_damage=runes.get("damage", 0),
        fire_resistance=resistances[0] if len(resistances) > 0 else 0,
        cold_resistance=resistances[1] if len(resistances) > 1 else 0,
        lightning_resistance=resistances[2] if len(resistances) > 2 else 0,
    )


def get_light_monsters() -> dict[LightDungeon, list[Monster]]:
    data = load_dungeons_json()
    result: dict[LightDungeon, list[Monster]] = {}
    for json_name, dungeon_enum in LIGHT_NAME_MAP.items():
        result[dungeon_enum] = [
            parse_monster(monster_data) for monster_data in data[json_name]["monsters"]
        ]
    return result


def get_shadow_monsters() -> dict[ShadowDungeon, list[Monster]]:
    data = load_dungeons_json()
    result: dict[ShadowDungeon, list[Monster]] = {}
    for json_name, dungeon_enum in SHADOW_NAME_MAP.items():
        result[dungeon_enum] = [
            parse_monster(monster_data) for monster_data in data[json_name]["monsters"]
        ]
    return result


def get_monster_at(
    dungeon: LightDungeon | ShadowDungeon,
    progress: int,
) -> Monster | None:
    if isinstance(dungeon, LightDungeon):
        monsters = get_light_monsters()[dungeon]
    else:
        monsters = get_shadow_monsters()[dungeon]

    if progress < 0 or progress >= len(monsters):
        return None

    return monsters[progress]

