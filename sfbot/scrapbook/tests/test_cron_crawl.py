import asyncio
import hashlib
import re
import sqlite3
import string
from pathlib import Path

import pytest

from cron_crawl import (
    NAME_PREFIXES,
    random_password,
    random_username,
    sha1,
    unique_servers,
)
from sfbot.persistence import accounts


class TestSha1:
    def test_known_hash(self) -> None:
        expected = hashlib.sha1(b"hello").hexdigest()
        assert sha1("hello") == expected

    def test_empty_string(self) -> None:
        expected = hashlib.sha1(b"").hexdigest()
        assert sha1("") == expected


class TestRandomUsername:
    def test_format(self) -> None:
        name = random_username()
        pattern = re.compile(r"^[A-Z][a-z]+[A-Z][a-z]+\d{1,3}$")
        assert pattern.match(name), f"unexpected format: {name}"

    def test_uses_prefix_and_suffix(self) -> None:
        name = random_username()
        has_prefix = any(name.startswith(p) for p in NAME_PREFIXES)
        assert has_prefix

    def test_unique_across_calls(self) -> None:
        names = {random_username() for _ in range(50)}
        assert len(names) > 1


class TestRandomPassword:
    def test_length(self) -> None:
        pw = random_password()
        assert len(pw) == 14

    def test_has_lowercase(self) -> None:
        pw = random_password()
        assert any(c in string.ascii_lowercase for c in pw)

    def test_has_uppercase(self) -> None:
        pw = random_password()
        assert any(c in string.ascii_uppercase for c in pw)

    def test_has_digits(self) -> None:
        pw = random_password()
        assert any(c in string.digits for c in pw)

    def test_has_special(self) -> None:
        pw = random_password()
        assert any(c in "!@#$%" for c in pw)


class TestUniqueServers:
    @pytest.fixture(autouse=True)
    def _temp_db(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(accounts, "DB_PATH", str(tmp_path / "accounts.db"))
        accounts.init_db()
        conn: sqlite3.Connection = accounts.connect_sync()
        try:
            self.account_id: int = accounts.upsert_account(conn, "user", "hash")
        finally:
            conn.close()

    def add_character(self, character_id: str, server: str, enabled: bool) -> None:
        conn: sqlite3.Connection = accounts.connect_sync()
        try:
            conn.execute(
                "INSERT INTO characters (account_id, name, character_id, server, enabled)"
                " VALUES (?, ?, ?, ?, ?)",
                (self.account_id, character_id, character_id, server, int(enabled)),
            )
            conn.commit()
        finally:
            conn.close()

    def test_returns_sorted_unique_servers(self) -> None:
        self.add_character("1", "s2.sfgame.net", True)
        self.add_character("2", "s1.sfgame.net", True)
        self.add_character("3", "s2.sfgame.net", True)
        assert asyncio.run(unique_servers()) == ["s1.sfgame.net", "s2.sfgame.net"]

    def test_empty_when_no_characters(self) -> None:
        assert asyncio.run(unique_servers()) == []

    def test_ignores_disabled_characters(self) -> None:
        self.add_character("1", "s1.sfgame.net", True)
        self.add_character("2", "s3.sfgame.net", False)
        assert asyncio.run(unique_servers()) == ["s1.sfgame.net"]
