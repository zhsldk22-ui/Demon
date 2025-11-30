import sqlite3
import pandas as pd
import os
from config import DB_PATH, DATA_DIR, DEFAULT_USER_ID, INITIAL_TICKETS

def _run_migrations(cursor):
    """DB 스키마 버전을 확인하고 필요한 마이그레이션을 수행합니다."""
    cursor.execute("PRAGMA user_version")
    db_version = cursor.fetchone()[0]

    if db_version < 1:
        # Version 1: inventory에 total_agi 추가 및 기본값 채우기
        try:
            print("[Migration] DB Version 0 -> 1. 'inventory' 테이블 스키마 변경 시도...")
            cursor.execute("ALTER TABLE inventory ADD COLUMN total_agi INTEGER")
            print("[Migration] 'inventory' 테이블에 'total_agi' 컬럼 추가 완료.")
            
            # characters 테이블의 agi 값으로 inventory.total_agi 초기화
            cursor.execute("""
                UPDATE inventory
                SET total_agi = (SELECT agi FROM characters WHERE id = inventory.char_id)
                WHERE EXISTS (SELECT 1 FROM characters WHERE id = inventory.char_id)
            """)
            print("[Migration] 'inventory.total_agi' 값을 'characters.agi'에서 가져와 초기화 완료.")

            cursor.execute("PRAGMA user_version = 1")
            print("[Migration] DB Version을 1로 업데이트했습니다.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("[Migration] 'total_agi' 컬럼이 이미 존재합니다. 버전만 1로 업데이트합니다.")
                cursor.execute("PRAGMA user_version = 1")
            else:
                print(f"[Migration Error] 스키마 변경 실패: {e}")
                raise e

    if db_version < 2:
        # Version 2: inventory.current_* -> total_* 컬럼명 변경
        try:
            print("[Migration] DB Version 1 -> 2. 'inventory' 테이블 스키마 변경(current_* -> total_*) 시도...")
            
            cursor.execute("PRAGMA table_info(inventory)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'current_max_hp' in columns and 'current_atk' in columns:
                print("[Migration] 기존 'current_max_hp', 'current_atk' 컬럼 확인. 스키마 재구성 및 데이터 이전 시작...")
                
                cursor.execute("ALTER TABLE inventory RENAME TO inventory_old")
                
                # 최신 스키마로 테이블 재생성
                _create_tables(cursor)

                # 데이터 이전 (컬럼명 매핑)
                cursor.execute("""
                    INSERT INTO inventory (
                        id, user_id, char_id, is_selected, level, exp,
                        current_hp, current_mp, current_sp,
                        total_atk, total_max_hp, total_agi,
                        acquired_at
                    )
                    SELECT
                        id, user_id, char_id, is_selected, level, exp,
                        current_hp, current_mp, current_sp,
                        current_atk, current_max_hp, total_agi,
                        acquired_at
                    FROM inventory_old
                """)
                
                cursor.execute("DROP TABLE inventory_old")
                print("[Migration] 스키마 재구성 및 데이터 이전 완료.")
            else:
                print("[Migration] 'total_max_hp', 'total_atk' 컬럼이 이미 적용되었거나, 구버전 컬럼이 없어 마이그레이션을 건너뜁니다.")

            cursor.execute("PRAGMA user_version = 2")
            print("[Migration] DB Version을 2로 업데이트했습니다.")
            
        except sqlite3.Error as e:
            print(f"[Migration Error] V2 스키마 변경 실패: {e}")
            raise e

def _create_tables(cursor):
    """[리팩토링] 테이블 생성 SQL을 별도 함수로 분리"""
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY, gold INTEGER DEFAULT 0,
            gems INTEGER DEFAULT 0, tickets INTEGER DEFAULT 0, 
            current_floor INTEGER DEFAULT 1,
            tutorial_completed INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS used_coupons (
            coupon_id TEXT PRIMARY KEY, used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY, name TEXT, origin TEXT, grade TEXT, attribute TEXT, 
            hp INTEGER, mp INTEGER, atk INTEGER, def INTEGER, agi INTEGER, sp_max INTEGER, 
            description TEXT, image TEXT, sfx_type TEXT, skill_name TEXT, ult_name TEXT
            )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, char_id INTEGER,
            is_selected INTEGER DEFAULT 0, 
            level INTEGER DEFAULT 1, exp INTEGER DEFAULT 0,
            current_hp INTEGER, current_mp INTEGER, current_sp INTEGER,
            total_atk INTEGER, total_max_hp INTEGER, total_agi INTEGER,
            acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(char_id) REFERENCES characters(id),
            UNIQUE(user_id, char_id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS enemies (
            id INTEGER PRIMARY KEY, name TEXT, biome TEXT, tier INTEGER, 
            role TEXT, attribute TEXT, hp INTEGER, atk INTEGER,
            def INTEGER, agi INTEGER, exp_reward INTEGER, image TEXT)''')

def init_db():
    """[수정] DB 초기화 시, 테이블 생성 후 마이그레이션을 실행하도록 순서 변경"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. 테이블이 없다면 우선 생성
        _create_tables(cursor)
        
        # 2. 생성된 테이블 스키마가 최신이 아니면 변경
        _run_migrations(cursor)

        cursor.execute("INSERT OR IGNORE INTO users (user_id, tickets) VALUES (?, ?)", (DEFAULT_USER_ID, INITIAL_TICKETS))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"[Critical Error] DB 초기화 실패: {e}")
        return False
    finally:
        if conn:
            conn.close()

def update_master_data_from_csv():
    """[리팩토링] CSV 데이터를 DB에 로드하고, 성공/실패 여부를 반환"""
    try:
        conn = sqlite3.connect(DB_PATH)
        if not load_csv_to_db(conn, "characters", "characters.csv"):
            return False
        if not load_csv_to_db(conn, "enemies", "enemies.csv"):
            return False
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"[Critical Error] CSV 데이터 로딩 중 DB 오류: {e}")
        return False
    finally:
        if conn:
            conn.close()

def start_new_run(conn, user_id=DEFAULT_USER_ID):
    """[수정] '새로 시작' 시 호출. 영구 스탯은 유지하고 현재 상태(HP, MP 등)만 초기화"""
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET current_floor = 1 WHERE user_id=?", (user_id,))
    # 영구 스탯(total_max_hp, total_atk, total_agi)은 제외하고 초기화
    cursor.execute("""
        UPDATE inventory SET 
            current_hp = NULL, current_mp = NULL, current_sp = NULL
        WHERE user_id=?
    """, (user_id,))
    print("[System] 새로운 등반을 시작합니다. (층 및 캐릭터 현재 상태 초기화)")

def add_tickets(cursor, amount, user_id=DEFAULT_USER_ID):
    """[수정] DB의 티켓 수를 증가/감소시키는 함수. (커서 사용)"""
    cursor.execute("UPDATE users SET tickets = tickets + ? WHERE user_id=?", (amount, user_id))

def get_tickets(user_id=DEFAULT_USER_ID):
    """[신규] 현재 사용자의 보유 티켓 수를 DB에서 조회하여 반환합니다."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT tickets FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def update_character_stats(cursor, inv_id, level, exp, max_hp, atk, agi):
    """[신규] 레벨업 후 영구 스탯(레벨, 경험치, 최대체력, 공격력, 민첩성)을 DB에 저장합니다."""
    cursor.execute("""
        UPDATE inventory 
        SET level = ?, exp = ?, total_max_hp = ?, total_atk = ?, total_agi = ?
        WHERE id = ?
    """, (level, exp, max_hp, atk, agi, inv_id))

def update_character_exp(cursor, inv_id, exp):
    """[수정] 전투, 뽑기 등에서 얻은 경험치만 DB에 저장합니다. (커서 사용)"""
    cursor.execute("UPDATE inventory SET exp = ? WHERE id = ?", (exp, inv_id))

def add_character_to_inventory(cursor, char_id, user_id=DEFAULT_USER_ID):
    """
    [수정] 인벤토리에 캐릭터를 추가하고, 신규/중복 여부와 캐릭터 정보를 반환합니다. (커서 사용)
    - 성공 시 (신규): (True, inv_id, char_name) 반환
    - 실패 시 (중복): (False, inv_id, char_name) 반환
    - 오류 시: (None, None, None) 반환
    """
    try:
        # 먼저 캐릭터의 기본 스탯과 이름을 가져옵니다.
        cursor.execute("SELECT hp, atk, agi, name FROM characters WHERE id=?", (char_id,))
        char_stats = cursor.fetchone()
        if not char_stats:
            print(f"[DB Error] 캐릭터 ID {char_id}를 찾을 수 없습니다.")
            return None, None, None

        base_hp, base_atk, base_agi, char_name = char_stats

        # 인벤토리에 캐릭터 추가 시도
        cursor.execute("""
            INSERT INTO inventory (user_id, char_id, total_max_hp, total_atk, total_agi)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, char_id, base_hp, base_atk, base_agi))
        
        inv_id = cursor.lastrowid
        return True, inv_id, char_name

    except sqlite3.IntegrityError: # UNIQUE 제약조건 위반 (중복)
        # 중복된 경우, 기존 inv_id와 캐릭터 이름을 찾아 반환합니다.
        cursor.execute("SELECT name FROM characters WHERE id=?", (char_id,))
        char_name = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM inventory WHERE user_id=? AND char_id=?", (user_id, char_id))
        inv_id = cursor.fetchone()[0]
        return False, inv_id, char_name
    except Exception as e:
        print(f"[DB Error] 인벤토리 저장 실패: {e}")
        return None, None, None

def get_character_grade_by_id(cursor, char_id):
    """ [신규] 캐릭터 ID로 등급을 조회합니다. (커서 사용) """
    cursor.execute("SELECT grade FROM characters WHERE id=?", (char_id,))
    result = cursor.fetchone()
    return result[0] if result else None

def get_character_details_by_inv_id(inv_id):
    """[신규] inv_id로 캐릭터의 모든 상세 정보를 조회하여 FighterData 생성을 돕습니다."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # battle_data_handler._load_party_data와 거의 동일한 쿼리
        query = """
            SELECT 
                c.name, c.hp as base_hp, c.mp as base_mp, c.sp_max, c.atk as base_atk, c.agi as base_agi,
                c.image, c.description, c.grade, 
                c.sfx_type, c.skill_name, c.ult_name,
                i.id as inv_id, i.level, i.exp,
                i.current_hp, i.current_mp, i.current_sp,
                i.total_atk, i.total_max_hp, i.total_agi
            FROM inventory i JOIN characters c ON i.char_id = c.id
            WHERE i.id = ?
        """
        cursor.execute(query, (inv_id,))
        row = cursor.fetchone()
        return row
    except sqlite3.Error as e:
        print(f"[DB Error] inv_id {inv_id}로 캐릭터 정보 조회 실패: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_character_details_by_inv_id_cursor(cursor, inv_id):
    """[신규] inv_id로 캐릭터의 모든 상세 정보를 조회하여 dict로 반환합니다. (커서 사용)"""
    try:
        query = """
            SELECT 
                c.name, c.hp as base_hp, c.mp as base_mp, c.sp_max, c.atk as base_atk, c.agi as base_agi,
                c.image, c.description, c.grade,
                c.sfx_type, c.skill_name, c.ult_name,
                i.id as inv_id, i.level, i.exp,
                i.current_hp, i.current_mp, i.current_sp,
                i.total_atk, i.total_max_hp, i.total_agi
            FROM inventory i JOIN characters c ON i.char_id = c.id
            WHERE i.id = ?
        """
        cursor.execute(query, (inv_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        # Manually create a dict to simulate sqlite3.Row
        column_names = [description[0] for description in cursor.description]
        return dict(zip(column_names, row))

    except sqlite3.Error as e:
        print(f"[DB Error] inv_id {inv_id}로 캐릭터 정보 조회 실패 (커서 사용): {e}")
        return None

def load_csv_to_db(conn, table_name, file_name):
    """[리팩토링] 단일 CSV 파일을 테이블에 로드하고 성공/실패 여부를 반환"""
    file_path = os.path.join(DATA_DIR, file_name)
    if not os.path.exists(file_path):
        print(f"[Warning] {file_name} 없음")
        return False
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        conn.execute(f"DELETE FROM {table_name}")
        df.to_sql(table_name, conn, if_exists='append', index=False)
        print(f"[System] {file_name} 로드 완료 ({len(df)}건)")
        return True
    except Exception as e:
        print(f"[Error] {file_name} 로드 실패: {e}")
        return False

if __name__ == "__main__":
    init_db()
    update_master_data_from_csv()
