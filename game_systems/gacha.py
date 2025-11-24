import sqlite3
import random
import sys
import os

# [수정] 부모 폴더(프로젝트 루트)를 파이썬 검색 경로에 추가
# 이렇게 해야 상위 폴더에 있는 config.py를 불러올 수 있습니다.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import DB_PATH

class GachaManager:
    # 요청하신 확률 설정 (단위: %)
    GACHA_RATES = {
        "MYTHIC": 0.2,   # 신화 (엄마, 아빠, 아들)
        "LEGEND": 2.8,   # 전설 (3.0% 누적)
        "SPECIAL": 5.0,  # 특별 (8.0% 누적)
        "RARE": 32.0,    # 희귀 (40.0% 누적)
        "COMMON": 60.0   # 일반 (100.0% 누적)
    }

    def __init__(self):
        self.pool = {} # 등급별 캐릭터 ID 리스트 저장소
        self._load_pool()

    def _load_pool(self):
        """DB에서 캐릭터 정보를 읽어와 등급별로 분류"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 초기화
        for grade in self.GACHA_RATES.keys():
            self.pool[grade] = []

        try:
            cursor.execute("SELECT id, name, grade FROM characters")
            rows = cursor.fetchall()
            
            for row in rows:
                char_id, name, grade_raw = row
                # CSV의 등급 표기(예: Mythic)를 대문자 키(MYTHIC)로 변환
                grade_key = grade_raw.upper().strip()
                
                if grade_key in self.pool:
                    self.pool[grade_key].append({"id": char_id, "name": name, "grade": grade_raw})
                else:
                    # CSV에 오타가 있거나 정의되지 않은 등급인 경우 Common으로 처리 (안전장치)
                    print(f"[Warning] 알 수 없는 등급: {name} ({grade_raw}) -> Common 처리")
                    self.pool["COMMON"].append({"id": char_id, "name": name, "grade": grade_raw})
            
            print(f"[System] 가챠 풀 로드 완료: {sum(len(v) for v in self.pool.values())}명")
            
        except Exception as e:
            print(f"[Error] 가챠 풀 로드 실패: {e}")
        finally:
            conn.close()

    def draw_10(self, user_id="son_01"):
        """10연차 뽑기 실행 및 인벤토리 저장"""
        results = []
        
        # 1. 확률에 따른 뽑기 로직
        grades = list(self.GACHA_RATES.keys())
        weights = list(self.GACHA_RATES.values())

        for _ in range(10):
            # 1단계: 등급 결정 (가중치 뽑기)
            selected_grade = random.choices(grades, weights=weights, k=1)[0]
            
            # 2단계: 해당 등급 내에서 캐릭터 랜덤 선택
            # (만약 해당 등급 캐릭터가 데이터에 없으면 Common에서 뽑음)
            if not self.pool[selected_grade]:
                selected_grade = "COMMON"
            
            char_info = random.choice(self.pool[selected_grade])
            results.append(char_info)

        # 2. 결과 DB 저장 (Inventory)
        self._save_to_inventory(user_id, results)
        
        return results

    def _save_to_inventory(self, user_id, results):
        """뽑은 결과(리스트)를 DB에 저장"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            for char in results:
                # 중복 획득 시: (나중에) 강화 재료로 변환하거나 레벨업 처리 가능
                # 현재는 단순히 목록에 추가 (동일 캐릭터 여러 개 보유 가능 구조)
                cursor.execute('''
                    INSERT INTO inventory (user_id, char_id) 
                    VALUES (?, ?)
                ''', (user_id, char['id']))
            
            conn.commit()
            print(f"[System] {len(results)}개 캐릭터 인벤토리 저장 완료")
        except Exception as e:
            print(f"[Error] 인벤토리 저장 실패: {e}")
        finally:
            conn.close()

# 테스트 코드
if __name__ == "__main__":
    gm = GachaManager()
    print("--- 10연차 테스트 ---")
    res = gm.draw_10()
    for i, r in enumerate(res):
        print(f"{i+1}. [{r['grade']}] {r['name']}")