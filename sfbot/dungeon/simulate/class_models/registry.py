from sfbot.constants.enums import CharClass
from sfbot.dungeon.simulate.class_models.assassin import AssassinModel
from sfbot.dungeon.simulate.class_models.bard import BardModel
from sfbot.dungeon.simulate.class_models.base import ClassModel
from sfbot.dungeon.simulate.class_models.battle_mage import BattleMageModel
from sfbot.dungeon.simulate.class_models.berserker import BerserkerModel
from sfbot.dungeon.simulate.class_models.demon_hunter import DemonHunterModel
from sfbot.dungeon.simulate.class_models.druid import DruidModel
from sfbot.dungeon.simulate.class_models.necromancer import NecromancerModel
from sfbot.dungeon.simulate.class_models.paladin import PaladinModel
from sfbot.dungeon.simulate.class_models.plague_doctor import PlagueDoctorModel

CLASS_MODEL_MAP: dict[CharClass, type[ClassModel]] = {
    CharClass.WARRIOR: ClassModel,
    CharClass.MAGE: ClassModel,
    CharClass.SCOUT: ClassModel,
    CharClass.ASSASSIN: AssassinModel,
    CharClass.BATTLE_MAGE: BattleMageModel,
    CharClass.BERSERKER: BerserkerModel,
    CharClass.DEMON_HUNTER: DemonHunterModel,
    CharClass.DRUID: DruidModel,
    CharClass.BARD: BardModel,
    CharClass.NECROMANCER: NecromancerModel,
    CharClass.PALADIN: PaladinModel,
    CharClass.PLAGUE_DOCTOR: PlagueDoctorModel,
}


def create_model(char_class: CharClass) -> ClassModel:
    return CLASS_MODEL_MAP[char_class]()
