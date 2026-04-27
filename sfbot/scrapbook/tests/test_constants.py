"""Tests for scrapbook constants."""

from sfbot.scrapbook.constants import (
    ITEM_POSITIONS,
    MONSTER_POSITIONS,
    QUEUE_REFRESH_INTERVAL,
    SCRAPBOOK_COUNT,
)


class TestQueueRefreshInterval:
    def test_value(self) -> None:
        assert QUEUE_REFRESH_INTERVAL == 1800


class TestConstants:
    def test_item_positions(self) -> None:
        assert ITEM_POSITIONS == SCRAPBOOK_COUNT - MONSTER_POSITIONS

    def test_scrapbook_count(self) -> None:
        assert SCRAPBOOK_COUNT == 2396

    def test_monster_positions(self) -> None:
        assert MONSTER_POSITIONS == 800
