from sfbot.constants.enums import CharClass
from sfbot.dungeon.models import Monster


class TestMonsterDataclass:
    def test_basic_construction(self) -> None:
        monster = Monster(
            name="Goblin",
            char_class=CharClass.WARRIOR,
            level=10,
            strength=100,
            dexterity=50,
            intelligence=30,
            constitution=80,
            luck=20,
            armor=50,
            min_dmg=10,
            max_dmg=20,
            health=500,
            rune_type=0,
            rune_damage=0,
            fire_resistance=0,
            cold_resistance=0,
            lightning_resistance=0,
        )
        assert monster.name == "Goblin"
        assert monster.char_class == CharClass.WARRIOR
        assert monster.level == 10
        assert monster.health == 500
        assert monster.is_mirror is False

    def test_mirror_monster(self) -> None:
        monster = Monster(
            name="Mirror",
            char_class=CharClass.WARRIOR,
            level=0,
            strength=0,
            dexterity=0,
            intelligence=0,
            constitution=0,
            luck=0,
            armor=0,
            min_dmg=None,
            max_dmg=None,
            health=0,
            rune_type=0,
            rune_damage=0,
            fire_resistance=0,
            cold_resistance=0,
            lightning_resistance=0,
            is_mirror=True,
        )
        assert monster.is_mirror is True
        assert monster.min_dmg is None
        assert monster.max_dmg is None

    def test_nullable_damage(self) -> None:
        monster = Monster(
            name="NoDmg",
            char_class=CharClass.MAGE,
            level=5,
            strength=10,
            dexterity=10,
            intelligence=50,
            constitution=20,
            luck=10,
            armor=0,
            min_dmg=None,
            max_dmg=None,
            health=100,
            rune_type=0,
            rune_damage=0,
            fire_resistance=0,
            cold_resistance=0,
            lightning_resistance=0,
        )
        assert monster.min_dmg is None
        assert monster.max_dmg is None

    def test_rune_fields(self) -> None:
        monster = Monster(
            name="Runed",
            char_class=CharClass.SCOUT,
            level=50,
            strength=200,
            dexterity=500,
            intelligence=100,
            constitution=300,
            luck=150,
            armor=100,
            min_dmg=30,
            max_dmg=60,
            health=3000,
            rune_type=40,
            rune_damage=30,
            fire_resistance=25,
            cold_resistance=10,
            lightning_resistance=50,
        )
        assert monster.rune_type == 40
        assert monster.rune_damage == 30
        assert monster.fire_resistance == 25
        assert monster.cold_resistance == 10
        assert monster.lightning_resistance == 50
