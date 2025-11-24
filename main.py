import pygame
import sys
from config import *
from database import init_db

def main():
    # 1. PyGame 초기화
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    # 2. DB 초기화 (게임 켤 때마다 CSV 새로고침)
    print("=== 게임 데이터를 로딩합니다 ===")
    init_db()
    
    # 폰트 설정 (한글 깨짐 방지, 시스템 폰트 사용)
    font = pygame.font.SysFont("malgungothic", 30) 

    running = True
    while running:
        # --- 이벤트 처리 (Event Handling) ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # --- 화면 그리기 (Rendering) ---
        screen.fill(BLACK) # 배경색
        
        # 텍스트 출력 테스트
        text_surface = font.render("DGFS 프로젝트 시작! (DB 연결됨)", True, WHITE)
        screen.blit(text_surface, (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2))

        # 화면 업데이트
        pygame.display.flip()
        
        # FPS 제한
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
