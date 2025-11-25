import pygame
from config import *

class Button:
    def __init__(self, x, y, width, height, text, action_code, color=None, hover_color=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action_code = action_code
        self.font = pygame.font.SysFont("malgungothic", 24, bold=True)
        self.is_hovered = False
        
        # [수정] 색상 인자 추가
        self.color = color if color else (50, 50, 200)
        self.hover_color = hover_color if hover_color else (100, 100, 255)

    def draw(self, screen):
        # [수정] 인스턴스 색상 사용
        color = self.hover_color if self.is_hovered else self.color
        
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, WHITE, self.rect, 2, border_radius=10)

        text_surf = self.font.render(self.text, True, WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def check_hover(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)

class InputBox:
    """사용자 텍스트 입력을 받는 상자"""
    def __init__(self, x, y, w, h, font_size=32):
        self.rect = pygame.Rect(x, y, w, h)
        self.color_inactive = GRAY
        self.color_active = GREEN
        self.color = self.color_inactive
        self.text = ''
        self.font = pygame.font.SysFont("malgungothic", font_size)
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # 상자를 클릭하면 활성화, 밖을 클릭하면 비활성화
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            self.color = self.color_active if self.active else self.color_inactive
            
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    return self.text # 엔터 치면 텍스트 반환
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    # 글자수 제한 (15자)
                    if len(self.text) < 15:
                        self.text += event.unicode
        return None

    def update(self):
        # 글자 길이에 맞춰 상자 크기 조절 (선택 사항)
        width = max(200, self.font.size(self.text)[0]+10)
        self.rect.w = width

    def draw(self, screen):
        # 텍스트 그리기
        txt_surface = self.font.render(self.text, True, WHITE)
        screen.blit(txt_surface, (self.rect.x+5, self.rect.y+5))
        # 상자 테두리 그리기
        pygame.draw.rect(screen, self.color, self.rect, 2)