from pathlib import Path

import aiosqlite

DB_PATH = str(
    Path(__file__).resolve().parent.parent.parent / "account_data" / "opponents.db"
)

_CREATE_TABLE = (
    "CREATE TABLE IF NOT EXISTS arena_opponents ("
    "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "  account TEXT NOT NULL,"
    "  name TEXT NOT NULL"
    ")"
)


async def _connect() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(DB_PATH)
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute(_CREATE_TABLE)
    return conn


async def load_opponents(account: str) -> list[str]:
    conn = await _connect()
    try:
        cursor = await conn.execute(
            "SELECT name FROM arena_opponents WHERE account = ? ORDER BY id",
            (account,),
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
    finally:
        await conn.close()


async def remove_opponent(account: str, name: str) -> None:
    conn = await _connect()
    try:
        await conn.execute(
            "DELETE FROM arena_opponents WHERE id = ("
            "  SELECT id FROM arena_opponents"
            "  WHERE account = ? AND name = ? ORDER BY id LIMIT 1"
            ")",
            (account, name),
        )
        await conn.commit()
    finally:
        await conn.close()


async def clear_opponents(account: str) -> None:
    conn = await _connect()
    try:
        await conn.execute(
            "DELETE FROM arena_opponents WHERE account = ?",
            (account,),
        )
        await conn.commit()
    finally:
        await conn.close()


async def insert_opponents(account: str, names: list[str]) -> int:
    conn = await _connect()
    try:
        await conn.executemany(
            "INSERT INTO arena_opponents (account, name) VALUES (?, ?)",
            [(account, name) for name in names],
        )
        await conn.commit()
        return len(names)
    finally:
        await conn.close()
