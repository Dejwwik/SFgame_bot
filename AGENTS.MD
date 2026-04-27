Always use `uv` as the Python package manager and command runner: `uv run <script> [args]`

---

## Project Overview

SFgame is a Python async bot for automating Shakes & Fidget game accounts. It manages multiple characters concurrently using asyncio/aiohttp, running a loop of daily tasks (quests, arena, dice, guard duty, etc.).

**Python**: >=3.13 | **Package manager**: uv | **Dependencies**: aiohttp, requests, python-dotenv

## Project Structure

```
main.py              # Async multi-account task loop (production entry point)
web.py               # Flask web UI for account/character management
cron_crawl.py        # HoF crawler — scrapbook data collection per server
sfbot/               # Core library package
├── __init__.py      # Re-exports Bot, exceptions, Item, GameSession, FightResult
├── bot.py           # Bot class — ties all subsystems together
├── session.py       # HTTP session, SSO auth, request helpers
├── constants.py     # All enums, indices, field offsets, delimiters
├── character.py     # Character attrs, potions, class/race, is_dungeon_ready
├── resources.py     # Gold, mushrooms, hourglasses, etc.
├── fight.py         # Shared FightResult dataclass + parse_fight_result()
├── inventory.py     # Backpack, equipment, item/gem equipping, 13-stage free slot chain
├── items.py         # Item parsing, formatting
├── events.py        # Server-side bonus events
├── exceptions.py    # APIError, LoginError, InventoryFullError, GemExtractedAlert, etc.
├── logging.py       # Logging helpers, per-account file + console handlers
├── state.py         # PlayerState dataclass for passing state to domains
├── utils.py         # Utility functions (format_silver, etc.)
│
├── persistence/     # SQLite database layer
│   ├── accounts.py  # Account/character/stats CRUD, init_db()
│   └── opponents.py # Opponent data persistence
│
├── arena/           # Arena domain
│   ├── arena.py     # Arena, Opponent classes
│   └── tasks/
│       ├── fight_arena.py
│       └── fight_opponent.py
│
├── simulate/        # Shared simulation package (used by dungeon + pets)
│   ├── __init__.py  # Re-exports all constants + combat functions
│   ├── constants.py # HEALTH/WEAPON/DAMAGE/ARMOR_MULTIPLIER, SKIP_CHANCE, CRIT_BASE, etc.
│   └── combat.py    # Combatant Protocol, calc_armor_reduction, calc_attribute_bonus, calc_crit_chance
│
├── attributes/      # Attribute upgrade domain
│   ├── attributes.py # Attributes class (base attr upgrading)
│   ├── tests/
│   └── tasks/
│
├── guard/           # City Guard domain
│   ├── guard.py     # Guard class
│   └── tasks/
│       ├── start_guard.py
│       └── collect_guard.py
│
├── guild/           # Guild domain
│   ├── guild.py     # Guild class (fights, portal, hydra, skill upgrades)
│   └── tasks/
│       ├── do_guild_fights.py
│       └── upgrade_buildings.py
│
├── gems/            # Gem data types and sacrifice config
│   ├── gems.py      # Gem dataclass, sacrifice filter logic
│   └── utils.py     # Gem utility helpers (calc_average_gem_attribute)
│
├── items/           # Item domain
│   ├── items.py     # Item dataclass, parsing, formatting
│   ├── comparison.py # T²/A scoring, socket gate, gem scoring
│   └── tests/
│
├── inventory/       # Inventory domain
│   ├── inventory.py # Backpack, equipment, item/gem equipping, 13-stage free slot chain
│   ├── tests/
│   │   ├── conftest.py       # make_item(), make_gem(), make_gemmed_item(), make_potion(), make_inventory()
│   │   ├── test_finders.py   # Tests for all finder/helper methods
│   │   └── test_ensure_free_slot.py  # Tests for all 13 stages
│   └── tasks/
│       ├── ensure_best_items_are_equipped.py  # Equip + wash best items
│       └── ensure_best_gems_are_equipped.py   # Socket best gems
│
├── shop/            # Shop domain
│   ├── shop.py      # Weapon/Magic shop
│   ├── tests/
│   └── tasks/
│       └── buy_items.py
│
├── witch/           # Witch enchantments domain
│   ├── witch.py     # Witch class
│   └── tasks/
│       └── buy_enchantments.py
│
├── tavern/          # Tavern domain (quests only)
│   ├── tavern.py    # Tavern class (beer + quest orchestration)
│   ├── quests.py    # Quest parsing, selection, start/collect
│   └── tasks/
│       ├── start_quest.py
│       └── collect_quest.py
│
├── dice/            # Dice game domain
│   ├── dice.py      # DiceGame class
│   └── tasks/
│       └── play_dice.py
│
├── wheel/           # Wheel of Fortune domain
│   ├── wheel.py     # Wheel class
│   └── tasks/
│       └── spin_wheel.py
│
├── toilet/          # Arcane Toilet domain
│   ├── toilet.py    # Toilet class
│   └── tasks/
│       ├── flush_toilet.py
│       └── sacrifice_toilet.py
│
├── mount/           # Mount domain
│   ├── mount.py     # Mounts class
│   └── tasks/
│       └── ensure_mount.py
│
├── pets/            # Pet system domain
│   ├── pets.py      # Pets class (habitats, feeding, PvP, pet dungeons)
│   ├── constants.py # Pet limits, feeding priority paths
│   ├── pet_reqs.py  # Pet requirement helpers
│   ├── simulate.py  # Pet dungeon battle simulation (sf-tools port)
│   ├── pet_dungeons.json  # Pre-computed pet dungeon boss stats
│   ├── pet_dungeons.MD    # Pet dungeon system documentation
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_pet_reqs.py
│   └── tasks/
│       ├── feed_pet.py
│       ├── fight_pet_dungeon.py
│       ├── fight_pets.py
│       └── unlock_features.py
│
├── potions/         # Potion domain
│   ├── potions.py   # Potion attr helpers, drink/keep decisions
│   ├── tests/
│   │   └── test_potions.py
│   └── tasks/
│       └── drink_potions.py
│
├── smith/           # Blacksmith domain (dismantling, gem extraction)
│   ├── smith.py     # Smith class
│   └── tasks/
│       └── dismantle_item.py  # Daily dismantle task
│
├── fortress/        # Fortress domain (buildings, resources, gems, attacks)
│   ├── fortress.py  # Fortress class (buildings, units, gem mine, attacks)
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_build_queue.py
│   │   ├── test_can_upgrade.py
│   │   ├── test_hok_units.py
│   │   ├── test_pick_upgrade.py
│   │   ├── test_properties.py
│   │   ├── test_train_soldiers.py
│   │   └── test_train_units.py
│   └── tasks/
│       ├── collect_resources.py
│       ├── upgrade_building.py
│       ├── upgrade_units.py
│       ├── search_gems.py
│       ├── train_soldiers.py
│       ├── train_defence_units.py
│       └── attack_fortress.py
│
├── legendary_dungeon/  # Legendary Dungeon domain (timed event, 100-floor dungeon)
│   ├── __init__.py      # Re-exports LegendaryDungeon
│   ├── legendary_dungeon.py  # LegendaryDungeon class — parsing, combat, room handling, run loop
│   ├── constants.py     # Tuning constants, door/room/encounter classification sets
│   ├── models.py        # Dataclasses and enums (DungeonState, Door, GemOfFate, etc.)
│   ├── utils.py         # Gem scoring functions (score_gem, pick_best_gem)
│   ├── README.md        # Full module documentation
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_combat_helpers.py
│   │   ├── test_door_selection.py
│   │   ├── test_gem_scoring.py
│   │   ├── test_loot.py
│   │   └── test_parsing.py
│   └── tasks/
│       └── run_dungeon.py  # Task: should_run() + run() for main.py loop
│
├── dungeon/         # Dungeon domain (light, shadow, tower, twister, portal)
│   ├── __init__.py  # Re-exports Dungeon, FightResult (from sfbot.fight)
│   ├── dungeon.py   # Dungeon class, simulate_dungeon_fight
│   ├── enums.py     # DungeonKind, LightDungeon (0-36), ShadowDungeon (0-36), RuneType
│   ├── constants.py # Floor counts, simulation iterations, MIN_WIN_CHANCE
│   ├── models.py    # Fighter, Monster dataclasses
│   ├── monsters.py  # Monster loading from dungeons.json, get_monster_at()
│   ├── simulate/    # Battle simulation package (sf-tools port)
│   │   ├── __init__.py      # Re-exports all simulation functions
│   │   ├── fight.py         # fight_once(), simulate_fight(), simulate_sequential_fight()
│   │   ├── fighters.py      # fighter_from_character/monster, precompute_combat_stats
│   │   ├── combat.py        # calc_hit_damage, will_skip, estimate_weapon/hand_damage
│   │   ├── constants.py     # Class ability tuning, BYPASS_SPECIAL, TWISTER_DAMAGE_PER_LEVEL
│   │   └── class_models/    # Polymorphic class ability system
│   │       ├── __init__.py  # Re-exports ClassModel, CombatStats, FightContext, TurnState
│   │       ├── base.py      # ClassModel base class, TurnState, CombatStats, FightContext
│   │       ├── registry.py  # CLASS_MODEL_MAP, create_model()
│   │       ├── assassin.py  # Dual-wield after-hit
│   │       ├── bard.py      # Melody buff (tiered damage multiplier)
│   │       ├── battle_mage.py # Pre-combat fireball
│   │       ├── berserker.py # Chain-skip (force attacker to lose turns)
│   │       ├── demon_hunter.py # Revive on death
│   │       ├── druid.py     # Eagle swoop + bear rage
│   │       ├── necromancer.py # Minion summon (skeleton/zombie/spectre)
│   │       ├── paladin.py   # Stance cycling + dodge heal
│   │       └── plague_doctor.py # Tincture poison
│   ├── tests/
│   │   ├── conftest.py       # make_fighter(), make_monster()
│   │   ├── test_class_abilities.py
│   │   ├── test_dungeon.py
│   │   ├── test_models.py
│   │   ├── test_monsters.py
│   │   └── test_simulate.py
│   └── tasks/
│       ├── fight_dungeon.py  # Picks best dungeon via simulation, fights it
│       └── fight_portal.py   # Daily portal fight
│
└── reward/          # Reward domain (calendar, daily tasks, events, mail)
    ├── calendar.py      # Calendar class
    ├── daily_task.py    # Daily task rewards
    ├── event_reward.py  # Event reward collection
    ├── mail_reward.py   # Mail reward collection
    ├── models.py        # Reward data models
    ├── utils.py         # Reward utility helpers
    └── tasks/
        ├── claim_calendar.py
        ├── claim_daily_task.py
        ├── claim_event.py
        └── claim_pending.py
```

## Architecture & Patterns

### Domain-Based Package Structure
Each game system is a package under `sfbot/` containing:
- **Domain logic** (`<name>.py`): The class with game state parsing and API methods
- **`__init__.py`**: Re-exports the main class (e.g. `from sfbot.arena.arena import Arena`)
- **`tasks/`**: Automation tasks that operate on the domain

### Task Pattern
Every task module exposes exactly two functions:
```python
def should_run(bot: Bot) -> bool:
    """Check if this task needs to run."""

async def run(bot: Bot) -> None:
    """Execute the task."""
```

### Bot Composition
`Bot` directly owns all subsystems as attributes:
- `bot.arena`, `bot.guild`, `bot.guard`, `bot.witch`, `bot.shop`
- `bot.tavern` (quests + beer only)
- `bot.dice`, `bot.wheel`, `bot.toilet`, `bot.smith`, `bot.mounts`, `bot.pets`
- `bot.legendary_dungeon` (timed event 100-floor dungeon with gems, shop, blessings)
- `bot.dungeon` (light, shadow, tower, twister, portal — with battle simulation)
- `bot.fortress` (buildings, resources, gem mine, units, attacks)
- `bot.character`, `bot.resources`, `bot.inventory`, `bot.events`
- `bot.session` (GameSession — HTTP + auth)

### Import Style
- **Absolute imports only** — no relative imports (`from .X` or `from ..X`)
- Task files import `from sfbot import Bot`, `from sfbot.constants import ...`, etc.
- Package `__init__.py` files use `from sfbot.<pkg>.<module> import Class`

### Logging
- Uses Python `logging` module via `sfbot.logging.get_logger()`
- Per-account log prefixes via `set_log_prefix()` / `reset_log_prefix()`
- Log files written to `logs/` directory — one file per account (`logs/<name>.log`)

### Logging Best Practices
- **No "Logged in" spam**: `session.login()` / `login_async()` log at DEBUG. The only INFO-level login message is the single one in `main.py` at startup.
- **No bare task labels**: `main.py` does NOT log task names like `"guild"`, `"toilet"`, `"dice"` before running them. The domain methods already log meaningful results.
- **Log in domain methods, not task files**: Task `run()` functions should be thin wrappers. Put log messages inside the domain class methods (e.g. `guild.run_daily_async()` logs `"Guild attack: registered"`).
- **Log only meaningful actions**: Log what was actually done, not what is about to run. Good: `"Guard: started 10h shift"`, `"Dice: won 500 GOLD"`. Bad: `"start_guard"`, `"dice"`.
- **Prefix with domain name**: All log messages start with the domain: `"Arena: ..."`, `"Guild: ..."`, `"Toilet: ..."`, `"Elixir: ..."`, `"Quest: ..."`, `"Guard: ..."`, `"Dice: ..."`, `"Wheel: ..."`, `"Calendar: ..."`, `"Mount: ..."`, `"Enchant: ..."`, `"Beer: ..."`, `"Pets: ..."`, `"Fortress: ..."`, `"Inventory: ..."`, `"Equip: ..."`, `"Gem: ..."`, `"Smith: ..."`, `"Shop: ..."`, `"Attributes: ..."`, `"Daily: ..."`, `"Event: ..."`, `"Mail: ..."`, `"Hydra: ..."`.
- **Use WARNING for non-fatal failures**: `APIError` catches → `logger.warning()`. Successful actions → `logger.info()`.
- **Silent skip is OK**: If a task has nothing to do (e.g. toilet has no gems to sacrifice), it returns silently — no log line needed.

### Server Time
- `bot.session.server_time()` returns corrected server timestamp
- All time comparisons use server time, not local `time.time()`

### Main Loop (main.py)
Each account runs as an independent asyncio task. `main()` polls the DB for enabled characters and spawns tasks.

**`main()`**: Polls DB every 60s for enabled characters with configs. Creates `Bot.from_db_config()` for new ones, spawns `asyncio.create_task(run_account(bot))` for each.

**`run_account(bot)`**:
1. **Login with retries** — loops forever until `bot.login_async()` succeeds. `LoginError`/`KnownAPIError` → `warning()` (no traceback), other exceptions → `exception()`. Sleeps `ERROR_RETRY_DELAY` (60s) between attempts.
2. **Task loop** — sequential task execution, each iteration:
```
collect_quest → wheel → toilet_flush → buy_special → fortress_gems → calendar →
equip_best_items → equip_best_gems →
extract_gems → dismantle → buy_better → toilet_sacrifice → enchantments → upgrade_items →
dungeon →
collect_guard → guild → guild_portal → guild_upgrade → fortress_collect →
fortress_upgrade_building → fortress_upgrade_units → fortress_attack →
fortress_train_soldiers → fortress_train_defence →
underworld_collect → underworld_thirst → underworld_building → underworld_lure → underworld_fighters →
arena_manager_sacrifice → arena_manager_upgrade → arena_manager_buy →
prepare_elixirs → potions → mount → attributes → start_quest → arena → scrapbook →
fight_opponent → dice → dungeon_portal →
unlock_features → fight_pets → fight_pet_dungeon → feed_pet → legendary_dungeon →
start_guard → daily_reward → event_reward → mail_reward → sleep 180s+jitter
```
3. **Error handling in task loop**: `LoginError` → `warning()` + retry, `KnownAPIError` → `error()` + retry, other → `exception()` + retry. All sleep `ERROR_RETRY_DELAY`.

### Crawl Loop (cron_crawl.py)
Each server runs as an independent asyncio task. Crawls the full Hall of Fame every 14 days per server.

**`main()`**: Discovers unique servers from enabled characters in DB, spawns `asyncio.create_task(run_server(server))` for each.

**`ensure_account(server) -> CrawlSession`**: Owns the full account lifecycle. Retries forever:
1. Try stored creds from DB → login → return session
2. Login fails → set `force_new = True` → next iteration creates a new throwaway account via `register_account()`, saves to DB
3. Account creation fails → sleep `LOGIN_RETRY_DELAY` (5min), retry

**`run_server(server)`**: Loops forever:
1. Check `finished_at` from DB — if last crawl was <14 days ago, sleep the remainder
2. Call `ensure_account(server)` — gets a logged-in `CrawlSession` (retries forever internally)
3. Run `ServerCrawler` — crawls all HoF pages, stores player equipment positions in SQLite
4. On crash → log error, loop back to step 1

## Conventions

- No `assert` statements for attribute existence — assume Bot is always fully initialized after login
- No `from __future__ import annotations` in ALL files
- No docstrings in files where its not needed
- Use `X | None` instead of `Optional[X]` — do not import `Optional` from `typing`
- Task file names are action-based verbs: `fight_arena`, `start_guard`, `buy_potions`, etc.
- Sync and async variants: `method()` / `method_async()` pattern
- Quests: `start_quest()` / `collect_quest()` (not `stop_quest`)
- Arena completion: `bot.arena.is_completed` (not `xp_fights_completed`)
- Tavern completion: `bot.tavern.is_completed(state)` (takes PlayerState)
- **Always use enums** — never use raw ints or strings for game constants (BuildingType, UnitType, etc.)
- **Type annotations everywhere** — all function signatures, variables, and test helpers must have type annotations
- **Only one `# type: ignore` for Pylance** — allowed only on `**kwargs` parameters, nowhere else
- **No enum-to-string mappings** — do not create `get_name()` methods or `dict[Enum, str]` lookup tables. Use `enum.name` directly (e.g. `unit.name`, `building.name`)

## Environment Variables

### Web UI (web.py)
| Variable | Required | Description |
|---|---|---|
| `WEB_USERNAME` | **Yes** | Web UI login username (no default — crashes if missing) |
| `WEB_PASSWORD` | **Yes** | Web UI login password (no default — crashes if missing) |
| `SECRET_KEY` | No | Flask session secret (has dev fallback — set in production) |
| `TZ` | No | Timezone for log timestamps (default: `Europe/Prague` in Docker) |

### Bot / Crawler (main.py, cron_crawl.py)
No env vars required — accounts and characters are managed via the web UI and stored in SQLite.

## Rust Reference

`rust_reference/` contains a Rust implementation of the SF game client. Use it as reference for:
- Protocol field indices and parsing logic
- Battle simulation constants
- Command/response formats

## sf-tools Reference

The battle simulation is ported from [HafisCZ/sf-tools](https://github.com/HafisCZ/sf-tools) — the most accurate S&F simulator. Key source files:
- `js/sim/base.js` — core simulation engine (damage, crit, health, rage, class multipliers)
- `js/sim/utils.js` — class config tables, damage reduction, skip chance
- `js/sim/dungeons.js` — dungeon-specific simulation logic
- `js/sim/data/` — monster data, raid data

Website: https://sftools.mar21.eu/ (simulator, dungeons, fortress tools)

## Item Comparison System (`sfbot/items/comparison.py`)

### T²/A Correction Formula
Items and gems are scored using a **target-ratio bias correction** that automatically prioritizes attrs the build is deficient in:
1. For each attribute, compute `current_ratio = current_value / total_value` (floored at `RATIO_FLOOR = 0.01`).
2. Correction weight = `target_ratio² / current_ratio` — this makes underrepresented attrs exponentially more valuable.
3. An attr with target ratio 0 → T²=0 → correction=0 regardless, so unwanted attrs contribute nothing.

### Scoring Constants
| Constant | Value | Purpose |
|---|---|---|
| `BLOCK_VALUE_MULTIPLIER` | 0.05 | Shield block chance → equivalent attr value |
| `RATIO_FLOOR` | 0.01 | Division-by-zero guard for missing attrs |
| `ITEM_IMPROVEMENT_RATIO` | 1.15 | `new/old` must exceed this to justify a shop purchase |
| `GEM_IMPROVEMENT_RATIO` | 1.15 | `new/old` must exceed this to replace a socketed gem |
| `SMITH_UPGRADE_MULTIPLIER` | 1.03 | Each smith upgrade boosts highest attr(s) by 3% |

### Socket Gate
At level >= `SOCKET_GATE_LEVEL` (25), items without gem sockets are auto-rejected when the currently equipped item has one, unless the new item has main attr or constitution (in which case socketed items are auto-accepted).

### Weapon Scoring
Weapons use marginal projected-damage gain: `P_new - P_old`, where projected damage includes min/max damage range and any main-attr bonus contribution.

### Gem Scoring
Gems use the same T²/A system scoped to gem attributes only (`gem_target_ratios`). `score_gem_best_placement()` picks the best profile (main char or companion) for a gem.

### ComparisonProfile
A `ComparisonProfile` captures one character's scoring context:
- `char_class`, `main_attr`, `equipment_target_ratios`, `gem_target_ratios`
- Optional `companion: CompanionClass` for companion equipment
- `base_attrs`: current base attrs (used for weapon damage projection)

`Bot.build_comparison_profiles()` creates one for main character + one per companion.

## Inventory System (`sfbot/inventory/`)

### Overview
`Inventory` manages the backpack: parsing, item/gem equipping, selling, and the 16-stage free-slot priority chain. It uses **dependency injection** — `Smith`, `Toilet`, and `ComparisonProfile` list are passed as params to `ensure_free_slot_async()`, not imported directly.

### Key Types
- **`InventorySlot`**: `(index, wire, item)` — a single occupied slot
- **`wire`**: String position identifier like `"5/3"` (main backpack) or `"6/1"` (extended), used in `PlayerItemMove` API calls
- **`ItemCommandIdent`**: `typ/full_model_id/price/mush_price` — identity verification sent with every move/sell/dismantle command

### Item Equipping Flow (`ensure_best_items_are_equipped` task)
1. Build `ComparisonProfile` list (main + companions)
2. For each backpack item, call `score_item_best()` to find the best placement across all profiles
3. If score > 0, equip via `PlayerItemMove`
4. Wash unwashed equippable items via Toilet (`toilet.wash_async()`)
5. Loop until no more upgrades found

### Gem Socketing Flow (`ensure_best_gems_are_equipped` task)
1. Build `ComparisonProfile` list
2. Load currently equipped gem data per profile
3. For each backpack gem, call `score_gem_best_placement()` — picks best profile + slot
4. Socket if `new_score / old_score >= GEM_IMPROVEMENT_RATIO` (1.15)
5. Loop until no more upgrades found

### Free Slot Priority Chain (`ensure_free_slot_async`)
Called from `bot.ensure_free_slot()` when backpack is full. Pre-requisites: equip best items/gems first. Then the 16-stage chain tries progressively more aggressive disposal:

**Gem protection sets:**
- `all_protected = keep_gem_attrs | {LEGENDARY, ALL}` — main+CON+legendary+black
- `precious_gems = {LEGENDARY, ALL}` — legendary+black only

**Stages:**
| # | Action | Finder method | Protection |
|---|--------|---------------|------------|
| 1 | Dismantle equippable item | `get_item_to_dismantle()` | Skips legendary-gem items, skips good black gems |
| 2 | Sacrifice gem to toilet | `get_sellable_gem(keep_gem_attrs)` | Skips `keep_gem_attrs` + legendary |
| 3 | Sell off-attr potion | `get_off_attr_potion(keep_attrs)` | Only sells non-main, non-CON |
| 4 | Sell sub-max potion | `get_sub_max_potion(keep_attrs, max_size)` | Sells main/CON below max size |
| 5 | Sell unprotected gem | `get_sellable_gem(all_protected)` | Keeps main+CON+legendary+black |
| 6 | Sell normal item | `get_sellable_item(NORMAL, all_protected)` | Skips items with protected gems |
| 7 | Rescue gem extraction | `get_item_with_rescuable_gem()` | Extracts main-attr/CON gem if it scores as upgrade; raises `GemExtractedAlert` |
| 8 | Sell normal item (relaxed) | `get_sellable_item(NORMAL, precious_gems)` | Only protects legendary+black gems |
| 9 | Sell low-value attr gem | `get_low_value_gem(avg, keep_gems)` | Sells main/CON gems below threshold |
| 10 | Sell epic/legendary items | `get_sellable_item()` × 2 per rarity | Tries `all_protected` then `precious_gems` |
| 11 | Sell gem (relaxed) | `get_sellable_gem(precious_gems)` | Only keeps legendary+black |
| 12 | Dismantle/sell low-value gem item | `get_item_with_low_value_gem()` | Skips legendary gems; threshold-checks black |
| 13 | Sell low-value gem | `get_low_value_gem()` | Skips legendary; threshold-checks black |
| 14 | Extract gem from item | `get_item_with_extractable_gem()` | Extracts legendary always; main-attr/CON above avg × GEM_IMPROVEMENT_RATIO; black above threshold; raises `GemExtractedAlert` |
| 15 | Force-socket or sell worst black gem | `get_worst_gem_by_attr(BLACK)` | Force-sockets if any improvement (old gem destroyed), otherwise sells worst black gem |
| 16 | Force-socket or sell worst legendary gem | `get_worst_gem_by_attr(LEGENDARY)` | Force-sockets if any improvement (old gem destroyed), otherwise sells worst legendary gem |

**Threshold math:** `value < average_single_attr_gem × GEM_IMPROVEMENT_RATIO × BLACK_GEM_ATTR_RATIO` for black gems.

**Stage 7 special:** Before relaxed sells lose items with main-attr/CON gems, `get_item_with_rescuable_gem()` uses `score_gem_best_placement()` to check if the socketed gem would be a scoring upgrade. Only extracts if the gem is useful. Logs at INFO level for observability.

**Stage 14 special:** Extracting a gem raises `GemExtractedAlert` — caught in `main.py` to trigger `continue` (re-poll + re-socket cycle). Also extracts valuable main-attr/CON gems (not just legendary/black).

### Logging in ensure_free_slot_async
- Stages log at DEBUG level: `logger.debug("Inventory: entering [N] ...")` and `logger.debug("Inventory: passed [N]")`
- Stage 7 (rescue extraction) logs at INFO level for observability
- Successful actions log at INFO: `"Inventory: [N] dismantled/sold/extracted ..."`
- Final fallback: `logger.warning("Inventory: could not free a slot")`

### Average Gem Attribute Calculation (`sfbot/gems/utils.py`)
`calc_average_gem_attribute(character_level, hall_of_knights, mine_level)` returns the expected single-attr gem value. Uses a linear formula for mine ≤ 25, and a polynomial regression for mine > 25. Hall of Knights adds `hok_level / 3` to both. This value is the baseline for all gem threshold comparisons in the free-slot chain.

### DI Pattern
- `Smith` owns `dismantle_slot_async()` and `extract_gem_from_slot_async()`
- `Toilet` owns `sacrifice_slot_async()` and `wash_async()`
- `Inventory.ensure_free_slot_async()` receives them as `smith: Smith | None`, `toilet: Toilet | None`, and `profiles: list[ComparisonProfile]`
- `bot.ensure_free_slot()` gates on level: `smith = bot.smith if level >= SMITH_UNLOCK_LEVEL else None`

## Dungeon System (`sfbot/dungeon/`)

> **Detailed reference**: `sfbot/dungeon/dungeons.MD` — full module docs with wire commands, edge cases, companion stats, and damage estimation tables.

### Overview
The dungeon system handles light dungeons, shadow dungeons, the Tower, the Twister, and the portal. It uses a **battle simulation** (ported from sf-tools/HafisCZ) to pick the best dungeon to fight each cycle.

### Dungeon Types
| Type | Enum | Floors | Wire command |
|---|---|---|---|
| Light (normal) | `LightDungeon` (0-36) | 10 per dungeon | `PlayerDungeonBattle` |
| Shadow | `ShadowDungeon` (0-36) | 10 per dungeon | `PlayerShadowBattle` |
| Tower | `LightDungeon.TOWER` (14) | 100 floors | `PlayerTowerBattle` |
| Twister | `ShadowDungeon.TWISTER` (14) | 1000 floors | `PlayerDungeonBattle` |
| Continuous Loop | `ShadowDungeon.CONTINUOUS_LOOP_OF_IDOLS` (17) | 21 floors | `PlayerShadowBattle` |
| Portal | separate system | 50 floors | `PlayerPortalBattle` |

### Progress Tracking
- `dungeon.light_progress: dict[int, int]` — dungeon_id → current floor (from `dungeonprogresslight(37)`)
- `dungeon.shadow_progress: dict[int, int]` — dungeon_id → current floor (from `dungeonprogressshadow(37)`)
- `LOCKED = -1` means not yet unlocked
- `is_finished_light()` / `is_finished_shadow()` compare progress against floor counts

### Fight Result Parsing
All fight methods across domains return `FightResult` from `sfbot/fight.py`, parsed from `fightresult.battlereward`:
```python
@dataclass(slots=True)
class FightResult:
    won: bool    # index 0 != 0
    xp: int      # index 3
    silver: int   # index 2
```
`parse_fight_result(result)` extracts from the `/`-delimited response. Used by dungeon, arena, and pet fight methods. Each domain method logs the result internally (`"Domain: won/lost {context} +{xp:,} XP"`).

### Battle Simulation (`sfbot/dungeon/simulate/`)
Port of sf-tools (HafisCZ) battle simulator, structured as a package:

| Module | Purpose |
|---|---|
| `fight.py` | Core combat loop (`fight_once`), Monte Carlo runners (`simulate_fight`, `simulate_sequential_fight`) |
| `fighters.py` | `fighter_from_character/monster`, `precompute_combat_stats`, `calc_class_multiplier`, `calc_crit_multiplier`, `calc_damage_range`, `calc_rune_bonus` |
| `combat.py` | `calc_hit_damage`, `will_skip`, `estimate_weapon_damage`, `estimate_hand_damage` |
| `constants.py` | Class ability tuning constants, `BYPASS_SPECIAL`, `TWISTER_DAMAGE_PER_LEVEL`, skip types |
| `class_models/` | Polymorphic class ability system (see below) |

Shared combat functions (`calc_armor_reduction`, `calc_attribute_bonus`, `calc_crit_chance`) live in `sfbot/simulate/combat.py` and are used by both dungeon and pet simulation.

### Class Ability System (`sfbot/dungeon/simulate/class_models/`)
Each of the 12 character classes has unique combat abilities modeled by a `ClassModel` subclass. The base class defines 10 hooks:

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

**Mage immunity (BYPASS_SPECIAL)**: Mages negate most class abilities. Each class model checks `ctx.defender_fighter.char_class in BYPASS_SPECIAL` before activating special effects.

`CLASS_MODEL_MAP` in `registry.py` maps `CharClass` → model factory. `create_model()` returns the appropriate subclass instance.

### Fighter Model (`sfbot/dungeon/models.py`)
```python
@dataclass(slots=True)
class Fighter:
    char_class, level, strength, dexterity, intelligence, constitution, luck
    armor, min_dmg, max_dmg
    rune_type: RuneType, rune_value: int
    fire_resistance, cold_resistance, lightning_resistance
    portal_hp_bonus, portal_dmg_bonus, rune_health
    gladiator: int
    has_sword_of_vengeance: bool   # weapon enchant: +5% crit damage
    has_shadow_of_cowboy: bool     # gloves enchant: attack first
    has_life_potion: bool          # Wings: +25% HP
    health: int                    # pre-computed for monsters (0 = calculate)
    is_companion: bool
```

### Enchantments (combat-relevant)
Two separate enchantments affect simulation — they are on **different equipment slots**:
- **`SWORD_OF_VENGEANCE`** (weapon, `Enchantment = 11`) → `+CRIT_ENCHANTMENT_BONUS (0.05)` to crit multiplier
- **`SHADOW_OF_COWBOY`** (gloves, `Enchantment = 51`) → attack priority (goes first)

These are stored separately on `EquipmentRunes` and `Fighter`. Never conflate them.

### Character Integration (`sfbot/character.py`)
`Character.parse()` pre-computes all simulation-relevant data:
- `character.runes: EquipmentRunes` — aggregated from all equipped items via `collect_runes()`
- `character.gladiator: int` — from `owntower.towerSave[GLADIATOR_TRAINER_INDEX]`
- `character.companions: dict[CompanionClass, CompanionInfo]` — per-companion total attrs, armor, dmg, runes
- `character.has_life_potion: bool` — Wings potion active
- `character.portal_hp_bonus` / `character.portal_dmg_bonus` — from character save

`EquipmentRunes` aggregates: fire/cold/lightning resistance, rune_health, weapon rune type/value, `has_sword_of_vengeance`, `has_shadow_of_cowboy`.

`CompanionInfo` stores: companion_class, char_class, level, total_attrs, armor, min/max_dmg, runes.

### Task Flow (`fight_dungeon.py`)
1. `should_run()` checks `bot.dungeon.is_free` (cooldown expired)
2. `run()` calls `dungeon.update_async()` to refresh progress
3. Builds `Fighter` instances from `bot.character` data (no re-parsing tower/equipment)
4. `dungeon.get_best_dungeon(player, companions)` simulates all fightable dungeons, returns `(kind, target, win_chance)`
5. Skips if `win_chance < MIN_WIN_CHANCE (0.25)`
6. Logs pre-fight: `"Dungeon: fighting {name} ({kind}), win chance {%}"`
7. Calls appropriate fight method → returns `FightResult`
8. Domain method logs: `"Dungeon: won/lost {name} ({kind}) +{xp} XP"`

### Key Constants (`sfbot/dungeon/constants.py`)
| Constant | Value |
|---|---|
| `FLOORS_PER_DUNGEON` | 10 |
| `TOWER_FLOORS` | 100 |
| `TWISTER_FLOORS` | 1000 |
| `CONTINUOUS_LOOP_FLOORS` | 21 |
| `PORTAL_FLOORS` | 50 |
| `LOCKED` | -1 |
| `MIN_WIN_CHANCE` | 0.25 |
| `MIRROR_WIN_CHANCE` | 0.5 |
| `SIMULATION_ITERATIONS` | 10,000 |

### Twister Weapon Damage
Twister monsters have `null` weapon damage in `dungeons.json`. Instead of using cached dungeon data, `estimate_weapon_damage()` uses per-level constants (`TWISTER_DAMAGE_PER_LEVEL`):

| Class | Dmg per level |
|---|---|
| Warrior | 2.78 |
| Mage | 5.87 |
| Scout | 3.46 |

`min_dmg = max_dmg = ratio × level`. Hybrid classes map to weapon base class via `TWISTER_WEAPON_BASE_CLASS`.

### Companion Base Attrs (`build_comparison_profiles`)
Companion profiles use the player's `base_attrs` with main attributes swapped — e.g. if player is Mage (INT), companion Bert (Warrior/STR) gets player's INT value in STR slot and vice versa. This reflects how companion base stats mirror the player's.

### Simulation Formulas (sf-tools port)
- **Health**: `CON × class_multiplier × (level + 1)`, then ceil each: `× (1 + life_potion/100)`, `× (1 + portal_hp/100)`, `× (1 + rune_health/100)`
- **Rage**: `1 + turn / 6` (increases each round)
- **Crit chance**: `min(0.5, luck × 2.5 / target_level / 100)`
- **Crit multiplier**: `2.0 + sword_of_vengeance × 0.05 + gladiator_advantage × 0.11`
- **Attribute bonus**: `1 + max(attacker_main/2, attacker_main - target_same_attr/2) / 10`
- **Damage**: `(1 + portal_dmg/100) × (1 - armor_reduction/100) × (1 + rune_bonus) × class_multiplier × (1 + attr_bonus/10)`
- **Rune damage**: `min(60, rune_value) × (1 - min(75, target_resistance) / 100)`