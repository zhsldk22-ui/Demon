import sqlite3
import random
import database
from config import DB_PATH, DEFAULT_USER_ID, GACHA_MULTI_DRAW_COUNT, GACHA_DUPLICATE_EXP
from game_systems.level_manager import LevelManager

class GachaManager:
    GACHA_RATES = {
        "MYTHIC": 0.05, "LEGEND": 0.5, "SPECIAL": 1.45, "RARE": 8.0, "COMMON": 90.0
    }

    def __init__(self):
        self.pool = {}
        self._load_pool()

    def _load_pool(self):
        for grade in self.GACHA_RATES.keys():
            self.pool[grade] = []
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM characters")
                rows = cursor.fetchall()
                
                for row in rows:
                    char_data = dict(row)
                    grade_key = char_data['grade'].upper().strip()
                    if grade_key in self.pool:
                        self.pool[grade_key].append(char_data)
                    else:
                        self.pool["COMMON"].append(char_data)
            print(f"[System] 가챠 풀 로드 완료: {len(rows)}명")
        except sqlite3.Error as e:
            print(f"[Critical Error] 가챠 풀 로드 실패: {e}")

    def _draw_single(self):
        grades, weights = list(self.GACHA_RATES.keys()), list(self.GACHA_RATES.values())
        selected_grade = random.choices(grades, weights=weights, k=1)[0]
        
        pool = self.pool.get(selected_grade)
        if not pool:
            print(f"[Warning] '{selected_grade}' 등급 캐릭터가 없어 Common 등급에서 뽑습니다.")
            pool = self.pool["COMMON"]
        
        return random.choice(pool)

    def draw_1(self, user_id=DEFAULT_USER_ID):
        char_info = self._draw_single()
        return self._save_to_inventory(user_id, [char_info])

    def draw_10(self, user_id=DEFAULT_USER_ID):
        drawn_chars = [self._draw_single() for _ in range(GACHA_MULTI_DRAW_COUNT)]
        return self._save_to_inventory(user_id, drawn_chars)

    def _save_to_inventory(self, user_id, drawn_chars):
        processed_results = []
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # 트랜잭션 시작 시점에 티켓 차감
            database.add_tickets(cursor, -len(drawn_chars), user_id)

            for char in drawn_chars:
                char_id = char['id']
                grade = char['grade'].upper()
                
                is_new, inv_id, char_name = database.add_character_to_inventory(cursor, char_id, user_id)
                
                result_info = {'char': char, 'is_duplicate': not is_new, 'exp_gain': 0}

                if is_new:
                    print(f"[Gacha] 신규 캐릭터 획득: {char_name}")
                else:  # 중복 캐릭터
                    exp_to_add = GACHA_DUPLICATE_EXP.get(grade, 0)
                    result_info['exp_gain'] = exp_to_add
                    
                    if exp_to_add > 0 and inv_id is not None:
                        print(f"[Gacha] 중복 캐릭터 획득: {char_name}. 경험치 +{exp_to_add}")
                        LevelManager.gain_exp_for_character(cursor, inv_id, exp_to_add)
                    else:
                        print(f"[Gacha] 중복 캐릭터 획득: {char_name}. (경험치 정보 없음 또는 inv_id 없음)")
                
                processed_results.append(result_info)

            conn.commit()
        except sqlite3.Error as e:
            print(f"[DB Error] 인벤토리 저장 실패: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

        return processed_results