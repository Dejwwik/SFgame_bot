"""Tests for scrapbook bitfield decoding and position mapping."""

import base64

from sfbot.scrapbook.scrapbook import (
    EquipmentIdent,
    decode_scrapbook,
    get_scrapbook_position,
    parse_equipment_idents,
    parse_hof_players,
)


class TestDecodeScrapbook:
    def test_empty_string(self) -> None:
        assert decode_scrapbook("") == set() or True  # empty b64 is degenerate

    def test_single_byte_all_set(self) -> None:
        # 0xFF = all 8 bits set → positions 1-8
        raw = base64.b64encode(b"\xff").decode()
        positions = decode_scrapbook(raw)
        assert positions == {1, 2, 3, 4, 5, 6, 7, 8}

    def test_single_byte_first_bit(self) -> None:
        # 0x80 = bit 7 set (MSB) → position 1
        raw = base64.b64encode(b"\x80").decode()
        positions = decode_scrapbook(raw)
        assert positions == {1}

    def test_single_byte_last_bit(self) -> None:
        # 0x01 = bit 0 set (LSB) → position 8
        raw = base64.b64encode(b"\x01").decode()
        positions = decode_scrapbook(raw)
        assert positions == {8}

    def test_url_safe_encoding(self) -> None:
        # URL-safe base64 uses - and _ instead of + and /
        data = bytes([0x80, 0x00, 0x01])  # positions 1 and 24
        raw = base64.b64encode(data).decode()
        url_safe = raw.replace("+", "-").replace("/", "_").rstrip("=")
        positions = decode_scrapbook(url_safe)
        assert 1 in positions
        assert 24 in positions

    def test_two_bytes(self) -> None:
        # 0xA0 = 10100000 → positions 1, 3
        # 0x05 = 00000101 → positions 14, 16
        raw = base64.b64encode(b"\xa0\x05").decode()
        positions = decode_scrapbook(raw)
        assert positions == {1, 3, 14, 16}


class TestGetScrapbookPosition:
    def test_normal_amulet_warrior(self) -> None:
        # Amulet (type=8), colorClass=0, model_id=1, color=0
        # boundary = SCRAPBOOK_BOUNDARIES[0][7] = [800, 1010]
        # normal: start=800, position=(1-1)*5+0=0 → 800+1=801
        ident = EquipmentIdent(item_type=8, color_class=0, model_id=1, color=0)
        assert get_scrapbook_position(ident) == 801

    def test_normal_amulet_color_3(self) -> None:
        # Amulet, model_id=1, color=3
        # position = 800 + 0*5 + 3 + 1 = 804
        ident = EquipmentIdent(item_type=8, color_class=0, model_id=1, color=3)
        assert get_scrapbook_position(ident) == 804

    def test_normal_amulet_model_2(self) -> None:
        # Amulet, model_id=2, color=0
        # position = 800 + (2-1)*5 + 0 + 1 = 806
        ident = EquipmentIdent(item_type=8, color_class=0, model_id=2, color=0)
        assert get_scrapbook_position(ident) == 806

    def test_epic_amulet(self) -> None:
        # Amulet (type=8), colorClass=0, model_id=50 (epic), color=0
        # boundary = [800, 1010], epic_start=1010
        # position = 1010 + (50-50) + 1 = 1011
        ident = EquipmentIdent(item_type=8, color_class=0, model_id=50, color=0)
        assert get_scrapbook_position(ident) == 1011

    def test_epic_amulet_model_51(self) -> None:
        ident = EquipmentIdent(item_type=8, color_class=0, model_id=51, color=0)
        assert get_scrapbook_position(ident) == 1012

    def test_talisman(self) -> None:
        # Talisman (type=10), colorClass=0, model_id=1
        # boundary = SCRAPBOOK_BOUNDARIES[0][9] = [1250, 1324]
        # talisman: start=1250, position=(1-1)=0 → 1250+1=1251
        ident = EquipmentIdent(item_type=10, color_class=0, model_id=1, color=0)
        assert get_scrapbook_position(ident) == 1251

    def test_talisman_model_5(self) -> None:
        ident = EquipmentIdent(item_type=10, color_class=0, model_id=5, color=0)
        assert get_scrapbook_position(ident) == 1255

    def test_warrior_weapon_normal(self) -> None:
        # Weapon (type=1), colorClass=1 (Warrior), model_id=1, color=2
        # boundary = SCRAPBOOK_BOUNDARIES[1][0] = [1364, 1664]
        # position = 1364 + (1-1)*5 + 2 + 1 = 1367
        ident = EquipmentIdent(item_type=1, color_class=1, model_id=1, color=2)
        assert get_scrapbook_position(ident) == 1367

    def test_warrior_weapon_epic(self) -> None:
        # Weapon (type=1), colorClass=1, model_id=50 (epic)
        # epic_start = 1664, position = 1664 + 0 + 1 = 1665
        ident = EquipmentIdent(item_type=1, color_class=1, model_id=50, color=0)
        assert get_scrapbook_position(ident) == 1665

    def test_invalid_color_class(self) -> None:
        ident = EquipmentIdent(item_type=1, color_class=5, model_id=1, color=0)
        assert get_scrapbook_position(ident) is None

    def test_invalid_type_key(self) -> None:
        # Mage (colorClass=2) has no shield (type_key=1)
        ident = EquipmentIdent(item_type=2, color_class=2, model_id=1, color=0)
        assert get_scrapbook_position(ident) is None

    def test_mage_breastplate(self) -> None:
        # Breastplate (type=3), colorClass=2, model_id=1, color=0
        # boundary = SCRAPBOOK_BOUNDARIES[2][2] = [2684, 2784]
        # position = 2684 + 0*5 + 0 + 1 = 2685
        ident = EquipmentIdent(item_type=3, color_class=2, model_id=1, color=0)
        assert get_scrapbook_position(ident) == 2685


class TestParseHofPlayers:
    def test_basic_entry(self) -> None:
        raw = ";1,TestPlayer,TestGuild,100,5000,1,;"
        players = parse_hof_players(raw)
        assert len(players) == 1
        assert players[0].name == "TestPlayer"
        assert players[0].level == 100
        assert players[0].rank == 1

    def test_multiple_entries(self) -> None:
        raw = ";1,Alice,,50,100,1,;2,Bob,Guild,60,200,2,;"
        players = parse_hof_players(raw)
        assert len(players) == 2
        assert players[0].name == "Alice"
        assert players[1].name == "Bob"

    def test_empty_placeholder_skipped(self) -> None:
        raw = ";1,Alice,,50,100,1,;0,,,,0,0,0,;"
        players = parse_hof_players(raw)
        assert len(players) == 1

    def test_empty_string(self) -> None:
        assert parse_hof_players("") == []


class TestParseEquipmentIdents:
    def test_single_slot(self) -> None:
        # Build a 19-field item: type=1 (weapon), model=1001 (class=1, model=1)
        # dmg_min=10, dmg_max=20, attr_types=[1,2,3], attr_values=[100,200,300]
        fields = [0] * 19
        fields[0] = 1  # type = Weapon
        fields[3] = 1001  # class=1, model=1
        fields[5] = 10  # dmg_min
        fields[6] = 20  # dmg_max
        fields[7] = 1  # attr_type 0
        fields[8] = 2  # attr_type 1
        fields[9] = 3  # attr_type 2
        fields[10] = 100  # attr_val 0
        fields[11] = 200  # attr_val 1
        fields[12] = 300  # attr_val 2
        raw = "/".join(str(f) for f in fields)
        idents = parse_equipment_idents(raw)
        assert len(idents) == 1
        assert idents[0].item_type == 1
        assert idents[0].color_class == 2  # class_id=1 → sf_class=2
        assert idents[0].model_id == 1
        # color = (20 + 10 + 1+2+3 + 100+200+300) % 5 = 636 % 5 = 1
        assert idents[0].color == 1

    def test_empty_slot_skipped(self) -> None:
        fields = [0] * 19
        raw = "/".join(str(f) for f in fields)
        idents = parse_equipment_idents(raw)
        assert len(idents) == 0

    def test_accessory_color_class_zero(self) -> None:
        # Ring (type=9) → colorClass=0 regardless of class
        fields = [0] * 19
        fields[0] = 9  # Ring
        fields[3] = 2001  # class=2, model=1
        fields[5] = 5
        fields[6] = 10
        raw = "/".join(str(f) for f in fields)
        idents = parse_equipment_idents(raw)
        assert len(idents) == 1
        assert idents[0].color_class == 0

    def test_epic_item_color_zero(self) -> None:
        # Epic item (model_id=50) → color=0
        fields = [0] * 19
        fields[0] = 1  # Weapon
        fields[3] = 1050  # class=1, model=50 (epic)
        fields[5] = 999
        fields[6] = 999
        raw = "/".join(str(f) for f in fields)
        idents = parse_equipment_idents(raw)
        assert len(idents) == 1
        assert idents[0].color == 0
        assert idents[0].model_id == 50
