"""Persistence for crawled player scrapbook positions (per server)."""

import json
import time
from pathlib import Path

import aiosqlite

DB_PATH = str(
    Path(__file__).resolve().parent.parent.parent / "account_data" / "opponents.db"
)


_CREATE_TABLE = (
    "CREATE TABLE IF NOT EXISTS scrapbook_players ("
    "  server TEXT NOT NULL,"
    "  name TEXT NOT NULL,"
    "  level INTEGER NOT NULL,"
    "  positions TEXT NOT NULL,"
    "  PRIMARY KEY (server, name)"
    ")"
)

_CREATE_CRAWL_ACCOUNTS = (
    "CREATE TABLE IF NOT EXISTS crawl_accounts ("
    "  server TEXT PRIMARY KEY,"
    "  username TEXT NOT NULL,"
    "  pw_hash TEXT NOT NULL,"
    "  login_count INTEGER NOT NULL DEFAULT 0"
    ")"
)

_CREATE_CRAWL_STATUS = (
    "CREATE TABLE IF NOT EXISTS crawl_status ("
    "  server TEXT PRIMARY KEY,"
    "  finished INTEGER NOT NULL DEFAULT 0,"
    "  last_page INTEGER NOT NULL DEFAULT 0,"
    "  finished_at INTEGER NOT NULL DEFAULT 0"
    ")"
)

_MIGRATE_FINISHED_AT = (
    "ALTER TABLE crawl_status ADD COLUMN finished_at INTEGER NOT NULL DEFAULT 0"
)


async def _connect() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(DB_PATH, timeout=30)
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA busy_timeout=30000")
    await conn.execute(_CREATE_TABLE)
    await conn.execute(_CREATE_CRAWL_ACCOUNTS)
    await conn.execute(_CREATE_CRAWL_STATUS)
    try:
        await conn.execute(_MIGRATE_FINISHED_AT)
    except Exception:
        pass
    return conn


async def upsert_player(
    server: str, name: str, level: int, positions: set[int]
) -> None:
    conn = await _connect()
    try:
        await conn.execute(
            "INSERT INTO scrapbook_players (server, name, level, positions) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(server, name) DO UPDATE SET "
            "level = excluded.level, positions = excluded.positions",
            (server, name, level, json.dumps(list(positions))),
        )
        await conn.commit()
    finally:
        await conn.close()


async def upsert_players_batch(
    server: str,
    players: list[tuple[str, int, set[int]]],
) -> None:
    """Batch upsert multiple players. Each tuple: (name, level, positions)."""
    conn = await _connect()
    try:
        rows = [
            (server, name, level, json.dumps(list(positions)))
            for name, level, positions in players
        ]
        await conn.executemany(
            "INSERT INTO scrapbook_players (server, name, level, positions) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(server, name) DO UPDATE SET "
            "level = excluded.level, positions = excluded.positions",
            rows,
        )
        await conn.commit()
    finally:
        await conn.close()


async def reset_crawl_status(server: str) -> None:
    conn = await _connect()
    try:
        await conn.execute(
            "INSERT INTO crawl_status (server, finished, last_page) VALUES (?, 0, 0) "
            "ON CONFLICT(server) DO UPDATE SET finished = 0, last_page = 0",
            (server,),
        )
        await conn.commit()
    finally:
        await conn.close()


async def is_crawl_finished(server: str) -> bool:
    conn = await _connect()
    try:
        cursor = await conn.execute(
            "SELECT finished FROM crawl_status WHERE server = ?",
            (server,),
        )
        row = await cursor.fetchone()
        return bool(row and row[0])
    finally:
        await conn.close()


async def set_crawl_finished(server: str) -> None:
    now = int(time.time())
    conn = await _connect()
    try:
        await conn.execute(
            "INSERT INTO crawl_status (server, finished, finished_at) VALUES (?, 1, ?) "
            "ON CONFLICT(server) DO UPDATE SET finished = 1, finished_at = excluded.finished_at",
            (server, now),
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_finished_at(server: str) -> int:
    conn = await _connect()
    try:
        cursor = await conn.execute(
            "SELECT finished_at FROM crawl_status WHERE server = ?",
            (server,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0
    finally:
        await conn.close()


async def get_last_page(server: str) -> int:
    conn = await _connect()
    try:
        cursor = await conn.execute(
            "SELECT last_page FROM crawl_status WHERE server = ?",
            (server,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0
    finally:
        await conn.close()


async def set_last_page(server: str, page: int) -> None:
    conn = await _connect()
    try:
        await conn.execute(
            "INSERT INTO crawl_status (server, last_page) VALUES (?, ?) "
            "ON CONFLICT(server) DO UPDATE SET last_page = excluded.last_page",
            (server, page),
        )
        await conn.commit()
    finally:
        await conn.close()


async def load_players(server: str, max_level: int) -> list[tuple[str, int, set[int]]]:
    """Load all crawled players for a server up to max_level.

    Returns list of (name, level, positions).
    """
    conn = await _connect()
    try:
        cursor = await conn.execute(
            "SELECT name, level, positions FROM scrapbook_players "
            "WHERE server = ? AND level <= ? ORDER BY name",
            (server, max_level),
        )
        rows = await cursor.fetchall()
        return [(row[0], row[1], set(json.loads(row[2]))) for row in rows]
    finally:
        await conn.close()


async def get_crawl_account(server: str) -> tuple[str, str, int] | None:
    """Get stored crawl account for a server. Returns (username, pw_hash, login_count) or None."""
    conn = await _connect()
    try:
        cursor = await conn.execute(
            "SELECT username, pw_hash, login_count FROM crawl_accounts WHERE server = ?",
            (server,),
        )
        row = await cursor.fetchone()
        return (row[0], row[1], row[2]) if row else None
    finally:
        await conn.close()


async def save_crawl_account(
    server: str, username: str, pw_hash: str, login_count: int = 0
) -> None:
    """Store crawl account credentials for a server."""
    conn = await _connect()
    try:
        await conn.execute(
            "INSERT INTO crawl_accounts (server, username, pw_hash, login_count) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(server) DO UPDATE SET "
            "username = excluded.username, pw_hash = excluded.pw_hash, "
            "login_count = excluded.login_count",
            (server, username, pw_hash, login_count),
        )
        await conn.commit()
    finally:
        await conn.close()
