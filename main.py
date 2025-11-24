import pygame
import sys
from config import *
from database import init_db
from ui.components import Button, InputBox
from game_systems.battle import BattleScene
from game_systems.coupon import CouponManager

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    
    init_db() # DB 초기화

    # --- 상태 관리 ---
    game_state = "LOBBY" # LOBBY, BATTLE, COUPON_POPUP
    
    # --- 로비 UI ---
    title_font = pygame.font.SysFont("malgungothic", 50, bold=True)
    
    # 버튼들
    btn_start = Button(SCREEN_WIDTH//2 - 100, 350, 200, 60, "전투 시작", "START_BATTLE")
    btn_deck = Button(SCREEN_WIDTH//2 - 100, 430, 200, 60, "내 덱 보기", "VIEW_DECK")
    btn_coupon = Button(SCREEN_WIDTH//2 - 100, 510, 200, 60, "비밀 쿠폰 입력", "OPEN_COUPON") # 추가됨
    
    lobby_buttons = [btn_start, btn_deck, btn_coupon]

    # --- 모듈 ---
    battle_scene = None
    coupon_manager = CouponManager()
    
    # 쿠폰 입력 UI
    input_box = InputBox(SCREEN_WIDTH//2 - 150, 300, 300, 50)
    coupon_message = "" # 결과 메시지 출력용

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # --- 쿠폰 입력창 상태일 때 ---
            if game_state == "COUPON_POPUP":
                # 1. 입력창 이벤트 처리 (글자 입력 등)
                result_text = input_box.handle_event(event)
                
                # 2. 엔터키 입력 시 쿠폰 검증 시도
                if result_text: 
                    success, msg = coupon_manager.redeem_coupon(result_text)
                    coupon_message = msg
                    if success:
                        # 성공하면 입력창 비우기
                        input_box.text = ""

                # 3. 바깥 클릭 시 팝업 닫기 (ESC 키나 X버튼 추가 가능)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    game_state = "LOBBY"
                    coupon_message = ""

            # --- 로비 상태일 때 ---
            elif game_state == "LOBBY":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        for btn in lobby_buttons:
                            if btn.is_clicked(mouse_pos):
                                if btn.action_code == "START_BATTLE":
                                    game_state = "BATTLE"
                                    battle_scene = BattleScene(screen)
                                
                                elif btn.action_code == "OPEN_COUPON":
                                    game_state = "COUPON_POPUP"
                                    input_box.text = ""
                                    input_box.active = True
                                    coupon_message = "쿠폰 코드를 입력하고 엔터를 누르세요."

            # --- 전투 상태일 때 ---
            elif game_state == "BATTLE":
                if battle_scene:
                    battle_scene.handle_event(event)

        # --- 화면 그리기 ---
        screen.fill(BLACK)

        if game_state == "LOBBY":
            title_surf = title_font.render("DGFS: 귀멸의 로그라이크", True, WHITE)
            screen.blit(title_surf, (SCREEN_WIDTH//2 - 250, 150))
            
            for btn in lobby_buttons:
                btn.check_hover(mouse_pos)
                btn.draw(screen)

        elif game_state == "COUPON_POPUP":
            # 로비 배경을 어둡게 깔고 그 위에 팝업
            title_surf = title_font.render("DGFS: 귀멸의 로그라이크", True, WHITE)
            screen.blit(title_surf, (SCREEN_WIDTH//2 - 250, 150))
            
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(180)
            overlay.fill(BLACK)
            screen.blit(overlay, (0,0))
            
            # 팝업 박스
            popup_rect = pygame.Rect(SCREEN_WIDTH//2 - 200, 200, 400, 300)
            pygame.draw.rect(screen, (50, 50, 50), popup_rect, border_radius=20)
            pygame.draw.rect(screen, WHITE, popup_rect, 2, border_radius=20)
            
            # 안내 메시지
            font_msg = pygame.font.SysFont("malgungothic", 20)
            msg_surf = font_msg.render(coupon_message, True, (255, 255, 0)) # 노란색
            msg_rect = msg_surf.get_rect(center=(SCREEN_WIDTH//2, 250))
            screen.blit(msg_surf, msg_rect)
            
            # 입력창 그리기
            input_box.update()
            input_box.draw(screen)
            
            # 닫기 안내
            close_surf = font_msg.render("[ESC] 키를 눌러 나가기", True, GRAY)
            screen.blit(close_surf, (SCREEN_WIDTH//2 - 100, 450))

        elif game_state == "BATTLE":
            if battle_scene:
                battle_scene.update()
                battle_scene.draw()

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()