# SFgame Bot

Async bot for automating [Shakes & Fidget](https://www.sfgame.net/) game accounts. Manages multiple characters concurrently, running a loop of daily tasks (quests, arena, dungeons, fortress, pets, guild, and more).

Includes a **Flask web UI** for managing accounts and characters, and a **HoF crawler** for scrapbook data collection.

## Requirements

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/) package manager
- Docker & Docker Compose (for deployment)

## Quick Start (Local)

```bash
# Install dependencies
uv sync

# Set required env vars for the web UI
export WEB_USERNAME=admin
export WEB_PASSWORD=your_password
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Start the web UI
uv run web.py

# In a separate terminal: start the bot
uv run main.py

# In a separate terminal: start the HoF crawler
uv run cron_crawl.py
```

The web UI runs at `http://localhost:5001`.

## Docker Deployment

### 1. Create `.env` file

```bash
cp .env.example .env
# Edit .env and set your credentials
```

### 2. Build and run

```bash
docker compose up -d --build
```

This starts three services:

| Service | Container | Description |
|---|---|---|
| `web` | `sfgame_web` | Flask web UI (port 5001) |
| `sfgame_bot` | `sfgame_bot` | Main bot loop |
| `cron_crawl` | `sfgame_crawl` | HoF crawler (every 14 days per server) |

### Useful commands

```bash
docker compose logs -f              # Follow all logs
docker compose logs -f sfgame_bot   # Follow bot logs only
docker compose restart sfgame_bot   # Restart bot
docker compose down                 # Stop everything
docker compose up -d --build        # Rebuild after changes
```

## Setup Flow

1. Start the web UI and log in with your `WEB_USERNAME`/`WEB_PASSWORD`
2. Click **Add Account** and enter your Shakes & Fidget credentials
3. Select which characters to manage
4. Configure target attribute ratios for each character via the **Config** button
5. Enable characters and they will be picked up by the bot automatically

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `WEB_USERNAME` | **Yes** | Web UI login username |
| `WEB_PASSWORD` | **Yes** | Web UI login password |
| `SECRET_KEY` | No | Flask session secret (defaults to a dev fallback — set in production) |
| `TZ` | No | Timezone for log timestamps (default: `Europe/Prague` in Docker) |

## Project Structure

```
main.py          # Async multi-account task loop
web.py           # Flask web UI for account management
cron_crawl.py    # HoF crawler (scrapbook data collection)
sfbot/           # Core bot library
├── bot.py       # Bot class — ties all subsystems together
├── session.py   # HTTP session, SSO auth
├── character.py # Character attributes, class, race
├── constants/   # Enums, indices, field offsets
├── persistence/ # SQLite DB (accounts, characters, stats)
├── arena/       # Arena fights
├── dungeon/     # Light/shadow dungeons, tower, twister, portal
├── fortress/    # Fortress buildings, resources, gem mine, units
├── guild/       # Guild fights, portal, hydra
├── inventory/   # Backpack management, item/gem equipping
├── items/       # Item parsing, T²/A comparison scoring
├── pets/        # Pet system (habitats, feeding, PvP, dungeons)
├── legendary_dungeon/  # Timed 100-floor dungeon event
├── scrapbook/   # Scrapbook tracking and HoF crawling
├── ...          # + tavern, guard, dice, wheel, toilet, etc.
└── tests/       # Unit tests
templates/       # Flask HTML templates
account_data/    # SQLite DB + per-character config JSON (bind-mounted)
logs/            # Per-character log files (bind-mounted)
```

## Data Storage

All persistent data lives in `account_data/`:
- `accounts.db` — SQLite database (accounts, characters, stats, crawl data)
- `{character_id}.json` — Per-character configuration (target ratios)

In Docker, `account_data/` and `logs/` are bind-mounted volumes shared across all services.

## Running Tests

```bash
uv run pytest
```
