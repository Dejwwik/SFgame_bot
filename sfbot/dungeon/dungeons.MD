# Dungeon System

## Overview

The dungeon system manages light dungeons, shadow dungeons, Tower, and Twister. Each dungeon has 10 floors of monsters loaded from `dungeons.json`. Special dungeons (Tower, Twister, Sandstorm, Continuous Loop) have more floors.

Fights are gated by a cooldown timer (`next_free_fight` from `characterstatus`). The bot picks the best dungeon by simulating every fightable opponent and choosing the one with the highest win chance (minimum 25%).

## Module Structure

| File | Purpose |
|---|---|
| `enums.py` | `DungeonKind`, `LightDungeon`, `ShadowDungeon`, `RuneType` enums |
| `constants.py` | Floor counts, simulation params |
| `models.py` | `Monster` and `Fighter` dataclasses |
| `monsters.py` | JSON loading, monster parsing |
| `dungeon.py` | Domain logic — progress tracking, selection, fight dispatch |
| `simulate/` | Battle simulation package (see below) |
| `simulate/fight.py` | Core combat loop (`fight_once`), Monte Carlo runners (`simulate_fight`, `simulate_sequential_fight`) |
| `simulate/fighters.py` | `fighter_from_character/monster`, `precompute_combat_stats`, damage range, crit, class multipliers |
| `simulate/combat.py` | `calc_hit_damage`, `will_skip`, `estimate_weapon_damage`, `estimate_hand_damage` |
| `simulate/constants.py` | Class ability tuning, `BYPASS_SPECIAL`, `TWISTER_DAMAGE_PER_LEVEL`, skip types |
| `simulate/class_models/` | Polymorphic class ability system (10 hooks, 10 subclasses) |
| `tasks/fight_dungeon.py` | Bot task (`should_run` / `run`) |
| `tasks/fight_portal.py` | Daily portal fight |

### Shared Simulation (`sfbot/simulate/`)

Combat functions shared between dungeon and pet simulation:

| File | Purpose |
|---|---|
| `constants.py` | `HEALTH_MULTIPLIER`, `WEAPON_MULTIPLIER`, `DAMAGE_MULTIPLIER`, `ARMOR_MULTIPLIER`, `SKIP_CHANCE`, `CRIT_BASE`, etc. |
| `combat.py` | `Combatant` Protocol, `calc_armor_reduction`, `calc_attribute_bonus`, `calc_crit_chance`, `MAX_CRIT_CHANCE` |

## Dungeon Types

### Light Dungeons (Solo)
Regular 1v1 fights. 37 dungeons (IDs 0–36, ID 17 is missing). Each has 10 floors except:
- **Sandstorm** — 1000 floors
- **Tower** — 100 floors (handled separately, see below)

### Shadow Dungeons (Companion 4v1)
All shadow dungeons use sequential 4v1 companion fights except Twister. 37 dungeons (IDs 0–36). Each has 10 floors except:
- **Continuous Loop of Idols** — 21 floors
- **Twister** — 1000 floors (handled separately, see below)

### Tower (Companion 4v1)
Light dungeon ID 14. Uses `PlayerTowerBattle {progress}/0` wire command (different from regular light battles). 100 floors. Uses sequential 4v1 companion fights.

### Twister (Solo)
Shadow dungeon ID 14. Despite being a shadow dungeon, Twister is **solo** (1v1). Uses `PlayerDungeonBattle {Tower_ID+1}/0` wire command (same as Tower's light command). 1000 floors. Twister monsters have `null` weapon damage in the JSON — estimated via interpolation (see Damage Estimation).

## Progress Tracking

Progress is parsed from login data:
- `dungeonprogresslight` — pipe-delimited values, indexed by `LightDungeon` ID
- `dungeonprogressshadow` — pipe-delimited values, indexed by `ShadowDungeon` ID

A progress value of `-1` (`LOCKED`) means the dungeon is not yet unlocked. A dungeon is finished when `progress >= floor_count`.

The `next_free_fight` timestamp comes from `characterstatus` at index `CHARACTER_STATUS_DUNGEON_NEXT_FREE_FIGHT_INDEX`. A fight is available when `next_free_fight <= server_time()`.

## Fight Selection (`get_best_dungeon`)

1. Collect all fightable light dungeons (unlocked, not finished, excludes Tower)
2. Collect all fightable shadow dungeons (unlocked, not finished, excludes Twister)
3. Check Tower and Twister separately via dedicated properties
4. Simulate every candidate against the player (+ companions for 4v1 dungeons)
5. Return the dungeon with the highest win chance

## Battle Simulation

Ported from [HafisCZ/sf-tools](https://github.com/HafisCZ/sf-tools) — the most accurate S&F simulator. Key source files for reference:
- `js/sim/base.js` — core simulation engine (damage, crit, health, rage, class multipliers)
- `js/sim/utils.js` — class config tables, damage reduction, skip chance
- `js/sim/dungeons.js` — dungeon-specific simulation logic
- `js/sim/data/` — monster data, raid data

Also uses the Rust reference implementation (`rust_reference/src/simulate/`).

### Fight Model

Each fight runs `SIMULATION_ITERATIONS` (10,000) iterations. Per iteration:

1. **First attacker**: Random 50/50, unless one fighter has the Shadow of the Cowboy enchantment (attacks first)
2. **Turns alternate** between attacker and defender, with a safety limit of `MAX_ROUNDS` (500)
3. **Rage scaling**: `rage = 1.0 + turn / 6.0` — damage increases each turn
4. **Dodge/Block**: Defender may skip the hit based on class `SKIP_CHANCE` (e.g. Scout 50%, Warrior 25%, Mage 0%). Mages bypass skip chance entirely
5. **Hit damage**: `random(min, max) × rage × crit_multiplier`
6. **Crit**: `chance = luck × 2.5 / target_level / 100`, capped at 50%. Base multiplier 2.0, +0.05 from enchantment, +0.11 per gladiator level advantage
7. Fight ends when one fighter's HP reaches 0

Win ratio = wins / iterations.

### Damage Calculation

```
damage_range = weapon_dmg × portal_multiplier × attribute_bonus × armor_reduction × rune_bonus × class_multiplier
```

| Factor | Formula |
|---|---|
| Portal multiplier | `1.0 + portal_dmg_bonus / 100` |
| Attribute bonus | `1.0 + max(main/2, main - target_main/2) / 10` |
| Armor reduction | `1.0 - min(armor × class_armor_mult / level, max_reduction) / 100`. Mages bypass armor |
| Rune bonus | `1.0 + (1 - resistance/100) × (rune_dmg/100)`. Capped at 60% rune damage, 75% resistance |
| Class multiplier | Base from `DAMAGE_MULTIPLIER` table × special class-vs-class bonuses |

### HP Calculation

```
base_hp = constitution × HEALTH_MULTIPLIER[class] × (level + 1)
```

Applied sequentially:
1. Wings (life potion): `× 1.25`
2. Portal HP bonus: `× (1 + portal_hp_bonus / 100)`
3. Rune health: `× (1 + rune_health / 100)`

Companion Warriors use `6.1×` HP multiplier instead of the normal `5.0×`.

### Class-Specific Rules

- **Mage**: Bypasses armor reduction AND dodge/block chance
- **Assassin**: Dual-wields weapon + shield slot, damage from both is summed
- **Berserker**: 1.25× damage multiplier, 50% dodge, but only 0.5× armor
- **Druid**: 1/3× damage multiplier but 4/3× vs Mage, 1.15× vs DemonHunter
- **Necromancer**: 5/9× damage multiplier, +0.1 additive (not multiplicative) vs DemonHunter
- **Paladin**: 0.833× damage, 6.0× HP, 1.5× vs Mage (mutual)
- **Companion Warriors**: 0% block chance (cannot dodge)

### Class Ability System (`simulate/class_models/`)

Each of the 12 character classes has unique combat abilities modeled by a `ClassModel` subclass. The base class (`base.py`) defines 10 hooks that subclasses override:

| Hook | Purpose | Used by |
|---|---|---|
| `before(ctx)` | Pre-fight effects | BattleMage (fireball) |
| `before_attack(ctx, ts)` | Modify attack stats before hit | Bard (melody), Druid (rage), Paladin (stance) |
| `control(ctx, ts, rage)` | Replacement attack ability | Druid (swoop), Necromancer (summon), PlagueDoctor (tincture) |
| `after_hit(ctx, ts, rage)` | Post-hit follow-up | Assassin (dual-wield) |
| `on_dodge(ctx, ts, rage)` | Reaction to dodged attack | Druid (request rage), Paladin (defensive heal) |
| `on_death(ctx)` | Death prevention | DemonHunter (revive) |
| `end_turn(ctx, ts, rage)` | End-of-turn effects | Bard (consume melody), Necromancer (minion follow-up) |
| `get_skip_override(ctx)` | Override defender skip chance | Paladin (stance), Necromancer (spectre) |
| `check_control_skip(ctx)` | Force attacker to lose turn | Berserker (chain-skip) |
| `get_total_health(fighter)` | Custom HP calculation | (base class, used by all) |

**Mage immunity (`BYPASS_SPECIAL`)**: Mages negate most class abilities. Each class model checks `ctx.defender_fighter.char_class in BYPASS_SPECIAL` before activating special effects.

`CLASS_MODEL_MAP` in `registry.py` maps `CharClass` → model factory. `create_model()` returns the appropriate subclass instance. New model instances are created per `fight_once()` call — no state carries over between iterations.

**Key types** (`base.py`):
- `CombatStats` — pre-computed per-fighter stats (damage range, crit chance/mult, total HP)
- `TurnState` — mutable per-turn modifiers (dmg_mult, crit overrides, defender skip override)
- `FightContext` — shared fight state (HP, turn counter, tincture tracking, attacker/defender swap)

## Sequential 4v1 Fights (Tower / Shadow)

Used by Tower and all shadow dungeons except Twister.

1. Companions fight in order: **Bert → Mark → Kunigunde → Player**
2. Each fighter has an independent sub-fight against the monster
3. Monster **retains HP** between sub-fights
4. **Rage resets** each sub-fight (turn counter starts at 0)
5. Monster damage/crit is **recalculated** per opponent (adjusts for different classes/stats)
6. If the monster dies during any sub-fight, the team wins
7. If all 4 fighters die, the team loses

### Companion Stats (Stat Shifting)

Companion stats are derived from the player's stats:

1. **Real companion attrs**: `CompanionInfo.total_attrs` from `character.companions` provides actual base+bonus attrs per companion from tower data. No attribute swapping needed.
2. **Equipment bonuses**: Each companion has their own equipped items, summed normally
3. **Total = companion_total_attrs + equipment**
4. **Potion percentages**: Player's active potions apply as percentage multipliers after the total (Small +10%, Medium +15%, Large +25%)

### Companion Weapon Damage

If a companion has an equipped weapon with damage values, those are used directly. Otherwise, `estimate_hand_damage()` provides a fallback based on level and class.

## Damage Estimation (Twister)

Twister monsters have `null` weapon damage in `dungeons.json`. The original `estimate_hand_damage()` (from Rust reference `get_hand_damage()`) significantly underestimates real damage.

`estimate_weapon_damage()` uses observed per-level damage constants:

| Class | Dmg per level |
|---|---|
| Warrior | 2.78 |
| Mage | 5.87 |
| Scout | 3.46 |

For simplicity, `min_dmg = max_dmg = ratio × level`. Hybrid classes are mapped to their weapon base class via `TWISTER_WEAPON_BASE_CLASS` (e.g. Assassin → Warrior, Necromancer → Mage, DemonHunter → Scout).

## Mirror Bosses

Some dungeon floors have a "mirror" special boss — the monster is a copy of the player. Since simulation would always be ~50/50, mirror bosses return `MIRROR_WIN_CHANCE` (0.5) without running the simulation.

## Wire Commands

| Dungeon Type | Command | Payload |
|---|---|---|
| Light (regular) | `PlayerDungeonBattle` | `{dungeon_id + 1}/0` |
| Shadow (regular) | `PlayerShadowBattle` | `{dungeon_id + 1}/0` |
| Tower | `PlayerTowerBattle` | `{progress}/0` |
| Twister | `PlayerDungeonBattle` | `{Tower_ID + 1}/0` |

Note: Twister uses the same wire command as light dungeons with Tower's ID, not a shadow battle command.

## Fighter Construction (Task)

The `fight_dungeon` task builds the player `Fighter` from:

- `character.total_attrs` — all 5 attributes
- `character.armor` — total armor
- `character.min_dmg` / `max_dmg` — weapon damage (summed for assassin dual-wield)
- `character.portal_hp_bonus` / `portal_dmg_bonus` — portal progression bonuses
- Equipment runes — weapon damage rune (fire/cold/lightning), resistance runes, HP rune
- `Enchantment.SHADOW_OF_COWBOY` — weapon enchantment check
- `PotionAttributeType.HP` — wings (life potion) active check
- Gladiator trainer level from `owntower` data

Companions are built via `build_companion_fighters()` using the stat shifting process described above.

## Edge Cases

- **LightDungeon ID 17 is missing** — light dungeons skip from 16 (Hemorridor) to 18 (Nordic Gods)
- **IntEnum cross-type equality**: `LightDungeon.TOWER` (14) and `ShadowDungeon.TWISTER` (14) share the same int value. `is_companion_dungeon()` uses `isinstance` checks (not frozenset membership) to avoid false matches
- **Circular import**: `dungeon.py` ↔ `monsters.py` — `monsters.py` import is lazy (inside `simulate_dungeon_fight()`)
- **Twister null damage**: Handled by `estimate_weapon_damage()` with per-level constants instead of the underestimating `estimate_hand_damage()` fallback
- **Unlocked companions**: `build_companion_fighters()` returns `[]` if companions are not unlocked, and `get_best_dungeon` / simulation handles empty companion lists gracefully
