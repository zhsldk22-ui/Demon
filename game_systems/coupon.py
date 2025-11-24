import pygame
import sqlite3
from config import *

class CouponManager:
    def __init__(self):
        pass

    def redeem_coupon(self, code):
        """
        쿠폰 코드 검증 및 보상 지급
        Format: SENDER(3) + DATE(6) + GRADE(1) -> 예: DAD251201N
        """
        code = code.upper().strip() # 대문자 변환, 공백 제거
        
        # 1. 길이 검증 (최소 10자리)
        if len(code) < 10:
            return False, "코드가 너무 짧습니다."

        sender = code[:3]   # DAD or MOM
        date_id = code[3:9] # 251201
        grade = code[-1]    # N, P, S

        # 2. 발신자 확인
        if sender not in ["DAD", "MOM"]:
            return False, "유효하지 않은 코드입니다. (DAD/MOM)"

        # 3. 등급별 보상 설정
        reward_tickets = 0
        if grade == 'N': reward_tickets = 10
        elif grade == 'P': reward_tickets = 20
        elif grade == 'S': reward_tickets = 30
        else:
            return False, "등급 코드가 잘못되었습니다. (N/P/S)"

        # 4. DB 중복 확인 및 지급
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # 이미 사용된 날짜(ID)인지 확인
            cursor.execute("SELECT * FROM used_coupons WHERE coupon_id=?", (date_id,))
            if cursor.fetchone():
                conn.close()
                return False, "이미 사용된 날짜의 쿠폰입니다."

            # 보상 지급 (티켓 추가)
            cursor.execute("UPDATE users SET tickets = tickets + ? WHERE user_id='son_01'", (reward_tickets,))
            
            # 사용 처리 (기록)
            cursor.execute("INSERT INTO used_coupons (coupon_id) VALUES (?)", (date_id,))
            
            conn.commit()
            conn.close()
            
            sender_name = "아빠" if sender == "DAD" else "엄마"
            return True, f"{sender_name}의 선물! 뽑기권 {reward_tickets}장 획득!"
            
        except Exception as e:
            conn.close()
            return False, f"오류 발생: {e}"