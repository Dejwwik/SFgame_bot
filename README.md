# SFgame Bot

Async bot for automating [Shakes & Fidget](https://www.sfgame.net/) game accounts. Manages multiple characters concurrently using `asyncio` and `aiohttp`, running a continuous loop of 50+ daily tasks — quests, arena, dungeons, fortress, pets, guild, and more.

Includes a **Flask web UI** for account/character management and a **Hall of Fame crawler** for scrapbook data collection.

## Features

- **Multi-account support** — run any number of game accounts simultaneously as independent asyncio tasks
- **50+ automated tasks** — arena fights, quests, dungeons, fortress management, pet system, guild activities, item optimization, and more
- **Battle simulation engine** — ported from [sf-tools](https://github.com/HafisCZ/sf-tools), simulates 10,000+ fights to pick optimal dungeon targets
- **Smart item/gem scoring** — T²/A correction formula automatically prioritizes attributes your build is deficient in
- **16-stage inventory management** — progressive disposal chain when backpack is full (dismantle → sacrifice → sell → extract gems)
- **Class ability system** — polymorphic combat models for all 9 character classes (Assassin, Bard, Berserker, etc.)
- **Web dashboard** — Flask UI for adding accounts, configuring characters, and monitoring stats
- **HoF crawler** — background scrapbook data collection from every game server (14-day cycle)
- **Night mode** — automatic sleep between 2:00–8:00 to mimic human activity patterns
- **Per-character logging** — separate log files per account with domain-prefixed messages

## Requirements

- **Python** >= 3.13
- **[uv](https://docs.astral.sh/uv/)** — Python package manager and runner
- **Docker & Docker Compose** — for production deployment (optional for local dev)

## Quick Start (Local)

```bash
# 1. Clone the repository
git clone <repo-url> && cd SFgame

# 2. Install dependencies
uv sync

# 3. Set required environment variables
export WEB_USERNAME=admin
export WEB_PASSWORD=your_password
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# 4. Start the web UI (http://localhost:5001)
uv run web.py

# 5. In a separate terminal — start the bot
uv run main.py

# 6. (Optional) In a separate terminal — start the HoF crawler
uv run cron_crawl.py
```

## Setup Flow

1. Open the web UI at `http://localhost:5001` and log in
2. Click **Add Account** — enter your Shakes & Fidget username and password
3. The app fetches your characters via SSO — select which ones to manage
4. Click **Config** on each character to set target attribute ratios (strength/dexterity/intelligence/constitution/luck distributions for equipment, gems, and companions)
5. **Enable** characters — the bot picks them up automatically within 60 seconds

## Docker Deployment (Production)

### 1. Create `.env` file

```bash
# Create .env with your credentials
cat > .env << EOF
WEB_USERNAME=admin
WEB_PASSWORD=your_secure_password
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
EOF
```

### 2. Build and run

```bash
docker compose up -d --build
```

This starts three containers from a single image:

| Service | Container | Port | Description |
|---|---|---|---|
| `web` | `sfgame_web` | 5001 | Flask web UI — account management dashboard |
| `sfgame_bot` | `sfgame_bot` | — | Main bot loop — runs all automated tasks |
| `cron_crawl` | `sfgame_crawl` | — | HoF crawler — scrapbook data every 14 days |

### Docker commands

```bash
docker compose logs -f              # Follow all service logs
docker compose logs -f sfgame_bot   # Follow bot logs only
docker compose restart sfgame_bot   # Restart the bot
docker compose down                 # Stop everything
docker compose up -d --build        # Rebuild after code changes
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `WEB_USERNAME` | **Yes** | Web UI login username (no default — app won't start without it) |
| `WEB_PASSWORD` | **Yes** | Web UI login password (no default — app won't start without it) |
| `SECRET_KEY` | No | Flask session secret (has dev fallback — **set in production**) |
| `TZ` | No | Timezone for log timestamps (default: `Europe/Prague` in Docker) |

## Project Structure

```
main.py              # Async multi-account task loop (production entry point)
web.py               # Flask web UI for account/character management
cron_crawl.py        # HoF crawler — scrapbook data collection per server
sfbot/               # Core bot library (~32,000 LOC, 250+ Python files)
├── bot.py           # Bot class — composes all subsystems
├── session.py       # HTTP session, SSO auth, request helpers
├── character.py     # Character attrs, potions, class/race
├── constants/       # All enums, indices, field offsets, delimiters
├── persistence/     # SQLite database layer (accounts, stats, opponents)
├── arena/           # Arena PvP fights
├── arena_manager/   # Arena manager buildings, runes, merchant
├── attributes/      # Base attribute upgrading
├── dice/            # Dice minigame
├── dungeon/         # Light/shadow dungeons, tower, twister, portal + battle sim
│   └── simulate/    # Full battle simulation engine (sf-tools port)
│       └── class_models/  # Polymorphic class abilities (9 classes)
├── expedition/      # Expedition system
├── fortress/        # Fortress buildings, resources, gem mine, units, attacks
├── gems/            # Gem data types and sacrifice logic
├── guard/           # City guard shifts
├── guild/           # Guild fights, portal, hydra, skill upgrades
├── inventory/       # Backpack mgmt, item/gem equipping, 16-stage free slot chain
├── items/           # Item parsing, T²/A comparison scoring
├── legendary_dungeon/  # Timed 100-floor dungeon event
├── mount/           # Mount management
├── pets/            # Pet system (habitats, feeding, PvP, pet dungeons)
├── potions/         # Potion management and elixirs
├── reward/          # Calendar, daily tasks, events, mail rewards
├── scrapbook/       # Scrapbook tracking and HoF crawling
├── shop/            # Weapon/magic shop purchasing
├── smith/           # Blacksmith (dismantle, gem extraction, upgrades)
├── tavern/          # Quest management + beer
├── toilet/          # Arcane toilet (flush + gem sacrifice)
├── underworld/      # Underworld buildings, resources, luring, fighters
├── wheel/           # Wheel of Fortune
├── witch/           # Witch enchantments
└── world_boss/      # World boss fights
templates/           # Flask HTML templates (8 pages)
account_data/        # SQLite DB + per-character config JSON (bind-mounted)
logs/                # Per-character log files (bind-mounted)
rust_reference/      # Rust SF client — used as protocol reference
```

## Data Storage

All persistent data lives in `account_data/`:

| File | Description |
|---|---|
| `accounts.db` | SQLite database — accounts, characters, stats, crawl progress, opponents |
| `{character_id}.json` | Per-character configuration — target attribute ratios for equipment, gems, companions |

In Docker, `account_data/` and `logs/` are bind-mounted volumes shared across all three services.

## Task Execution Order

Each bot loop iteration runs ~50 tasks sequentially, then sleeps 180s (+ random jitter):

1. **Collect & claim** — quests, wheel, toilet flush, special shop items, fortress gems, calendar
2. **Optimize gear** — equip best items, equip best gems
3. **Process inventory** — extract gems, dismantle, buy better items, toilet sacrifice, enchantments, upgrade items
4. **Combat** — dungeons (simulated), guard, guild fights/portal/upgrades
5. **Fortress** — collect resources, upgrade buildings, upgrade units, attack, train soldiers/defence
6. **Underworld** — collect, thirst, buildings, lure, fighters
7. **Arena manager** — sacrifice runes, upgrade buildings, buy bonuses
8. **Character** — elixirs, potions, mount, attributes, start quest, arena fights
9. **Exploration** — scrapbook, opponent fights, dice, portal, pets, legendary dungeon, world boss
10. **Wrap up** — start guard, daily/event/mail rewards

## Error Handling

| Error | Behavior |
|---|---|
| `LoginError` | Warning log (no traceback), retry after 60s |
| `KnownAPIError` | Error log, retry after 60s |
| `InventoryFullError` | Warning log, restart task loop immediately |
| `GemExtractedAlert` | Info log, restart loop to re-equip |
| Unhandled exception | Full traceback logged, retry after 60s |

The bot **never crashes permanently** — all errors trigger a retry loop.

## Running Tests

```bash
uv run pytest
```

Tests cover battle simulation, inventory management, fortress logic, item comparison, pet requirements, and more.

## Development

```bash
# Run locally with caffeinate (macOS — prevents sleep)
just start

# Clear logs and restart
just clear

# Docker rebuild
just docker-restart
```
