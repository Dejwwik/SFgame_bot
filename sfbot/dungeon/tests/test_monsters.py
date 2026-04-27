import pytest

from sfbot.constants.enums import CharClass
from sfbot.dungeon.enums import LightDungeon, ShadowDungeon
from sfbot.dungeon.monsters import (
    CLASS_NAME_MAP,
    LIGHT_NAME_MAP,
    SHADOW_NAME_MAP,
    get_light_monsters,
    get_monster_at,
    get_shadow_monsters,
    load_dungeons_json,
    parse_monster,
)
from sfbot.dungeon.simulate import estimate_hand_damage, estimate_weapon_damage


class TestClassNameMap:
    def test_all_standard_classes_present(self) -> None:
        expected = {
            "Warrior",
            "Mage",
            "Scout",
            "Assassin",
            "BattleMage",
            "Berserker",
            "DemonHunter",
            "Druid",
            "Bard",
            "Necromancer",
            "Paladin",
            "PlagueDoctor",
        }
        assert expected.issubset(CLASS_NAME_MAP.keys())

    def test_warmage_alias_maps_to_battle_mage(self) -> None:
        assert CLASS_NAME_MAP["WarMage"] == CharClass.BATTLE_MAGE

    def test_all_values_are_charclass(self) -> None:
        for value in CLASS_NAME_MAP.values():
            assert isinstance(value, CharClass)


class TestNameMaps:
    def test_light_map_covers_all_light_dungeons(self) -> None:
        mapped_ids = set(LIGHT_NAME_MAP.values())
        for member in LightDungeon:
            assert member in mapped_ids, (
                f"LightDungeon.{member.name} not in LIGHT_NAME_MAP"
            )

    def test_shadow_map_covers_all_shadow_dungeons(self) -> None:
        mapped_ids = set(SHADOW_NAME_MAP.values())
        for member in ShadowDungeon:
            assert member in mapped_ids, (
                f"ShadowDungeon.{member.name} not in SHADOW_NAME_MAP"
            )


class TestParseMonster:
    def test_normal_monster(self) -> None:
        data = {
            "name": "TestGoblin",
            "class": "Warrior",
            "level": 10,
            "strength": 100,
            "dexterity": 50,
            "intelligence": 30,
            "constitution": 80,
            "luck": 20,
            "armor": 50,
            "min_dmg": 10,
            "max_dmg": 20,
            "life": 500,
        }
        monster = parse_monster(data)
        assert monster.name == "TestGoblin"
        assert monster.char_class == CharClass.WARRIOR
        assert monster.level == 10
        assert monster.health == 500
        assert monster.min_dmg == 10
        assert monster.max_dmg == 20
        assert monster.armor == 50
        assert monster.is_mirror is False

    def test_monster_without_name(self) -> None:
        data = {
            "class": "Mage",
            "level": 5,
            "strength": 10,
            "dexterity": 10,
            "intelligence": 50,
            "constitution": 20,
            "luck": 10,
            "min_dmg": 5,
            "max_dmg": 10,
            "life": 100,
        }
        monster = parse_monster(data)
        assert monster.name == ""

    def test_monster_without_armor(self) -> None:
        data = {
            "class": "Scout",
            "level": 5,
            "strength": 10,
            "dexterity": 50,
            "intelligence": 10,
            "constitution": 20,
            "luck": 10,
            "min_dmg": 5,
            "max_dmg": 10,
            "life": 100,
        }
        monster = parse_monster(data)
        assert monster.armor == 0

    def test_monster_with_runes(self) -> None:
        data = {
            "class": "Warrior",
            "level": 50,
            "strength": 200,
            "dexterity": 100,
            "intelligence": 50,
            "constitution": 150,
            "luck": 80,
            "min_dmg": 30,
            "max_dmg": 60,
            "life": 3000,
            "runes": {
                "type": 40,
                "damage": 30,
                "res": [25, 10, 50],
            },
        }
        monster = parse_monster(data)
        assert monster.rune_type == 40
        assert monster.rune_damage == 30
        assert monster.fire_resistance == 25
        assert monster.cold_resistance == 10
        assert monster.lightning_resistance == 50

    def test_monster_with_partial_resistances(self) -> None:
        data = {
            "class": "Warrior",
            "level": 10,
            "strength": 100,
            "dexterity": 50,
            "intelligence": 30,
            "constitution": 80,
            "luck": 20,
            "min_dmg": 10,
            "max_dmg": 20,
            "life": 500,
            "runes": {"type": 41, "damage": 15, "res": [10]},
        }
        monster = parse_monster(data)
        assert monster.fire_resistance == 10
        assert monster.cold_resistance == 0
        assert monster.lightning_resistance == 0

    def test_mirror_monster(self) -> None:
        data = {"special": "mirror"}
        monster = parse_monster(data)
        assert monster.is_mirror is True
        assert monster.name == "Mirror"
        assert monster.min_dmg is None
        assert monster.max_dmg is None
        assert monster.health == 0

    def test_null_damage_values(self) -> None:
        data = {
            "class": "Assassin",
            "level": 20,
            "strength": 50,
            "dexterity": 100,
            "intelligence": 30,
            "constitution": 60,
            "luck": 40,
            "min_dmg": None,
            "max_dmg": None,
            "life": 800,
        }
        monster = parse_monster(data)
        assert monster.min_dmg is None
        assert monster.max_dmg is None

    def test_warmage_class_parsed(self) -> None:
        data = {
            "class": "WarMage",
            "level": 30,
            "strength": 150,
            "dexterity": 80,
            "intelligence": 120,
            "constitution": 100,
            "luck": 60,
            "min_dmg": 20,
            "max_dmg": 40,
            "life": 2000,
        }
        monster = parse_monster(data)
        assert monster.char_class == CharClass.BATTLE_MAGE


class TestLoadDungeonsJson:
    def test_loads_without_error(self) -> None:
        data = load_dungeons_json()
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_all_light_dungeon_keys_present(self) -> None:
        data = load_dungeons_json()
        for json_name in LIGHT_NAME_MAP:
            assert json_name in data, f"Missing key: {json_name}"

    def test_all_shadow_dungeon_keys_present(self) -> None:
        data = load_dungeons_json()
        for json_name in SHADOW_NAME_MAP:
            assert json_name in data, f"Missing key: {json_name}"


class TestGetMonsters:
    def test_get_light_monsters_returns_all_dungeons(self) -> None:
        monsters = get_light_monsters()
        for member in LightDungeon:
            assert member in monsters, f"Missing LightDungeon.{member.name}"

    def test_get_shadow_monsters_returns_all_dungeons(self) -> None:
        monsters = get_shadow_monsters()
        for member in ShadowDungeon:
            assert member in monsters, f"Missing ShadowDungeon.{member.name}"

    def test_light_dungeon_has_correct_floor_count(self) -> None:
        monsters = get_light_monsters()
        for dungeon, monster_list in monsters.items():
            assert len(monster_list) > 0, f"{dungeon.name} has no monsters"

    def test_all_parsed_monsters_have_class(self) -> None:
        monsters = get_light_monsters()
        for dungeon, monster_list in monsters.items():
            for monster in monster_list:
                assert isinstance(monster.char_class, CharClass), (
                    f"{dungeon.name}: invalid char_class"
                )


class TestGetMonsterAt:
    def test_valid_light_dungeon_floor(self) -> None:
        monster = get_monster_at(LightDungeon.DESECRATED_CATACOMBS, 0)
        assert monster is not None
        assert isinstance(monster.char_class, CharClass)

    def test_valid_shadow_dungeon_floor(self) -> None:
        monster = get_monster_at(ShadowDungeon.DESECRATED_CATACOMBS, 0)
        assert monster is not None

    def test_out_of_range_returns_none(self) -> None:
        assert get_monster_at(LightDungeon.DESECRATED_CATACOMBS, 999) is None

    def test_negative_progress_returns_none(self) -> None:
        assert get_monster_at(LightDungeon.DESECRATED_CATACOMBS, -1) is None

    def test_last_floor_returns_monster(self) -> None:
        monsters = get_light_monsters()
        monster_list = monsters[LightDungeon.DESECRATED_CATACOMBS]
        last = get_monster_at(LightDungeon.DESECRATED_CATACOMBS, len(monster_list) - 1)
        assert last is not None


class TestEstimateWeaponDamage:
    def test_warrior_uses_constant_ratio(self) -> None:
        min_dmg, max_dmg = estimate_weapon_damage(400, CharClass.WARRIOR)
        assert min_dmg == pytest.approx(2.78 * 400)
        assert min_dmg == max_dmg

    def test_mage_uses_constant_ratio(self) -> None:
        min_dmg, max_dmg = estimate_weapon_damage(400, CharClass.MAGE)
        assert min_dmg == pytest.approx(5.87 * 400)
        assert min_dmg == max_dmg

    def test_scout_uses_constant_ratio(self) -> None:
        min_dmg, max_dmg = estimate_weapon_damage(400, CharClass.SCOUT)
        assert min_dmg == pytest.approx(3.46 * 400)
        assert min_dmg == max_dmg

    def test_higher_level_has_higher_damage(self) -> None:
        _, low_max = estimate_weapon_damage(100, CharClass.WARRIOR)
        _, high_max = estimate_weapon_damage(500, CharClass.WARRIOR)
        assert high_max > low_max

    def test_min_equals_max(self) -> None:
        """Twister damage estimation uses min=max for simplicity."""
        for cls in (CharClass.WARRIOR, CharClass.MAGE, CharClass.SCOUT):
            min_dmg, max_dmg = estimate_weapon_damage(300, cls)
            assert min_dmg == max_dmg

    def test_hybrid_class_maps_to_base(self) -> None:
        """Hybrid classes use their weapon base class ratio."""
        warrior_dmg = estimate_weapon_damage(400, CharClass.WARRIOR)
        assert estimate_weapon_damage(400, CharClass.ASSASSIN) == warrior_dmg
        assert estimate_weapon_damage(400, CharClass.BERSERKER) == warrior_dmg
        assert estimate_weapon_damage(400, CharClass.PALADIN) == warrior_dmg

        mage_dmg = estimate_weapon_damage(400, CharClass.MAGE)
        assert estimate_weapon_damage(400, CharClass.NECROMANCER) == mage_dmg
        assert estimate_weapon_damage(400, CharClass.BARD) == mage_dmg

        scout_dmg = estimate_weapon_damage(400, CharClass.SCOUT)
        assert estimate_weapon_damage(400, CharClass.DEMON_HUNTER) == scout_dmg

    def test_damage_much_higher_than_hand_damage(self) -> None:
        """Weapon damage estimate should be significantly higher than unarmed formula."""
        for cls in (CharClass.WARRIOR, CharClass.MAGE, CharClass.SCOUT):
            weapon_min, weapon_max = estimate_weapon_damage(300, cls)
            hand_min, hand_max = estimate_hand_damage(300, cls)
            assert weapon_max > hand_max, f"{cls.name}: weapon should exceed hand"

    def test_level_zero_returns_minimum(self) -> None:
        min_dmg, max_dmg = estimate_weapon_damage(0, CharClass.WARRIOR)
        assert min_dmg == 1.0
        assert max_dmg == 1.0
