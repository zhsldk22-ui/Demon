import pygame
from config import *

class Button:
    def __init__(self, x, y, width, height, text, action_code):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action_code = action_code # 클릭 시 어떤 행동을 할지 구분하는 코드 (예: "START", "GACHA")
        self.font = pygame.font.SysFont("malgungothic", 24, bold=True)
        self.is_hovered = False

    def draw(self, screen):
        # 마우스가 올라가면 색을 밝게, 아니면 어둡게 (인터랙션 효과)
        color = (100, 100, 255) if self.is_hovered else (50, 50, 200)
        
        # 버튼 네모 그리기
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, WHITE, self.rect, 2, border_radius=10) # 테두리

        # 글자 그리기 (중앙 정렬)
        text_surf = self.font.render(self.text, True, WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def check_hover(self, mouse_pos):
        """마우스가 버튼 위에 있는지 확인"""
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, mouse_pos):
        """클릭되었는지 확인"""
        return self.rect.collidepoint(mouse_pos)