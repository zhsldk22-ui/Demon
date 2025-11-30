import pygame
import os
from scenes.base_scene import BaseScene
from ui.components import Button, Action
from ui.audio_manager import AudioManager
from config import *
from database import add_tickets, get_tickets

class GachaScene(BaseScene):
    def __init__(self, screen, shared_data, gacha_manager):
        super().__init__()
        self.screen = screen
        self.shared_data = shared_data
        self.gacha_manager = gacha_manager
        self.mode = "SELECT"
        self.results = []
        self.character_images = {}

        self.bg_shop = self.shared_data['background_manager'].get_ui_background('shop')
        self.bg_gacha_1 = self.shared_data['background_manager'].get_ui_background('gacha_1')
        self.bg_gacha_10 = self.shared_data['background_manager'].get_ui_background('gacha_10')

        gacha_1_img_normal = pygame.image.load(os.path.join(ASSETS_DIR, 'images', 'ui', 'btn_gacha_1_normal.png')).convert_alpha()
        gacha_1_img_hover = pygame.image.load(os.path.join(ASSETS_DIR, 'images', 'ui', 'btn_gacha_1_hover.png')).convert_alpha()
        gacha_10_img_normal = pygame.image.load(os.path.join(ASSETS_DIR, 'images', 'ui', 'btn_gacha_10_normal.png')).convert_alpha()
        gacha_10_img_hover = pygame.image.load(os.path.join(ASSETS_DIR, 'images', 'ui', 'btn_gacha_10_hover.png')).convert_alpha()

        self.btn_gacha_1 = Button(50, 520, 0, 0, "", "GACHA_1", image_normal=gacha_1_img_normal, image_hover=gacha_1_img_hover)
        self.btn_gacha_10 = Button(300, 460, 0, 0, "", "GACHA_10", image_normal=gacha_10_img_normal, image_hover=gacha_10_img_hover)
        self.btn_back_to_lobby = Button(SCREEN_WIDTH - 220, SCREEN_HEIGHT - 70, 200, 50, "로비로 돌아가기", "LOBBY")
        
        self.buttons = [self.btn_gacha_1, self.btn_gacha_10, self.btn_back_to_lobby]

        self.ticket_panel_rect = pygame.Rect(SCREEN_WIDTH - 240, 20, 220, 50)
        self.ticket_panel_surface = pygame.Surface(self.ticket_panel_rect.size, pygame.SRCALPHA)
        self.ticket_panel_surface.fill((0, 0, 0, 150))

    def enter(self):
        """씬에 진입할 때 로비 BGM을 재생합니다."""
        super().enter()
        AudioManager().play_bgm("bgm_lobby.mp3")

    def handle_events(self, events, mouse_pos):
        for event in events:
            if self.mode == "RESULT":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.mode = "SELECT"
                    self.results = []
                    return
            elif self.mode == "SELECT":
                for btn in self.buttons:
                    action = btn.handle_event(event)
                    if action and action != Action.NO_ACTION:
                        if action == "GACHA_1" and get_tickets() >= 1:
                            self.results = self.gacha_manager.draw_1()
                            AudioManager().play_sfx('sfx_open_gacha_1.wav')
                            self.mode = "RESULT"
                            self.preload_character_images()
                        elif action == "GACHA_10" and get_tickets() >= 10:
                            self.results = self.gacha_manager.draw_10()
                            AudioManager().play_sfx('sfx_open_gacha_10.wav')
                            self.mode = "RESULT"
                            self.preload_character_images()
                        elif action in ["GACHA_1", "GACHA_10"]:
                            self.shared_data['system_message'] = "티켓이 부족합니다!"
                        elif action == "LOBBY":
                            self.next_scene_name = "LOBBY"
                        # An action was handled, no need to check other buttons for this event
                        break

    def preload_character_images(self):
        self.character_images.clear()
        for result_info in self.results:
            char = result_info['char']
            if 'image' in char and char['image']:
                image_path = os.path.join(ASSETS_DIR, 'images', char['image'])
                try:
                    if os.path.exists(image_path):
                        self.character_images[char['id']] = pygame.image.load(image_path).convert_alpha()
                    else: self.character_images[char['id']] = None
                except pygame.error as e:
                    print(f"이미지 로드 오류 '{image_path}': {e}")
                    self.character_images[char['id']] = None

    def update(self):
        pass

    def _draw_character_on_altar(self, screen, font, result_info, position, scale=1.0):
        character = result_info['char']
        char_img = self.character_images.get(character['id'])
        if char_img:
            original_size = char_img.get_size()
            scaled_size = (int(original_size[0] * scale), int(original_size[1] * scale))
            scaled_img = pygame.transform.scale(char_img, scaled_size)
            img_rect = scaled_img.get_rect(centerx=position[0], bottom=position[1])
            screen.blit(scaled_img, img_rect)
        else:
            # [New] 이미지가 없을 경우 Placeholder 표시
            placeholder_rect = pygame.Rect(0, 0, 100 * scale, 120 * scale)
            placeholder_rect.centerx = position[0]
            placeholder_rect.bottom = position[1]
            pygame.draw.rect(screen, GRAY, placeholder_rect)
            name_surf = font.render(character['name'], True, WHITE)
            name_rect = name_surf.get_rect(center=placeholder_rect.center)
            screen.blit(name_surf, name_rect)
        
        y_offset = position[1] + 5
        grade_color = GRADE_COLORS.get(character['grade'].upper(), WHITE)
        grade_surf = font.render(f"[{character['grade']}]", True, grade_color)
        grade_rect = grade_surf.get_rect(centerx=position[0], y=y_offset)
        screen.blit(grade_surf, grade_rect)
        y_offset += 20

        name_surf = font.render(character['name'], True, WHITE)
        name_rect = name_surf.get_rect(centerx=position[0], y=y_offset)
        screen.blit(name_surf, name_rect)
        y_offset += 20
        
        if result_info['is_duplicate']:
            exp_text = f"+{result_info['exp_gain']} EXP"
            exp_surf = font.render(exp_text, True, GOLD)
            exp_rect = exp_surf.get_rect(centerx=position[0], y=y_offset)
            screen.blit(exp_surf, exp_rect)
        else: # 신규 획득
            new_surf = font.render("NEW!", True, (100, 255, 100))
            new_rect = new_surf.get_rect(centerx=position[0], y=y_offset)
            screen.blit(new_surf, new_rect)


    def draw(self, screen):
        info_font = self.shared_data['info_font']
        if self.mode == "RESULT":
            bg = self.bg_gacha_1 if len(self.results) == 1 else self.bg_gacha_10
            screen.blit(bg, (0, 0)) if bg else screen.fill(BLACK)

            if len(self.results) == 1:
                self._draw_character_on_altar(screen, info_font, self.results[0], (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 200), scale=1.2)
            else:
                back_row_y, front_row_y = 380, 620
                back_row_x, front_row_x = [200, 370, 540, 710, 880], [180, 360, 540, 720, 900]
                
                for i in range(5):
                    if i < len(self.results):
                        self._draw_character_on_altar(screen, info_font, self.results[i], (back_row_x[i], back_row_y), scale=0.8)
                for i in range(5):
                    if i + 5 < len(self.results):
                        self._draw_character_on_altar(screen, info_font, self.results[i + 5], (front_row_x[i], front_row_y), scale=1.0)
            
            msg_surf = info_font.render("화면을 클릭하면 상점으로 돌아갑니다", True, WHITE)
            msg_rect = msg_surf.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT - 30))
            pygame.draw.rect(screen, (0,0,0,150), msg_rect.inflate(20,10))
            screen.blit(msg_surf, msg_rect)
        
        elif self.mode == "SELECT":
            screen.blit(self.bg_shop, (0, 0)) if self.bg_shop else screen.fill(BLACK)

            tickets = get_tickets()
            screen.blit(self.ticket_panel_surface, self.ticket_panel_rect.topleft)
            ticket_text = info_font.render(f"보유 티켓: {tickets}", True, (255, 255, 0))
            text_rect = ticket_text.get_rect(center=self.ticket_panel_rect.center)
            screen.blit(ticket_text, text_rect)
            
            mouse_pos = pygame.mouse.get_pos()
            for btn in self.buttons:
                btn.check_hover(mouse_pos)
                btn.draw(screen)

            system_message = self.shared_data.get('system_message')
            if system_message:
                 msg_surf = info_font.render(system_message, True, RED)
                 msg_rect = msg_surf.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT - 30))
                 screen.blit(msg_surf, msg_rect)
                 self.shared_data['system_message'] = None