"""Cron script: crawl full HoF per server, store player equipment in DB.

Run once a day per server. Creates throwaway non-SSO accounts (one per server)
and uses them to crawl the full HoF.
Stores scrapbook positions so the main bot can score locally without API calls.

Usage: uv run cron_crawl.py
"""

import asyncio
import base64
import hashlib
import os
import random
import string
import sys
import time

import aiohttp

sys.path.insert(0, os.path.dirname(__file__))

from sfbot.exceptions import APIError, LoginError, RateLimitError
from sfbot.logging import CrawlLogContext, get_crawl_logger, get_crawl_main_logger
from sfbot.persistence.accounts import connect_async as connect_accounts_async
from sfbot.persistence.accounts import init_db
from sfbot.scrapbook.constants import (
    MIN_PLAYER_LEVEL,
    PLAYERS_ABOVE,
    PLAYERS_BELOW,
    PLAYERS_PER_PAGE,
)
from sfbot.scrapbook.crawl_persistence import (
    get_crawl_account,
    get_finished_at,
    get_last_page,
    is_crawl_finished,
    reset_crawl_status,
    save_crawl_account,
    set_crawl_finished,
    set_last_page,
    upsert_players_batch,
)
from sfbot.scrapbook.scrapbook import (
    HofPlayer,
    get_scrapbook_position,
    parse_equipment_idents,
    parse_hof_players,
)
from sfbot.session import (
    COMMON_HEADERS,
    HASH_SALT,
    GameSession,
    check_response_for_error,
    parse_response,
)

HOF_START = 26
BATCH_SIZE = 200
DEFAULT_PORTRAIT = "8,203,201,6,199,3,1,2,1"
REQUEST_DELAY = 0.19
CRAWL_INTERVAL = 86_400 * 14  # 14 days
LOGIN_RETRY_DELAY = 300  # 5 minutes between login retries

logger = get_crawl_main_logger()

NAME_PREFIXES = [
    "Dark",
    "Shadow",
    "Iron",
    "Storm",
    "Fire",
    "Ice",
    "Red",
    "Blue",
    "Night",
    "Star",
    "Wolf",
    "Bear",
    "Hawk",
    "Lion",
    "Rune",
    "Blade",
]
NAME_SUFFIXES = [
    "Knight",
    "Hunter",
    "Slayer",
    "Mage",
    "Lord",
    "King",
    "Fury",
    "Fist",
    "Storm",
    "Soul",
    "Bane",
    "Rage",
    "Eye",
    "Fang",
    "Wind",
    "Blade",
]


def sha1(val: str) -> str:
    return hashlib.sha1(val.encode()).hexdigest()


def random_username() -> str:
    prefix = random.choice(NAME_PREFIXES)
    suffix = random.choice(NAME_SUFFIXES)
    num = random.randint(1, 999)
    return f"{prefix}{suffix}{num}"


def random_password() -> str:
    letters = random.choices(string.ascii_lowercase, k=6)
    uppers = random.choices(string.ascii_uppercase, k=3)
    digits = random.choices(string.digits, k=3)
    specials = random.choices("!@#$%", k=2)
    chars = letters + uppers + digits + specials
    random.shuffle(chars)
    return "".join(chars)


async def unique_servers() -> list[str]:
    conn = await connect_accounts_async()
    try:
        cursor = await conn.execute(
            "SELECT DISTINCT server FROM characters WHERE enabled = 1"
        )
        rows = await cursor.fetchall()
        return sorted(r[0] for r in rows)
    finally:
        await conn.close()


async def register_account(server: str) -> tuple[str, str] | None:
    """Create a throwaway account on a server. Returns (username, pw_hash) or None."""
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as client:
        for _ in range(3):
            username = random_username()
            password = random_password()
            pw_hash = sha1(password + HASH_SALT)
            params = f"{username}/{password}/{username}@playa.sso/2/1/1/{DEFAULT_PORTRAIT}/0//en"
            encoded = base64.b64encode(params.encode()).decode()
            async with client.get(
                f"https://{server}/cmd.php",
                params={
                    "req": "AccountCreate",
                    "params": encoded,
                    "sid": "0-00000000000000",
                },
                headers={
                    **COMMON_HEADERS,
                    "pg-player": "0",
                    "pg-session": "00000000000000000000000000000000",
                },
            ) as resp:
                text = await resp.text()
            result = parse_response(text)
            if result.get("tracking.s") == "signup":
                return username, pw_hash
    return None


class CrawlSession(GameSession):
    """Non-SSO game session for throwaway crawl accounts."""

    def __init__(self, server: str, username: str, pw_hash: str) -> None:
        self.server = server
        self.username = username
        self.pw_hash = pw_hash
        self.sid: str | None = None
        self.pg_player: str | None = None
        self.pg_session: str | None = None
        self.player_name: str = ""
        self.login_data: dict[str, str] = {}
        self.server_time_diff: int = 0
        self._client = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))

    async def login_async(self) -> "CrawlSession":
        login_hash = sha1(self.pw_hash + "1")
        params = (
            f"{self.username}/{login_hash}/1/unity3d_webglplayer//295000000000///0/"
        )
        encoded = base64.b64encode(params.encode()).decode()
        async with self._client.get(
            f"https://{self.server}/cmd.php",
            params={
                "req": "AccountLogin",
                "params": encoded,
                "sid": "0-00000000000000",
            },
            headers={
                **COMMON_HEADERS,
                "pg-player": "0",
                "pg-session": "00000000000000000000000000000000",
            },
        ) as resp:
            text = await resp.text()

        data = parse_response(text)
        if "error" in data or "ownplayersave.playerSave" not in data:
            raise LoginError(f"Crawl login failed: {data.get('error', 'unknown')}")

        self.login_data = data
        self.sid = data["cryptoid"]
        self.pg_session = data["sessionid"]
        self.player_name = data.get("ownplayername.r", self.username)
        self.pg_player = data["ownplayersave.playerSave"].split("/")[1]
        return self


async def ensure_account(server: str) -> CrawlSession:
    """Get or create a crawl account, login, and return a live session. Retries forever."""
    force_new = False
    failed_counter = 0
    while True:
        creds: tuple[str, str] | None = None
        if not force_new:
            stored = await get_crawl_account(server)
            if stored:
                creds = stored[0], stored[1]
        if creds is None:
            creds = await register_account(server)
            if creds:
                await save_crawl_account(server, creds[0], creds[1])
        if creds is None:
            logger.warning(
                f"Crawl: {server} account creation failed, "
                f"retrying in {LOGIN_RETRY_DELAY}s"
            )
            await asyncio.sleep(LOGIN_RETRY_DELAY)
            continue

        session = CrawlSession(server, creds[0], creds[1])
        try:
            await session.login_async()
            return session
        except Exception as e:
            logger.warning(f"Crawl: {server} login failed: {e}")
            await session.close()
            failed_counter += 1
            if failed_counter % 5 == 0:
                force_new = True
                logger.warning(
                    f"Crawl: {server} login failed 5 times, "
                    f"forcing new account creation"
                )
            else:
                force_new = False

            await asyncio.sleep(LOGIN_RETRY_DELAY)


class ServerCrawler:
    """Crawls one server's HoF and stores player equipment positions."""

    def __init__(self, server: str, session: CrawlSession) -> None:
        CrawlLogContext.set(server)
        self.server = server
        self.session = session
        self.slog = get_crawl_logger()
        self.batch: list[tuple[str, int, set[int]]] = []
        self.total_stored = 0
        self.total_looked_up = 0
        self.hof_position = HOF_START

    async def request(self, req: str, params: str = "") -> dict[str, str]:
        text = await self.session.request_async(req, params)
        result = parse_response(text)
        check_response_for_error(result)
        return result

    async def run(self) -> None:
        logger.info(f"Crawl: {self.server} starting as {self.session.player_name}")
        self.slog.info(f"Crawl: starting as {self.session.player_name}")
        start_time = time.monotonic()

        finished = await is_crawl_finished(self.server)
        if finished:
            await reset_crawl_status(self.server)
            self.slog.info("Crawl: previous crawl finished, starting fresh")
        else:
            last_page = await get_last_page(self.server)
            if last_page > 0:
                self.hof_position = last_page
                self.slog.info(f"Crawl: resuming from page {last_page}")

        try:
            await self.crawl_all()
            await set_crawl_finished(self.server)
        finally:
            if self.batch:
                await upsert_players_batch(self.server, self.batch)
                self.batch.clear()
            await set_last_page(self.server, self.hof_position)
            await self.session.close()

        elapsed = time.monotonic() - start_time
        msg = (
            f"Crawl: done — {self.total_stored} stored, "
            f"{self.total_looked_up} looked up, "
            f"last page {self.hof_position} in {elapsed:.0f}s"
        )
        logger.info(f"Crawl: {self.server} {msg[7:]}")
        self.slog.info(msg)

    async def sleep_rate_limit(self, context: str) -> None:
        now = int(time.time())
        timeout = 60 - (now % 60) + 1
        await asyncio.sleep(timeout)

    async def lookup_player(self, name: str) -> dict[str, str] | None:
        while True:
            await asyncio.sleep(REQUEST_DELAY)
            try:
                return await self.request("PlayerLookAt", name)
            except RateLimitError:
                await self.sleep_rate_limit(f"PlayerLookAt {name}")
            except APIError as e:
                self.slog.warning(f"Crawl: PlayerLookAt {name} failed: {e}")
                return None
            except Exception as e:
                self.slog.warning(f"Crawl: PlayerLookAt {name} network error: {e}")
                await asyncio.sleep(5)
                return None

    async def crawl_all(self) -> None:
        """Fetch HoF pages and process each player sequentially."""
        while True:
            await asyncio.sleep(REQUEST_DELAY)
            try:
                result = await self.request(
                    "PlayerGetHallOfFame",
                    f"{self.hof_position}//{PLAYERS_ABOVE}/{PLAYERS_BELOW}",
                )
            except RateLimitError:
                await self.sleep_rate_limit(f"HoF page {self.hof_position}")
                continue
            except APIError as e:
                self.slog.warning(
                    f"Crawl: HoF page {self.hof_position} failed: {e}, relogging"
                )
                try:
                    await self.session.relogin_async()
                    self.slog.info("Crawl: relogin successful")
                except Exception as ex:
                    self.slog.warning(f"Crawl: relogin failed: {ex}")
                continue
            except Exception as e:
                self.slog.warning(
                    f"Crawl: HoF page {self.hof_position} network error: {e}"
                )
                await asyncio.sleep(5)
                continue

            players = parse_hof_players(result.get("Ranklistplayer.r", ""))
            if not players:
                self.slog.warning(
                    f"Crawl: HoF page {self.hof_position} returned no players, relogging"
                )
                try:
                    await self.session.relogin_async()
                    self.slog.info("Crawl: relogin successful")
                except Exception as ex:
                    self.slog.warning(f"Crawl: relogin failed: {ex}")
                await asyncio.sleep(5)
                continue

            self.slog.info(
                f"Crawl: page {self.hof_position} — "
                f"{len(players)} players (lv {players[0].level}–{players[-1].level})"
            )

            below = sum(1 for p in players if p.level < MIN_PLAYER_LEVEL)
            stop = below >= len(players) * 0.2

            for player in players:
                if player.level < MIN_PLAYER_LEVEL:
                    continue
                await self.process_player(player)

            if stop:
                self.slog.info(f"Crawl: reached min level at page {self.hof_position}")
                break

            self.hof_position += PLAYERS_PER_PAGE

    async def process_player(self, player: HofPlayer) -> None:
        equip_result = await self.lookup_player(player.name)
        if equip_result is None:
            return

        self.total_looked_up += 1
        equip_raw = equip_result.get("otherplayersaveequipment", "")
        if not equip_raw:
            # Session may have expired — relogin and retry once
            self.slog.warning(
                f"Crawl: player {player.name} has no equipment data, relogging"
            )
            try:
                await self.session.relogin_async()
            except Exception:
                return
            equip_result = await self.lookup_player(player.name)
            if equip_result is None:
                self.slog.warning(
                    f"Crawl: player {player.name} has no equipment data after relogin"
                )
                return
            equip_raw = equip_result.get("otherplayersaveequipment", "")
            if not equip_raw:
                self.slog.warning(
                    f"Crawl: player {player.name} has no equipment data after relogin"
                )
                return

        positions: set[int] = set()
        for ident in parse_equipment_idents(equip_raw):
            pos = get_scrapbook_position(ident)
            if pos is not None:
                positions.add(pos)

        if not positions:
            self.slog.info(f"Crawl: player {player.name} has no items.")
            return

        self.batch.append((player.name, player.level, positions))
        self.total_stored += 1
        if len(self.batch) >= BATCH_SIZE:
            await upsert_players_batch(self.server, self.batch)
            self.batch.clear()
            await set_last_page(self.server, self.hof_position)


async def run_server(server: str) -> None:
    """Independent task for one server — login with retries, crawl, sleep, repeat."""
    while True:
        # --- should-run check ---
        finished_at = await get_finished_at(server)
        if finished_at > 0:
            remaining = CRAWL_INTERVAL - (int(time.time()) - finished_at)
            if remaining > 0:
                logger.info(
                    f"Crawl: {server} last finished {(int(time.time()) - finished_at) // 3600}h ago, "
                    f"sleeping {remaining // 3600}h"
                )
                await asyncio.sleep(remaining)

        # --- ensure account + login ---
        session = await ensure_account(server)

        # --- crawl ---
        try:
            crawler = ServerCrawler(server, session)
            await crawler.run()
        except Exception as exc:
            logger.error(
                f"Crawl: {server} failed",
                exc_info=(type(exc), exc, exc.__traceback__),
            )


POLL_NEW_SERVERS_INTERVAL = 300


async def main() -> None:
    active_tasks: dict[str, asyncio.Task] = {}  # server -> task

    try:
        while True:
            servers = await unique_servers()
            if not servers:
                logger.info("Crawl: no active servers found, sleeping")
            for server in servers:
                if server in active_tasks and not active_tasks[server].done():
                    continue
                logger.info(f"Crawl: spawning task for {server}")
                active_tasks[server] = asyncio.create_task(run_server(server))

            await asyncio.sleep(POLL_NEW_SERVERS_INTERVAL)
    except asyncio.CancelledError:
        pass
    finally:
        for t in active_tasks.values():
            t.cancel()
        await asyncio.gather(*active_tasks.values(), return_exceptions=True)


if __name__ == "__main__":
    init_db()
    asyncio.run(main())
