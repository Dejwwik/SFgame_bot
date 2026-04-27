from unittest.mock import MagicMock

from sfbot.legendary_dungeon.legendary_dungeon import LegendaryDungeon
from sfbot.legendary_dungeon.models import (
    Door,
    DoorTrap,
    DoorType,
    DungeonEffect,
    DungeonEffectType,
    DungeonStage,
    DungeonState,
    GemEffect,
    GemOfFate,
    GemSpecial,
    GemType,
    RoomEncounter,
    RoomType,
)


def make_effect(
    typ: DungeonEffectType,
    remaining_uses: int = 3,
    max_uses: int = 5,
    strength: int = 100,
) -> DungeonEffect:
    return DungeonEffect(
        typ=typ,
        remaining_uses=remaining_uses,
        max_uses=max_uses,
        strength=strength,
    )


def make_door(
    typ: DoorType = DoorType.OPEN_DOOR,
    trap: DoorTrap | None = None,
) -> Door:
    return Door(typ=typ, trap=trap)


def make_gem(
    typ: GemType = GemType.EYE_OF_THE_BULL,
    advantage: GemEffect | None = None,
    advantage_pwr: int = 0,
    disadvantage: GemEffect | None = None,
    disadvantage_pwr: int = 0,
    special: GemSpecial | None = None,
) -> GemOfFate:
    return GemOfFate(
        typ=typ,
        advantage=advantage,
        advantage_pwr=advantage_pwr,
        disadvantage=disadvantage,
        disadvantage_pwr=disadvantage_pwr,
        special=special,
    )


def make_dungeon_state(
    current_hp: int = 1000,
    max_hp: int = 1000,
    current_floor: int = 1,
    max_floor: int = 100,
    stage: DungeonStage = DungeonStage.DOOR_SELECT,
    keys: int = 0,
    doors: list[Door] | None = None,
    room_type: RoomType | None = None,
    encounter: RoomEncounter | None = None,
    blessings: list[DungeonEffect | None] | None = None,
    curses: list[DungeonEffect | None] | None = None,
    health_status: int = 0,
) -> DungeonState:
    return DungeonState(
        health_status=health_status,
        current_hp=current_hp,
        max_hp=max_hp,
        current_floor=current_floor,
        max_floor=max_floor,
        stage=stage,
        keys=keys,
        doors=doors or [Door(DoorType.BLOCKED), Door(DoorType.BLOCKED)],
        room_type=room_type,
        encounter=encounter or RoomEncounter(),
        blessings=blessings or [None, None, None],
        curses=curses or [None, None, None],
    )


def make_dungeon(
    current_hp: int = 1000,
    max_hp: int = 1000,
    current_floor: int = 1,
    max_floor: int = 100,
    stage: DungeonStage = DungeonStage.DOOR_SELECT,
    keys: int = 0,
    doors: list[Door] | None = None,
    room_type: RoomType | None = None,
    encounter: RoomEncounter | None = None,
    blessings: list[DungeonEffect | None] | None = None,
    curses: list[DungeonEffect | None] | None = None,
    owned_gems: list[GemOfFate] | None = None,
    health_status: int = 0,
    server_time: int = 100,
    start_ts: int = 0,
    end_ts: int = 10_000,
    close_ts: int = 20_000,
) -> LegendaryDungeon:
    mock_session = MagicMock()
    mock_session.login_data = {}
    mock_session.server_time.return_value = server_time
    mock_inventory = MagicMock()
    mock_inventory.get_free_slot.return_value = None

    ld = object.__new__(LegendaryDungeon)
    ld.session = mock_session
    ld.inventory = mock_inventory
    ld.theme = None
    ld.start_ts = start_ts
    ld.end_ts = end_ts
    ld.close_ts = close_ts
    ld.run_stats = None
    ld.total_stats = None
    ld.owned_gems = owned_gems or []
    ld.available_gems = []

    ld.dungeon = make_dungeon_state(
        current_hp=current_hp,
        max_hp=max_hp,
        current_floor=current_floor,
        max_floor=max_floor,
        stage=stage,
        keys=keys,
        doors=doors,
        room_type=room_type,
        encounter=encounter,
        blessings=blessings,
        curses=curses,
        health_status=health_status,
    )

    return ld
