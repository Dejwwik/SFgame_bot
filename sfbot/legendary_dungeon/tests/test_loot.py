from sfbot.constants import (
    ITEM_FIELD_MODEL,
    ITEM_FIELD_MUSHROOM_PRICE,
    ITEM_FIELD_PRICE,
    ITEM_FIELD_TYPE,
    VALUES_DELIMITER,
)
from sfbot.legendary_dungeon.tests.conftest import make_dungeon

# ═══════════════════════════════════════════════════════════════════════════
# _loot_source — identifies where pending loot data lives
# ═══════════════════════════════════════════════════════════════════════════


def _make_item_wire(
    item_type: int = 1,
    model: int = 1001,
    price: int = 500,
    mush_price: int = 0,
    num_fields: int = 19,
) -> str:
    fields = ["0"] * num_fields
    fields[ITEM_FIELD_TYPE] = str(item_type)
    fields[ITEM_FIELD_MODEL] = str(model)
    fields[ITEM_FIELD_PRICE] = str(price)
    fields[ITEM_FIELD_MUSHROOM_PRICE] = str(mush_price)
    return VALUES_DELIMITER.join(fields)


def _make_pending_wire(
    count: int = 1,
    item_type: int = 1,
    model: int = 2002,
    price: int = 1000,
    mush_price: int = 5,
) -> str:
    # iapendingitems has count prefix + 19 item fields = 20 fields
    fields = ["0"] * 20
    fields[0] = str(count)
    fields[1 + ITEM_FIELD_TYPE] = str(item_type)
    fields[1 + ITEM_FIELD_MODEL] = str(model)
    fields[1 + ITEM_FIELD_PRICE] = str(price)
    fields[1 + ITEM_FIELD_MUSHROOM_PRICE] = str(mush_price)
    return VALUES_DELIMITER.join(fields)


class TestLootSource:
    def test_no_loot_returns_none(self):
        ld = make_dungeon()
        assert ld._loot_source() is None

    def test_ialootitem_room_loot(self):
        ld = make_dungeon()
        ld.session.login_data["ialootitem"] = _make_item_wire()
        source = ld._loot_source()
        assert source is not None
        assert source[0] == "ialootitem"
        assert source[1] == 0

    def test_iapendingitems_boss_reward(self):
        ld = make_dungeon()
        ld.session.login_data["iapendingitems"] = _make_pending_wire()
        source = ld._loot_source()
        assert source is not None
        assert source[0] == "iapendingitems"
        assert source[1] == 1

    def test_ialootitem_takes_priority(self):
        ld = make_dungeon()
        ld.session.login_data["ialootitem"] = _make_item_wire()
        ld.session.login_data["iapendingitems"] = _make_pending_wire()
        source = ld._loot_source()
        assert source is not None
        assert source[0] == "ialootitem"

    def test_empty_ialootitem_falls_through(self):
        ld = make_dungeon()
        ld.session.login_data["ialootitem"] = ""
        ld.session.login_data["iapendingitems"] = _make_pending_wire()
        source = ld._loot_source()
        assert source is not None
        assert source[0] == "iapendingitems"

    def test_zero_type_ialootitem_falls_through(self):
        ld = make_dungeon()
        ld.session.login_data["ialootitem"] = _make_item_wire(item_type=0)
        ld.session.login_data["iapendingitems"] = _make_pending_wire()
        source = ld._loot_source()
        assert source is not None
        assert source[0] == "iapendingitems"

    def test_too_short_ialootitem_falls_through(self):
        ld = make_dungeon()
        # Less than 19 fields → not a full item wire
        ld.session.login_data["ialootitem"] = VALUES_DELIMITER.join(["1"] * 10)
        ld.session.login_data["iapendingitems"] = _make_pending_wire()
        source = ld._loot_source()
        assert source is not None
        assert source[0] == "iapendingitems"

    def test_zero_count_pending_returns_none(self):
        ld = make_dungeon()
        ld.session.login_data["iapendingitems"] = _make_pending_wire(count=0)
        assert ld._loot_source() is None


class TestHasPendingLoot:
    def test_no_loot(self):
        ld = make_dungeon()
        assert ld.has_pending_loot() is False

    def test_has_room_loot(self):
        ld = make_dungeon()
        ld.session.login_data["ialootitem"] = _make_item_wire()
        assert ld.has_pending_loot() is True

    def test_has_boss_loot(self):
        ld = make_dungeon()
        ld.session.login_data["iapendingitems"] = _make_pending_wire()
        assert ld.has_pending_loot() is True


class TestLootIdent:
    def test_room_loot_ident(self):
        ld = make_dungeon()
        ld.session.login_data["ialootitem"] = _make_item_wire(
            item_type=5, model=3003, price=750, mush_price=2
        )
        ident = ld._loot_ident()
        assert ident == f"{5 & 0xFF}/{3003 & 0xFFFF}/750/2"

    def test_boss_loot_ident(self):
        ld = make_dungeon()
        ld.session.login_data["iapendingitems"] = _make_pending_wire(
            item_type=3, model=4004, price=1500, mush_price=10
        )
        ident = ld._loot_ident()
        assert ident == f"{3 & 0xFF}/{4004 & 0xFFFF}/1500/10"

    def test_no_loot_returns_empty(self):
        ld = make_dungeon()
        assert ld._loot_ident() == ""
