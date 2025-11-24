import pygame
import sys
import sqlite3
from config import *
from database import init_db
from ui.components import Button, InputBox
from game_systems.battle import BattleScene
from game_systems.coupon import CouponManager
from game_systems.gacha import GachaManager

def get_user_tickets():
    """DB에서 현재 티켓 수 조회"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT tickets FROM users WHERE user_id='son_01'")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def add_tickets(amount):
    """티켓 지급"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET tickets = tickets + ? WHERE user_id='son_01'", (amount,))
    conn.commit()
    conn.close()

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    
    init_db() # DB 초기화

    # --- 상태 관리 ---
    game_state = "LOBBY" # LOBBY, BATTLE, COUPON_POPUP, GACHA_RESULT
    
    # --- 로비 UI ---
    title_font = pygame.font.SysFont("malgungothic", 50, bold=True)
    info_font = pygame.font.SysFont("malgungothic", 24)
    
    # 버튼들
    btn_start = Button(SCREEN_WIDTH//2 - 100, 300, 200, 50, "전투 시작", "START_BATTLE")
    btn_deck = Button(SCREEN_WIDTH//2 - 100, 370, 200, 50, "내 덱 보기", "VIEW_DECK")
    btn_gacha = Button(SCREEN_WIDTH//2 - 100, 440, 200, 50, "소환 상점 (10장)", "GACHA")
    btn_coupon = Button(SCREEN_WIDTH//2 - 100, 510, 200, 50, "비밀 쿠폰 입력", "OPEN_COUPON")
    
    lobby_buttons = [btn_start, btn_deck, btn_gacha, btn_coupon]

    # --- 모듈 ---
    battle_scene = None
    coupon_manager = CouponManager()
    gacha_manager = GachaManager()
    
    # UI 상태 변수
    input_box = InputBox(SCREEN_WIDTH//2 - 150, 300, 300, 50)
    coupon_message = ""
    gacha_results = [] 
    system_message = "" 

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        current_tickets = 0
        if game_state == "LOBBY":
            current_tickets = get_user_tickets()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # --- 쿠폰 팝업 ---
            if game_state == "COUPON_POPUP":
                result_text = input_box.handle_event(event)
                if result_text: 
                    success, msg = coupon_manager.redeem_coupon(result_text)
                    coupon_message = msg
                    if success: input_box.text = ""
                
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    game_state = "LOBBY"
                    coupon_message = ""

            # --- 가챠 결과 화면 ---
            elif game_state == "GACHA_RESULT":
                if event.type == pygame.MOUSEBUTTONDOWN or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    game_state = "LOBBY"

            # --- 로비 ---
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
                                
                                elif btn.action_code == "GACHA":
                                    if current_tickets >= 10:
                                        add_tickets(-10)
                                        gacha_results = gacha_manager.draw_10()
                                        game_state = "GACHA_RESULT"
                                        system_message = "소환 완료! 인벤토리를 확인하세요."
                                    else:
                                        system_message = "티켓이 부족합니다! (10장 필요)"

            # --- 전투 ---
            elif game_state == "BATTLE":
                if battle_scene:
                    # 전투 종료(승리/패배) 후 클릭 처리
                    if battle_scene.battle_state in ["VICTORY", "DEFEAT"]:
                        if event.type == pygame.MOUSEBUTTONDOWN:
                            
                            # 튜토리얼 패배 보상
                            if battle_scene.battle_state == "DEFEAT" and battle_scene.mode == "TUTORIAL":
                                add_tickets(10)
                                system_message = "튜토리얼 종료! 엄마 아빠의 선물: 뽑기권 10장"
                                print("[System] 튜토리얼 보상 지급 완료 (Ticket +10)")
                            
                            # 패배 시 바로 로비 복귀
                            if battle_scene.battle_state == "DEFEAT":
                                game_state = "LOBBY"
                                battle_scene = None
                    
                    # [수정됨] battle_scene이 None이 아닐 때만 이벤트 전달
                    if battle_scene:
                        battle_scene.handle_event(event)

        # --- 화면 그리기 ---
        screen.fill(BLACK)

        if game_state == "LOBBY":
            title_surf = title_font.render("DGFS: 귀멸의 로그라이크", True, WHITE)
            screen.blit(title_surf, (SCREEN_WIDTH//2 - 250, 100))
            
            ticket_surf = info_font.render(f"보유 티켓: {current_tickets}장", True, (255, 255, 0))
            screen.blit(ticket_surf, (SCREEN_WIDTH - 200, 20))
            
            if system_message:
                sys_surf = info_font.render(system_message, True, GREEN)
                sys_rect = sys_surf.get_rect(center=(SCREEN_WIDTH//2, 200))
                screen.blit(sys_surf, sys_rect)
            
            for btn in lobby_buttons:
                btn.check_hover(mouse_pos)
                btn.draw(screen)

        elif game_state == "COUPON_POPUP":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(180)
            overlay.fill(BLACK)
            screen.blit(overlay, (0,0))
            
            popup_rect = pygame.Rect(SCREEN_WIDTH//2 - 200, 200, 400, 300)
            pygame.draw.rect(screen, (50, 50, 50), popup_rect, border_radius=20)
            pygame.draw.rect(screen, WHITE, popup_rect, 2, border_radius=20)
            
            font_msg = pygame.font.SysFont("malgungothic", 20)
            msg_surf = font_msg.render(coupon_message, True, (255, 255, 0))
            msg_rect = msg_surf.get_rect(center=(SCREEN_WIDTH//2, 250))
            screen.blit(msg_surf, msg_rect)
            
            input_box.update()
            input_box.draw(screen)
            
            close_surf = font_msg.render("[ESC] 키를 눌러 나가기", True, GRAY)
            screen.blit(close_surf, (SCREEN_WIDTH//2 - 100, 450))

        elif game_state == "GACHA_RESULT":
            screen.fill((20, 20, 40))
            res_title = title_font.render("소환 결과!", True, (255, 215, 0))
            screen.blit(res_title, (SCREEN_WIDTH//2 - 100, 50))
            
            font_res = pygame.font.SysFont("malgungothic", 24)
            for idx, char in enumerate(gacha_results):
                col = idx % 2
                row = idx // 2
                txt = f"[{char['grade']}] {char['name']}"
                color = WHITE
                if char['grade'] in ['LEGEND', 'MYTHIC']: color = (255, 0, 255)
                elif char['grade'] == 'SPECIAL': color = (0, 255, 255)
                elif char['grade'] == 'RARE': color = (0, 255, 0)
                
                res_surf = font_res.render(txt, True, color)
                screen.blit(res_surf, (300 + col * 400, 150 + row * 50))

            guide_surf = info_font.render("아무 곳이나 클릭하여 돌아가기", True, GRAY)
            screen.blit(guide_surf, (SCREEN_WIDTH//2 - 150, 650))

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