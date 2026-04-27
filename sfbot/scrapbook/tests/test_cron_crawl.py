import hashlib
import re
import string

import pytest

from cron_crawl import (
    NAME_PREFIXES,
    random_password,
    random_username,
    sha1,
    unique_servers,
)


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
    def _clear_char_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import os

        for k in list(os.environ):
            if k.startswith("SF_CHAR_"):
                monkeypatch.delenv(k)

    def test_parses_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SF_CHAR_1", "alice,123,s1.sfgame.net")
        monkeypatch.setenv("SF_CHAR_2", "bob,456,s2.sfgame.net")
        monkeypatch.setenv("SF_CHAR_3", "carol,789,s1.sfgame.net")
        assert unique_servers() == ["s1.sfgame.net", "s2.sfgame.net"]

    def test_empty_when_no_vars(self) -> None:
        assert unique_servers() == []

    def test_ignores_malformed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SF_CHAR_1", "only_two_parts,123")
        monkeypatch.setenv("SF_CHAR_2", "ok,456,s1.sfgame.net")
        assert unique_servers() == ["s1.sfgame.net"]
