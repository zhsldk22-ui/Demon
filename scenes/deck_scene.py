import pygame
import sqlite3
from scenes.base_scene import BaseScene
from config import *
from ui.components import CharacterCard, Action
from ui.audio_manager import AudioManager
from ui.popup import CharacterDetailPopup
from game_systems.fighter_data import FighterData

class DeckScene(BaseScene):
    """
    '내 덱 보기' 화면. CharacterCard와 Popup을 사용하여 UI를 구성한다.
    """
    def __init__(self, screen, shared_data):
        super().__init__()
        self.screen = screen
        self.shared_data = shared_data
        self.character_cards = []
        self.scroll_offset = 0
        self.popup = None

        # --- Background and Overlay ---
        self.background = self.shared_data['background_manager'].get_ui_background('deck')
        panel_x, panel_y = 50, 80
        panel_width, panel_height = SCREEN_WIDTH - 100, SCREEN_HEIGHT - 150
        self.overlay_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        self.overlay_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        self.overlay_surface.fill((0, 0, 0, 180))

        # --- UI Components ---
        from ui.components import Button # Avoid circular import if Button uses Action
        self.lobby_button = Button(
            SCREEN_WIDTH - 220, SCREEN_HEIGHT - 70, 200, 50, "로비로 돌아가기"
        )
        
        self.load_character_cards()

    def enter(self):
        """씬에 진입할 때 로비 BGM을 재생합니다."""
        super().enter()
        AudioManager().play_bgm("bgm_lobby.mp3")

    def load_character_cards(self):
        """[FIXED] DB에서 캐릭터의 '영구 성장 스탯'을 포함하여 불러오도록 수정합니다."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # [수정] c.hp, c.atk 대신 i.total_max_hp, i.total_atk 등을 가져오도록 쿼리 변경
        cur.execute("""
            SELECT 
                i.id as inv_id, i.level, i.exp, i.is_selected,
                c.id as char_id, c.name, c.grade, c.description, c.image as image_path,
                c.mp, c.sp_max, c.skill_name, c.sfx_type, c.ult_name,
                COALESCE(i.total_max_hp, c.hp) as final_hp,
                COALESCE(i.total_atk, c.atk) as final_atk,
                COALESCE(i.total_agi, c.agi) as final_agi
            FROM inventory i JOIN characters c ON i.char_id = c.id 
            WHERE i.user_id=?
            ORDER BY CASE UPPER(c.grade)
                WHEN 'MYTHIC' THEN 0 WHEN 'LEGEND' THEN 1 WHEN 'SPECIAL' THEN 2
                WHEN 'RARE' THEN 3 WHEN 'COMMON' THEN 4
                ELSE 5 END, c.id
        """, (DEFAULT_USER_ID,))
        db_characters = cur.fetchall()
        conn.close()

        self.character_cards = []
        
        # Define grid layout
        cols = 5
        card_margin_x, card_margin_y = 40, 30
        card_area_width = self.overlay_rect.width - 2 * card_margin_x
        card_width = (card_area_width - (cols - 1) * card_margin_x) / cols
        # CharacterCard has a fixed width, so we adjust layout based on it.
        card_width = CharacterCard.CARD_WIDTH
        start_x = self.overlay_rect.left + (self.overlay_rect.width - (cols * card_width + (cols - 1) * card_margin_x)) / 2


        for i, char_data in enumerate(db_characters):
            # [수정] FighterData 생성 시, 기본 스탯 대신 최종 스탯(final_hp 등)을 사용
            fighter = FighterData(
                x=0, y=0, name=char_data['name'], is_enemy=False,
                hp=char_data['final_hp'], max_hp=char_data['final_hp'],
                mp=char_data['mp'], max_mp=char_data['mp'],
                sp_max=char_data['sp_max'], atk=char_data['final_atk'], agi=char_data['final_agi'],
                image_path=char_data['image_path'], description=char_data['description'],
                inv_id=char_data['inv_id'], level=char_data['level'], exp=char_data['exp'],
                grade=char_data['grade'].upper(),
                skill_name=char_data['skill_name'], skill_description=char_data['description'], # [Fix] 스킬 설명을 캐릭터 설명으로 대체
                sfx_type=char_data['sfx_type'], ult_name=char_data['ult_name']
            )
            
            row = i // cols
            col = i % cols
            
            card_x = start_x + col * (card_width + card_margin_x)
            card_y = self.overlay_rect.top + card_margin_y + row * (CharacterCard.CARD_HEIGHT + card_margin_y)

            card = CharacterCard(card_x, card_y, fighter, is_selected=bool(char_data['is_selected']))
            self.character_cards.append(card)

    def toggle_selection(self, card):
        """[FIXED] 캐릭터의 '덱 선택' 상태를 변경하고, 최대 2명 제한을 올바르게 적용합니다."""
        # CharacterCard의 handle_event에서 버튼 상태는 이미 변경되었습니다.
        is_selecting = card.select_button.is_on

        if is_selecting:
            # 카드를 '선택'하는 경우, 현재 선택된 카드 수를 확인합니다.
            selected_cards = [c for c in self.character_cards if c.select_button.is_on]
            if len(selected_cards) > 2:
                print("최대 2명의 캐릭터만 선택할 수 있습니다.")
                card.select_button.toggle()  # 방금 켠 버튼을 다시 끔 (선택 취소)
                return  # DB에 저장하지 않고 함수 종료
        
        # 선택 해제는 항상 허용되거나, 선택 시 2명 이하인 경우에만 아래 코드가 실행됩니다.
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        new_status = 1 if card.select_button.is_on else 0
        cur.execute("UPDATE inventory SET is_selected=? WHERE id=?", (new_status, card.fighter_data.inv_id))
        conn.commit()
        conn.close()

    def handle_events(self, events, mouse_pos):
        if self.popup:
            # Simplified event handling for popup
            for event in events:
                if self.popup.handle_event(event):
                    return
            return

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if self.lobby_button.rect.collidepoint(mouse_pos):
                        self.next_scene_name = "LOBBY"
                        return

                    for card in self.character_cards:
                        draw_rect = card.rect.move(0, -self.scroll_offset)
                        if draw_rect.collidepoint(mouse_pos):
                            action = card.handle_event(event, draw_rect=draw_rect)
                            if action == Action.DETAIL:
                                self.popup = CharacterDetailPopup(self, card.fighter_data)
                                return # Stop processing further events
                            elif action == Action.SELECT:
                                self.toggle_selection(card)
                                return
                
                elif event.button == 3: # Right-click to go back
                    self.next_scene_name = "LOBBY"
                    return

            elif event.type == pygame.MOUSEWHEEL:
                # Calculate max scroll based on content height
                num_rows = (len(self.character_cards) + 4) // 5 # 5 cards per row
                content_height = num_rows * (CharacterCard.CARD_HEIGHT + 30) # card_margin_y = 30
                max_scroll = max(0, content_height - self.overlay_rect.height)
                self.scroll_offset -= event.y * 30
                self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

    def update(self):
        mouse_pos = pygame.mouse.get_pos()
        if self.popup:
            self.popup.update()
        else:
            self.lobby_button.check_hover(mouse_pos)
            for card in self.character_cards:
                draw_rect = card.rect.move(0, -self.scroll_offset)
                card.update(mouse_pos, draw_rect)

    def draw(self, screen):
        # 1. Background and Overlay
        if self.background:
            screen.blit(self.background, (0, 0))
        else:
            screen.fill((20, 30, 40))
        screen.blit(self.overlay_surface, self.overlay_rect.topleft)

        # 2. Title
        title_font = self.shared_data['title_font']
        screen.blit(title_font.render("캐릭터 선택 (최대 2명)", True, WHITE), (self.overlay_rect.left + 20, self.overlay_rect.top - 60))

        # 3. Character Cards
        # Create a temporary surface for clipping the cards within the overlay
        card_area = self.overlay_surface.copy()
        card_area.fill((0,0,0,0)) # Make it transparent

        for card in self.character_cards:
            draw_rect = card.rect.move(0, -self.scroll_offset)
            if draw_rect.colliderect(self.overlay_rect):
                card.draw(screen, draw_rect)

        # 4. UI Components
        self.lobby_button.draw(screen)
        
        # 5. Popup
        if self.popup:
            self.popup.draw()
            
        # 6. Footer hint
        info_font = self.shared_data['info_font']
        screen.blit(info_font.render("우클릭/버튼: 나가기 | 카드 클릭: 상세정보/선택 | 휠: 스크롤", True, GRAY), (50, SCREEN_HEIGHT - 50))