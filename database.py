import sqlite3
import pandas as pd
import os
from config import DB_PATH, DATA_DIR

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Users
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY, gold INTEGER DEFAULT 0,
            gems INTEGER DEFAULT 0, tickets INTEGER DEFAULT 0,
            current_floor INTEGER DEFAULT 1)''')
    
    # 2. Used Coupons
    cursor.execute('''CREATE TABLE IF NOT EXISTS used_coupons (
            coupon_id TEXT PRIMARY KEY, used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 3. Characters
    cursor.execute("DROP TABLE IF EXISTS characters") 
    cursor.execute('''CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY, name TEXT, origin TEXT, grade TEXT, 
            attribute TEXT, hp INTEGER, mp INTEGER, atk INTEGER, def INTEGER, agi INTEGER,
            sp_max INTEGER, description TEXT,
            skill_name TEXT, skill_description TEXT, 
            skill_mp_cost INTEGER, skill_power INTEGER,
            image TEXT)''')
    
    # 4. Inventory (is_selected 추가!)
    # [버그 수정] 개발 중 스키마 변경을 원활하게 하기 위해 테이블을 매번 재생성 (주의: 데이터 초기화됨)
    cursor.execute("DROP TABLE IF EXISTS inventory")
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, char_id INTEGER,
            is_selected INTEGER DEFAULT 0, 
            level INTEGER DEFAULT 1, exp INTEGER DEFAULT 0,
            current_hp INTEGER, current_mp INTEGER, current_sp INTEGER,
            current_atk INTEGER, current_max_hp INTEGER,
            acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(char_id) REFERENCES characters(id))''')

    # 5. Enemies
    cursor.execute("DROP TABLE IF EXISTS enemies")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enemies (
            id INTEGER PRIMARY KEY, name TEXT, biome TEXT, tier INTEGER, 
            role TEXT, attribute TEXT, hp INTEGER, atk INTEGER,
            def INTEGER, agi INTEGER, exp_reward INTEGER, image TEXT
        )
    ''')

    load_csv_to_db(conn, "characters", "characters.csv")
    load_csv_to_db(conn, "enemies", "enemies.csv")
    cursor.execute("INSERT OR IGNORE INTO users (user_id, tickets) VALUES ('son_01', 0)")

    # [개선] 테스트 편의를 위해 기본 캐릭터 지급 (인벤토리가 비어있을 경우)
    cursor.execute("SELECT COUNT(*) FROM inventory WHERE user_id='son_01'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO inventory (user_id, char_id) VALUES ('son_01', 1)") # 탄지로
        cursor.execute("INSERT INTO inventory (user_id, char_id) VALUES ('son_01', 2)") # 네즈코

    conn.commit()
    conn.close()

def load_csv_to_db(conn, table_name, file_name):
    file_path = os.path.join(DATA_DIR, file_name)
    if not os.path.exists(file_path):
        print(f"[Warning] {file_name} 없음")
        return
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig') 
        conn.execute(f"DELETE FROM {table_name}")
        df.to_sql(table_name, conn, if_exists='append', index=False)
        print(f"[System] {file_name} 로드 완료 ({len(df)}건)")
    except Exception as e:
        print(f"[Error] {file_name} 로드 실패: {e}")

if __name__ == "__main__":
    init_db()