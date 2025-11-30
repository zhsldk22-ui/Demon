import pygame
from config import RED

class FloatingText:
    def __init__(self, x, y, text, color, duration=60, speed=-1):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.duration = duration
        self.speed = speed
        self.alpha = 255
        self.font = pygame.font.SysFont("malgungothic", 36)

    def update(self):
        self.y += self.speed
        self.duration -= 1
        if self.duration < 20:
            self.alpha = max(0, self.alpha - 15)

    def draw(self, surface):
        text_surface = self.font.render(self.text, True, self.color)
        text_surface.set_alpha(self.alpha)
        surface.blit(text_surface, (self.x, self.y))

class HitEffect:
    """[New] 피격/타격 시 나타나는 사각형 이펙트"""
    def __init__(self, rect, duration=15):
        self.rect = rect
        self.duration = duration
        self.alpha = 255
        self.color = RED

    def update(self):
        self.duration -= 1
        # 사라지기 직전에 빠르게 fade-out
        if self.duration < 10:
            self.alpha = max(0, self.alpha - 25)

    def draw(self, surface):
        if self.alpha > 0:
            # 알파 값을 적용하기 위해 별도의 Surface에 그림
            effect_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            effect_surface.fill((self.color[0], self.color[1], self.color[2], self.alpha))
            surface.blit(effect_surface, self.rect.topleft)

class VFXManager:
    """[Refactored] 모든 시각 효과(텍스트, 도형 등)를 관리"""
    def __init__(self):
        self.effects = []

    def clear(self):
        self.effects = []

    def add_text(self, x, y, text, color=(255, 255, 255)):
        self.effects.append(FloatingText(x, y, text, color))

    def add_hit_effect(self, rect):
        self.effects.append(HitEffect(rect.copy()))

    def update(self):
        self.effects = [effect for effect in self.effects if effect.duration > 0]
        for effect in self.effects:
            effect.update()

    def draw(self, surface):
        for effect in self.effects:
            effect.draw(surface)
