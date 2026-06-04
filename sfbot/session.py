import asyncio
import base64
import hashlib
import time
from typing import Any

import aiohttp

from sfbot.constants import VALUES_DELIMITER
from sfbot.exceptions import APIError, KnownAPIError, LoginError, RateLimitError
from sfbot.logging import get_main_logger

SSO_URL = "https://sso.playa-games.com"
CLIENT_ID = "i43nwwnmfc5tced4jtuk4auuygqghud2yopx"
HASH_SALT = "ahHoj2woo1eeChiech6ohphoB7Aithoh"
SERVER_MAP_CACHE: dict[str, int] = {}


async def init_server_map_async() -> None:
    async with aiohttp.ClientSession() as client:
        global SERVER_MAP_CACHE
        SERVER_MAP_CACHE = await fetch_server_id_map_async(client)


def hash_password(password: str) -> str:
    """Hash a plain-text password the way the SF server expects for SSO login."""
    pw_hash = hashlib.sha1((password + HASH_SALT).encode()).hexdigest()
    return hashlib.sha1((pw_hash + "0").encode()).hexdigest()


COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8",
    "Origin": "https://sfgame.net",
    "Referer": "https://sfgame.net/",
    "Sec-Fetch-Site": "same-site",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Sec-Ch-Ua": '"Chromium";v="134", "Not-A.Brand";v="24", "Google Chrome";v="134"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Priority": "u=1, i",
}


def parse_response(text: str) -> dict[str, str]:
    """Parse the custom key:value&key:value response format."""
    parts: dict[str, str] = {}
    for part in text.split("&"):
        if ":" in part:
            k, v = part.split(":", 1)
            parts[k] = v
    return parts


def parse_response_multi(text: str) -> list[tuple[str, str]]:
    """Parse the response keeping ALL key-value pairs (including duplicates)."""
    pairs: list[tuple[str, str]] = []
    for part in text.split("&"):
        if ":" in part:
            k, v = part.split(":", 1)
            pairs.append((k, v))
    return pairs


ERROR_MAP: list[tuple[str, type[APIError]]] = [
    ("too many request", RateLimitError),
    ("cannot do this right now", RateLimitError),
]


def check_response_for_error(result: dict[str, str]) -> dict[str, str]:
    """Raise the most specific APIError subclass for known error strings."""
    if "error" in result:
        error = result["error"]
        error_lower = error.lower()
        for pattern, exc_cls in ERROR_MAP:
            if pattern in error_lower:
                raise exc_cls(error)
        raise APIError(error)
    return result


async def fetch_server_id_map_async(client: aiohttp.ClientSession) -> dict[str, int]:
    async with client.get("https://sfgame.net/config.json", timeout=aiohttp.ClientTimeout(total=10)) as resp:
        data: dict[str, Any] = await resp.json(content_type=None)
    result: dict[str, int] = {}
    for s in data.get("servers", []):
        sid = s.get("i")
        for key in ("md", "d"):
            domain = s.get(key, "")
            if domain and sid is not None:
                result[domain] = sid
                break
    return result


async def sso_list_characters_async(
    username: str, password_hash: str
) -> list[dict[str, Any]]:
    """SSO login and list all characters for an account (no server/character needed)."""
    async with aiohttp.ClientSession() as client:
        async with client.post(
            f"{SSO_URL}/json/login",
            params={"client_id": CLIENT_ID, "auth_type": "access_token"},
            data={
                "username": username,
                "password": password_hash,
                "language": "en",
            },
            headers={
                **COMMON_HEADERS,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        ) as resp:
            data: dict[str, Any] = await resp.json(content_type=None)

        try:
            bearer_token = data["data"]["token"]["access_token"]
        except (KeyError, TypeError) as exc:
            raise LoginError(f"SSO login failed: {data}") from exc

        async with client.get(
            f"{SSO_URL}/json/client/characters",
            headers={
                **COMMON_HEADERS,
                "Authorization": f"Bearer {bearer_token}",
            },
        ) as resp:
            data = await resp.json(content_type=None)
        return data.get("data", {}).get("characters", [])


class GameSession:
    """Handles SSO login and game session management."""

    def __init__(
        self,
        username: str,
        password_hash: str,
        server: str,
        character_id: str,
    ) -> None:
        self.username = username
        self.password_hash = password_hash
        self.server = server
        self.character_id = character_id
        self.bearer_token: str | None = None
        self.account_uuid: str | None = None
        self.sid: str | None = None
        self.pg_player: str | None = None
        self.pg_session: str | None = None
        self.player_name: str = ""
        self.group_name: str = ""
        self.login_data: dict[str, str] = {}
        self.server_time_diff: int = 0
        self._client = aiohttp.ClientSession()

    def server_time(self) -> int:
        """Return the current server unix timestamp."""
        return int(time.time()) + self.server_time_diff

    async def close(self) -> None:
        if not self._client.closed:
            await self._client.close()

    async def _sso_login_async(self) -> None:
        try:
            async with self._client.post(
                f"{SSO_URL}/json/login",
                params={"client_id": CLIENT_ID, "auth_type": "access_token"},
                data={
                    "username": self.username,
                    "password": self.password_hash,
                    "language": "en",
                },
                headers={
                    **COMMON_HEADERS,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            ) as resp:
                data: dict[str, Any] = await resp.json(content_type=None)
        except (aiohttp.ClientError, ValueError) as exc:
            raise LoginError(f"SSO request failed: {exc}") from exc

        try:
            self.bearer_token = data["data"]["token"]["access_token"]
            self.account_uuid = data["data"]["account"]["uuid"]
        except (KeyError, TypeError) as exc:
            raise LoginError(f"SSO login failed: {data}") from exc

    async def list_characters_async(self) -> list[dict[str, Any]]:
        if not self.bearer_token:
            await self._sso_login_async()

        async with self._client.get(
            f"{SSO_URL}/json/client/characters",
            headers={
                **COMMON_HEADERS,
                "Authorization": f"Bearer {self.bearer_token}",
            },
        ) as resp:
            data: dict[str, Any] = await resp.json(content_type=None)
        return data.get("data", {}).get("characters", [])

    async def login_async(self) -> "GameSession":
        await self._sso_login_async()

        server_id = SERVER_MAP_CACHE.get(self.server)
        suffix = f"/{server_id}" if server_id else ""
        char_params = base64.b64encode(
            f"{self.account_uuid}/{self.character_id}/unity3d_webglplayer//305000000000{suffix}".encode()
        ).decode()

        async with self._client.get(
            f"https://{self.server}/cmd.php",
            params={
                "req": "SFAccountCharLogin",
                "params": char_params,
                "sid": "0-00000000000000",
            },
            headers={
                **COMMON_HEADERS,
                "Authorization": f"Bearer {self.bearer_token}",
                "pg-player": "0",
                "pg-sso-server": SSO_URL,
            },
        ) as resp:
            text = await resp.text()

        data = parse_response(text)
        try:
            check_response_for_error(data)
        except KnownAPIError:
            raise
        except APIError as e:
            raise LoginError(f"Game login failed: {e}") from e

        self.login_data = data
        try:
            self.pg_player = self.login_data["ownplayersavecharacter"].split(
                VALUES_DELIMITER
            )[1]
            self.sid = self.login_data["cryptoid"]
            self.pg_session = self.login_data["sessionid"]
            self.player_name = self.login_data["ownplayername.r"]
        except KeyError as exc:
            raise LoginError(f"Game login response missing key: {exc}") from exc
        self.group_name = self.login_data.get("owngroupname.r", "")

        server_ts = int(self.login_data["timestamp"])
        self.server_time_diff = server_ts - int(time.time())

        get_main_logger().debug(
            f"Logged in as {self.player_name} (ID: {self.pg_player})"
        )
        return self

    async def request_async(self, req: str, params_str: str = "") -> str:
        if self.sid is None or self.pg_player is None or self.pg_session is None:
            raise LoginError(
                "Game session is not initialized. Call login_async() first."
            )

        encoded_params = base64.b64encode(params_str.encode()).decode()
        async with self._client.get(
            f"https://{self.server}/cmd.php",
            params={"req": req, "params": encoded_params, "sid": self.sid},
            headers={
                **COMMON_HEADERS,
                "pg-player": str(self.pg_player),
                "pg-session": self.pg_session,
            },
        ) as resp:
            return await resp.text()

    RELOGIN_RETRIES = 3
    RELOGIN_DELAY = 10

    async def relogin_async(self) -> None:
        """Re-login with retries for transient failures."""
        for attempt in range(self.RELOGIN_RETRIES):
            try:
                await self.login_async()
                return
            except LoginError:
                if attempt == self.RELOGIN_RETRIES - 1:
                    raise
                get_main_logger().warning(
                    f"Relogin attempt {attempt + 1}/{self.RELOGIN_RETRIES} failed, "
                    f"retrying in {self.RELOGIN_DELAY}s"
                )
                await asyncio.sleep(self.RELOGIN_DELAY)

    async def request_and_update_async(
        self, req: str, params_str: str = ""
    ) -> dict[str, str]:
        # Ensure we have the latest login_data before making the request
        await self.relogin_async()
        text = await self.request_async(req, params_str)
        result = parse_response(text)
        check_response_for_error(result)
        self.login_data.update(result)
        return result

    async def poll_async(self) -> None:
        text = await self.request_async("Poll")
        poll_data = parse_response(text)
        self.login_data.update(poll_data)
