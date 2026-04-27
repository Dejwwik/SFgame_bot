"""Persistence for scrapbook crawl timestamps."""

from pathlib import Path

import aiosqlite

DB_PATH = str(
    Path(__file__).resolve().parent.parent.parent / "account_data" / "opponents.db"
)

_CREATE_TABLE = (
    "CREATE TABLE IF NOT EXISTS scrapbook_crawl ("
    "  account TEXT PRIMARY KEY,"
    "  last_crawl_ts INTEGER NOT NULL DEFAULT 0"
    ")"
)


async def _connect() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(DB_PATH)
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute(_CREATE_TABLE)
    return conn


async def get_last_crawl_ts(account: str) -> int:
    conn = await _connect()
    try:
        cursor = await conn.execute(
            "SELECT last_crawl_ts FROM scrapbook_crawl WHERE account = ?",
            (account,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0
    finally:
        await conn.close()


async def set_last_crawl_ts(account: str, ts: int) -> None:
    conn = await _connect()
    try:
        await conn.execute(
            "INSERT INTO scrapbook_crawl (account, last_crawl_ts) "
            "VALUES (?, ?) "
            "ON CONFLICT(account) DO UPDATE SET last_crawl_ts = excluded.last_crawl_ts",
            (account, ts),
        )
        await conn.commit()
    finally:
        await conn.close()
