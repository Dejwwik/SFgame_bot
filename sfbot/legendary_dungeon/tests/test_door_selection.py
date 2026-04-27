from sfbot.legendary_dungeon.models import (
    DoorTrap,
    DoorType,
    DungeonEffectType,
)
from sfbot.legendary_dungeon.tests.conftest import make_door, make_dungeon, make_effect

# ═══════════════════════════════════════════════════════════════════════════
# Door Selection — Basic Preferences
# ═══════════════════════════════════════════════════════════════════════════


class TestDoorPreferences:
    def test_open_door_over_blocked(self):
        ld = make_dungeon(
            doors=[
                make_door(DoorType.OPEN_DOOR),
                make_door(DoorType.BLOCKED),
            ]
        )
        assert ld.pick_door() == 0

    def test_blocked_loses_to_anything(self):
        ld = make_dungeon(
            doors=[
                make_door(DoorType.BLOCKED),
                make_door(DoorType.MONSTER_1),
            ]
        )
        assert ld.pick_door() == 1

    def test_open_door_over_monster(self):
        ld = make_dungeon(
            doors=[
                make_door(DoorType.MONSTER_1),
                make_door(DoorType.OPEN_DOOR),
            ]
        )
        assert ld.pick_door() == 1

    def test_epic_door_preferred(self):
        ld = make_dungeon(
            doors=[
                make_door(DoorType.MONSTER_2),
                make_door(DoorType.EPIC_DOOR),
            ]
        )
        assert ld.pick_door() == 1

    def test_golden_door_preferred(self):
        ld = make_dungeon(
            doors=[
                make_door(DoorType.GOLDEN_DOOR),
                make_door(DoorType.MONSTER_1),
            ]
        )
        assert ld.pick_door() == 0

    def test_blessing_door_preferred(self):
        ld = make_dungeon(
            doors=[
                make_door(DoorType.MONSTER_3),
                make_door(DoorType.BLESSING_DOOR),
            ]
        )
        assert ld.pick_door() == 1

    def test_key_master_shop_preferred(self):
        ld = make_dungeon(
            doors=[
                make_door(DoorType.KEY_MASTER_SHOP),
                make_door(DoorType.MONSTER_1),
            ]
        )
        assert ld.pick_door() == 0

    def test_resource_door_over_monster(self):
        ld = make_dungeon(
            doors=[
                make_door(DoorType.MONSTER_1),
                make_door(DoorType.WOOD),
            ]
        )
        assert ld.pick_door() == 1

    def test_trial_door_over_monster(self):
        ld = make_dungeon(
            doors=[
                make_door(DoorType.TRIAL_ROOM_1),
                make_door(DoorType.MONSTER_2),
            ]
        )
        # Trial rooms score -10, monsters score 0 → monster preferred
        assert ld.pick_door() == 1

    def test_good_door_over_resource(self):
        ld = make_dungeon(
            doors=[
                make_door(DoorType.STONE),
                make_door(DoorType.OPEN_DOOR),
            ]
        )
        assert ld.pick_door() == 1

    def test_resource_over_trial(self):
        ld = make_dungeon(
            doors=[
                make_door(DoorType.WOOD),
                make_door(DoorType.TRIAL_ROOM_2),
            ]
        )
        assert ld.pick_door() == 0


# ═══════════════════════════════════════════════════════════════════════════
# Door Selection — Cursed & Sacrificial Doors
# ═══════════════════════════════════════════════════════════════════════════


class TestDoorCursedSacrificial:
    def test_cursed_door_avoided(self):
        ld = make_dungeon(
            doors=[
                make_door(DoorType.MONSTER_1),
                make_door(DoorType.CURSED_DOOR),
            ]
        )
        assert ld.pick_door() == 0

    def test_sacrificial_door_avoided(self):
        ld = make_dungeon(
            doors=[
                make_door(DoorType.SACRIFICIAL_DOOR),
                make_door(DoorType.MONSTER_1),
            ]
        )
        assert ld.pick_door() == 1

    def test_cursed_worse_than_sacrificial(self):
        ld = make_dungeon(
            doors=[
                make_door(DoorType.SACRIFICIAL_DOOR),
                make_door(DoorType.CURSED_DOOR),
            ]
        )
        assert ld.pick_door() == 0


# ═══════════════════════════════════════════════════════════════════════════
# Door Selection — Locked Doors & Keys
# ═══════════════════════════════════════════════════════════════════════════


class TestDoorLockedKeys:
    def test_locked_door_with_no_keys_avoided(self):
        ld = make_dungeon(
            keys=0,
            doors=[make_door(DoorType.LOCKED_DOOR), make_door(DoorType.MONSTER_1)],
        )
        assert ld.pick_door() == 1

    def test_locked_door_with_key_in_last_section(self):
        ld = make_dungeon(
            keys=2,
            current_floor=80,
            doors=[make_door(DoorType.LOCKED_DOOR), make_door(DoorType.MONSTER_1)],
        )
        assert ld.pick_door() == 0

    def test_double_locked_with_no_keys_avoided(self):
        ld = make_dungeon(
            keys=0,
            doors=[
                make_door(DoorType.DOUBLE_LOCKED_DOOR),
                make_door(DoorType.MONSTER_1),
            ],
        )
        assert ld.pick_door() == 1

    def test_double_locked_needs_two_keys(self):
        ld = make_dungeon(
            keys=1,
            doors=[
                make_door(DoorType.DOUBLE_LOCKED_DOOR),
                make_door(DoorType.MONSTER_1),
            ],
        )
        assert ld.pick_door() == 1

    def test_double_locked_with_two_keys_in_last_section(self):
        ld = make_dungeon(
            keys=2,
            current_floor=80,
            doors=[
                make_door(DoorType.DOUBLE_LOCKED_DOOR),
                make_door(DoorType.MONSTER_1),
            ],
        )
        assert ld.pick_door() == 0

    def test_locked_door_with_lock_pick_blessing(self):
        ld = make_dungeon(
            keys=0,
            blessings=[make_effect(DungeonEffectType.LOCK_PICK), None, None],
            doors=[make_door(DoorType.LOCKED_DOOR), make_door(DoorType.MONSTER_1)],
        )
        assert ld.pick_door() == 0

    def test_double_locked_with_lock_pick_blessing(self):
        ld = make_dungeon(
            keys=0,
            blessings=[make_effect(DungeonEffectType.LOCK_PICK), None, None],
            doors=[
                make_door(DoorType.DOUBLE_LOCKED_DOOR),
                make_door(DoorType.MONSTER_1),
            ],
        )
        assert ld.pick_door() == 0

    def test_locked_door_avoided_when_hoarding_keys(self):
        # keys < KEYS_TARGET and not last section → hoarding
        ld = make_dungeon(
            keys=2,
            current_floor=10,
            doors=[make_door(DoorType.LOCKED_DOOR), make_door(DoorType.MONSTER_1)],
        )
        assert ld.pick_door() == 1

    def test_double_locked_avoided_when_hoarding(self):
        ld = make_dungeon(
            keys=3,
            current_floor=10,
            doors=[
                make_door(DoorType.DOUBLE_LOCKED_DOOR),
                make_door(DoorType.MONSTER_1),
            ],
        )
        assert ld.pick_door() == 1


# ═══════════════════════════════════════════════════════════════════════════
# Door Selection — Doomed State (can't survive boss)
# ═══════════════════════════════════════════════════════════════════════════


class TestDoorDoomed:
    def test_locked_door_avoided_when_doomed(self):
        # Very low HP → can't survive boss → doomed
        ld = make_dungeon(
            current_hp=100,
            max_hp=1000,
            keys=3,
            doors=[make_door(DoorType.LOCKED_DOOR), make_door(DoorType.MONSTER_1)],
        )
        assert ld.pick_door() == 1

    def test_double_locked_avoided_when_doomed(self):
        ld = make_dungeon(
            current_hp=100,
            max_hp=1000,
            keys=5,
            doors=[
                make_door(DoorType.DOUBLE_LOCKED_DOOR),
                make_door(DoorType.MONSTER_1),
            ],
        )
        assert ld.pick_door() == 1


# ═══════════════════════════════════════════════════════════════════════════
# Door Selection — Traps
# ═══════════════════════════════════════════════════════════════════════════


class TestDoorTraps:
    def test_trap_on_low_hp_avoided(self):
        # HP ≤ TRAP_DMG (10%) → trapped door is -95
        ld = make_dungeon(
            current_hp=80,
            max_hp=1000,
            doors=[
                make_door(DoorType.MONSTER_1, trap=DoorTrap.BEAR_TRAP),
                make_door(DoorType.MONSTER_2),
            ],
        )
        assert ld.pick_door() == 1

    def test_trap_tolerated_at_high_hp(self):
        ld = make_dungeon(
            current_hp=900,
            max_hp=1000,
            doors=[
                make_door(DoorType.OPEN_DOOR, trap=DoorTrap.SWINGING_AXE),
                make_door(DoorType.MONSTER_1),
            ],
        )
        assert ld.pick_door() == 0

    def test_trap_with_disarm_blessing_ignored(self):
        ld = make_dungeon(
            current_hp=80,
            max_hp=1000,
            blessings=[make_effect(DungeonEffectType.DISARM_TRAPS), None, None],
            doors=[
                make_door(DoorType.MONSTER_1, trap=DoorTrap.BEAR_TRAP),
                make_door(DoorType.BLOCKED),
            ],
        )
        assert ld.pick_door() == 0

    def test_mystery_door_with_trap_penalized(self):
        ld = make_dungeon(
            doors=[
                make_door(DoorType.MYSTERY_DOOR, trap=DoorTrap.GUILLOTINE),
                make_door(DoorType.MONSTER_1),
            ],
        )
        assert ld.pick_door() == 1

    def test_mystery_door_without_trap_preferred_over_monster(self):
        ld = make_dungeon(
            doors=[
                make_door(DoorType.MYSTERY_DOOR),
                make_door(DoorType.MONSTER_1),
            ],
        )
        assert ld.pick_door() == 0

    def test_monster_with_trap_very_negative(self):
        ld = make_dungeon(
            doors=[
                make_door(DoorType.MONSTER_1, trap=DoorTrap.TRIP_WIRE),
                make_door(DoorType.SACRIFICIAL_DOOR),
            ],
        )
        assert ld.pick_door() == 1


# ═══════════════════════════════════════════════════════════════════════════
# Door Selection — Healing Blessing Impact
# ═══════════════════════════════════════════════════════════════════════════


class TestDoorHealingBlessing:
    def test_monster_door_better_with_healing(self):
        ld = make_dungeon(
            blessings=[make_effect(DungeonEffectType.ROAD_TO_RECOVERY), None, None],
            doors=[
                make_door(DoorType.MONSTER_1),
                make_door(DoorType.MYSTERY_DOOR),
            ],
        )
        assert ld.pick_door() == 0

    def test_monster_door_preferred_with_elixir(self):
        ld = make_dungeon(
            blessings=[make_effect(DungeonEffectType.ELIXIR_OF_LIFE), None, None],
            doors=[
                make_door(DoorType.MONSTER_1),
                make_door(DoorType.MYSTERY_DOOR),
            ],
        )
        assert ld.pick_door() == 0


# ═══════════════════════════════════════════════════════════════════════════
# Door Selection — No Dungeon State
# ═══════════════════════════════════════════════════════════════════════════


class TestDoorNoDungeon:
    def test_no_dungeon_returns_zero(self):
        ld = make_dungeon()
        ld.dungeon = None
        assert ld.pick_door() == 0
