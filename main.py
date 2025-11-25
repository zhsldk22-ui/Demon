import pygame, sys, sqlite3
from config import *
from database import init_db
from ui.components import Button, InputBox
from game_systems.battle import BattleScene
from game_systems.coupon import CouponManager
from game_systems.gacha import GachaManager

def get_user_tickets():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT tickets FROM users WHERE user_id='son_01'")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0

def add_tickets(amount):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET tickets = tickets + ? WHERE user_id='son_01'", (amount,))
    conn.commit(); conn.close()

def toggle_selection(inv_id):
    """덱 선택/해제 토글 (최대 2명)"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # 1. 현재 내 상태 확인
    cur.execute("SELECT is_selected FROM inventory WHERE id=?", (inv_id,))
    row = cur.fetchone()
    if not row: return
    current_status = row[0]

    if current_status == 1:
        # 해제는 언제나 가능
        cur.execute("UPDATE inventory SET is_selected=0 WHERE id=?", (inv_id,))
    else:
        # 선택은 최대 2명 제한 확인
        cur.execute("SELECT COUNT(*) FROM inventory WHERE user_id='son_01' AND is_selected=1")
        count = cur.fetchone()[0]
        if count < 2:
            cur.execute("UPDATE inventory SET is_selected=1 WHERE id=?", (inv_id,))
    
    conn.commit(); conn.close()

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    init_db()

    game_state = "LOBBY"
    title_font = pygame.font.SysFont("malgungothic", 50, bold=True)
    info_font = pygame.font.SysFont("malgungothic", 24)

    btn_start = Button(SCREEN_WIDTH//2 - 100, 300, 200, 50, "전투 시작", "START_BATTLE")
    btn_deck = Button(SCREEN_WIDTH//2 - 100, 370, 200, 50, "내 덱 보기", "VIEW_DECK")
    btn_gacha = Button(SCREEN_WIDTH//2 - 100, 440, 200, 50, "소환 상점 (10장)", "GACHA")
    btn_coupon = Button(SCREEN_WIDTH//2 - 100, 510, 200, 50, "비밀 쿠폰 입력", "OPEN_COUPON")
    lobby_buttons = [btn_start, btn_deck, btn_gacha, btn_coupon]

    battle_scene = None
    coupon_manager = CouponManager()
    gacha_manager = GachaManager()
    input_box = InputBox(SCREEN_WIDTH//2 - 150, 300, 300, 50)
    coupon_message, system_message = "", ""
    gacha_results, my_deck = [], []

    while True:
        mouse_pos = pygame.mouse.get_pos()
        tickets = get_user_tickets() if game_state == "LOBBY" else 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()

            if game_state == "LOBBY" and event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for btn in lobby_buttons:
                        if btn.is_clicked(mouse_pos):
                            if btn.action_code == "START_BATTLE":
                                game_state = "BATTLE"
                                battle_scene = BattleScene(screen)
                            elif btn.action_code == "VIEW_DECK":
                                game_state = "DECK_VIEW"
                                # 덱 데이터 로드 (inventory ID 포함)
                                conn = sqlite3.connect(DB_PATH)
                                cur = conn.cursor()
                                cur.execute("SELECT i.id, c.name, c.grade, c.hp, c.atk, i.is_selected FROM inventory i JOIN characters c ON i.char_id = c.id WHERE i.user_id='son_01'")
                                my_deck = cur.fetchall()
                                conn.close()
                            elif btn.action_code == "GACHA":
                                if tickets >= 10:
                                    add_tickets(-10)
                                    gacha_results = gacha_manager.draw_10()
                                    game_state = "GACHA_RESULT"
                                    system_message = "소환 완료!"
                                else: system_message = "티켓 부족!"
                            elif btn.action_code == "OPEN_COUPON":
                                game_state = "COUPON_POPUP"
                                input_box.text = ""; input_box.active = True

            elif game_state == "COUPON_POPUP":
                res = input_box.handle_event(event)
                if res: 
                    suc, msg = coupon_manager.redeem_coupon(res)
                    coupon_message = msg
                    if suc: input_box.text = ""
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: game_state = "LOBBY"

            elif game_state == "DECK_VIEW":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    game_state = "LOBBY"
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # 클릭하여 선택 토글
                    y_off = 120
                    for i, char in enumerate(my_deck):
                        x_pos = 100 if i % 2 == 0 else 600
                        if i % 2 == 0 and i > 0: y_off += 40
                        if y_off > SCREEN_HEIGHT - 50: break
                        
                        rect = pygame.Rect(x_pos, y_off, 400, 30)
                        if rect.collidepoint(event.pos):
                            toggle_selection(char[0]) # char[0] is inventory id
                            # 리스트 새로고침
                            conn = sqlite3.connect(DB_PATH)
                            cur = conn.cursor()
                            cur.execute("SELECT i.id, c.name, c.grade, c.hp, c.atk, i.is_selected FROM inventory i JOIN characters c ON i.char_id = c.id WHERE i.user_id='son_01'")
                            my_deck = cur.fetchall()
                            conn.close()
                            break

            elif game_state == "GACHA_RESULT":
                if event.type == pygame.MOUSEBUTTONDOWN or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    game_state = "LOBBY"

            elif game_state == "BATTLE" and battle_scene:
                if battle_scene.battle_state in ["VICTORY", "DEFEAT"]:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if battle_scene.battle_state == "DEFEAT" and battle_scene.mode == "TUTORIAL":
                            add_tickets(10); system_message = "튜토리얼 보상 지급!"
                        if battle_scene.battle_state == "DEFEAT":
                            game_state = "LOBBY"; battle_scene = None
                
                if battle_scene: battle_scene.handle_event(event)

        screen.fill(BLACK)
        
        if game_state == "LOBBY":
            screen.blit(title_font.render("DGFS: 귀멸의 로그라이크", True, WHITE), (SCREEN_WIDTH//2 - 250, 100))
            screen.blit(info_font.render(f"티켓: {tickets}", True, (255, 255, 0)), (SCREEN_WIDTH - 150, 20))
            if system_message: screen.blit(info_font.render(system_message, True, GREEN), (SCREEN_WIDTH//2 - 100, 200))
            for btn in lobby_buttons: btn.check_hover(mouse_pos); btn.draw(screen)

        elif game_state == "DECK_VIEW":
            screen.fill((20, 30, 40))
            screen.blit(title_font.render("캐릭터 선택 (최대 2명)", True, WHITE), (50, 50))
            y_off = 120
            for i, char in enumerate(my_deck):
                # char: id, name, grade, hp, atk, is_selected
                x_pos = 100 if i % 2 == 0 else 600
                if i % 2 == 0 and i > 0: y_off += 40
                if y_off > SCREEN_HEIGHT - 50: break 
                
                color = GREEN if char[5] == 1 else WHITE
                txt = f"[{char[2]}] {char[1]} (HP:{char[3]} ATK:{char[4]})"
                surf = info_font.render(txt, True, color)
                screen.blit(surf, (x_pos, y_off))
                
                if char[5] == 1: # 선택됨 표시
                    pygame.draw.rect(screen, GREEN, (x_pos-5, y_off-2, 410, 30), 2)

            screen.blit(info_font.render("[ESC] 나가기 / 클릭하여 선택", True, GRAY), (SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT - 50))

        elif game_state == "GACHA_RESULT":
            screen.fill((20, 20, 40))
            screen.blit(title_font.render("소환 결과!", True, (255, 215, 0)), (SCREEN_WIDTH//2 - 100, 50))
            for idx, char in enumerate(gacha_results):
                col, row = idx % 2, idx // 2
                c = WHITE
                if char['grade'] in ['LEGEND', 'MYTHIC']: c = (255, 0, 255)
                elif char['grade'] == 'SPECIAL': c = (0, 255, 255)
                screen.blit(info_font.render(f"[{char['grade']}] {char['name']}", True, c), (300 + col * 400, 150 + row * 50))
            screen.blit(info_font.render("클릭하여 나가기", True, GRAY), (SCREEN_WIDTH//2 - 150, 650))

        elif game_state == "COUPON_POPUP":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); overlay.set_alpha(180); overlay.fill(BLACK); screen.blit(overlay, (0,0))
            pygame.draw.rect(screen, (50,50,50), (SCREEN_WIDTH//2-200, 200, 400, 300), border_radius=20)
            pygame.draw.rect(screen, WHITE, (SCREEN_WIDTH//2-200, 200, 400, 300), 2, border_radius=20)
            screen.blit(info_font.render(coupon_message, True, (255,255,0)), (SCREEN_WIDTH//2 - 100, 250))
            input_box.update(); input_box.draw(screen)
            screen.blit(info_font.render("[ESC] 나가기", True, GRAY), (SCREEN_WIDTH//2 - 60, 450))

        elif game_state == "BATTLE" and battle_scene:
            battle_scene.update(); battle_scene.draw()

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__": main()