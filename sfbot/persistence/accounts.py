import json
import sqlite3
from pathlib import Path

import aiosqlite

DB_PATH = str(
    Path(__file__).resolve().parent.parent.parent / "account_data" / "accounts.db"
)
CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "account_data"


def config_path(character_id: str) -> Path:
    return CONFIG_DIR / f"{character_id}.json"


def save_config_json(character_id: str, config: dict) -> Path:
    path = config_path(character_id)
    path.write_text(json.dumps(config, indent=4))
    return path


def load_config_json(character_id: str) -> dict | None:
    path = config_path(character_id)
    if path.exists():
        return json.loads(path.read_text())
    return None


_CREATE_ACCOUNTS = (
    "CREATE TABLE IF NOT EXISTS accounts ("
    "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "  username TEXT NOT NULL UNIQUE,"
    "  password_hash TEXT NOT NULL"
    ")"
)

_CREATE_CHARACTERS = (
    "CREATE TABLE IF NOT EXISTS characters ("
    "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "  account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,"
    "  name TEXT NOT NULL,"
    "  character_id TEXT NOT NULL,"
    "  server TEXT NOT NULL,"
    "  char_class TEXT,"
    "  enabled INTEGER NOT NULL DEFAULT 1,"
    "  running INTEGER NOT NULL DEFAULT 0,"
    "  UNIQUE(account_id, character_id, server)"
    ")"
)

_CREATE_CHARACTER_STATS = (
    "CREATE TABLE IF NOT EXISTS character_stats ("
    "  character_id TEXT NOT NULL PRIMARY KEY,"
    "  level INTEGER NOT NULL DEFAULT 0,"
    "  silver_total INTEGER NOT NULL DEFAULT 0,"
    "  mushrooms INTEGER NOT NULL DEFAULT 0,"
    "  lucky_coins INTEGER NOT NULL DEFAULT 0,"
    "  updated_at TEXT NOT NULL DEFAULT (datetime('now'))"
    ")"
)


def init_db() -> None:
    """Create tables if needed. Call once at startup."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(_CREATE_ACCOUNTS)
        conn.execute(_CREATE_CHARACTERS)
        conn.execute(_CREATE_CHARACTER_STATS)
        conn.commit()
    finally:
        conn.close()


def connect_sync() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


async def connect_async() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys=ON")
    return conn


# --------------- sync helpers (for Flask UI) ---------------


def upsert_account(conn: sqlite3.Connection, username: str, password_hash: str) -> int:
    """Insert or update account, return account id."""
    row = conn.execute(
        "SELECT id FROM accounts WHERE username = ?", (username,)
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE accounts SET password_hash = ? WHERE id = ?",
            (password_hash, row["id"]),
        )
        conn.commit()
        return row["id"]
    cursor = conn.execute(
        "INSERT INTO accounts (username, password_hash) VALUES (?, ?)",
        (username, password_hash),
    )
    conn.commit()
    return cursor.lastrowid  # type: ignore[return-value]


def upsert_character(
    conn: sqlite3.Connection,
    account_id: int,
    name: str,
    character_id: str,
    server: str,
    enabled: bool | None = None,
    char_class: str | None = None,
) -> int:
    """Insert or update a character, return character row id.

    When ``enabled`` is None (default), the update path preserves the
    existing value and the insert path defaults to disabled.
    """
    row = conn.execute(
        "SELECT id FROM characters WHERE account_id = ? AND character_id = ? AND server = ?",
        (account_id, character_id, server),
    ).fetchone()
    if row:
        if enabled is not None:
            conn.execute(
                "UPDATE characters SET name = ?, enabled = ?, char_class = COALESCE(?, char_class) WHERE id = ?",
                (name, int(enabled), char_class, row["id"]),
            )
        else:
            conn.execute(
                "UPDATE characters SET name = ?, char_class = COALESCE(?, char_class) WHERE id = ?",
                (name, char_class, row["id"]),
            )
        conn.commit()
        return row["id"]
    cursor = conn.execute(
        "INSERT INTO characters (account_id, name, character_id, server, enabled, char_class) VALUES (?, ?, ?, ?, ?, ?)",
        (account_id, name, character_id, server, int(enabled or False), char_class),
    )
    conn.commit()
    return cursor.lastrowid  # type: ignore[return-value]


def set_character_enabled(
    conn: sqlite3.Connection, char_row_id: int, enabled: bool
) -> None:
    conn.execute(
        "UPDATE characters SET enabled = ? WHERE id = ?",
        (int(enabled), char_row_id),
    )
    conn.commit()


def set_character_running(
    conn: sqlite3.Connection, char_row_id: int, running: bool
) -> None:
    conn.execute(
        "UPDATE characters SET running = ? WHERE id = ?",
        (int(running), char_row_id),
    )
    conn.commit()


def get_characters_for_account(
    conn: sqlite3.Connection, account_id: int
) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM characters WHERE account_id = ? ORDER BY id",
        (account_id,),
    ).fetchall()


def get_all_enabled_characters(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT c.*, a.username, a.password_hash "
        "FROM characters c JOIN accounts a ON c.account_id = a.id "
        "WHERE c.enabled = 1 ORDER BY c.id"
    ).fetchall()


def get_all_accounts(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM accounts ORDER BY id").fetchall()


def get_all_characters(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT c.*, a.username, a.password_hash "
        "FROM characters c JOIN accounts a ON c.account_id = a.id "
        "ORDER BY c.id"
    ).fetchall()


def delete_character(conn: sqlite3.Connection, char_row_id: int) -> None:
    conn.execute("DELETE FROM characters WHERE id = ?", (char_row_id,))
    conn.commit()


def delete_account(conn: sqlite3.Connection, account_id: int) -> None:
    conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    conn.commit()


# --------------- async helpers (for main.py) ---------------


async def get_all_enabled_characters_async(
    conn: aiosqlite.Connection,
) -> list[aiosqlite.Row]:
    cursor = await conn.execute(
        "SELECT c.*, a.username, a.password_hash "
        "FROM characters c JOIN accounts a ON c.account_id = a.id "
        "WHERE c.enabled = 1 ORDER BY c.id"
    )
    return list(await cursor.fetchall())


async def is_character_running_async(
    conn: aiosqlite.Connection, character_id: str
) -> bool:
    cursor = await conn.execute(
        "SELECT running FROM characters WHERE character_id = ?",
        (character_id,),
    )
    row = await cursor.fetchone()
    return bool(row and row[0])


async def upsert_character_stats_async(
    conn: aiosqlite.Connection,
    character_id: str,
    level: int,
    silver_total: int,
    mushrooms: int,
    lucky_coins: int,
) -> None:
    await conn.execute(
        "INSERT INTO character_stats (character_id, level, silver_total, mushrooms, lucky_coins, updated_at) "
        "VALUES (?, ?, ?, ?, ?, datetime('now')) "
        "ON CONFLICT(character_id) DO UPDATE SET "
        "level = excluded.level, silver_total = excluded.silver_total, "
        "mushrooms = excluded.mushrooms, lucky_coins = excluded.lucky_coins, "
        "updated_at = excluded.updated_at",
        (character_id, level, silver_total, mushrooms, lucky_coins),
    )
    await conn.commit()


def get_stats_for_characters(
    conn: sqlite3.Connection, character_ids: list[str]
) -> dict[str, sqlite3.Row]:
    if not character_ids:
        return {}
    placeholders = ",".join("?" for _ in character_ids)
    rows = conn.execute(
        f"SELECT * FROM character_stats WHERE character_id IN ({placeholders})",
        character_ids,
    ).fetchall()
    return {r["character_id"]: r for r in rows}
