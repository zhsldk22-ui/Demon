from __future__ import annotations
import math

# 순환 참조 방지를 위한 Type Hinting
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from game_systems.fighter_data import FighterData

from game_systems.fighter_data import FighterData
import config
import database

class LevelManager:
    """
    [Controller]
    캐릭터 성장(레벨, 경험치, 스탯) 관련 로직을 전담하는 정적 클래스.
    """
    @staticmethod
    def calculate_next_max_exp(level: int) -> int:
        """다음 레벨업에 필요한 총 경험치를 계산합니다."""
        if level >= config.MAX_LEVEL:
            return 0
        return level * config.EXP_PER_LEVEL_COEFF

    @staticmethod
    def _apply_stat_growth(fighter_data: FighterData):
        """
        레벨업 시 등급에 따라 스탯을 분배하여 영구적으로 상승시킵니다.
        - HP: 60%, ATK: 30%, AGI: 10%
        - 모든 스탯은 정수로 내림 처리됩니다.
        """
        # [Fix] .upper()를 사용하여 등급명의 대소문자 달라도 값을 찾도록 수정
        total_growth = config.STAT_GROWTH_RATE.get(fighter_data.grade.upper(), 0)
        if total_growth == 0:
            print(f"[Warning] {fighter_data.grade} 등급의 성장률이 정의되지 않았습니다.")
            return

        hp_gain = math.floor(total_growth * 0.6)
        atk_gain = math.floor(total_growth * 0.3)
        agi_gain = total_growth - hp_gain - atk_gain

        fighter_data.max_hp += hp_gain
        fighter_data.atk += atk_gain
        fighter_data.agi += agi_gain
        
        fighter_data.hp = fighter_data.max_hp
        
        print(f"[LevelUp] {fighter_data.name} 스탯 상승! HP: +{hp_gain}, ATK: +{atk_gain}, AGI: +{agi_gain}")

    @staticmethod
    def _calculate_level_ups(fighter_data: FighterData, amount: int) -> list:
        """
        [FIXED] 경험치 획득 및 레벨업 로직 수행. 레벨업 정보를 '리스트'로 반환.
        """
        if fighter_data.level >= config.MAX_LEVEL:
            if amount > 0:
                print(f"[EXP] {fighter_data.name}이(가) 최대 레벨이어서 경험치를 획득할 수 없습니다.")
            return []

        fighter_data.exp += amount
        print(f"[EXP] {fighter_data.name}이(가) 경험치 {amount}를 획득했습니다. (현재: {fighter_data.exp}/{fighter_data.max_exp})")
        
        level_up_events = []
        while fighter_data.exp >= fighter_data.max_exp and fighter_data.level < config.MAX_LEVEL:
            old_level = fighter_data.level
            excess_exp = fighter_data.exp - fighter_data.max_exp
            fighter_data.level += 1
            fighter_data.exp = excess_exp
            
            LevelManager._apply_stat_growth(fighter_data)
            fighter_data.max_exp = LevelManager.calculate_next_max_exp(fighter_data.level)
            
            event_info = {"old": old_level, "new": fighter_data.level}
            level_up_events.append(event_info)
            print(f"[LevelUp] {fighter_data.name}이(가) 레벨 {fighter_data.level}이 되었습니다!")

            if fighter_data.level >= config.MAX_LEVEL:
                fighter_data.exp = 0
                print(f"[LevelUp] {fighter_data.name}이(가) 최대 레벨에 도달했습니다!")
                break
        
        return level_up_events

    @staticmethod
    def gain_session_exp(fighter_data: FighterData, amount: int) -> list:
        """[FIXED] 세션 중 경험치를 획득하고, 레벨업 정보를 리스트로 반환."""
        if amount <= 0:
            return []
        return LevelManager._calculate_level_ups(fighter_data, amount)

    @staticmethod
    def gain_exp_for_character(cursor: database.sqlite3.Cursor, inv_id: int, amount: int):
        """
        [FIXED] ID로 캐릭터를 조회하여 '영구' 경험치를 부여하고, 레벨업 시 스탯을 DB에 저장합니다.
        기존 gain_exp 함수를 인라인하여 로직을 명확하게 합니다.
        """
        if amount <= 0: return

        char_db_data = database.get_character_details_by_inv_id_cursor(cursor, inv_id)
        if not char_db_data:
            print(f"[Error] LevelManager: inv_id {inv_id}에 해당하는 캐릭터를 찾을 수 없습니다.")
            return

        # DB 데이터에서 FighterData 객체를 생성합니다. 이 객체는 일시적인 데이터 컨테이너로 사용됩니다.
        max_hp = char_db_data['total_max_hp'] if char_db_data['total_max_hp'] is not None else char_db_data['base_hp']
        atk = char_db_data['total_atk'] if char_db_data['total_atk'] is not None else char_db_data['base_atk']
        agi = char_db_data['total_agi'] if char_db_data['total_agi'] is not None else char_db_data['base_agi']
        
        fighter = FighterData(
            x=0, y=0, name=char_db_data['name'], is_enemy=False,
            hp=max_hp, max_hp=max_hp, mp=char_db_data['base_mp'], max_mp=char_db_data['base_mp'],
            sp_max=char_db_data['sp_max'], atk=atk, agi=agi,
            image_path=char_db_data['image'], description=char_db_data['description'],
            inv_id=char_db_data['inv_id'], level=char_db_data['level'],
            exp=char_db_data['exp'], grade=char_db_data['grade']
        )
        
        # --- Start of inlined gain_exp logic ---
        level_up_events = LevelManager._calculate_level_ups(fighter, amount)
        
        if level_up_events:
            # 레벨업이 발생한 경우, 변경된 모든 스탯(레벨, 경험치, 최대체력, 공격력, 민첩성)을 DB에 저장합니다.
            database.update_character_stats(
                cursor,
                inv_id=fighter.inv_id, level=fighter.level, exp=fighter.exp,
                max_hp=fighter.max_hp, atk=fighter.atk, agi=fighter.agi
            )
        elif amount > 0:
            # 레벨업은 하지 않았지만 경험치를 얻은 경우, 경험치만 DB에 저장합니다.
            database.update_character_exp(cursor, inv_id=fighter.inv_id, exp=fighter.exp)
        # --- End of inlined gain_exp logic ---


    @staticmethod
    def gain_temp_exp(fighter, exp_to_gain, temp_stats_dict):
        """
        등반 중 임시 경험치 획득 및 레벨업을 처리합니다.
        DB에 저장하지 않고, 임시 스탯 정보만 업데이트합니다.
        """
        character_id = fighter.id
        
        # 현재 임시 스탯을 가져옵니다. 정보가 없으면 파이터의 등반 시작 레벨로 시작합니다.
        current_level, current_exp = temp_stats_dict.get(character_id, (fighter.base_level, 0))

        if current_level >= LevelManager.MAX_LEVEL:
            return

        print(f"[In-Run EXP] {fighter.name}이(가) 임시 경험치 {exp_to_gain}를 획득했습니다.")
        current_exp += exp_to_gain
        
        new_level = current_level
        
        while new_level < LevelManager.MAX_LEVEL:
            exp_for_next_level = LevelManager.EXP_TABLE.get(new_level, float('inf'))
            if current_exp >= exp_for_next_level:
                current_exp -= exp_for_next_level
                new_level += 1
                print(f"[In-Run LEVEL UP] {fighter.name}이(가) 임시 레벨 {new_level} 달성!")
            else:
                break
        
        if new_level > current_level:
            # 파이터 인스턴스의 스탯을 업데이트하여 현재 등반에 적용합니다.
            level_diff = new_level - current_level
            fighter.level = new_level
            fighter.attack += level_diff * config.ATTACK_PER_LEVEL
            fighter.max_hp += level_diff * config.HEALTH_PER_LEVEL
            fighter.current_hp = fighter.max_hp # 레벨업 시 체력 완전 회복
            print(f"[In-Run Stats Up] {fighter.name} 능력치 상승! 공격력: {fighter.attack}, 체력: {fighter.max_hp}")

        # 업데이트된 임시 스탯을 딕셔너리에 저장합니다.
        temp_stats_dict[character_id] = (new_level, current_exp)
