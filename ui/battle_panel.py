import pygame
import os
from config import (SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, GRAY, GOLD, RED, BLUE, GREEN, ASSETS_DIR)
from ui.components import Button

# --- Font Helper (Copied from components.py for standalone use) ---
def create_font(size, is_bold=False):
    """지정된 크기와 굵기로 폰트 객체를 생성합니다."""
    font_name = "Maplestory Bold.ttf" if is_bold else "Maplestory Light.ttf"
    font_path = os.path.join(ASSETS_DIR, "fonts", font_name)
    try:
        return pygame.font.Font(font_path, size)
    except pygame.error:
        print(f"Warning: Font '{font_name}' not found. Falling back to default font.")
        return pygame.font.SysFont("malgungothic", size, bold=is_bold)

class BattlePanel:
    """전투 화면 하단의 UI 패널. 3단 구조로 아군, 커맨드, 적군 정보를 표시한다."""
    def __init__(self):
        self.panel_height = int(SCREEN_HEIGHT / 4.5)
        self.rect = pygame.Rect(0, SCREEN_HEIGHT - self.panel_height, SCREEN_WIDTH, self.panel_height)
        
        # 폰트
        self.font_name = create_font(20, is_bold=True) # 이름/레벨 폰트
        self.font_stats = create_font(17, is_bold=True) # 스탯 폰트
        self.font_gauge = create_font(15)             # 게이지 텍스트 폰트
        self.font_command_title = create_font(15)

        # 레이아웃
        self.left_panel_width = SCREEN_WIDTH * 0.35
        self.center_panel_width = SCREEN_WIDTH * 0.3
        self.right_panel_width = SCREEN_WIDTH * 0.35

        # 데이터
        self.player_fighters = []
        self.enemy_fighters = []
        self.active_fighter = None
        self.target_fighter = None

        # 버튼
        self.buttons = self._create_command_buttons()
        self.current_button_index = 0
        if self.buttons:
            self.buttons[self.current_button_index].is_focused = True

    def _create_command_buttons(self):
        buttons = []
        center_x = self.left_panel_width + self.center_panel_width / 2
        button_y = self.rect.y + self.rect.height * 0.35
        button_width, button_height = 100, 45
        spacing = 15
        commands = [("공격", "attack"), ("스킬", "skill"), ("필살", "ultimate")]
        total_width = len(commands) * button_width + (len(commands) - 1) * spacing
        start_x = center_x - total_width / 2
        for i, (text, action) in enumerate(commands):
            x = start_x + i * (button_width + spacing)
            btn = Button(x, button_y, button_width, button_height, text, action)
            buttons.append(btn)
        return buttons

    def update_info(self, player_fighters, enemy_fighters, active_fighter=None, target_fighter=None):
        self.player_fighters = player_fighters
        self.enemy_fighters = enemy_fighters
        self.active_fighter = active_fighter
        self.target_fighter = target_fighter

    def draw(self, screen):
        pygame.draw.rect(screen, (20, 20, 20), self.rect)
        pygame.draw.line(screen, WHITE, (self.rect.left, self.rect.top), (self.rect.right, self.rect.top), 2)

        line_y_end = self.rect.bottom
        line1_x = self.left_panel_width
        line2_x = self.left_panel_width + self.center_panel_width
        pygame.draw.line(screen, (80, 80, 80), (line1_x, self.rect.top), (line1_x, line_y_end), 2)
        pygame.draw.line(screen, (80, 80, 80), (line2_x, self.rect.top), (line2_x, line_y_end), 2)

        self._draw_ally_panel(screen)
        self._draw_center_panel(screen)
        self._draw_right_panel(screen)



    def _draw_gauge_bar(self, screen, x, y, width, height, current_val, max_val, color, text=""):
        """[수정] 게이지 바 헬퍼: 커스텀 텍스트 지원"""
        bg_color = (50, 50, 50)
        pygame.draw.rect(screen, bg_color, (x, y, width, height), border_radius=3)
        ratio = current_val / max_val if max_val > 0 else 0
        fill_width = int(width * ratio)
        pygame.draw.rect(screen, color, (x, y, fill_width, height), border_radius=3)
        pygame.draw.rect(screen, WHITE, (x, y, width, height), 1, border_radius=3)
        
        display_text = text if text else f"{int(current_val)}/{int(max_val)}"
        text_surf = self.font_gauge.render(display_text, True, WHITE)
        text_rect = text_surf.get_rect(center=(x + width / 2, y + height / 2))
        screen.blit(text_surf, text_rect)

    def _draw_single_ally_info(self, screen, fighter, x, y, slot_width):
        """[재작성] 아군 한 명의 정보를 좌/우 분할된 슬롯 안에 세로로 나열합니다."""
        padding = 5
        is_active = self.active_fighter and self.active_fighter.inv_id == fighter.inv_id

        # 1. 이름/레벨
        name_color = GOLD if is_active else WHITE
        name_surf = self.font_name.render(f"[Lv.{fighter.level}] {fighter.name}", True, name_color)
        name_rect = name_surf.get_rect(left=x + padding, top=y)
        screen.blit(name_surf, name_rect)

        # 2. 게이지
        gauge_width = slot_width * 0.9
        gauge_height = 14
        gauge_x = x + (slot_width - gauge_width) / 2
        gauge_y = name_rect.bottom + padding * 2
        
        self._draw_gauge_bar(screen, gauge_x, gauge_y, gauge_width, gauge_height, fighter.hp, fighter.max_hp, (200, 50, 50))
        gauge_y += gauge_height + padding
        self._draw_gauge_bar(screen, gauge_x, gauge_y, gauge_width, gauge_height, fighter.mp, fighter.max_mp, (50, 100, 200))
        gauge_y += gauge_height + padding
        self._draw_gauge_bar(screen, gauge_x, gauge_y, gauge_width, gauge_height, fighter.sp, fighter.max_sp, (220, 180, 50))

        # 3. 스탯 텍스트
        stats_y = gauge_y + gauge_height + padding
        atk_surf = self.font_stats.render(f"ATK: {fighter.atk}", True, WHITE)
        agi_surf = self.font_stats.render(f"AGI: {fighter.agi}", True, WHITE)
        atk_rect = atk_surf.get_rect(left=gauge_x, top=stats_y)
        agi_rect = agi_surf.get_rect(left=atk_rect.right + 15, top=stats_y)
        screen.blit(atk_surf, atk_rect)
        screen.blit(agi_surf, agi_rect)
        
        # 4. 개별 경험치 바
        exp_y = atk_rect.bottom + padding
        self._draw_gauge_bar(screen, gauge_x, exp_y, gauge_width, gauge_height, fighter.exp, fighter.max_exp, GREEN, text="EXP")


    def _draw_ally_panel(self, screen):
        """[재작성] 좌측: 아군 정보를 좌/우 2열로 나누어 표시"""
        if not self.player_fighters: return
        
        slot_width = self.left_panel_width / 2
        y_start = self.rect.top + 5
        
        for i, fighter in enumerate(self.player_fighters[:2]):
            x_start = 5 + (i * slot_width)
            self._draw_single_ally_info(screen, fighter, x_start, y_start, slot_width)

    def _draw_center_panel(self, screen):
        title_surf = self.font_command_title.render("COMMAND", True, (150, 150, 150))
        title_pos = title_surf.get_rect(centerx=self.left_panel_width + self.center_panel_width/2, y=self.rect.top + 10)
        screen.blit(title_surf, title_pos)
        for button in self.buttons:
            button.draw(screen)

    def _draw_right_panel(self, screen):
        char_panel_width = self.right_panel_width / 2
        y_start = self.rect.top + 15
        for i, fighter in enumerate(self.enemy_fighters[:2]):
            x_start = self.left_panel_width + self.center_panel_width + 20 + (i * char_panel_width)
            is_target = self.target_fighter and self.target_fighter == fighter
            name_color = GOLD if is_target else WHITE
            name_surf = self.font_name.render(fighter.name, True, name_color)
            screen.blit(name_surf, (x_start, y_start))
            hp_val = fighter.hp if fighter.is_alive else 0
            hp_text = f"HP: {int(hp_val)}/{int(fighter.max_hp)}"
            hp_color = RED if hp_val > 0 and hp_val / fighter.max_hp < 0.3 else WHITE
            hp_surf = self.font_stats.render(hp_text, True, hp_color)
            screen.blit(hp_surf, (x_start, y_start + 30))

    def handle_event(self, event):
        if not self.buttons: return None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT:
                self.buttons[self.current_button_index].is_focused = False
                self.current_button_index = (self.current_button_index + 1) % len(self.buttons)
                self.buttons[self.current_button_index].is_focused = True
            elif event.key == pygame.K_LEFT:
                self.buttons[self.current_button_index].is_focused = False
                self.current_button_index = (self.current_button_index - 1) % len(self.buttons)
                self.buttons[self.current_button_index].is_focused = True
            elif event.key == pygame.K_z:
                return self.buttons[self.current_button_index].action_code
        if event.type == pygame.MOUSEMOTION:
            mouse_pos = pygame.mouse.get_pos()
            for i, button in enumerate(self.buttons):
                if button.is_hovered != button.rect.collidepoint(mouse_pos):
                    button.is_hovered = not button.is_hovered
                    if button.is_hovered:
                        self.buttons[self.current_button_index].is_focused = False
                        self.current_button_index = i
                        self.buttons[self.current_button_index].is_focused = True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            for button in self.buttons:
                if button.is_clicked(mouse_pos):
                    return button.action_code
        return None
