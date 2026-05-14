# SFgame Bot — Shakes & Fidget Automation Platform

> A full-stack Python automation platform that plays the browser RPG [Shakes & Fidget](https://www.sfgame.net/) autonomously. It manages multiple game accounts concurrently, makes intelligent decisions using Monte Carlo battle simulation, and optimizes character progression across 50+ game systems — all running 24/7 with zero manual intervention.

---

## The Problem

Shakes & Fidget is a browser-based RPG where progression depends on performing dozens of repetitive daily tasks — fighting arena battles, running dungeons, managing fortress resources, optimizing gear, feeding pets, and more. Each task has cooldowns, prerequisites, and optimal timing. Doing this manually across multiple characters is tedious and time-consuming.

## The Solution

I built an async Python bot that fully automates the game. It logs into multiple accounts via SSO, reverse-engineers the game's HTTP API, and runs a continuous task loop — performing every action a human player would, but smarter. The system includes:

- A **battle simulation engine** that runs 10,000 Monte Carlo iterations to pick the optimal dungeon
- A **gear scoring algorithm** that mathematically determines the best item for each slot
- A **16-stage inventory management chain** that intelligently handles a full backpack
- A **Flask web dashboard** for managing accounts and monitoring progress
- A **Hall of Fame crawler** that scrapes player data from every game server

---

## Technical Highlights

### Architecture: Domain-Driven Design with Async Composition

The bot is structured as **28 domain packages**, each encapsulating a game system (arena, dungeon, fortress, pets, etc.). Every domain follows the same pattern:

```
sfbot/dungeon/
├── dungeon.py          # Domain class — state parsing + API methods
├── enums.py            # Domain-specific enums
├── constants.py        # Tuning constants
├── models.py           # Data models (dataclasses)
├── simulate/           # Battle simulation sub-package
│   ├── fight.py        # Core combat loop + Monte Carlo runners
│   ├── fighters.py     # Fighter construction from game data
│   ├── combat.py       # Hit damage, skip chance calculations
│   └── class_models/   # Polymorphic class ability system (9 classes)
├── tasks/              # Automation tasks (should_run/run protocol)
│   ├── fight_dungeon.py
│   └── fight_portal.py
└── tests/              # Unit tests with fixtures
```

The central `Bot` class composes all domains as attributes — no inheritance, no god class. Each domain receives only a `GameSession` reference and parses its own data from the server response.

**Task protocol**: Every automation task exposes exactly two functions:
```python
def should_run(bot: Bot) -> bool:  # Check preconditions
async def run(bot: Bot) -> None:   # Execute the action
```

This keeps the main loop dead simple — iterate through tasks, check, run, sleep.

### Concurrency: Asyncio Multi-Account Engine

The main loop uses `asyncio` to run any number of game accounts as independent tasks:

```
main() → polls DB every 60s for enabled characters
       → spawns asyncio.create_task(run_account(bot)) for each
       → each account runs its own sequential task loop
       → sleeps 180s + random jitter between iterations
       → night mode: auto-sleeps 2:00–8:00
```

Each account is fully independent — login retries, error recovery, and task execution are all self-contained. The bot never crashes permanently; every error triggers a retry loop.

### Battle Simulation: Monte Carlo with Class Abilities

The dungeon system includes a **full combat simulator** ported from the community's most accurate tool ([sf-tools by HafisCZ](https://github.com/HafisCZ/sf-tools)). It models:

- **Turn-based combat** with rage scaling, critical hits, dodge mechanics, and armor reduction
- **9 character class abilities** via a polymorphic `ClassModel` system:
  - *Assassin* — dual-wield follow-up attacks
  - *Bard* — tiered melody damage buff
  - *Battle Mage* — pre-combat fireball
  - *Berserker* — chain-skip (force opponent to lose turns)
  - *Demon Hunter* — revive on death
  - *Druid* — eagle swoop + bear rage mode
  - *Necromancer* — minion summoning (skeleton → zombie → spectre)
  - *Paladin* — stance cycling + dodge healing
  - *Plague Doctor* — tincture poison over time
- **Elemental runes** — fire/cold/lightning with resistance calculations
- **Enchantment effects** — Sword of Vengeance (+5% crit), Shadow of Cowboy (attack priority)

For each dungeon, the simulator runs **10,000 iterations** and returns a win probability. The bot picks the dungeon with the highest expected progress and skips any with less than 25% win chance.

### Item Scoring: T²/A Bias Correction

Items and gems are scored using a target-ratio bias correction formula that automatically prioritizes attributes the build is deficient in:

1. For each attribute, compute `current_ratio = current_value / total_value`
2. Correction weight = `target_ratio² / current_ratio`
3. Attributes with target ratio 0 contribute nothing — unwanted stats are ignored

This means: if your character is a Mage and you're low on Intelligence, items with INT get a massive scoring boost. The system naturally balances attribute distribution toward your configured targets without hardcoded priority lists.

**Weapons** use marginal projected-damage gain instead of the T²/A formula. **Gems** use the same T²/A system scoped to gem-specific target ratios. The scoring works across both the main character and companions — each gem is placed where it provides the most value.

### Inventory Management: 16-Stage Progressive Disposal

When the backpack is full, the bot runs a priority chain of 16 increasingly aggressive actions:

| Stage | Action | Protection Level |
|---|---|---|
| 1 | Dismantle worst equippable item | Skips legendary gems |
| 2 | Sacrifice gem to toilet | Protects main-attr gems |
| 3–4 | Sell off-attribute/sub-max potions | Keeps main + CON |
| 5–6 | Sell unprotected gems/items | Protects main+CON+legendary+black |
| 7 | **Rescue extraction** — extract gem if it scores as upgrade | Uses scoring engine |
| 8–10 | Sell items (relaxed protection) | Only protects legendary+black gems |
| 11–13 | Sell gems (relaxed protection) | Threshold-based value checks |
| 14 | Extract valuable gems from items | Triggers re-equip cycle |
| 15–16 | Force-socket or sell worst legendary/black gems | Last resort |

Stage 7 is particularly interesting — before items with useful gems are sold, the bot runs `score_gem_best_placement()` to check if the socketed gem would be an upgrade anywhere. If so, it extracts the gem and triggers a re-equip cycle instead of losing it.

### HTTP Session: Reverse-Engineered Game Protocol

The `GameSession` class handles the full communication with S&F servers:

- **SSO authentication** — login via the central auth server, obtain character-specific tokens
- **Request/response parsing** — the game uses a custom delimiter-based wire protocol (not JSON)
- **Server time synchronization** — all timing decisions use corrected server timestamps
- **Rate limiting and retry logic** — handles transient errors, session expiry, and re-authentication

### Data Layer: SQLite with Async Support

All persistence uses SQLite via `aiosqlite`:
- **Account/character CRUD** — web UI manages accounts, bot reads them
- **Character stats tracking** — periodic snapshots for progress monitoring
- **Opponent data** — arena opponent persistence for fight selection
- **Crawl state** — per-server HoF crawl progress (last page, completion timestamp)
- **Per-character config** — JSON files with target attribute ratios

### Hall of Fame Crawler

A separate background process crawls the Hall of Fame on every game server:
- Creates throwaway game accounts automatically via the registration API
- Scrapes player equipment data from all HoF pages
- Stores scrapbook item positions in SQLite for the main bot to use
- Runs on a 14-day cycle per server
- Handles account bans gracefully — creates new accounts as needed

### Web Dashboard

A Flask web application provides a management interface:
- **Account management** — add/remove S&F accounts, view characters
- **Character configuration** — set target attribute ratios per character (5 attributes × equipment/gems × main + companions)
- **Enable/disable** — toggle characters on/off without restarting the bot
- **Stats monitoring** — view character progression over time
- **Log viewing** — read per-character log files from the browser
- **Authentication** — simple username/password login for the web UI

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.13+ |
| Async runtime | asyncio + aiohttp |
| Web framework | Flask |
| Database | SQLite (aiosqlite) |
| Package manager | uv |
| Deployment | Docker + Docker Compose |
| Testing | pytest + pytest-asyncio |
| Reference impl | Rust (protocol reference), JavaScript (sf-tools simulation port) |

## Codebase Stats

| Metric | Value |
|---|---|
| Total Python files | 250+ |
| Lines of code | ~32,000 |
| Domain packages | 28 |
| Automated tasks | 53 |
| Test files | 46 |
| Character class models | 9 |
| Inventory disposal stages | 16 |
| Simulation iterations per dungeon | 10,000 |

## Deployment

The entire system runs as three Docker containers from a single image:

```yaml
services:
  web:        # Flask dashboard (port 5001)
  sfgame_bot: # Main bot loop (all accounts)
  cron_crawl: # HoF crawler (all servers)
```

Data is persisted via bind-mounted volumes (`account_data/` for SQLite + configs, `logs/` for per-character logs). The system runs unattended on a server — no manual intervention needed after initial account setup.

---

## Key Engineering Decisions

**Why asyncio, not threads?** — Each account needs I/O-bound HTTP calls with 1-3s delays between them. Asyncio handles hundreds of concurrent accounts with minimal overhead. No shared mutable state, no locks.

**Why SQLite, not Postgres?** — The data model is simple (accounts, stats, crawl state). SQLite is zero-config, lives in a single file, and `aiosqlite` provides async access. No reason to add infrastructure complexity.

**Why a custom wire protocol parser?** — The game doesn't use JSON. Responses are delimiter-separated fields at fixed indices. Parsing is just string splitting + integer conversion — no serialization library needed.

**Why port sf-tools instead of calling it?** — The JavaScript simulator runs in a browser context. Porting to Python gives native integration, type safety, and the ability to run simulations inline during the task loop without subprocess overhead.

**Why 16 stages for inventory?** — Each stage represents a different value trade-off. Early stages sacrifice worthless items. Middle stages run scoring algorithms to rescue valuable gems before they're lost. Late stages are last-resort actions. This layered approach minimizes value loss from a full backpack.

**Why the T²/A formula?** — Simple "highest stat wins" comparisons don't account for what your build actually needs. The quadratic correction makes underrepresented attributes exponentially more valuable, naturally steering attribute distribution toward configured targets without manual priority tuning.

---

## What I Learned

- **Reverse engineering HTTP APIs** — intercepting game traffic, mapping field indices, handling auth flows
- **Monte Carlo simulation at scale** — balancing accuracy vs. performance (10K iterations per dungeon × many dungeons per cycle)
- **Domain-driven design in Python** — structuring a 32K LOC project with clear boundaries, dependency injection, and the Protocol pattern
- **Async error recovery** — building systems that handle every failure gracefully and never need manual restarts
- **Porting algorithms across languages** — translating a JavaScript combat simulator to idiomatic Python with type annotations and dataclasses
