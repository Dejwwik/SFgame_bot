from sfbot.legendary_dungeon.legendary_dungeon import (
    parse_dungeon_state,
    parse_effect,
    parse_gem,
    parse_run_stats,
    parse_soul_stones,
    parse_total_stats,
)
from sfbot.legendary_dungeon.models import (
    DoorTrap,
    DoorType,
    DungeonEffectType,
    DungeonStage,
    GemEffect,
    GemSpecial,
    GemType,
    RoomEncounter,
    RoomEncounterType,
    RoomType,
)

# ═══════════════════════════════════════════════════════════════════════════
# parse_effect
# ═══════════════════════════════════════════════════════════════════════════


class TestParseEffect:
    def test_zero_type_returns_none(self):
        assert parse_effect(0, 50000, 5) is None

    def test_negative_type_returns_none(self):
        assert parse_effect(-1, 50000, 5) is None

    def test_valid_blessing(self):
        # remaining_strength = remaining_uses * 10000 + strength
        # 3 * 10000 + 8000 = 38000
        eff = parse_effect(DungeonEffectType.RAIDER, 38000, 5)
        assert eff is not None
        assert eff.typ == DungeonEffectType.RAIDER
        assert eff.remaining_uses == 3
        assert eff.strength == 8000
        assert eff.max_uses == 5

    def test_valid_curse(self):
        eff = parse_effect(DungeonEffectType.BROKEN_ARMOR, 20000, 3)
        assert eff is not None
        assert eff.typ == DungeonEffectType.BROKEN_ARMOR
        assert eff.remaining_uses == 2
        assert eff.strength == 0

    def test_strength_encoding(self):
        # remaining_strength = 5 * 10000 + 1234 = 51234
        eff = parse_effect(DungeonEffectType.ESCAPE_ASSISTANT, 51234, 10)
        assert eff is not None
        assert eff.remaining_uses == 5
        assert eff.strength == 1234

    def test_zero_remaining_uses(self):
        # remaining_strength = 0 * 10000 + 5000 = 5000
        eff = parse_effect(DungeonEffectType.ELIXIR_OF_LIFE, 5000, 1)
        assert eff is not None
        assert eff.remaining_uses == 0
        assert eff.strength == 5000


# ═══════════════════════════════════════════════════════════════════════════
# parse_dungeon_state
# ═══════════════════════════════════════════════════════════════════════════


class TestParseDungeonState:
    def _make_vals(self, **overrides: int) -> list[str]:
        # Minimal wire with 48 fields (indices 0..47)
        vals = ["0"] * 48
        index_map: dict[str, int] = {
            "health_status": 1,
            "current_hp": 2,
            "pre_battle_hp": 3,
            "max_hp": 4,
            "stage": 15,
            "gem_count": 16,
            "current_floor": 17,
            "max_floor": 18,
            "keys": 39,
        }
        for key, value in overrides.items():
            if key in index_map:
                vals[index_map[key]] = str(value)
        return vals

    def test_basic_fields(self):
        vals = self._make_vals(
            health_status=0,
            current_hp=800,
            max_hp=1000,
            current_floor=42,
            max_floor=100,
            keys=3,
            stage=1,
        )
        state = parse_dungeon_state(vals)
        assert state.current_hp == 800
        assert state.max_hp == 1000
        assert state.current_floor == 42
        assert state.max_floor == 100
        assert state.keys == 3
        assert state.stage == DungeonStage.DOOR_SELECT

    def test_not_entered_stage(self):
        vals = self._make_vals(stage=0)
        state = parse_dungeon_state(vals)
        assert state.stage == DungeonStage.NOT_ENTERED

    def test_doors_parsed_in_door_select(self):
        vals = self._make_vals(stage=1)
        vals[19] = str(DoorType.OPEN_DOOR)
        vals[20] = str(DoorType.LOCKED_DOOR)
        vals[25] = str(DoorTrap.BEAR_TRAP)
        vals[26] = "0"
        state = parse_dungeon_state(vals)
        assert state.doors[0].typ == DoorType.OPEN_DOOR
        assert state.doors[0].trap == DoorTrap.BEAR_TRAP
        assert state.doors[1].typ == DoorType.LOCKED_DOOR
        assert state.doors[1].trap is None

    def test_room_type_parsed_outside_door_select(self):
        vals = self._make_vals(stage=10)
        vals[19] = str(RoomType.FOUNTAIN_OF_LIFE)
        state = parse_dungeon_state(vals)
        assert state.room_type == RoomType.FOUNTAIN_OF_LIFE

    def test_blessings_parsed(self):
        vals = self._make_vals(stage=1)
        vals[5] = str(DungeonEffectType.RAIDER)
        vals[6] = str(DungeonEffectType.ONE_HIT_WONDER)
        vals[7] = "0"
        vals[11] = str(3 * 10_000 + 100)  # remaining=3, strength=100
        vals[12] = str(2 * 10_000)
        vals[13] = "0"
        vals[42] = "5"
        vals[43] = "4"
        vals[44] = "0"
        state = parse_dungeon_state(vals)
        assert state.blessings[0] is not None
        assert state.blessings[0].typ == DungeonEffectType.RAIDER
        assert state.blessings[0].remaining_uses == 3
        assert state.blessings[1] is not None
        assert state.blessings[1].typ == DungeonEffectType.ONE_HIT_WONDER
        assert state.blessings[2] is None

    def test_curses_parsed(self):
        vals = self._make_vals(stage=1)
        vals[8] = str(DungeonEffectType.BROKEN_ARMOR)
        vals[9] = "0"
        vals[10] = str(DungeonEffectType.POISONED)
        # Curse strengths: [14, 40, 41]
        vals[14] = str(2 * 10_000 + 5000)
        vals[40] = "0"
        vals[41] = str(1 * 10_000 + 500)
        vals[45] = "3"
        vals[46] = "0"
        vals[47] = "2"
        state = parse_dungeon_state(vals)
        assert state.curses[0] is not None
        assert state.curses[0].typ == DungeonEffectType.BROKEN_ARMOR
        assert state.curses[1] is None
        assert state.curses[2] is not None
        assert state.curses[2].typ == DungeonEffectType.POISONED

    def test_encounter_monster(self):
        vals = self._make_vals(stage=10)
        vals[22] = "-500"  # Negative = monster with id 500
        state = parse_dungeon_state(vals)
        assert state.encounter.is_monster is True
        assert state.encounter.monster_id == 500

    def test_encounter_chest(self):
        vals = self._make_vals(stage=10)
        vals[22] = str(RoomEncounterType.SILVER_CHEST)
        state = parse_dungeon_state(vals)
        assert state.encounter.encounter_type == RoomEncounterType.SILVER_CHEST

    def test_zero_room_type_is_none(self):
        vals = self._make_vals(stage=10)
        vals[19] = "0"
        state = parse_dungeon_state(vals)
        assert state.room_type is None


# ═══════════════════════════════════════════════════════════════════════════
# RoomEncounter.parse
# ═══════════════════════════════════════════════════════════════════════════


class TestRoomEncounterParse:
    def test_negative_value_is_monster(self):
        enc = RoomEncounter.parse(-42)
        assert enc.is_monster is True
        assert enc.monster_id == 42

    def test_known_encounter_type(self):
        enc = RoomEncounter.parse(RoomEncounterType.EPIC_CHEST)
        assert enc.encounter_type == RoomEncounterType.EPIC_CHEST
        assert enc.is_monster is False

    def test_unknown_positive_value_returns_empty(self):
        enc = RoomEncounter.parse(99999)
        assert enc.is_monster is False
        assert enc.encounter_type is None

    def test_zero_is_bronze_chest(self):
        enc = RoomEncounter.parse(0)
        assert enc.encounter_type == RoomEncounterType.BRONZE_CHEST

    def test_barrel(self):
        enc = RoomEncounter.parse(RoomEncounterType.BARREL)
        assert enc.encounter_type == RoomEncounterType.BARREL

    def test_mimic_chest(self):
        enc = RoomEncounter.parse(RoomEncounterType.MIMIC_CHEST)
        assert enc.encounter_type == RoomEncounterType.MIMIC_CHEST

    def test_sacrificial_chest(self):
        enc = RoomEncounter.parse(RoomEncounterType.SACRIFICIAL_CHEST)
        assert enc.encounter_type == RoomEncounterType.SACRIFICIAL_CHEST


# ═══════════════════════════════════════════════════════════════════════════
# parse_gem
# ═══════════════════════════════════════════════════════════════════════════


class TestParseGem:
    def test_all_zeros_returns_none(self):
        assert parse_gem([0, 0, 0, 0, 0, 0]) is None

    def test_valid_gem(self):
        gem = parse_gem(
            [
                GemType.EYE_OF_THE_BULL,
                GemEffect.DAMAGE_FROM_MONSTERS,
                20,
                GemEffect.DAMAGE_FROM_TRAPS,
                10,
                GemSpecial.WEAKER_MONSTERS_SPAWN,
            ]
        )
        assert gem is not None
        assert gem.typ == GemType.EYE_OF_THE_BULL
        assert gem.advantage == GemEffect.DAMAGE_FROM_MONSTERS
        assert gem.advantage_pwr == 20
        assert gem.disadvantage == GemEffect.DAMAGE_FROM_TRAPS
        assert gem.disadvantage_pwr == 10
        assert gem.special == GemSpecial.WEAKER_MONSTERS_SPAWN

    def test_no_advantage(self):
        gem = parse_gem(
            [GemType.SOUL_OF_THE_RABBIT, 0, 0, GemEffect.ESCAPE_CHANCE, 15, 0]
        )
        assert gem is not None
        assert gem.advantage is None
        assert gem.disadvantage == GemEffect.ESCAPE_CHANCE

    def test_no_disadvantage(self):
        gem = parse_gem(
            [GemType.BOULDER_OF_GREED, GemEffect.CHANCE_OF_KEYS, 25, 0, 0, 0]
        )
        assert gem is not None
        assert gem.advantage == GemEffect.CHANCE_OF_KEYS
        assert gem.disadvantage is None
        assert gem.special is None

    def test_no_special(self):
        gem = parse_gem(
            [
                GemType.EMERALD_OF_THE_EXPLORER,
                GemEffect.DAMAGE_FROM_MONSTERS,
                10,
                GemEffect.DAMAGE_FROM_CHESTS,
                5,
                0,
            ]
        )
        assert gem is not None
        assert gem.special is None

    def test_only_type_nonzero(self):
        gem = parse_gem([GemType.LODE_STONE, 0, 0, 0, 0, 0])
        assert gem is not None
        assert gem.typ == GemType.LODE_STONE


# ═══════════════════════════════════════════════════════════════════════════
# parse_soul_stones
# ═══════════════════════════════════════════════════════════════════════════


class TestParseSoulStones:
    def test_empty_string(self):
        owned, available = parse_soul_stones("")
        assert owned == []
        assert available == []

    def test_three_owned_no_available(self):
        # 3 gems × 6 fields = 18 ints
        chunks = [
            f"{GemType.EYE_OF_THE_BULL}/{GemEffect.DAMAGE_FROM_MONSTERS}/20/0/0/0",
            f"{GemType.SOUL_OF_THE_RABBIT}/{GemEffect.ESCAPE_CHANCE}/15/0/0/0",
            f"{GemType.BOULDER_OF_GREED}/{GemEffect.CHANCE_OF_KEYS}/10/0/0/0",
        ]
        raw = "/".join(chunks)
        owned, available = parse_soul_stones(raw)
        assert len(owned) == 3
        assert len(available) == 0
        assert owned[0].typ == GemType.EYE_OF_THE_BULL
        assert owned[1].typ == GemType.SOUL_OF_THE_RABBIT
        assert owned[2].typ == GemType.BOULDER_OF_GREED

    def test_three_owned_two_available(self):
        chunks = [
            f"{GemType.EYE_OF_THE_BULL}/0/0/0/0/0",
            f"{GemType.SOUL_OF_THE_RABBIT}/0/0/0/0/0",
            f"{GemType.BOULDER_OF_GREED}/0/0/0/0/0",
            f"{GemType.EMERALD_OF_THE_EXPLORER}/{GemEffect.DAMAGE_FROM_MONSTERS}/20/0/0/0",
            f"{GemType.PEARL_OF_THE_MASOCHIST}/{GemEffect.ESCAPE_CHANCE}/10/0/0/0",
        ]
        raw = "/".join(chunks)
        owned, available = parse_soul_stones(raw)
        assert len(owned) == 3
        assert len(available) == 2
        assert available[0].typ == GemType.EMERALD_OF_THE_EXPLORER
        assert available[1].typ == GemType.PEARL_OF_THE_MASOCHIST

    def test_null_owned_gems_skipped(self):
        # First owned slot is all zeros (no gem)
        chunks = [
            "0/0/0/0/0/0",
            f"{GemType.SOUL_OF_THE_RABBIT}/0/0/0/0/0",
            "0/0/0/0/0/0",
        ]
        raw = "/".join(chunks)
        owned, available = parse_soul_stones(raw)
        assert len(owned) == 1
        assert owned[0].typ == GemType.SOUL_OF_THE_RABBIT


# ═══════════════════════════════════════════════════════════════════════════
# parse_run_stats / parse_total_stats
# ═══════════════════════════════════════════════════════════════════════════


class TestParseRunStats:
    def test_full_stats(self):
        vals = ["5", "2", "8", "1000", "3"]
        stats = parse_run_stats(vals)
        assert stats.items_found == 5
        assert stats.epics_found == 2
        assert stats.keys_found == 8
        assert stats.silver_found == 1000
        assert stats.attempts == 3


class TestParseTotalStats:
    def test_full_stats(self):
        vals = ["12", "50", "300", "20", "99999"]
        stats = parse_total_stats(vals)
        assert stats.legendaries_found == 12
        assert stats.best_run_attempts == 50
        assert stats.enemies_defeated == 300
        assert stats.epics_found == 20
        assert stats.gold_found == 99999
