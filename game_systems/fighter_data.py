import random
from config import (SKILL_MP_COST, ULTIMATE_MULTIPLIER, NORMAL_ATTACK_MP_REGEN, 
                  SKILL_MULTIPLIER, EXP_PER_LEVEL_COEFF)

class FighterData:
    """
    [Model]
    캐릭터의 모든 순수 데이터와 그 데이터를 조작하는 메서드를 포함합니다.
    Pygame에 대한 의존성이 전혀 없습니다.
    """
    def __init__(self, x, y, name, is_enemy, hp, max_hp, mp, max_mp, sp_max, atk, agi, 
                 image_path=None, description="", inv_id=None, level=1, exp=0, grade="COMMON",
                 skill_name="", skill_description="", ult_name="", sfx_type="NORMAL"):
        # 위치 정보 (View가 참조)
        self.x = x
        self.y = y
        
        # 고유 정보
        self.name = name
        self.grade = grade
        self.is_enemy = is_enemy
        self.inv_id = inv_id
        self.image_path = image_path
        self.description = description
        self.skill_name = skill_name
        self.skill_description = skill_description
        self.ult_name = ult_name
        self.sfx_type = sfx_type

        # 핵심 스탯 (변동)
        self.hp = hp
        self.max_hp = max_hp
        self.mp = mp
        self.max_mp = max_mp
        self.sp = 0
        self.max_sp = sp_max
        self.atk = atk
        self.agi = agi
        
        # 성장 정보
        self.level = level
        self.exp = exp
        self.max_exp = self.level * EXP_PER_LEVEL_COEFF

        self.is_alive = True

    @staticmethod
    def from_dict(data, x=0, y=0, is_enemy=False):
        """
        [Factory Method]
        사전(dict) 데이터로부터 FighterData 객체를 생성합니다.
        주로 DB에서 읽어온 데이터로 객체를 만들 때 사용됩니다.
        """
        # 등반 중 임시 데이터(current_hp/mp)가 있으면 그것을, 없으면 영구 데이터(hp/mp)를 사용
        hp = data.get('current_hp', data.get('hp'))
        mp = data.get('current_mp', data.get('mp'))

        return FighterData(
            x=x,
            y=y,
            name=data.get('name', 'Unknown'),
            is_enemy=is_enemy,
            hp=hp,
            max_hp=data.get('hp'),
            mp=mp,
            max_mp=data.get('mp'),
            sp_max=data.get('sp_max'),
            atk=data.get('atk'),
            agi=data.get('agi'),
            image_path=data.get('image'),
            description=data.get('description', ''),
            inv_id=data.get('inv_id'),
            level=data.get('level', 1),
            exp=data.get('exp', 0),
            grade=data.get('grade', 'COMMON'),
            skill_name=data.get('skill_name', ''),
            skill_description=data.get('skill_description', ''),
            ult_name=data.get('ult_name', ''),
            sfx_type=data.get('sfx_type') or 'NORMAL' # 값이 없거나 비어있으면 'NORMAL'
        )

    def take_damage(self, damage):
        self.hp -= damage
        if self.hp <= 0:
            self.hp = 0
            self.is_alive = False
        
        # 피격 시 SP 충전 로직
        charge = int(self.max_sp * 0.1) + random.randint(1, 5)
        self.sp = min(self.sp + charge, self.max_sp)

    def use_skill(self, target: 'FighterData'):
        self.mp -= SKILL_MP_COST
        return int(self.atk * SKILL_MULTIPLIER)

    def use_ultimate(self, target: 'FighterData'):
        self.sp = 0
        return int(self.atk * ULTIMATE_MULTIPLIER)

    def normal_attack(self, target: 'FighterData'):
        self.mp = min(self.mp + NORMAL_ATTACK_MP_REGEN, self.max_mp)
        return self.atk