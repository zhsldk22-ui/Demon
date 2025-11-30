import pygame

class BaseScene:
    """
    모든 Scene 클래스의 부모 클래스 (공통 업무 매뉴얼).
    모든 직원은 아래의 기본 업무 능력을 갖추어야 합니다.
    """
    def __init__(self):
        self.next_scene_name = None

    def enter(self):
        """이 씬으로 전환될 때 한 번 호출됩니다."""
        pass

    def handle_events(self, events, mouse_pos):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError

    def draw(self, screen):
        raise NotImplementedError