import sqlite3
from config import DB_PATH, DEFAULT_USER_ID
import database
from game_systems.stage_manager import StageManager
import random

class BattleDataHandler:
    def __init__(self, stage_manager):
        self.stage_manager = stage_manager

    def _connect(self):
        """Creates and returns a new database connection."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def setup_battle_data(self, floor, mode):
        """
        Loads all necessary data for a battle.
        - Handles starting a new run.
        - Loads party and enemy data.
        Returns a tuple of (party_data, enemy_data, new_floor).
        """
        try:
            conn = self._connect() # [Fix] DB 연결
            cursor = conn.cursor()

            if mode == 'NEW_GAME':
                database.start_new_run(conn) # [FIX] database 모듈의 함수를 호출
            
            party_data, new_floor = self._load_party_data(cursor, floor, mode)
            enemy_list = self._spawn_enemies(cursor, new_floor)

            conn.commit()
            return party_data, enemy_list, new_floor
        except sqlite3.Error as e:
            print(f"[Critical Error] BattleDataHandler setup failed: {e}")
            return [], [], floor
        finally:
            if conn: # [Fix] DB 연결 닫기
                conn.close() 

    def _load_party_data(self, cursor, current_floor, mode):
        """[Fixed] DB에서 플레이어 파티의 영구 성장 데이터를 포함하여 로드합니다."""
        party_data = []
        try:
            cursor.execute("SELECT current_floor FROM users WHERE user_id=?", (DEFAULT_USER_ID,))
            floor_data = cursor.fetchone()
            floor = floor_data['current_floor'] if floor_data else 1
        except sqlite3.Error as e:
            print(f"[DB Error] 현재 층 정보 조회 실패: {e}")
            floor = current_floor

        # [Fix] COALESCE를 사용해 영구 스탯이 NULL이면 기본 스탯을 사용하도록 쿼리 수정
        query = """
            SELECT 
                c.name, c.mp as base_mp, c.sp_max, c.image, c.description, c.grade, 
                c.sfx_type, c.skill_name, c.ult_name,
                i.id as inv_id, i.level, i.exp,
                i.current_hp, i.current_mp, i.current_sp,
                COALESCE(i.total_max_hp, c.hp) as max_hp,
                COALESCE(i.total_atk, c.atk) as atk,
                COALESCE(i.total_agi, c.agi) as agi
            FROM inventory i JOIN characters c ON i.char_id = c.id
            WHERE i.user_id = ? AND i.is_selected = 1
        """
        cursor.execute(query, (DEFAULT_USER_ID,))
        rows = cursor.fetchall()
        if not rows: raise sqlite3.Error("선택된 파티 정보를 찾을 수 없습니다.")

        is_boss_floor = self.stage_manager.get_stage_info(floor)['is_boss_floor']
        for r in rows: # [Fix] '새로 하기' 시 체력 완전 회복 로직 수정
            # '새로 하기' 또는 보스 클리어 시 체력 완전 회복
            should_heal_fully = (mode == 'NEW_GAME') or is_boss_floor or (r['current_hp'] is None) or (r['current_hp'] <= 0)
            
            hp = r['max_hp'] if should_heal_fully else r['current_hp']
            mp = r['base_mp'] # 등반 중 MP는 항상 최대로 시작
            sp = 0            # 등반 중 SP는 항상 0으로 시작

            party_data.append({
                "inv_id": r['inv_id'], "name": r['name'], "grade": r['grade'],
                "level": r['level'], "exp": r['exp'],
                "hp": hp, "max_hp": r['max_hp'], 
                "mp": mp, "max_mp": r['base_mp'], 
                "sp": sp, "sp_max": r['sp_max'],
                "atk": r['atk'], "agi": r['agi'],
                "sfx_type": r['sfx_type'], "skill_name": r['skill_name'], "ult_name": r['ult_name'],
                "image": r['image'], "description": r['description'] or r['name']
            })
        return party_data, floor

    def _spawn_enemies(self, cursor, floor):
        """[수정] 적 스탯을 DB값이 아닌 층수 기반 고정 스케일링으로 생성합니다."""
        stage_info = self.stage_manager.get_stage_info(floor)
        biome, tier = stage_info['biome'], stage_info['tier']
        enemies_to_spawn = []

        if stage_info['fixed_boss_id']:
            cursor.execute("SELECT * FROM enemies WHERE id=?", (stage_info['fixed_boss_id'],))
            enemies_to_spawn = cursor.fetchall()
        elif stage_info['is_boss_floor']:
            cursor.execute("SELECT * FROM enemies WHERE biome=? AND tier=? AND role='BOSS' ORDER BY RANDOM() LIMIT 1", (biome, tier))
            enemies_to_spawn = cursor.fetchall()
            if not enemies_to_spawn:
                 cursor.execute("SELECT * FROM enemies WHERE biome=? AND role='BOSS' ORDER BY tier ASC LIMIT 1", (biome,))
                 enemies_to_spawn = cursor.fetchall()
        
        if not enemies_to_spawn:
            cursor.execute("SELECT * FROM enemies WHERE biome=? AND tier=? AND role='MOB' ORDER BY RANDOM() LIMIT 2", (biome, tier))
            enemies_to_spawn = cursor.fetchall()

        enemy_data = []
        for row in enemies_to_spawn:
            data = dict(row)
            # [신규] 층수 기반 고정 스탯 스케일링 적용
            data['hp'] = floor * 100
            data['atk'] = floor * 10
            # agi, def 등 다른 스탯은 DB 값 유지
            enemy_data.append(data)
        
        return enemy_data

    def save_run_state(self, floor_to_save, player_fighters):
        """[수정] 등반 중 '현재 상태'(HP, MP, SP)만 저장하고, 영구 스탯은 건드리지 않습니다."""
        conn = None
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET current_floor = ? WHERE user_id=?", (floor_to_save, DEFAULT_USER_ID))
            for fighter in player_fighters:
                if fighter.is_enemy: continue # 아군 캐릭터만 저장
                
                cursor.execute("""
                    UPDATE inventory 
                    SET current_hp=?, current_mp=?, current_sp=?
                    WHERE id=?
                """, (fighter.hp, fighter.mp, fighter.sp, fighter.inv_id))
            conn.commit()
            print(f"[System] 진행 상황 저장 완료 (다음 층: {floor_to_save}층)")
        except sqlite3.Error as e:
            print(f"[DB Error] 진행 상황 저장 실패: {e}")
        finally:
            if conn:
                conn.close()

    def grant_ticket_reward(self, is_boss_floor):
        """Adds tickets to the user's account."""
        # This function is problematic as it doesn't use a transaction.
        # For now, let's just return the amount. The actual DB update needs a rethink.
        return 5 if is_boss_floor else 1
