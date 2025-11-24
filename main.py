import pygame
import sys
from config import *
from database import init_db
from ui.components import Button
from game_systems.battle import BattleScene # 방금 만든 모듈 import

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    
    # DB 초기화
    init_db()

    # --- 게임 상태 관리 변수 ---
    # "LOBBY": 메인 화면, "BATTLE": 전투 화면
    game_state = "LOBBY" 
    
    # --- 로비 UI 요소 ---
    title_font = pygame.font.SysFont("malgungothic", 50, bold=True)
    btn_start = Button(SCREEN_WIDTH//2 - 100, 400, 200, 60, "전투 시작", "START_BATTLE")
    btn_deck = Button(SCREEN_WIDTH//2 - 100, 480, 200, 60, "내 덱 보기", "VIEW_DECK")
    btn_gacha = Button(SCREEN_WIDTH//2 - 100, 560, 200, 60, "뽑기 상점", "GACHA")
    lobby_buttons = [btn_start, btn_deck, btn_gacha]

    # --- 전투 관리자 (초기엔 None) ---
    battle_scene = None

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()

        # 1. 이벤트 처리
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # 클릭 이벤트
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # 좌클릭
                    
                    if game_state == "LOBBY":
                        for btn in lobby_buttons:
                            if btn.is_clicked(mouse_pos):
                                print(f"[로비] {btn.text} 클릭됨")
                                
                                # [전투 시작] 버튼을 누르면 상태 변경
                                if btn.action_code == "START_BATTLE":
                                    game_state = "BATTLE"
                                    battle_scene = BattleScene(screen) # 전투 장면 생성
                                    print(">>> 전투 화면으로 전환합니다.")

                    elif game_state == "BATTLE":
                        # (임시) 전투 중 화면 클릭하면 다시 로비로 도망치기 기능
                        # 나중에는 '전투 종료' 버튼으로 대체
                        # game_state = "LOBBY"
                        pass

        # 2. 화면 그리기 및 업데이트
        if game_state == "LOBBY":
            screen.fill(BLACK)
            
            # 타이틀
            title_surf = title_font.render("DGFS: 귀멸의 로그라이크", True, WHITE)
            title_rect = title_surf.get_rect(center=(SCREEN_WIDTH//2, 200))
            screen.blit(title_surf, title_rect)

            # 버튼
            for btn in lobby_buttons:
                btn.check_hover(mouse_pos)
                btn.draw(screen)

        elif game_state == "BATTLE":
            if battle_scene:
                battle_scene.update() # 로직 계산
                battle_scene.draw()   # 화면 출력
                battle_scene.handle_event(event)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()