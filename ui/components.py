import pygame
import os
from enum import Enum, auto

from config import (WHITE, BLACK, GRAY, GREEN, GOLD, COLOR_BUTTON_NORMAL, COLOR_BUTTON_HOVER, 
                    COLOR_INPUT_INACTIVE, COLOR_INPUT_ACTIVE, FONT_SIZE_BUTTON, 
                    FONT_SIZE_INPUT, BUTTON_BORDER_RADIUS, BUTTON_BORDER_THICKNESS,
                    INPUT_MAX_LENGTH, INPUT_TEXT_PADDING, GRADE_COLORS, ASSETS_DIR)
from ui.audio_manager import AudioManager

# --- Font Helper ---
def create_font(size, is_bold=False):
    """지정된 크기와 굵기로 폰트 객체를 생성합니다."""
    font_name = "Maplestory Bold.ttf" if is_bold else "Maplestory Light.ttf"
    font_path = os.path.join(ASSETS_DIR, "fonts", font_name)
    try:
        return pygame.font.Font(font_path, size)
    except pygame.error:
        print(f"Warning: Font '{font_name}' not found at '{font_path}'. Falling back to default font.")
        # In case of error, use a default system font
        return pygame.font.SysFont("malgungothic", size, bold=is_bold)


# --- [New] Action Enum for UI interactions ---
class Action(Enum):
    SELECT = auto()
    DETAIL = auto()
    NO_ACTION = auto()

class Button:
    def __init__(self, x, y, width, height, text, action_code=None, color=None, hover_color=None, image_normal=None, image_hover=None, font_size=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action_code = action_code
        size = font_size if font_size else FONT_SIZE_BUTTON
        self.font = create_font(size, is_bold=True) # Use create_font
        self.is_hovered = False
        self.is_focused = False

        self.color = color if color else COLOR_BUTTON_NORMAL
        self.hover_color = hover_color if hover_color else COLOR_BUTTON_HOVER

        # --- [New] Image Support ---
        self.image_normal = image_normal
        self.image_hover = image_hover
        if self.image_normal:
            self.rect = self.image_normal.get_rect(topleft=(x,y))
        # ---

    def draw(self, screen):
        # --- [Updated] Draw Logic ---
        if self.image_normal:
            # Image-based button
            current_image = self.image_hover if self.is_hovered and self.image_hover else self.image_normal
            screen.blit(current_image, self.rect)
        else:
            # Original text-and-color button
            color = self.hover_color if self.is_hovered or self.is_focused else self.color
            pygame.draw.rect(screen, color, self.rect, border_radius=BUTTON_BORDER_RADIUS)
            border_color = GOLD if self.is_focused else WHITE
            pygame.draw.rect(screen, border_color, self.rect, BUTTON_BORDER_THICKNESS, border_radius=BUTTON_BORDER_RADIUS)

            if self.text:
                text_surf = self.font.render(self.text, True, WHITE)
                text_rect = text_surf.get_rect(center=self.rect.center)
                screen.blit(text_surf, text_rect)
        # ---

    def check_hover(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)

    def handle_event(self, event):
        """Handles user input for the button."""
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.rect.collidepoint(event.pos):
                AudioManager().play_sfx('ui_click.wav') # 사운드 재생
                if self.action_code:
                    return self.action_code
                return Action.SELECT
        return Action.NO_ACTION


# --- [New] ToggleButton for selection states ---
class ToggleButton(Button):
    def __init__(self, x, y, width, height, text_on, text_off, is_on=False, action_code=None, font_size=None):
        super().__init__(x, y, width, height, text_off, action_code=action_code, font_size=font_size)
        self.text_on = text_on
        self.text_off = text_off
        self.is_on = is_on

    def draw(self, screen):
        text = self.text_on if self.is_on else self.text_off
        color = GREEN if self.is_on else self.color
        if self.is_hovered:
            color = self.hover_color

        pygame.draw.rect(screen, color, self.rect, border_radius=BUTTON_BORDER_RADIUS)
        pygame.draw.rect(screen, WHITE, self.rect, BUTTON_BORDER_THICKNESS, border_radius=BUTTON_BORDER_RADIUS)
        
        text_surf = self.font.render(text, True, WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def toggle(self):
        self.is_on = not self.is_on

# --- [New] CharacterCard Class ---
class CharacterCard:
    CARD_WIDTH, CARD_HEIGHT = 150, 320 # Height adjusted for name
    IMG_HEIGHT = 180
    BTN_HEIGHT = 25

    def __init__(self, x, y, fighter_data, is_selected=False):
        self.rect = pygame.Rect(x, y, self.CARD_WIDTH, self.CARD_HEIGHT)
        self.fighter_data = fighter_data
        
        # Fonts using the new helper
        self.font_name = create_font(20, is_bold=True)
        self.font_grade = create_font(16, is_bold=True)
        self.font_level = create_font(16, is_bold=True)

        # Card background
        self.bg_color = GRAY
        
        # Character Image
        self.image_surface = self._load_image()

        # Child UI Components
        self.detail_button = Button(
            self.rect.left + 10, self.rect.bottom - self.BTN_HEIGHT - 10, 
            60, self.BTN_HEIGHT, "상세", font_size=16
        )
        self.select_button = ToggleButton(
            self.rect.right - 70, self.rect.bottom - self.BTN_HEIGHT - 10,
            60, self.BTN_HEIGHT, "선택됨", "덱 선택", font_size=16, is_on=is_selected
        )
        self.components = [self.detail_button, self.select_button]

    def _load_image(self):
        """Load character image or create a placeholder."""
        img_w, img_h = self.CARD_WIDTH - 10, self.IMG_HEIGHT - 10
        try:
            # Assuming ASSETS_DIR is configured to be the absolute path to the assets folder
            image_path = os.path.join(ASSETS_DIR, 'images', self.fighter_data.image_path)
            img = pygame.image.load(image_path).convert_alpha()
            return pygame.transform.scale(img, (img_w, img_h))
        except (pygame.error, FileNotFoundError, TypeError):
            # [수정] 이미지가 없을 때 회색 배경과 캐릭터 이름을 포함하는 Placeholder 생성
            placeholder = pygame.Surface((img_w, img_h))
            placeholder.fill(GRAY)
            
            # Placeholder 위에 캐릭터 이름 텍스트 렌더링
            name_font = create_font(18, is_bold=True)
            name_surf = name_font.render(self.fighter_data.name, True, WHITE)
            name_rect = name_surf.get_rect(center=(img_w / 2, img_h / 2))
            placeholder.blit(name_surf, name_rect)
            
            return placeholder

    def handle_event(self, event, draw_rect=None):
        """Handles user input and returns an Action."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Use draw_rect for collision detection if provided
            target_rect = draw_rect if draw_rect else self.rect
            
            # Create temporary buttons with updated positions for checking clicks
            offset_x = target_rect.left - self.rect.left
            offset_y = target_rect.top - self.rect.top
            detail_button_rect = self.detail_button.rect.move(offset_x, offset_y)
            select_button_rect = self.select_button.rect.move(offset_x, offset_y)

            if detail_button_rect.collidepoint(event.pos):
                AudioManager().play_sfx('ui_click.wav') # 사운드 재생
                return Action.DETAIL
            if select_button_rect.collidepoint(event.pos):
                AudioManager().play_sfx('ui_click.wav') # 사운드 재생
                self.select_button.toggle()
                return Action.SELECT
        return Action.NO_ACTION

    def update(self, mouse_pos, draw_rect=None):
        """Update hover state for child components."""
        target_rect = draw_rect if draw_rect else self.rect
        for component in self.components:
            # Create a temporary rect for the component relative to the card's draw position
            offset_x = target_rect.left - self.rect.left
            offset_y = target_rect.top - self.rect.top
            component_rect = component.rect.move(offset_x, offset_y)
            component.is_hovered = component_rect.collidepoint(mouse_pos)

    def draw(self, screen, draw_rect=None):
        """Draw the entire card at a given position."""
        target_rect = draw_rect if draw_rect else self.rect

        # Draw background and border
        pygame.draw.rect(screen, self.bg_color, target_rect, border_radius=10)
        grade_color = GRADE_COLORS.get(self.fighter_data.grade, BLACK) # Default to black
        pygame.draw.rect(screen, WHITE, target_rect, 2, border_radius=10) # Neutral border

        # Draw character image box
        image_box_rect = pygame.Rect(target_rect.left, target_rect.top, target_rect.width, self.IMG_HEIGHT + 10)
        pygame.draw.rect(screen, BLACK, image_box_rect, border_top_left_radius=10, border_top_right_radius=10)

        # Draw character image
        img_rect = self.image_surface.get_rect(center=image_box_rect.center)
        screen.blit(self.image_surface, img_rect)

        # --- Draw Name, Grade, and Level ---
        # 1. Name
        name_surf = self.font_name.render(self.fighter_data.name, True, grade_color)
        name_rect = name_surf.get_rect(center=(target_rect.centerx, image_box_rect.bottom + 25))
        screen.blit(name_surf, name_rect)
        
        # 2. Grade
        grade_text_surf = self.font_grade.render(self.fighter_data.grade, True, grade_color)
        grade_text_rect = grade_text_surf.get_rect(center=(target_rect.centerx, name_rect.bottom + 15))
        screen.blit(grade_text_surf, grade_text_rect)

        # 3. Level
        level_text_surf = self.font_level.render(f"Lv. {self.fighter_data.level}", True, BLACK)
        level_text_rect = level_text_surf.get_rect(center=(target_rect.centerx, grade_text_rect.bottom + 15))
        screen.blit(level_text_surf, level_text_rect)
        # ---

        # Draw buttons at the correct scrolled position
        for component in self.components:
            original_comp_rect = component.rect.copy()
            offset_x = target_rect.left - self.rect.left
            offset_y = target_rect.top - self.rect.top
            component.rect = original_comp_rect.move(offset_x, offset_y)
            component.draw(screen)
            component.rect = original_comp_rect # Reset for next frame


class InputBox:
    """사용자 텍스트 입력을 받는 상자"""
    def __init__(self, x, y, w, h, font_size=FONT_SIZE_INPUT):
        self.rect = pygame.Rect(x, y, w, h)
        self.color_inactive = COLOR_INPUT_INACTIVE
        self.color_active = COLOR_INPUT_ACTIVE
        self.color = self.color_inactive
        self.text = ''
        self.font = create_font(font_size) # Use create_font
        self.active = False

    def _handle_mouse_event(self, event):
        """[리팩토링] 마우스 클릭 이벤트 처리"""
        if self.rect.collidepoint(event.pos):
            self.active = not self.active
        else:
            self.active = False
        self.color = self.color_active if self.active else self.color_inactive

    def _handle_key_event(self, event):
        """[리팩토링] 키보드 입력 이벤트 처리"""
        if not self.active:
            return None
            
        if event.key == pygame.K_RETURN:
            return self.text # 엔터 치면 텍스트 반환
        elif event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
        else:
            # 글자수 제한 + 인쇄 가능한 문자만 입력되도록 수정
            if len(self.text) < INPUT_MAX_LENGTH and event.unicode.isprintable():
                self.text += event.unicode
        return None

    def handle_event(self, event):
        """[리팩토링] 이벤트를 받아 내부 메서드로 분기"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_mouse_event(event)
        elif event.type == pygame.KEYDOWN:
            return self._handle_key_event(event)
        return None

    def update(self):
        pass # 현재는 특별한 업데이트 로직 없음

    def draw(self, screen):
        # 텍스트 색상을 검은색으로 변경
        txt_surface = self.font.render(self.text, True, BLACK)
        screen.blit(txt_surface, (self.rect.x + INPUT_TEXT_PADDING, self.rect.y + INPUT_TEXT_PADDING))
        pygame.draw.rect(screen, self.color, self.rect, BUTTON_BORDER_THICKNESS)