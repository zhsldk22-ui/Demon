import pygame
import os
import random
from config import *
from game_systems.fighter_data import FighterData

class FighterView(pygame.sprite.Sprite):
    """
    [View]
    FighterData를 기반으로 캐릭터의 시각적 표현과 애니메이션을 담당합니다.
    - HP/MP 바 그리기
    - 캐릭터 이미지 렌더링
    - 피격/사망 애니메이션 처리
    """
    def __init__(self, fighter_data: FighterData):
        super().__init__()
        self.data = fighter_data
        
        # Pygame 관련 속성
        self.image = None
        self.rect = pygame.Rect(self.data.x, self.data.y, 100, 100)
        self.hud_font = pygame.font.Font(None, 20)
        
        # 애니메이션 상태
        self.offset_x = 0
        self.action_timer = 0
        self.dying = False
        self.alpha = 255
        
        self._load_image(self.data.image_path)

    def _load_image(self, image_path):
        if not image_path: return
        full_path = os.path.join(ASSETS_DIR, "images", image_path)
        if not os.path.exists(full_path):
            print(f"[Warning] 이미지 파일을 찾을 수 없습니다: {full_path}")
            self.image = None
            return
        try:
            loaded_img = pygame.image.load(full_path).convert_alpha()
            self.image = pygame.transform.smoothscale(loaded_img, (100, 120))
        except pygame.error as e:
            print(f"[Error] 이미지 로드 실패: {self.data.name} ({full_path}) - {e}")
            self.image = None

    def take_damage_animation(self):
        """피격 시 흔들리는 애니메이션을 재생합니다."""
        self.offset_x = random.randint(-10, 10)
        self.action_timer = 15

    def attack_animation(self):
        """공격 시 앞으로 나아가는 애니메이션을 재생합니다."""
        direction = -1 if self.data.is_enemy else 1
        self.offset_x = 50 * direction
        self.action_timer = 20

    def update(self, dt):
        # 애니메이션 타이머 업데이트
        if self.action_timer > 0:
            self.action_timer -= 1
            if self.action_timer == 0:
                self.offset_x = 0
        
        # 사망 애니메이션 처리
        if not self.data.is_alive and not self.dying:
            self.dying = True
        
        if self.dying:
            self.alpha -= 5
            if self.alpha < 0:
                self.alpha = 0
                # self.kill() # Sprite Group에서 제거하는 것은 BattleView가 담당

    def draw(self, screen):
        if self.alpha == 0: return
        
        draw_rect = self.rect.copy()
        draw_rect.x += self.offset_x
        
        # 캐릭터 그리기
        if self.image:
            temp_image = self.image.copy()
            temp_image.set_alpha(self.alpha)
            screen.blit(temp_image, draw_rect)
        else: # 이미지가 없을 경우 사각형으로 대체
            color = RED if self.data.is_enemy else BLUE
            pygame.draw.rect(screen, color, draw_rect)
            font = pygame.font.SysFont("malgungothic", 12)
            screen.blit(font.render(self.data.name, True, WHITE), (draw_rect.x, draw_rect.y + 40))

        # 상태 바 그리기
        bar_width = 100
        hp_ratio = self.data.hp / self.data.max_hp if self.data.max_hp > 0 else 0
        hp_color = GREEN if hp_ratio > 0.5 else (RED if hp_ratio < 0.2 else (255, 255, 0))
        pygame.draw.rect(screen, GRAY, (draw_rect.x, draw_rect.y - 15, bar_width, 8))
        pygame.draw.rect(screen, hp_color, (draw_rect.x, draw_rect.y - 15, int(bar_width * hp_ratio), 8))
        pygame.draw.rect(screen, BLACK, (draw_rect.x, draw_rect.y - 15, bar_width, 8), 1)
        mp_ratio = self.data.mp / self.data.max_mp if self.data.max_mp > 0 else 0
        pygame.draw.rect(screen, GRAY, (draw_rect.x, draw_rect.y - 6, bar_width, 4))
        pygame.draw.rect(screen, (0, 100, 255), (draw_rect.x, draw_rect.y - 6, int(bar_width * mp_ratio), 4))
        sp_ratio = self.data.sp / self.data.max_sp if self.data.max_sp > 0 else 0
        sp_color = (255, 165, 0) if self.data.sp < self.data.max_sp else (255, 215, 0)
        pygame.draw.rect(screen, GRAY, (draw_rect.x, draw_rect.y - 2, bar_width, 4))
        pygame.draw.rect(screen, sp_color, (draw_rect.x, draw_rect.y - 2, int(bar_width * sp_ratio), 4))