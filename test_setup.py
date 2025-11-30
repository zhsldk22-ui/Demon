import sqlite3
from config import DB_PATH, DEFAULT_USER_ID
from database import init_db # DB 초기화 함수 임포트

def run_test_setup():
    """테스트를 위한 DB 상태를 조작하고, 필요한 경우 DB를 초기화합니다."""
    # 1. DB 초기화 (테이블이 없으면 생성)
    print("--- DB 초기화 확인 ---")
    if init_db():
        print("[OK] DB 초기화 성공 또는 이미 존재함.")
    else:
        print("[FATAL] DB 초기화 실패. 스크립트를 중단합니다.")
        return
        
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            print("\n--- 테스트 설정 시작 ---")
            
            # 2. 티켓 999개 지급
            cursor.execute("UPDATE users SET tickets = 999 WHERE user_id = ?", (DEFAULT_USER_ID,))
            print(f"[OK] {DEFAULT_USER_ID}에게 티켓 999개 지급 완료.")

            # 3. 특정 COMMON/MYTHIC 캐릭터 강제 소유
            common_char_id = 1
            mythic_char_id = 18
            
            cursor.execute("INSERT OR IGNORE INTO inventory (user_id, char_id) VALUES (?, ?)", (DEFAULT_USER_ID, common_char_id))
            cursor.execute("INSERT OR IGNORE INTO inventory (user_id, char_id) VALUES (?, ?)", (DEFAULT_USER_ID, mythic_char_id))
            
            cursor.execute("""
                UPDATE inventory
                SET total_max_hp = (SELECT hp FROM characters WHERE id = inventory.char_id),
                    total_atk = (SELECT atk FROM characters WHERE id = inventory.char_id),
                    total_agi = (SELECT agi FROM characters WHERE id = inventory.char_id)
                WHERE user_id = ? AND char_id IN (?, ?) AND total_max_hp IS NULL
            """, (DEFAULT_USER_ID, common_char_id, mythic_char_id))
            print(f"[OK] COMMON(ID:{common_char_id}), MYTHIC(ID:{mythic_char_id}) 캐릭터 강제 소유 완료 및 스탯 초기화.")

            # 4. COMMON 캐릭터(Tanjiro) 레벨 20으로 설정
            cursor.execute("UPDATE inventory SET level = 20 WHERE user_id = ? AND char_id = ?", (DEFAULT_USER_ID, common_char_id))
            print(f"[OK] COMMON(ID:{common_char_id}) 캐릭터 레벨 20으로 설정 완료.")
            
            # 5. MYTHIC 캐릭터(Seoho) 레벨업 직전 상태로 설정
            cursor.execute("UPDATE inventory SET exp = 90 WHERE user_id = ? AND char_id = ?", (DEFAULT_USER_ID, mythic_char_id))
            print(f"[OK] MYTHIC(ID:{mythic_char_id}) 캐릭터 경험치 90으로 설정 (레벨업 직전).")
            
            conn.commit()
            print("\n--- 테스트 설정 완료 ---")

    except sqlite3.Error as e:
        print(f"\n--- 테스트 설정 실패 ---")
        print(f"[ERROR] DB 작업 중 오류 발생: {e}")

if __name__ == "__main__":
    run_test_setup()