import sqlite3
import pandas as pd
import os
from config import DB_PATH, DATA_DIR

def init_db():
    """DB 테이블 생성 및 CSV 데이터 로드"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("[System] 데이터베이스 연결 성공")

    # 1. Users 테이블 (tickets 컬럼 추가됨)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            gold INTEGER DEFAULT 0,
            gems INTEGER DEFAULT 0,
            tickets INTEGER DEFAULT 0,
            current_floor INTEGER DEFAULT 1
        )
    ''')
    
    # 2. Coupons 테이블 (사용된 쿠폰 기록용 - 신규)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS used_coupons (
            coupon_id TEXT PRIMARY KEY,
            used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 3. Characters (도감)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY,
            name TEXT,
            origin TEXT,
            grade TEXT,
            attribute TEXT,
            hp INTEGER,
            mp INTEGER,
            sp_max INTEGER,
            atk INTEGER,
            def INTEGER,
            agi INTEGER,
            image TEXT
        )
    ''')
    
    # 4. Inventory (보유)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            char_id INTEGER,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            enhancement INTEGER DEFAULT 0,
            FOREIGN KEY(char_id) REFERENCES characters(id)
        )
    ''')

    # 5. Enemies (적)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enemies (
            id INTEGER PRIMARY KEY,
            name TEXT,
            biome TEXT,
            attribute TEXT,
            hp INTEGER,
            atk INTEGER,
            def INTEGER,
            agi INTEGER,
            exp_reward INTEGER,
            image TEXT
        )
    ''')
    
    conn.commit()
    print("[System] 테이블 구조 확인 완료")

    # CSV 데이터 로드
    load_csv_to_db(conn, "characters", "characters.csv")
    load_csv_to_db(conn, "enemies", "enemies.csv")
    
    # 초기 유저 생성
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES ('son_01')")
    conn.commit()
    conn.close()

def load_csv_to_db(conn, table_name, file_name):
    file_path = os.path.join(DATA_DIR, file_name)
    if not os.path.exists(file_path):
        print(f"[Warning] {file_name} 파일을 찾을 수 없습니다.")
        return

    try:
        df = pd.read_csv(file_path)
        conn.execute(f"DELETE FROM {table_name}")
        df.to_sql(table_name, conn, if_exists='append', index=False)
        print(f"[System] {file_name} -> {table_name} 테이블 로드 완료 ({len(df)}건)")
    except Exception as e:
        print(f"[Error] {file_name} 로드 중 오류 발생: {e}")

if __name__ == "__main__":
    init_db()