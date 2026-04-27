# Scrapbook Opponent Queue System

## Overview

The scrapbook system identifies arena opponents whose equipment contains items missing from the character's scrapbook collection. It works in three stages:

1. **`cron_crawl.py`** — daily cron job that crawls every server's Hall of Fame and stores player equipment data in SQLite
2. **`update_queue` task** — runs every 10h inside the main bot loop, scores crawled players against the character's scrapbook, and populates an ordered opponent queue
3. **`fight_opponent` task** — runs each bot loop iteration, consumes one opponent from the queue and fights them in arena

```
┌──────────────┐     ┌───────────────────┐     ┌──────────────────┐
│  cron_crawl  │────▶│  scrapbook_players │────▶│   update_queue   │
│  (daily)     │     │  (SQLite table)    │     │   (every 10h)    │
└──────────────┘     └───────────────────┘     └────────┬─────────┘
                                                        │
                                                        ▼
                                               ┌──────────────────┐
                                               │  arena_opponents  │
                                               │  (SQLite table)   │
                                               └────────┬─────────┘
                                                        │
                                                        ▼
                                               ┌──────────────────┐
                                               │  fight_opponent   │
                                               │  (each loop)      │
                                               └──────────────────┘
```

---

## Database Schema

All tables in `config/opponents.db` (SQLite, WAL journal mode).

### `scrapbook_players`
Populated by `cron_crawl.py`. Cleared and re-filled on each daily run per server.

| Column | Type | Description |
|---|---|---|
| `server` | `TEXT NOT NULL` | Server URL (e.g. `s1.sfgame.net`) |
| `name` | `TEXT NOT NULL` | Player name |
| `level` | `INTEGER NOT NULL` | Player level |
| `positions` | `TEXT NOT NULL` | JSON array of sorted scrapbook bit positions |
| **PK** | `(server, name)` | Composite primary key |

### `crawl_accounts`
One throwaway non-SSO account per server, created on first run.

| Column | Type | Description |
|---|---|---|
| `server` | `TEXT PRIMARY KEY` | One account per server |
| `username` | `TEXT NOT NULL` | Auto-generated username (e.g. `DarkSlayer742`) |
| `pw_hash` | `TEXT NOT NULL` | `SHA1(plain_password + HASH_SALT)` |
| `login_count` | `INTEGER NOT NULL DEFAULT 0` | Legacy column |

### `scrapbook_crawl`
Tracks when each bot character last refreshed its opponent queue.

| Column | Type | Description |
|---|---|---|
| `account` | `TEXT PRIMARY KEY` | `bot.session.character_id` |
| `last_crawl_ts` | `INTEGER NOT NULL DEFAULT 0` | Unix timestamp of last queue refresh |

### `arena_opponents`
Ordered queue of opponents to fight, consumed FIFO.

| Column | Type | Description |
|---|---|---|
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | FIFO ordering key |
| `account` | `TEXT NOT NULL` | Character ID that owns this queue |
| `name` | `TEXT NOT NULL` | Opponent player name |

---

## Stage 1: `cron_crawl.py` (Daily Crawl)

Runs as a separate Docker service (`cron_crawl`), once every 24 hours. All servers are crawled concurrently via `asyncio.gather()`.

### Per-Server Flow

1. **`ensure_account()`**: Checks `crawl_accounts` for an existing account. If none, registers a new throwaway account (up to 3 attempts with random usernames/passwords).

2. **`session.login()`**: Logs in via non-SSO `AccountLogin`.

3. **`clear_server(server)`**: Deletes all existing `scrapbook_players` rows for this server (full refresh each run).

4. **HoF walk loop**:
   - Starts at position 26 (center of ranks 1–51, since PLAYERS_ABOVE=25).
   - Calls `PlayerGetHallOfFame` → gets up to 51 players per page.
   - For each player with `level >= 2`:
     - Calls `PlayerLookAt` → gets `otherplayersaveequipment`.
     - Parses equipment into item idents via `parse_equipment_idents()`.
     - Converts each ident to a scrapbook bit position via `get_scrapbook_position()`.
     - Collects `(name, level, positions)` into a batch.
   - Every 200 players, flushes batch to DB via `upsert_players_batch()`.
   - Advances position by 51 (PLAYERS_PER_PAGE) each page.
   - Stops when player levels drop below `MIN_PLAYER_LEVEL` or no more players.

5. Final batch flush, session close.

### Authentication (Non-SSO)

**Registration:**
```
pw_hash = SHA1(plain_password + HASH_SALT)
params = "{username}/{plain_password}/{email}/2/1/1/{portrait}/0//en"
→ AccountCreate → success if tracking.s == "signup"
```

**Login:**
```
login_hash = SHA1(pw_hash + "1")   # login_count is always "1"
params = "{username}/{login_hash}/1/unity3d_webglplayer//295000000000///0/"
→ AccountLogin → extracts cryptoid, sessionid, pg_player
```

**Usernames:** Random combo from `NAME_PREFIXES × NAME_SUFFIXES + random(1-999)` (e.g. `IronHunter451`, `NightBane88`).

**Passwords:** 14 chars: 6 lowercase + 3 uppercase + 3 digits + 2 special (`!@#$%`), shuffled. Meets server security requirements.

### Request Timing
- `REQUEST_DELAY = 0.05s` + random `0–0.1s` jitter between `PlayerLookAt` calls.
- All params are base64-encoded before sending.

---

## Stage 2: `update_queue` Task (Every 10h)

Runs inside `main.py`'s bot loop, after daily arena XP fights.

### `should_run(bot) → bool`
1. `bot.scrapbook.owned_positions` must be non-empty (scrapbook parsed).
2. `count_players_sync(server) > 0` — DB has crawled data for this server.
3. `server_time() - last_crawl_ts >= QUEUE_REFRESH_INTERVAL (36,000s = 10h)`.

### `run(bot)`
1. Calls `scrapbook.rank_from_db_async(bot.character.level)`.
2. If no targets: updates timestamp, returns.
3. Clears existing `arena_opponents` for this account.
4. Inserts new ranked opponent names (FIFO order).
5. Updates `last_crawl_ts`.

### Scoring: `rank_from_db_async(max_level)`
1. **Polls** fresh scrapbook from server (`PlayerPollScrapbook`).
2. **Loads** all crawled players for this server where `level <= max_level`.
3. **Scores** each player: `missing = len(player.positions - owned_positions)` — how many scrapbook items this player has that we don't.
4. **Filters** out players with `missing == 0` and own player name.
5. **Sorts** by `(-missing, level)` — most missing items first, then lowest level (easier to beat).
6. **Truncates** to `MAX_QUEUE_SIZE (50)`.

---

## Stage 3: `fight_opponent` Task (Each Loop)

Runs every bot loop iteration (~180s), after `update_queue`.

### `should_run(bot) → bool`
- `bot.arena.is_free` (no cooldown) **AND** `bot.arena.is_completed` (daily 10 XP fights done).

### `run(bot)`
1. Loads opponents from `arena_opponents` (ordered by `id` ASC = insertion order).
2. Takes first opponent (FIFO).
3. Fights via `bot.arena.fight_async(name)`.
4. Removes that opponent from DB regardless of win/loss.
5. On API error: logs warning, removes opponent, continues.

---

## Scrapbook Position Calculation

The scrapbook bitfield has **2396 total positions**: 1–800 = monsters, 801+ = items.

### Equipment Ident Parsing
From `otherplayersaveequipment` (10 equipment slots × 19 fields, `/`-delimited):
- `item_type` = field 0, masked to byte (1–10)
- `model_info` = field 3, masked to u16
- `class_id = model_info // 1000`, `model_id = model_info % 1000`
- `sf_class = class_id + 1` (1=Warrior, 2=Mage, 3=Scout)
- `color_class = 0` for accessories (type ≥ 8), else `sf_class`
- Items with `model_id >= 90` (legendary) are excluded

### Position Lookup
Uses `SCRAPBOOK_BOUNDARIES[color_class][type_key]` → `[normal_start, epic_start]`:
- **Epic** (`model_id >= 50`): `position = epic_start + (model_id - 50) + 1`
- **Talisman** (`type == 10`): `position = normal_start + (model_id - 1) + 1`
- **Normal**: `position = normal_start + (model_id - 1) * 5 + color + 1`

Color is derived from a checksum of item stats: `(damage_max + damage_min + attr_types_sum + attr_values_sum) % 5`.

---

## Constants

| Constant | Value | Location | Purpose |
|---|---|---|---|
| `SCRAPBOOK_COUNT` | 2396 | constants.py | Total scrapbook positions |
| `MONSTER_POSITIONS` | 800 | constants.py | Positions 1–800 |
| `ITEM_POSITIONS` | 1596 | constants.py | Positions 801–2396 |
| `MAX_MODEL_ID` | 90 | constants.py | Legendary cutoff |
| `QUEUE_REFRESH_INTERVAL` | 36,000 | constants.py | 10h between re-scores |
| `MAX_QUEUE_SIZE` | 50 | constants.py | Max queued opponents |
| `PLAYERS_PER_PAGE` | 51 | constants.py | HoF page size |
| `PLAYERS_ABOVE` | 25 | constants.py | HoF window above center |
| `PLAYERS_BELOW` | 25 | constants.py | HoF window below center |
| `HOF_START_POSITION` | 26 | constants.py | First page center rank |
| `MIN_PLAYER_LEVEL` | 2 | constants.py | Skip inactive accounts |
| `HOF_START` | 26 | cron_crawl.py | First page center |
| `BATCH_SIZE` | 200 | cron_crawl.py | DB batch flush size |
| `REQUEST_DELAY` | 0.05 | cron_crawl.py | Base delay between requests |

---

## `main.py` Task Order (Relevant Section)

```
... → arena_task → scrapbook_task → fight_opponent_task → dice_task → ...
```

- `arena_task`: Daily 10 XP arena fights
- `scrapbook_task` (`update_queue`): Re-scores and queues opponents every 10h
- `fight_opponent_task`: Consumes one queued opponent per loop (only after daily arena is done)
