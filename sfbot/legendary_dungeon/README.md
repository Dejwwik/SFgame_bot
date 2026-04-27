# Legendary Dungeon

The Legendary Dungeon is a timed event (runs for several days) where the player navigates a 100-floor dungeon. The bot fully automates: entering, choosing doors, fighting/escaping monsters, interacting with rooms, shopping at the Key Master, collecting loot, and selecting Gems of Fate after bosses.

## Dungeon Layout

```
Floors  1-24:  Section 0  →  Boss at floor 25  →  Gem pick #1
Floors 26-49:  Section 1  →  Boss at floor 50  →  Gem pick #2
Floors 51-74:  Section 2  →  Boss at floor 75  →  Gem pick #3
Floors 76-99:  Section 3  →  Final boss at 100  (no gem pick)
```

Each section has ~25 floors with monsters, traps, encounters, and rooms. Bosses guard the section boundaries. After killing a boss (except the final), the player picks one Gem of Fate from 3 choices.

## All Damage is %-based

All damage in the dungeon is a percentage of max HP — character level is irrelevant. Key damage values:

| Source | Damage (% HP) |
|---|---|
| Section 0 monster | up to 14.4% |
| Section 1 monster | up to 20.6% |
| Section 2 monster | up to 23.3% |
| Section 3 monster | up to 25.7% |
| Boss at 25 | up to 19.6% |
| Boss at 50/75 | up to 28.1% |
| Final boss at 100 | up to 52.5% |
| Trap | 10% |
| Sacrificial door | 12% |
| Sacrificial chest | 15% |
| Poison curse | 5% per room |
| Broken Armor curse | +50% fight damage |

Failed escapes deal the same damage as fighting. Successful escapes deal 0.

## Stage Machine

The dungeon operates as a state machine. Each API response puts the player in one of these stages:

| Stage | Meaning | Bot action |
|---|---|---|
| `NOT_ENTERED` | No run in progress | Enter if active and HP threshold met |
| `DOOR_SELECT` | Two doors shown | Score both doors, pick the better one |
| `ROOM_ENTERED` | Inside a room | Handle monster/encounter/room (see below) |
| `ROOM_INTERACTED` | Interacted with a room | Collect key & loot, continue |
| `ROOM_SPECIAL` | Gem selection after boss | Score gems, pick the best |
| `ROOM_FINISHED` | Room completed | Collect loot, advance |
| `HEALING` | Dead, healing in progress | Stop — wait for next cycle |
| `COMPLETED` | Run finished (floor 100 cleared) | Stop — do not re-enter |

The main loop (`run_async`) calls `step_async()` up to 300 times. Each step reads the current stage and performs the appropriate action.

## Wire Protocol Parsing

### iadungeon / iadungeonsave

The dungeon state arrives as `|`-delimited integers. Key field positions:

```
[0]  random_id        [1]  health_status   [2]  current_hp
[3]  pre_battle_hp    [4]  max_hp
[5..7]   blessing types         [8..10]  curse types
[11..13] blessing strength      [14]     curse_0 strength
[15] stage            [16] gem_count       [17] current_floor  [18] max_floor
[19..20] door types (in DOOR_SELECT) / [19] room_type (otherwise)
[22] encounter
[25..26] door traps
[39] keys
[40..41] curse_1/curse_2 strength
[42..44] blessing max_uses      [45..47] curse max_uses
```

Effect strength is encoded as a composite integer: `remaining_uses × 10000 + power`.

### iadungeonsoulstones

Gems are encoded as groups of 6 ints: `[type, adv_effect, adv_pwr, dis_effect, dis_pwr, special]`. First 3 groups = owned gems, remaining = available choices.

### Encounters

Encounter field [22] encodes:
- **Negative value**: Monster (monster_id = abs(value))
- **Positive value**: `RoomEncounterType` enum (chest, barrel, skeleton, etc.)

### Loot

Loot appears in `ialootitem` (direct drop) or `iapendingitems` (queued with count prefix). The bot auto-collects into the first free backpack slot using `PlayerItemMove` with an `ItemCommandIdent` verification string.

## Door Selection (`pick_door`)

Each door gets a score based on type, then the higher-scoring door is picked. Factors:

- **Good doors** (open, epic, golden, blessing, key master shop): +50
- **Resource doors** (wood, stone, souls, etc.): +30
- **Trial doors**: +20
- **Monster doors**: 0 baseline, -55 if trapped without Disarm
- **Locked doors**: +15 if Lock Pick blessing, -80 if no keys or doomed, -20 if hoarding keys, +15 in last section
- **Double-locked doors**: similar but stricter (-90 if < 2 keys)
- **Sacrificial doors**: -25 (unavoidable HP cost)
- **Cursed doors**: -60 (very bad)
- **Blocked**: -100

Context modifiers: `doomed` (can't survive boss), `hoarding` (need more keys before boss), `last_section` (floors 75+, spend keys freely), `has_disarm`/`has_pick` (blessings negate traps/locks).

## Monster Handling (`handle_monster`)

Priority chain:
1. **Boss** → always fight (can't escape)
2. **One-Hit Wonder** blessing → fight (0 damage)
3. **Escape Assistant** blessing → escape (+80% success rate)
4. **Doomed + near boss + can survive fight** → fight (hunt keys for shop)
5. **Doomed + near boss + can't survive fight** → escape (get closer to boss)
6. **Need keys + can survive** → fight (keys drop from fights)
7. **Otherwise** → escape (preserve HP for the boss)

## Key Master's Shop (`handle_key_master_shop`)

Buys blessings in priority order, preferring the large (more expensive) version:

| Blessing | Small cost | Large cost | Effect |
|---|---|---|---|
| One-Hit Wonder | 2 keys | 4 keys | Instant-kill for 4/8 rooms |
| Escape Assistant | 3 keys | 6 keys | +80% escape for 5/10 rooms |
| Road to Recovery | 1 key | 3 keys | Heal 10%/20% per room |
| Elixir of Life | 1 key | 3 keys | Instant 25%/50% heal |

Healing blessings are skipped if HP ≥ 70%.

## Gem of Fate Scoring

After each boss kill (floors 25, 50, 75), the player picks one Gem of Fate from 3 choices. Each gem has:
- **Advantage**: a beneficial effect with a power value
- **Disadvantage**: a harmful effect with a power value
- **Special**: a passive dungeon modifier (more/fewer traps, monsters, etc.)

### Scoring Formula

Every gem is scored in units of **"% of max HP saved"** over the remaining dungeon:

```
score = effect_hp_impact(advantage) - effect_hp_impact(disadvantage) + special_hp_impact(special)
```

`remaining_context(pick_floor)` returns how many sections and bosses remain. A gem picked at floor 25 affects 3 more sections; at floor 75 it only affects 1.

### Effect HP Impact

Each effect is valued by counting expected encounters of the relevant type and multiplying by the damage reduction:

- **DAMAGE_FROM_MONSTERS**: `(total_fight_dmg + total_boss_dmg) × p`
- **DAMAGE_FROM_TRAPS**: `sections × traps/section × 10% × p`
- **ESCAPE_CHANCE**: `sections × escapes/section × fight_dmg × p`
- **CHANCE_OF_KEYS**: `fights × p × avg_fight_dmg × 0.3` (keys save fights via locked doors)
- **DURATION_OF_BLESSINGS**: `sections × 2 blessings × 3.0 HP_value × p`

Where `p = pwr_abs / 100` (convert percentage to fraction).

### Special HP Impact

Specials modify dungeon layout, valued per remaining section:
- `WEAKER_MONSTERS_SPAWN`: +10% total fight damage saved
- `STRONGER_MONSTERS_SPAWN`: -10% total fight damage
- `MORE_TRAPS_SPAWN` / `ALWAYS_ONE_TRAP`: -2 × trap damage per section
- `CHANCE_OF_UNLOCKED_DOORS`: +0.3 × 2 × avg fight damage per section (skipped fights)

The gem with the highest score is picked.

## Run Start Threshold (`should_start_run`)

The bot checks if the character has enough HP to push further:
- Floors < 97: requires ≥ 99% HP (effectively fully healed)
- Floor 97: HP > final_boss_dmg + 2 × fight_cost
- Floor 98: HP > final_boss_dmg + fight_cost
- Floor 99: HP > final_boss_dmg
- **Urgency**: if < 2 hours remain before event ends, enter with ≥ 20% HP

The task-level `should_run()` mirrors these thresholds: normally waits for 99% HP, but if < 2 hours remain (`URGENT_TIME_REMAINING = 7200`), accepts ≥ 20% HP (`URGENT_HP_THRESHOLD`).

Fight cost accounts for gem-based damage reduction and escape chance bonuses.

## Event Time Windows

The server provides three timestamps via `iadungeontime`: `start_ts`, `end_ts`, `close_ts`.

| Property | Window | Purpose |
|---|---|---|
| `is_enterable` | `start_ts` to `end_ts` | Normal entry window |
| `is_active` | `start_ts` to `close_ts` | Event still exists (grace period after `end_ts`) |

Between `end_ts` and `close_ts`, the game allows one final re-entry for characters in HEALING state. The bot uses `is_active` (not `is_enterable`) to gate entry in `should_run()` and `step_async()`, so it can take advantage of this grace period. `COMPLETED` always returns `False` immediately.

## Room Handling

| Room type | Action |
|---|---|
| Safe rooms (fountain, narrator, rocks, sewers, etc.) | Interact (free loot/heal) |
| Key Master Shop | Buy blessings, then leave |
| Key to Failure Shop | Leave immediately (skip) |
| Skip rooms (lava, wheel, undead, rainbow, etc.) | Leave immediately |
| Encounters: safe (chests, crates, barrels) | Open |
| Encounters: risky (skeletons, mimic, sacrifice, curse) | Skip |
| Empty / unknown | Continue / leave |

## Optional / Not Implemented

- **Key to Failure Shop**: The shop sells curses (negative effects) for keys. The Rust reference uses `LegendaryDungeonBuyCurse { effect, keys }` (same `IADungeonMerchantBuy` wire command as the Key Master). Buying a curse when HP is high could be beneficial — some curses are mild and spending keys on them prevents worse random curses. Currently the bot skips this room entirely.

## Files

```
__init__.py             # Re-exports LegendaryDungeon
legendary_dungeon.py    # LegendaryDungeon class — parsing, combat, room handling, run loop
constants.py            # All tuning constants, door/room/encounter classification sets
models.py               # Dataclasses and enums (DungeonState, Door, GemOfFate, etc.)
utils.py                # Gem scoring functions (score_gem, pick_best_gem, remaining_context)
tasks/
  run_dungeon.py        # Task: should_run() + run() for main.py loop
tests/
  conftest.py           # Test fixtures (make_dungeon, make_door, make_effect, etc.)
  test_combat_helpers.py
  test_door_selection.py
  test_gem_scoring.py
  test_loot.py
  test_parsing.py
```

## API Commands

| Action | Command | Parameter |
|---|---|---|
| Enter dungeon | `IADungeonStart` | `theme/0` |
| Pick door 0/1 | `IADungeonInteract` | `1`/`2` (or `5`/`6` with key) |
| Fight | `IADungeonInteract` | `20` |
| Escape | `IADungeonInteract` | `21` |
| Open encounter | `IADungeonInteract` | `40` |
| Skip encounter | `IADungeonInteract` | `42` |
| Interact room | `IADungeonInteract` | `50` |
| Leave room | `IADungeonInteract` | `51` |
| Collect key | `IADungeonInteract` | `60` |
| Continue | `IADungeonInteract` | `70` |
| Rock/Paper/Scissors | `IADungeonInteract` | `90`+choice |
| Pick gem | `IADungeonSelectSoulStone` | gem_type value |
| Buy from shop | `IADungeonMerchantBuy` | `effect/keys` |
| Buy curse | `IADungeonMerchantBuy` | `effect/keys` (same command, Key to Failure shop) |
| Take loot | `PlayerItemMove` | `401/1/wire/ident` |
