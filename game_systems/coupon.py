import pygame
import sqlite3
from config import (DB_PATH, DEFAULT_USER_ID, COUPON_MIN_LENGTH, COUPON_SENDER_LENGTH, 
                    COUPON_DATE_LENGTH, COUPON_REWARDS, COUPON_VALID_SENDERS)

class CouponManager:
    def __init__(self):
        pass

    def _parse_and_validate_code(self, code):
        """[리팩토링] 쿠폰 코드의 형식과 구조를 파싱하고 검증합니다."""
        code = code.upper().strip() # 대문자 변환, 공백 제거
        
        if len(code) < COUPON_MIN_LENGTH:
            return None, "코드가 너무 짧습니다."

        sender = code[:COUPON_SENDER_LENGTH]
        date_id = code[COUPON_SENDER_LENGTH : COUPON_SENDER_LENGTH + COUPON_DATE_LENGTH]
        grade = code[-1]    # N, P, S

        if sender not in COUPON_VALID_SENDERS:
            return None, f"유효하지 않은 코드입니다. ({'/'.join(COUPON_VALID_SENDERS)})"

        if grade not in COUPON_REWARDS:
            return None, f"등급 코드가 잘못되었습니다. ({'/'.join(COUPON_REWARDS.keys())})"
        
        reward_tickets = COUPON_REWARDS[grade]
        parsed_info = {'sender': sender, 'date_id': date_id, 'reward': reward_tickets}
        return parsed_info, "코드 형식 확인 완료"

    def _process_db_transaction(self, date_id, reward_tickets, user_id):
        """[리팩토링] DB 관련 작업을 트랜잭션으로 처리합니다."""
        try:
            # [리팩토링] with 구문을 사용하여 DB 연결을 안전하게 관리합니다.
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM used_coupons WHERE coupon_id=?", (date_id,))
                if cursor.fetchone():
                    return False, "이미 사용된 날짜의 쿠폰입니다."

                # [리팩토링] user_id를 매개변수로 받도록 수정
                cursor.execute("UPDATE users SET tickets = tickets + ? WHERE user_id=?", (reward_tickets, user_id))
                cursor.execute("INSERT INTO used_coupons (coupon_id) VALUES (?)", (date_id,))
                conn.commit()
            return True, "보상 지급 완료!"
        except sqlite3.Error as e:
            print(f"[DB Error] 쿠폰 처리 중 오류 발생: {e}")
            return False, "데이터베이스 오류가 발생했습니다."

    def redeem_coupon(self, code, user_id=DEFAULT_USER_ID):
        """[리팩토링] 쿠폰 코드 검증 및 보상 지급 과정을 총괄합니다."""
        # 1. 코드 형식 검증
        parsed_info, message = self._parse_and_validate_code(code)
        if not parsed_info:
            return False, message

        # 2. DB 처리 (중복 확인 및 보상 지급)
        success, db_message = self._process_db_transaction(parsed_info['date_id'], parsed_info['reward'], user_id)
        if not success:
            return False, db_message

        # 3. 최종 성공 메시지 반환
        sender_name = "아빠" if parsed_info['sender'] == "DAD" else "엄마"
        reward_amount = parsed_info['reward']
        return True, f"{sender_name}의 선물! 뽑기권 {reward_amount}장 획득!"