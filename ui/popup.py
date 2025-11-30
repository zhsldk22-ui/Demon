import pygame
import os
from ui.components import Button, Action

# Font paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH_LIGHT = os.path.join(BASE_DIR, "assets", "fonts", "Maplestory Light.ttf")
FONT_PATH_BOLD = os.path.join(BASE_DIR, "assets", "fonts", "Maplestory Bold.ttf")

class BasePopup:
    def __init__(self, scene):
        self.scene = scene
        self.screen = scene.screen
        self.screen_rect = self.screen.get_rect()
        
        # Create a semi-transparent background
        self.dimmed_surface = pygame.Surface(self.screen_rect.size, pygame.SRCALPHA)
        self.dimmed_surface.fill((0, 0, 0, 128))

    def draw(self):
        # Draw the dimmed background first
        self.screen.blit(self.dimmed_surface, (0, 0))

    def handle_event(self, event):
        # Base implementation prevents events from propagating to the scene below
        return True

    def update(self):
        pass

class CharacterDetailPopup(BasePopup):
    def __init__(self, scene, fighter_data):
        super().__init__(scene)
        self.fighter_data = fighter_data
        
        # Define colors and fonts
        self.font = pygame.font.Font(FONT_PATH_BOLD, 36)
        self.small_font = pygame.font.Font(FONT_PATH_LIGHT, 28)
        self.text_color = (255, 255, 255)
        self.bar_color = (0, 128, 255)
        self.bar_bg_color = (50, 50, 50)

        self._setup_layout()

    def _setup_layout(self):
        # Popup dimensions and position
        popup_width = 500
        popup_height = 600
        self.popup_rect = pygame.Rect(
            (self.screen_rect.width - popup_width) / 2,
            (self.screen_rect.height - popup_height) / 2,
            popup_width,
            popup_height
        )

        # Close button
        btn_x = self.popup_rect.right - 40
        btn_y = self.popup_rect.top + 10
        self.close_button = Button(
            btn_x, btn_y, 30, 30,
            text="X",
            font_size=24
        )

        # EXP Bar dimensions
        self.exp_bar_rect = pygame.Rect(
            self.popup_rect.left + 20,
            self.popup_rect.bottom - 50,
            self.popup_rect.width - 40,
            20
        )

    def draw(self):
        super().draw()  # Draw dimmed background

        # Draw the popup background
        pygame.draw.rect(self.screen, (20, 20, 40), self.popup_rect, border_radius=10)
        pygame.draw.rect(self.screen, (100, 100, 120), self.popup_rect, 2, border_radius=10)

        # Draw Title
        title_text = self.font.render(f"{self.fighter_data.name} (Lv. {self.fighter_data.level})", True, self.text_color)
        self.screen.blit(title_text, (self.popup_rect.centerx - title_text.get_width() // 2, self.popup_rect.top + 20))

        # Draw Stats
        stats = {
            "HP": self.fighter_data.hp,
            "MP": self.fighter_data.mp,
            "SP": self.fighter_data.sp,
            "ATK": self.fighter_data.atk,
            "AGI": self.fighter_data.agi,
        }
        y_offset = self.popup_rect.top + 70
        for i, (stat, value) in enumerate(stats.items()):
            stat_text = self.small_font.render(f"{stat}: {value}", True, self.text_color)
            self.screen.blit(stat_text, (self.popup_rect.left + 40, y_offset + i * 35))

        # Draw Skill
        skills_title = self.font.render("Skill", True, self.text_color)
        self.screen.blit(skills_title, (self.popup_rect.left + 40, y_offset + len(stats) * 35 + 20))
        y_offset += len(stats) * 35 + 50

        skill_name_surf = self.small_font.render(f"[{self.fighter_data.skill_name}]", True, (255, 215, 0))
        self.screen.blit(skill_name_surf, (self.popup_rect.left + 40, y_offset))

        # Basic text wrapping for description
        if self.fighter_data.skill_description:
            desc_font = pygame.font.Font(FONT_PATH_LIGHT, 24)
            words = self.fighter_data.skill_description.split(' ')
            lines = []
            current_line = ""
            line_width = self.popup_rect.width - 80
            
            for word in words:
                test_line = current_line + word + " "
                if desc_font.size(test_line)[0] < line_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word + " "
            lines.append(current_line)

            for i, line in enumerate(lines):
                desc_surf = desc_font.render(line, True, (200, 200, 200))
                self.screen.blit(desc_surf, (self.popup_rect.left + 50, y_offset + 35 + i * 25))
        
        
        # Draw EXP Bar
        self._draw_exp_bar()
        
        # Draw Close button
        self.close_button.draw(self.screen)


    def _draw_exp_bar(self):
        # Background
        pygame.draw.rect(self.screen, self.bar_bg_color, self.exp_bar_rect)
        
        # Foreground (current EXP)
        exp_ratio = 0
        if self.fighter_data.max_exp > 0:
            exp_ratio = self.fighter_data.exp / self.fighter_data.max_exp
        
        current_exp_width = int(self.exp_bar_rect.width * exp_ratio)
        current_exp_rect = pygame.Rect(self.exp_bar_rect.left, self.exp_bar_rect.top, current_exp_width, self.exp_bar_rect.height)
        pygame.draw.rect(self.screen, self.bar_color, current_exp_rect)

        # Border
        pygame.draw.rect(self.screen, self.text_color, self.exp_bar_rect, 2)

        # Text
        exp_text = self.small_font.render(f"EXP: {self.fighter_data.exp} / {self.fighter_data.max_exp}", True, self.text_color)
        self.screen.blit(exp_text, (self.exp_bar_rect.centerx - exp_text.get_width() // 2, self.exp_bar_rect.top - 25))

    def handle_event(self, event):
        if event and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Handle close button click
            if self.close_button.is_clicked(event.pos):
                self.scene.popup = None
                return True  # Event handled

            # If the click is outside the popup, close it
            if not self.popup_rect.collidepoint(event.pos):
                self.scene.popup = None
                return True  # Event handled

        # Return True to block other events from reaching the scene below
        return True