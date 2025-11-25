import pygame, sys, sqlite3, os
from config import *
from database import init_db
from ui.components import Button, InputBox
from game_systems.coupon import CouponManager
from game_systems.battle import BattleScene, add_tickets
from game_systems.gacha import GachaManager

def get_user_tickets():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT tickets FROM users WHERE user_id='son_01'")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0

def get_current_floor():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT current_floor FROM users WHERE user_id='son_01'")
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] is not None else 1

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

def save_run_state(battle_scene):
    """현재 게임 상태(층, 파티 스탯)를 DB에 저장"""
    if not battle_scene: return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # 1. 현재 층수 저장
    cur.execute("UPDATE users SET current_floor = ? WHERE user_id='son_01'", (battle_scene.floor,))
    # 2. 파티원 스탯 저장
    for p_data in battle_scene.party_data:
        cur.execute("""
            UPDATE inventory SET current_hp=?, current_mp=?, current_sp=?, current_atk=?, current_max_hp=?
            WHERE id=?
        """, (p_data['hp'], p_data['mp'], p_data['sp'], p_data['atk'], p_data['max_hp'], p_data['inv_id']))
    conn.commit(); conn.close()
    print(f"[System] 게임 상태 저장 완료 (Floor: {battle_scene.floor})")

def reset_run_state():
    """게임 진행 상태를 초기화 (1층부터)"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET current_floor = 1 WHERE user_id='son_01'")
    # [수정] 인벤토리를 완전히 비움 (기본 캐릭터 지급은 init_db에서 담당)
    cur.execute("DELETE FROM inventory WHERE user_id='son_01'")

    conn.commit(); conn.close()
    print("[System] 게임 상태 초기화 완료.")

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    init_db()

    game_state = "LOBBY"
    title_font = pygame.font.SysFont("malgungothic", 50, bold=True)
    info_font = pygame.font.SysFont("malgungothic", 24)

    # [추가] 로비 배경 이미지 로드
    lobby_bg_path = os.path.join(ASSETS_DIR, "images", "lobby_background.png") # 파일명을 실제 파일명으로 변경하세요
    lobby_bg_image = pygame.image.load(lobby_bg_path).convert()
    lobby_bg_image = pygame.transform.scale(lobby_bg_image, (SCREEN_WIDTH, SCREEN_HEIGHT))

    # [수정] 버튼 재구성
    btn_new_game = Button(SCREEN_WIDTH//2 - 100, 300, 200, 50, "새로 하기", "NEW_GAME")
    btn_continue = Button(SCREEN_WIDTH//2 - 100, 370, 200, 50, "이어 하기", "CONTINUE")
    btn_deck = Button(SCREEN_WIDTH//2 - 100, 440, 200, 50, "내 덱 보기", "VIEW_DECK")
    btn_gacha_shop = Button(SCREEN_WIDTH//2 - 100, 510, 200, 50, "소환상점", "GACHA_SHOP")
    btn_coupon = Button(SCREEN_WIDTH//2 - 100, 580, 200, 50, "쿠폰입력", "OPEN_COUPON")
    lobby_buttons = [btn_new_game, btn_continue, btn_deck, btn_gacha_shop, btn_coupon]

    battle_scene = None
    coupon_manager = CouponManager()
    gacha_manager = GachaManager()
    gacha_shop_mode = "SELECT" # "SELECT" or "RESULT"
    input_box = InputBox(SCREEN_WIDTH//2 - 150, 300, 300, 50)
    coupon_message, system_message, system_message_timer = "", "", 0
    popup_message, popup_buttons = None, []
    gacha_results, my_deck = [], []
    scroll_offset = 0 # 덱 보기 화면용 스크롤 오프셋

    while True:
        mouse_pos = pygame.mouse.get_pos()
        # [버그 수정] 항상 최신 티켓 수를 가져오도록 수정
        tickets = get_user_tickets()

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()

            if popup_message and event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for btn in popup_buttons:
                        if btn.is_clicked(mouse_pos):
                            if btn.action_code == "CONFIRM_NEW_GAME":
                                reset_run_state()
                                game_state = "BATTLE"
                                battle_scene = BattleScene(screen)
                            popup_message = None # '예', '아니오' 둘 다 팝업은 닫음

            elif game_state == "LOBBY" and event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for btn in lobby_buttons:
                        if btn.is_clicked(mouse_pos):
                            if btn.action_code == "CONTINUE":
                                if get_current_floor() > 1:
                                    game_state = "BATTLE"
                                    battle_scene = BattleScene(screen)
                                else:
                                    system_message, system_message_timer = "저장된 게임이 없습니다!", 120
                            elif btn.action_code == "NEW_GAME":
                                popup_message = "정말 새로 시작하시겠습니까?\n(진행 상황이 모두 초기화됩니다)"
                                popup_buttons = [Button(SCREEN_WIDTH//2 - 170, 400, 150, 50, "예", "CONFIRM_NEW_GAME"), Button(SCREEN_WIDTH//2 + 20, 400, 150, 50, "아니오", "CANCEL")]
                            elif btn.action_code == "VIEW_DECK":
                                game_state = "DECK_VIEW"
                                # 덱 데이터 로드 (inventory ID 포함)
                                conn = sqlite3.connect(DB_PATH)
                                cur = conn.cursor()
                                # [수정] 레어도(등급) 순으로 정렬
                                cur.execute("""
                                    SELECT i.id, c.name, c.grade, c.hp, c.atk, i.is_selected 
                                    FROM inventory i JOIN characters c ON i.char_id = c.id 
                                    WHERE i.user_id='son_01'
                                    ORDER BY CASE UPPER(c.grade)
                                        WHEN 'MYTHIC' THEN 0 WHEN 'LEGEND' THEN 1 WHEN 'SPECIAL' THEN 2
                                        WHEN 'RARE' THEN 3 WHEN 'COMMON' THEN 4
                                        ELSE 5 END
                                """)
                                my_deck = cur.fetchall()
                                conn.close()
                            elif btn.action_code == "GACHA_SHOP":
                                game_state = "GACHA_SHOP"
                            elif btn.action_code == "OPEN_COUPON":
                                game_state = "COUPON_POPUP"
                                input_box.text = ""; input_box.active = True

            elif game_state == "GACHA_SHOP" and event.type == pygame.MOUSEBUTTONDOWN:
                if gacha_shop_mode == "RESULT":
                    gacha_shop_mode = "SELECT" # 결과 화면에서 클릭 시 선택 화면으로
                elif gacha_shop_mode == "SELECT":
                    if event.button == 1:
                        # 여기에 1회, 10회 뽑기 버튼 로직 추가
                        btn_gacha_1 = Button(SCREEN_WIDTH//2 - 220, 550, 200, 50, "1회 소환", "GACHA_1")
                        btn_gacha_10 = Button(SCREEN_WIDTH//2 + 20, 550, 200, 50, "10회 소환", "GACHA_10")
                        btn_back_to_lobby = Button(SCREEN_WIDTH//2 - 100, 620, 200, 50, "로비로 돌아가기", "LOBBY", color=(80,80,80))

                        if btn_gacha_1.is_clicked(mouse_pos):
                            if tickets >= 1: add_tickets(-1); gacha_results = gacha_manager.draw_1(); gacha_shop_mode = "RESULT"
                            else: system_message, system_message_timer = "티켓 부족!", 120
                        elif btn_gacha_10.is_clicked(mouse_pos):
                            if tickets >= 10: add_tickets(-10); gacha_results = gacha_manager.draw_10(); gacha_shop_mode = "RESULT"
                            else: system_message, system_message_timer = "티켓 부족!", 120
                        elif btn_back_to_lobby.is_clicked(mouse_pos):
                            game_state = "LOBBY"

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if game_state == "GACHA_SHOP":
                    if gacha_shop_mode == "RESULT": gacha_shop_mode = "SELECT"
                    else: game_state = "LOBBY"
                elif game_state in ["DECK_VIEW", "COUPON_POPUP"]:
                    game_state = "LOBBY"


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
                    if event.button == 1: # 좌클릭
                        # 클릭하여 선택 토글
                        y_off = 120 - scroll_offset
                        for i, char in enumerate(my_deck):
                            x_pos = 100 if i % 2 == 0 else 700
                            if i > 0 and i % 2 == 0: y_off += 40
                            
                            rect = pygame.Rect(x_pos, y_off, 400, 30)
                            if rect.collidepoint(event.pos):
                                toggle_selection(char[0]) # char[0] is inventory id
                                # 리스트 새로고침
                                conn = sqlite3.connect(DB_PATH)
                                cur = conn.cursor()
                                # [수정] 레어도(등급) 순으로 정렬
                                cur.execute("""
                                    SELECT i.id, c.name, c.grade, c.hp, c.atk, i.is_selected 
                                    FROM inventory i JOIN characters c ON i.char_id = c.id 
                                    WHERE i.user_id='son_01'
                                    ORDER BY CASE UPPER(c.grade)
                                        WHEN 'MYTHIC' THEN 0 WHEN 'LEGEND' THEN 1 WHEN 'SPECIAL' THEN 2
                                        WHEN 'RARE' THEN 3 WHEN 'COMMON' THEN 4
                                        ELSE 5 END
                                """)
                                my_deck = cur.fetchall()
                                conn.close()
                                break
                elif event.type == pygame.MOUSEWHEEL: # 마우스 휠 스크롤
                    scroll_offset -= event.y * 20 # 스크롤 속도
                    # 스크롤 범위 제한
                    max_scroll = max(0, (len(my_deck) + 1) // 2 * 40 - (SCREEN_HEIGHT - 200))
                    if scroll_offset < 0: scroll_offset = 0
                    if scroll_offset > max_scroll: scroll_offset = max_scroll

            elif game_state == "BATTLE" and battle_scene:
                if battle_scene.battle_state in ["VICTORY", "DEFEAT"]:
                    # 패배 시 로비 복귀 (튜토리얼은 보상 지급)
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if battle_scene.battle_state == "DEFEAT":
                            if battle_scene.mode == "TUTORIAL":
                                add_tickets(10); system_message, system_message_timer = "튜토리얼 보상 지급!", 120
                            reset_run_state() # 패배 시 초기화
                            game_state = "LOBBY"
                            battle_scene = None
                
                if battle_scene and event.type == pygame.MOUSEBUTTONDOWN:
                    action = battle_scene.handle_event(event)
                    if action == "SAVE_AND_EXIT":
                        save_run_state(battle_scene)
                        game_state = "LOBBY"
                        battle_scene = None
                        system_message, system_message_timer = "진행 상황이 저장되었습니다.", 120

        screen.fill(BLACK)
        
        if game_state == "LOBBY":
            screen.blit(lobby_bg_image, (0, 0)) # [수정] 배경 이미지 그리기
            screen.blit(info_font.render(f"티켓: {tickets}", True, (255, 255, 0)), (SCREEN_WIDTH - 150, 20))
            
            # '이어하기' 버튼 활성화/비활성화
            btn_continue.color = (50, 50, 200) if get_current_floor() > 1 else (80, 80, 80)

            for btn in lobby_buttons: btn.check_hover(mouse_pos); btn.draw(screen)

        elif game_state == "DECK_VIEW":
            screen.fill((20, 30, 40))
            screen.blit(title_font.render("캐릭터 선택 (최대 2명)", True, WHITE), (50, 50))
            
            # --- 스크롤 가능한 캐릭터 목록 ---
            y_off = 120 - scroll_offset
            for i, char in enumerate(my_deck):
                # char: id, name, grade, hp, atk, is_selected
                x_pos = 100 if i % 2 == 0 else 700
                if i > 0 and i % 2 == 0: y_off += 40
                
                # 화면 밖으로 나가는 항목은 그리지 않음
                if y_off > SCREEN_HEIGHT - 80 or y_off < 100: continue

                color = (100, 255, 100) if char[5] == 1 else WHITE
                txt = f"[{char[2]}] {char[1]} (HP:{char[3]}, ATK:{char[4]})"
                surf = info_font.render(txt, True, color)
                screen.blit(surf, (x_pos, y_off))

            # --- 스크롤바 ---
            total_height = (len(my_deck) + 1) // 2 * 40
            view_height = SCREEN_HEIGHT - 120
            if total_height > view_height:
                bar_height = max(20, view_height * (view_height / total_height))
                bar_y = 120 + (scroll_offset / total_height) * view_height
                pygame.draw.rect(screen, GRAY, (SCREEN_WIDTH - 25, 120, 15, view_height))
                pygame.draw.rect(screen, WHITE, (SCREEN_WIDTH - 25, bar_y, 15, bar_height), border_radius=7)

            screen.blit(info_font.render("[ESC] 나가기 / 클릭하여 선택 / 휠 스크롤", True, GRAY), (SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT - 50))

        elif game_state == "COUPON_POPUP":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); overlay.set_alpha(180); overlay.fill(BLACK); screen.blit(overlay, (0,0))
            pygame.draw.rect(screen, (50,50,50), (SCREEN_WIDTH//2-200, 200, 400, 300), border_radius=20)
            pygame.draw.rect(screen, WHITE, (SCREEN_WIDTH//2-200, 200, 400, 300), 2, border_radius=20)
            # [수정] 안내 문구를 두 줄로 나누어 표시
            guide_lines = ["엄마아빠에게 사랑스러운 짓을 해서", "쿠폰을 받으세요!"]
            for i, line in enumerate(guide_lines):
                guide_surf = info_font.render(line, True, WHITE)
                screen.blit(guide_surf, guide_surf.get_rect(center=(SCREEN_WIDTH//2, 240 + i * 30)))

            if coupon_message: screen.blit(info_font.render(coupon_message, True, (255,255,0)), (SCREEN_WIDTH//2 - 100, 310))
            input_box.update(); input_box.draw(screen)
            screen.blit(info_font.render("[ESC] 나가기", True, GRAY), (SCREEN_WIDTH//2 - 60, 450))

        elif game_state == "GACHA_SHOP":
            screen.fill(BLACK) # TODO: 소환상점 배경 이미지 추가
            
            if gacha_shop_mode == "RESULT":
                screen.blit(title_font.render("소환 결과", True, (255, 215, 0)), (SCREEN_WIDTH//2 - 100, 50))
                if len(gacha_results) == 1: # 1회 뽑기 연출
                    char = gacha_results[0]
                    pygame.draw.rect(screen, GRAY, (SCREEN_WIDTH//2 - 150, 200, 300, 400), border_radius=15)
                    grade_color = {'MYTHIC': (255,0,255), 'LEGEND': (255,215,0), 'SPECIAL': (0,255,255), 'RARE': (100,100,255)}.get(char['grade'].upper(), WHITE)
                    screen.blit(info_font.render(f"[{char['grade']}]", True, grade_color), (SCREEN_WIDTH//2 - 50, 450))
                    screen.blit(info_font.render(char['name'], True, WHITE), (SCREEN_WIDTH//2 - 50, 500))
                else: # 10회 뽑기 연출
                    for idx, char in enumerate(gacha_results):
                        col, row = idx % 5, idx // 5
                        x, y = 140 + col * 200, 200 + row * 250
                        pygame.draw.rect(screen, GRAY, (x, y, 180, 220), border_radius=10)
                        grade_color = {'MYTHIC': (255,0,255), 'LEGEND': (255,215,0), 'SPECIAL': (0,255,255), 'RARE': (100,100,255)}.get(char['grade'].upper(), WHITE)
                        screen.blit(info_font.render(f"[{char['grade']}]", True, grade_color), (x + 10, y + 160))
                        screen.blit(info_font.render(char['name'], True, WHITE), (x + 10, y + 190))
                screen.blit(info_font.render("클릭 또는 ESC를 눌러 돌아가기", True, GRAY), (SCREEN_WIDTH//2 - 150, 650))
            
            elif gacha_shop_mode == "SELECT":
                screen.blit(title_font.render("소환 상점", True, WHITE), (SCREEN_WIDTH//2 - 100, 100))
                screen.blit(info_font.render(f"보유 티켓: {tickets}", True, (255, 255, 0)), (SCREEN_WIDTH - 200, 50))
                btn_gacha_1 = Button(SCREEN_WIDTH//2 - 220, 550, 200, 50, "1회 소환", "GACHA_1")
                btn_gacha_10 = Button(SCREEN_WIDTH//2 + 20, 550, 200, 50, "10회 소환", "GACHA_10")
                btn_back_to_lobby = Button(SCREEN_WIDTH//2 - 100, 620, 200, 50, "로비로 돌아가기", "LOBBY", color=(80,80,80))
                for btn in [btn_gacha_1, btn_gacha_10, btn_back_to_lobby]: btn.check_hover(mouse_pos); btn.draw(screen)

        elif game_state == "BATTLE" and battle_scene:
            battle_scene.update(); battle_scene.draw()

        # [수정] 시스템 메시지 UI
        if system_message_timer > 0:
            system_message_timer -= 1
            overlay = pygame.Surface((800, 60))
            overlay.set_alpha(180); overlay.fill(BLACK)
            screen.blit(overlay, (SCREEN_WIDTH//2 - 400, 20))
            msg_surf = info_font.render(system_message, True, WHITE)
            screen.blit(msg_surf, msg_surf.get_rect(center=(SCREEN_WIDTH//2, 50)))
        else:
            system_message = ""

        # [추가] 팝업 메시지
        if popup_message:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); overlay.set_alpha(200); overlay.fill(BLACK); screen.blit(overlay, (0,0))
            bg_rect = pygame.Rect(SCREEN_WIDTH//2 - 250, 300, 500, 200)
            pygame.draw.rect(screen, (50,50,50), bg_rect, border_radius=15)
            pygame.draw.rect(screen, WHITE, bg_rect, 2, border_radius=15)
            for i, line in enumerate(popup_message.split('\n')):
                msg_surf = info_font.render(line, True, WHITE)
                screen.blit(msg_surf, msg_surf.get_rect(center=(SCREEN_WIDTH//2, 340 + i * 30)))
            for btn in popup_buttons: btn.check_hover(mouse_pos); btn.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__": main()