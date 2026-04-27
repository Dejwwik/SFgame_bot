import json
import random
from dataclasses import dataclass
from functools import lru_cache
from math import floor
from pathlib import Path

from sfbot.constants.enums import Attribute, CharClass, HabitatType
from sfbot.pets.pets import Habitat, Pet
from sfbot.simulate.combat import (
    calc_armor_reduction,
    calc_attribute_bonus,
    calc_crit_chance,
)
from sfbot.simulate.constants import (
    BYPASS_SKIP_CHANCE,
    CRIT_BASE,
    CRIT_GLADIATOR_BONUS,
    DAMAGE_MULTIPLIER,
    HEALTH_MULTIPLIER,
    MAX_DAMAGE_REDUCTION,
    SKIP_CHANCE,
    WEAPON_MULTIPLIER,
)

# --- Pet stat factor tables (from sf-tools js/sim/pets.js) ---

PET_FACTOR_MAP: list[int] = [
    10,
    11,
    12,
    13,
    14,
    16,
    18,
    20,
    25,
    30,
    35,
    40,
    50,
    60,
    70,
    80,
    100,
    130,
    160,
    160,
]

PET_FACTOR_MAP_LUCK: list[float] = [
    7.5,
    8.5,
    9.0,
    9.5,
    10.5,
    12.0,
    13.5,
    15.0,
    19.0,
    22.5,
    26.0,
    30.0,
    37.5,
    45.0,
    52.5,
    60.0,
    75,
    97.5,
    120,
    120,
]

PET_CLASS_MAP: dict[HabitatType, list[CharClass]] = {
    HabitatType.SHADOW: [
        CharClass.SCOUT,
        CharClass.WARRIOR,
        CharClass.WARRIOR,
        CharClass.MAGE,
        CharClass.MAGE,
        CharClass.MAGE,
        CharClass.SCOUT,
        CharClass.SCOUT,
        CharClass.SCOUT,
        CharClass.WARRIOR,
        CharClass.MAGE,
        CharClass.MAGE,
        CharClass.SCOUT,
        CharClass.SCOUT,
        CharClass.WARRIOR,
        CharClass.WARRIOR,
        CharClass.MAGE,
        CharClass.WARRIOR,
        CharClass.WARRIOR,
        CharClass.SCOUT,
    ],
    HabitatType.LIGHT: [
        CharClass.WARRIOR,
        CharClass.WARRIOR,
        CharClass.MAGE,
        CharClass.MAGE,
        CharClass.SCOUT,
        CharClass.SCOUT,
        CharClass.MAGE,
        CharClass.WARRIOR,
        CharClass.WARRIOR,
        CharClass.MAGE,
        CharClass.MAGE,
        CharClass.SCOUT,
        CharClass.SCOUT,
        CharClass.MAGE,
        CharClass.MAGE,
        CharClass.WARRIOR,
        CharClass.WARRIOR,
        CharClass.WARRIOR,
        CharClass.MAGE,
        CharClass.SCOUT,
    ],
    HabitatType.EARTH: [
        CharClass.WARRIOR,
        CharClass.WARRIOR,
        CharClass.SCOUT,
        CharClass.SCOUT,
        CharClass.WARRIOR,
        CharClass.SCOUT,
        CharClass.MAGE,
        CharClass.MAGE,
        CharClass.WARRIOR,
        CharClass.WARRIOR,
        CharClass.SCOUT,
        CharClass.WARRIOR,
        CharClass.SCOUT,
        CharClass.SCOUT,
        CharClass.MAGE,
        CharClass.MAGE,
        CharClass.MAGE,
        CharClass.WARRIOR,
        CharClass.WARRIOR,
        CharClass.WARRIOR,
    ],
    HabitatType.FIRE: [
        CharClass.SCOUT,
        CharClass.SCOUT,
        CharClass.WARRIOR,
        CharClass.MAGE,
        CharClass.MAGE,
        CharClass.SCOUT,
        CharClass.SCOUT,
        CharClass.MAGE,
        CharClass.WARRIOR,
        CharClass.MAGE,
        CharClass.MAGE,
        CharClass.SCOUT,
        CharClass.SCOUT,
        CharClass.SCOUT,
        CharClass.SCOUT,
        CharClass.SCOUT,
        CharClass.MAGE,
        CharClass.WARRIOR,
        CharClass.MAGE,
        CharClass.WARRIOR,
    ],
    HabitatType.WATER: [
        CharClass.MAGE,
        CharClass.WARRIOR,
        CharClass.WARRIOR,
        CharClass.WARRIOR,
        CharClass.WARRIOR,
        CharClass.SCOUT,
        CharClass.WARRIOR,
        CharClass.SCOUT,
        CharClass.SCOUT,
        CharClass.WARRIOR,
        CharClass.MAGE,
        CharClass.MAGE,
        CharClass.MAGE,
        CharClass.WARRIOR,
        CharClass.MAGE,
        CharClass.MAGE,
        CharClass.WARRIOR,
        CharClass.MAGE,
        CharClass.WARRIOR,
        CharClass.SCOUT,
    ],
}

SIMULATION_ITERATIONS = 10_000
MIN_WIN_CHANCE = 0.001
MAX_ROUNDS = 500

CLASS_NAME_MAP: dict[str, CharClass] = {
    "Warrior": CharClass.WARRIOR,
    "Mage": CharClass.MAGE,
    "Scout": CharClass.SCOUT,
}

PET_DUNGEON_KEY_MAP: dict[str, HabitatType] = {
    "Shadow": HabitatType.SHADOW,
    "Light": HabitatType.LIGHT,
    "Earth": HabitatType.EARTH,
    "Fire": HabitatType.FIRE,
    "Water": HabitatType.WATER,
}


# --- Pet Fighter ---


@dataclass(slots=True)
class PetFighter:
    char_class: CharClass
    level: int
    strength: int
    dexterity: int
    intelligence: int
    constitution: int
    luck: int
    armor: int
    min_dmg: float
    max_dmg: float
    health: float
    gladiator: int = 0

    def get_attr(self, attr: Attribute) -> int:
        match attr:
            case Attribute.STRENGTH:
                return self.strength
            case Attribute.DEXTERITY:
                return self.dexterity
            case Attribute.INTELLIGENCE:
                return self.intelligence
            case _:
                return self.strength


# --- Pack bonus calculation ---


def calc_pack_bonus(habitat: Habitat) -> float:
    """Compute pack bonus as a fraction (sf-tools: 5 * trunc(pack + at200 + at150*0.75 + at100*0.5) / 100)."""
    pack = 0
    at100 = 0
    at150 = 0
    at200 = 0
    for p in habitat.pets:
        if not p.unlocked:
            continue
        pack += 1
        if p.level >= 100:
            at100 += 1
        if p.level >= 150:
            at150 += 1
        if p.level >= 200:
            at200 += 1
    bonus_pct = 5 * int(pack + at200 + at150 * 0.75 + at100 * 0.5)
    return bonus_pct / 100.0


# --- Fighter construction ---


def fighter_from_pet(
    pet: Pet,
    habitat: Habitat,
    gladiator: int,
) -> PetFighter:
    position = pet.position
    bonus = calc_pack_bonus(habitat)

    base_stat = PET_FACTOR_MAP[position]
    multiplier = (pet.level + 1) * (1.0 + bonus)

    main = floor(base_stat * multiplier)
    luck = floor(PET_FACTOR_MAP_LUCK[position] * multiplier)

    char_class = PET_CLASS_MAP[pet.element][position]
    dmg = floor((pet.level + 1) * WEAPON_MULTIPLIER[char_class])
    armor = pet.level * MAX_DAMAGE_REDUCTION[char_class]

    if char_class == CharClass.WARRIOR:
        strength, dexterity, intelligence = main, floor(main / 2), floor(main / 2)
    elif char_class == CharClass.MAGE:
        strength, dexterity, intelligence = floor(main / 2), floor(main / 2), main
    else:  # Scout
        strength, dexterity, intelligence = floor(main / 2), main, floor(main / 2)

    hp = main * HEALTH_MULTIPLIER[char_class] * (pet.level + 1)

    return PetFighter(
        char_class=char_class,
        level=pet.level,
        strength=strength,
        dexterity=dexterity,
        intelligence=intelligence,
        constitution=main,
        luck=luck,
        armor=armor,
        min_dmg=float(dmg),
        max_dmg=float(dmg),
        health=float(floor(hp)),
        gladiator=gladiator,
    )


# --- Pet dungeon monster loading ---


@dataclass(slots=True)
class PetDungeonMonster:
    char_class: CharClass
    level: int
    strength: int
    dexterity: int
    intelligence: int
    constitution: int
    luck: int
    life: int


@lru_cache(maxsize=1)
def load_pet_dungeon_monsters() -> dict[HabitatType, list[PetDungeonMonster]]:
    path = Path(__file__).parent / "pet_dungeons.json"
    with open(path) as f:
        data = json.load(f)
    result: dict[HabitatType, list[PetDungeonMonster]] = {}
    for key, monsters in data.items():
        result[PET_DUNGEON_KEY_MAP[key]] = [
            PetDungeonMonster(
                char_class=CLASS_NAME_MAP[m["class"]],
                level=m["level"],
                strength=m["strength"],
                dexterity=m["dexterity"],
                intelligence=m["intelligence"],
                constitution=m["constitution"],
                luck=m["luck"],
                life=m["life"],
            )
            for m in monsters
        ]
    return result


def fighter_from_pet_dungeon_monster(
    element: HabitatType,
    position: int,
) -> PetFighter | None:
    monsters = load_pet_dungeon_monsters()
    monster_list = monsters[element]
    if position >= len(monster_list):
        return None
    m = monster_list[position]
    dmg = float(floor((m.level + 1) * WEAPON_MULTIPLIER[m.char_class]))
    return PetFighter(
        char_class=m.char_class,
        level=m.level,
        strength=m.strength,
        dexterity=m.dexterity,
        intelligence=m.intelligence,
        constitution=m.constitution,
        luck=m.luck,
        armor=m.level * MAX_DAMAGE_REDUCTION[m.char_class],
        min_dmg=dmg,
        max_dmg=dmg,
        health=float(m.life),
    )


# --- Pet combat calculations ---


def calc_damage_range(attacker: PetFighter, target: PetFighter) -> tuple[float, float]:
    attribute_bonus = calc_attribute_bonus(attacker, target)
    armor_reduction = 1.0 - calc_armor_reduction(attacker, target) / 100.0
    class_multiplier = DAMAGE_MULTIPLIER[attacker.char_class]

    total = attribute_bonus * armor_reduction * class_multiplier
    return attacker.min_dmg * total, attacker.max_dmg * total


def calc_crit_multiplier(attacker: PetFighter, target: PetFighter) -> float:
    gladiator_advantage = max(0, attacker.gladiator - target.gladiator)
    return CRIT_BASE + CRIT_GLADIATOR_BONUS * gladiator_advantage


def will_skip(defender: PetFighter, attacker: PetFighter) -> bool:
    if attacker.char_class in BYPASS_SKIP_CHANCE:
        return False
    skip_chance = SKIP_CHANCE[defender.char_class]
    if skip_chance <= 0.0:
        return False
    return random.random() < skip_chance


# --- Main simulation ---


def simulate_pet_fight(
    player: PetFighter,
    boss: PetFighter,
    iterations: int = SIMULATION_ITERATIONS,
) -> float:
    """Simulate a pet fight and return win ratio (0.0 to 1.0)."""
    wins = 0

    p_dmg_min, p_dmg_max = calc_damage_range(player, boss)
    b_dmg_min, b_dmg_max = calc_damage_range(boss, player)

    p_crit_chance = calc_crit_chance(player, boss)
    b_crit_chance = calc_crit_chance(boss, player)

    p_crit_multi = calc_crit_multiplier(player, boss)
    b_crit_multi = calc_crit_multiplier(boss, player)

    p_hp = player.health
    b_hp = boss.health

    for _ in range(iterations):
        player_hp = p_hp
        boss_hp = b_hp
        turn = 0

        player_first = random.random() < 0.5
        attacker_is_player = player_first

        for _ in range(MAX_ROUNDS):
            rage = 1.0 + turn / 6.0
            turn += 1

            if attacker_is_player:
                if not will_skip(boss, player):
                    base = random.random() * (1.0 + p_dmg_max - p_dmg_min) + p_dmg_min
                    damage = base * rage
                    if random.random() < p_crit_chance:
                        damage *= p_crit_multi
                    boss_hp -= damage
                    if boss_hp <= 0:
                        wins += 1
                        break
            else:
                if not will_skip(player, boss):
                    base = random.random() * (1.0 + b_dmg_max - b_dmg_min) + b_dmg_min
                    damage = base * rage
                    if random.random() < b_crit_chance:
                        damage *= b_crit_multi
                    player_hp -= damage
                    if player_hp <= 0:
                        break

            attacker_is_player = not attacker_is_player

    return wins / iterations


# --- Best pet dungeon fight selection ---


@dataclass(slots=True)
class PetDungeonFightResult:
    habitat: Habitat
    pet: Pet
    win_chance: float


def get_best_pet_dungeon_fight(
    habitats: dict[HabitatType, Habitat],
    gladiator: int,
) -> PetDungeonFightResult | None:
    """Find the best pet dungeon fight across all explorable habitats.

    For each explorable habitat, simulates every available (unlocked) pet
    against the next boss. Returns the fight with the highest win chance,
    or None if no explorable habitat exists.
    """
    best: PetDungeonFightResult | None = None

    for habitat in habitats.values():
        if not habitat.can_explore:
            continue

        boss_position = habitat.explored_count
        boss = fighter_from_pet_dungeon_monster(habitat.element, boss_position)
        if boss is None:
            continue

        for pet in habitat.pets:
            if not pet.unlocked:
                continue

            pet_fighter = fighter_from_pet(pet, habitat, gladiator)
            win_chance = simulate_pet_fight(pet_fighter, boss)

            if best is None or win_chance > best.win_chance:
                best = PetDungeonFightResult(
                    habitat=habitat,
                    pet=pet,
                    win_chance=win_chance,
                )

    return best
