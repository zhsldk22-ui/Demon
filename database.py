import sqlite3
import pandas as pd
import os
from config import DB_PATH, DATA_DIR

def init_db():
    """DB 테이블 생성 및 CSV 데이터 로드"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("[System] 데이터베이스 연결 성공")

    # 1. 테이블 생성 (스키마 정의)
    # Users 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            gold INTEGER DEFAULT 0,
            gems INTEGER DEFAULT 0,
            current_floor INTEGER DEFAULT 1
        )
    ''')
    
    # Characters (도감) 테이블
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
            image_path TEXT
        )
    ''')
    
    # Inventory (내 보유 캐릭터) 테이블
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

    # Enemies (적) 테이블
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
            image_path TEXT
        )
    ''')
    
    conn.commit()
    print("[System] 테이블 구조 확인 완료")

    # 2. CSV 데이터 로드 (덮어쓰기)
    load_csv_to_db(conn, "characters", "characters.csv")
    load_csv_to_db(conn, "enemies", "enemies.csv")
    
    # 3. 초기 유저 생성 (테스트용)
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES ('son_01')")
    conn.commit()
    
    conn.close()

def load_csv_to_db(conn, table_name, file_name):
    """CSV 파일을 읽어서 DB에 Insert/Replace 하는 함수"""
    file_path = os.path.join(DATA_DIR, file_name)
    
    if not os.path.exists(file_path):
        print(f"[Warning] {file_name} 파일을 찾을 수 없습니다. 스킵합니다.")
        return

    try:
        # Pandas로 CSV 읽기
        df = pd.read_csv(file_path)
        # DB에 저장 (if_exists='replace'는 테이블을 지우고 다시 만드므로 'append' 사용 권장하나,
        # 초기 개발 단계에서는 데이터 동기화를 위해 데이터를 먼저 비우고 다시 넣는 방식을 씀)
        
        # 기존 데이터 삭제 후 재입력 (ID 충돌 방지)
        conn.execute(f"DELETE FROM {table_name}")
        
        # Pandas의 to_sql 기능 활용
        df.to_sql(table_name, conn, if_exists='append', index=False)
        print(f"[System] {file_name} -> {table_name} 테이블 로드 완료 ({len(df)}건)")
        
    except Exception as e:
        print(f"[Error] {file_name} 로드 중 오류 발생: {e}")

if __name__ == "__main__":
    # 이 파일을 직접 실행하면 DB 초기화 수행
    init_db()
