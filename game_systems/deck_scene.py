import pygame
import sqlite3
from scenes.base_scene import BaseScene
from ui.components import CharacterCard, Action, Button
from ui.popup import CharacterDetailPopup
from ui.audio_manager import AudioManager
from config import *
from game_systems.fighter_data import FighterData

class DeckScene(BaseScene):
    def __init__(self, screen, shared_data):
        super().__init__()
        self.screen = screen
        self.shared_data = shared_data
        self.font = shared_data['info_font']
        self.bg_deck = self.shared_data['background_manager'].get_ui_background('deck')

        self.character_cards = []
        self.popup = None

        # --- [New] Scrolling variables ---
        self.scroll_y = 0
        self.scroll_speed = 30
        self.content_height = 0
        # ---

        # --- [New] Back button ---
        self.btn_back_to_lobby = Button(
            SCREEN_WIDTH - 220, SCREEN_HEIGHT - 70, 200, 50, "로비로 돌아가기", "LOBBY"
        )
        # ---

        self.load_character_cards()

    def enter(self):
        """씬에 진입할 때 로비 BGM을 재생합니다."""
        super().enter()
        AudioManager().play_bgm("bgm_lobby.mp3")
        self.load_character_cards()

    def load_character_cards(self):
        self.character_cards.clear()
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # [Fix] c.skill_description 컬럼 제거
        cur.execute("""
            SELECT 
                c.id as char_id, c.name, c.origin, c.grade, c.attribute, c.hp, c.mp, c.atk, c.def, c.agi, c.sp_max,
                c.description, c.image, c.sfx_type, c.skill_name, c.ult_name,
                i.id as inv_id, i.level, i.exp, i.is_selected
            FROM inventory i JOIN characters c ON i.char_id = c.id
            WHERE i.user_id = ?
            ORDER BY 
                CASE c.grade
                    WHEN 'MYTHIC' THEN 0
                    WHEN 'LEGEND' THEN 1
                    WHEN 'SPECIAL' THEN 2
                    WHEN 'RARE' THEN 3
                    WHEN 'COMMON' THEN 4
                    ELSE 5 END, c.id
        """, (DEFAULT_USER_ID,))
        rows = cur.fetchall()
        conn.close()

        card_x, card_y = 100, 100
        for row in rows:
            fighter_data = FighterData.from_dict(dict(row))
            card = CharacterCard(card_x, card_y, fighter_data, is_selected=row['is_selected'])
            self.character_cards.append(card)

    def handle_event(self, event, mouse_pos):
        if self.popup:
            if self.popup.handle_event(event):
                return

        if event.type == pygame.MOUSEWHEEL:
            self.scroll_y += event.y * self.scroll_speed
            max_scroll = self.content_height - (SCREEN_HEIGHT - 150)
            self.scroll_y = max(0, min(self.scroll_y, max_scroll))

        if self.btn_back_to_lobby.handle_event(event) == "LOBBY":
            self.next_scene_name = "LOBBY"
            return

        for card in self.character_cards:
            draw_rect = card.rect.move(0, -self.scroll_y)
            action = card.handle_event(event, draw_rect)
            if action == Action.DETAIL:
                self.popup = CharacterDetailPopup(self, card.fighter_data)
                break
            elif action == Action.SELECT:
                self.toggle_selection(card)
                break

    def toggle_selection(self, selected_card):
        selected_count = sum(1 for c in self.character_cards if c.select_button.is_on)
        if not selected_card.select_button.is_on and selected_count >= 2:
            selected_card.select_button.toggle()
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE inventory SET is_selected = ? WHERE id = ?", 
                    (1 if selected_card.select_button.is_on else 0, selected_card.fighter_data.inv_id))
        conn.commit()
        conn.close()

    def update(self):
        mouse_pos = pygame.mouse.get_pos()
        self.btn_back_to_lobby.check_hover(mouse_pos)
        for card in self.character_cards:
            draw_rect = card.rect.move(0, -self.scroll_y)
            card.update(mouse_pos, draw_rect)

    def draw(self, screen):
        screen.blit(self.bg_deck, (0,0))

        overlay = pygame.Surface((SCREEN_WIDTH - 200, SCREEN_HEIGHT - 150), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (100, 75))

        num_cols = 5
        padding = 20
        card_width = CharacterCard.CARD_WIDTH
        start_x, start_y = 150, 100

        for i, card in enumerate(self.character_cards):
            row, col = divmod(i, num_cols)
            x = start_x + col * (card_width + padding)
            y = start_y + row * (CharacterCard.CARD_HEIGHT + padding) - self.scroll_y
            
            if y + CharacterCard.CARD_HEIGHT > 75 and y < SCREEN_HEIGHT - 75:
                card.draw(screen, pygame.Rect(x, y, card.rect.width, card.rect.height))

        self.content_height = start_y + (len(self.character_cards) // num_cols + 1) * (CharacterCard.CARD_HEIGHT + padding)

        self.btn_back_to_lobby.draw(screen)

        if self.popup:
            self.popup.draw()