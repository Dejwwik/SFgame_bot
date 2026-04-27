# Pet Dungeon System

## Overview

Each habitat (Shadow, Light, Earth, Fire, Water) has 20 pet dungeon fights. Defeating a boss at position N discovers the pet at that position. Fights are gated by a cooldown timer (`next_free_exploration` from `characterstatus`).

The bot picks the best fight by simulating every unlocked pet in every explorable habitat against the next boss.

## Module Structure

| File | Purpose |
|---|---|
| `simulate.py` | Pet simulation engine, fighter construction, best-fight selection |
| `pet_dungeons.json` | Pre-computed boss stats per habitat (20 bosses × 5 elements) |
| `pets.py` | Habitat/Pet parsing, `fight_pet_dungeon_async()` → `FightResult`, cooldown tracking |
| `tasks/fight_pet_dungeon.py` | Bot task (`should_run` / `run`) — skips if `is_dungeon_ready` |

## Habitats

| Element | Enum | Fights |
|---|---|---|
| Shadow | `HabitatType.SHADOW` | 20 |
| Light | `HabitatType.LIGHT` | 20 |
| Earth | `HabitatType.EARTH` | 20 |
| Fire | `HabitatType.FIRE` | 20 |
| Water | `HabitatType.WATER` | 20 |

Each habitat has 20 pets at positions 0–19. A pet is discovered when `explored_count > position`, and unlocked when its level > 0.

## Progress Tracking

- `habitat.explored_count` — number of bosses defeated (0–20)
- `habitat.can_explore` — `explored_count < 20`
- `pets.next_free_exploration` — cooldown timestamp from `characterstatus`
- `pets.can_fight_pet_dungeon_now()` — cooldown expired

## Pet Fighter Stats

Pet stats are computed from position-based factor tables and a pack bonus:

### Factor Tables (`PET_FACTOR_MAP` / `PET_FACTOR_MAP_LUCK`)

Position 0 has base stat 10, scaling up to position 16–19 at 100–160. Luck uses a separate table at 75% of the main stat factor.

### Pack Bonus (sf-tools formula)

```
bonus_pct = 5 × trunc(pack + at200 + at150 × 0.75 + at100 × 0.5)
```

Where:
- `pack` = number of unlocked pets in this habitat
- `at100` = pets with level ≥ 100
- `at150` = pets with level ≥ 150
- `at200` = pets with level ≥ 200

The result is an integer percentage divided by 100 to get the fractional multiplier.

### Stat Formulas

```
multiplier = (level + 1) × (1 + pack_bonus)
main_stat  = floor(PET_FACTOR_MAP[position] × multiplier)
luck       = floor(PET_FACTOR_MAP_LUCK[position] × multiplier)
off_stat   = floor(main_stat / 2)
constitution = main_stat
```

Main stat assignment depends on pet class (from `PET_CLASS_MAP[element][position]`):
- Warrior → `strength = main`
- Mage → `intelligence = main`
- Scout → `dexterity = main`

### Weapon Damage

```
damage = floor((level + 1) × WEAPON_MULTIPLIER[class])
min_dmg = max_dmg = damage
```

Pets have a single damage value (no min/max range).

### Armor

```
armor = level × MAX_DAMAGE_REDUCTION[class]
```

### HP

```
hp = floor(main_stat × HEALTH_MULTIPLIER[class] × (level + 1))
```

No wings, no portal bonus, no rune health — these don't exist for pets.

## Boss Stats

Bosses are loaded from `pet_dungeons.json`. Each boss has pre-computed stats (`strength`, `dexterity`, `intelligence`, `constitution`, `luck`, `life`). Armor and weapon damage are derived from the boss's level and class at load time.

Boss position within a habitat determines the boss index in the JSON array (0-based).

## Battle Simulation

Ported from [HafisCZ/sf-tools](https://github.com/HafisCZ/sf-tools) PetSimulator (`js/sim/pets.js`). Uses the same core combat engine as regular dungeons with these simplifications:

### Differences from Regular Dungeons

| Feature | Regular Dungeons | Pet Dungeons |
|---|---|---|
| Weapons | Equipped weapon min/max | Single damage value |
| Runes | Fire/cold/lightning runes | None |
| Enchantments | Sword of Vengeance, Shadow of Cowboy | None |
| Portal bonuses | HP + damage bonuses | None |
| Wings (life potion) | +25% HP | None |
| Element advantage | N/A | Not applied (same element) |
| First attacker | Random or Shadow of Cowboy | Random 50/50 |
| Fight type | 1v1 or sequential 4v1 | 1v1 only |

### Fight Model

Each fight runs `SIMULATION_ITERATIONS` (10,000) iterations:

1. **First attacker**: Random 50/50
2. **Turns alternate** with a safety limit of `MAX_ROUNDS` (500)
3. **Rage**: `1.0 + turn / 6.0` — increases each round
4. **Dodge/Block**: Scout 50%, Warrior 25%, Mage 0%. Mages bypass dodge
5. **Damage**: `random(min, max) × rage × crit_multiplier`
6. **Crit chance**: `min(0.50, luck × 2.5 / target_level / 100)`
7. **Crit multiplier**: `2.0 + gladiator_advantage × 0.11`
8. Fight ends when one fighter's HP reaches 0

### Damage Calculation

```
damage_range = weapon_dmg × attribute_bonus × armor_reduction × class_multiplier
```

| Factor | Formula |
|---|---|
| Attribute bonus | `1.0 + max(main/2, main - target_main/2) / 10` |
| Armor reduction | `1.0 - min(armor × class_armor_mult / level, max_reduction) / 100`. Mages bypass |
| Class multiplier | From `DAMAGE_MULTIPLIER` table |

No portal multiplier, no rune bonus.

## Fight Selection (`get_best_pet_dungeon_fight`)

1. Iterate all habitats where `can_explore` is True
2. For each habitat, load the boss at `explored_count` position
3. For each unlocked pet, build a `PetFighter` and simulate against the boss
4. Return the `PetDungeonFightResult` with the highest win chance
5. Returns `None` if no explorable habitat exists

## Wire Command

| Command | Payload |
|---|---|
| `PetsDungeonFight` | `{use_mush}/{element+1}/{enemy_pos}/{player_pet_id}` |

`enemy_pos` is `explored_count + 1` (1-based). `use_mush` is 0 for free fights.

## Class-Specific Rules

Only base 3 classes appear in pet dungeons (Warrior, Mage, Scout):

- **Mage**: Bypasses armor reduction AND dodge/block chance
- **Scout**: 50% dodge chance
- **Warrior**: 25% block chance

## Constants

| Constant | Value | Purpose |
|---|---|---|
| `SIMULATION_ITERATIONS` | 10,000 | Monte Carlo iterations per fight |
| `MAX_ROUNDS` | 500 | Safety limit per iteration |
| `MAX_CRIT_CHANCE` | 0.50 | Crit chance cap |
| `PETS_PER_HABITAT` | 20 | Bosses per habitat |
