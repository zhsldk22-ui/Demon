import pygame
import sys
from config import *
from database import init_db
from ui.components import Button

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    # DB 초기화
    init_db()
    
    # 폰트
    title_font = pygame.font.SysFont("malgungothic", 50, bold=True)

    # --- 버튼 생성 (객체화) ---
    # 화면 중앙 하단에 배치
    btn_start = Button(SCREEN_WIDTH//2 - 100, 400, 200, 60, "전투 시작", "BATTLE")
    btn_deck = Button(SCREEN_WIDTH//2 - 100, 480, 200, 60, "내 덱 보기", "DECK")
    btn_gacha = Button(SCREEN_WIDTH//2 - 100, 560, 200, 60, "뽑기 상점", "GACHA")
    
    buttons = [btn_start, btn_deck, btn_gacha]

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()

        # --- 이벤트 처리 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # 마우스 클릭 이벤트
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # 좌클릭
                    for btn in buttons:
                        if btn.is_clicked(mouse_pos):
                            print(f"[클릭됨] {btn.text} -> 기능: {btn.action_code}")
                            # 여기서 나중에 화면 전환 로직이 들어감

        # --- 그리기 ---
        screen.fill(BLACK) 
        
        # 타이틀
        title_surf = title_font.render("DGFS: 귀멸의 로그라이크", True, WHITE)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH//2, 200))
        screen.blit(title_surf, title_rect)

        # 버튼 그리기 및 호버 체크
        for btn in buttons:
            btn.check_hover(mouse_pos)
            btn.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()