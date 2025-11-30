
import pygame
from scenes.base_scene import BaseScene
from ui.components import Button, InputBox
from game_systems.coupon import CouponManager
from ui.audio_manager import AudioManager
from config import *

class CouponScene(BaseScene):
    def __init__(self, screen, shared_data):
        super().__init__()
        self.screen = screen
        self.shared_data = shared_data
        self.user_id = DEFAULT_USER_ID
        self.coupon_manager = CouponManager()

        # --- Background and Styles ---
        self.background = self.shared_data['background_manager'].get_ui_background('coupon')
        self.paper_color = (240, 230, 210) # 밝은 종이 색상

        # --- UI Components with new positions ---
        # TODO: 이미지에 맞춰 조정 필요
        self.input_box = InputBox(270, 310, 300, 50, font_size=32)
        self.submit_button = Button(360, 380, 100, 50, '입력', action_code='SUBMIT')
        self.back_button = Button(SCREEN_WIDTH - 220, SCREEN_HEIGHT - 70, 200, 50, "로비로 돌아가기", "LOBBY")
        
        self.message = ""
        self.message_color = WHITE

    def enter(self):
        """씬에 진입할 때 로비 BGM을 재생합니다."""
        super().enter()
        AudioManager().play_bgm("bgm_lobby.mp3")

    def handle_events(self, events, mouse_pos):
        for event in events:
            # InputBox가 반환하는 값(엔터 시)을 처리할 수 있으나, 여기선 버튼으로만 제출.
            returned_text = self.input_box.handle_event(event)
            if returned_text is not None:
                self.submit_coupon()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.submit_button.is_clicked(mouse_pos):
                    self.submit_coupon()
                elif self.back_button.is_clicked(mouse_pos):
                    self.next_scene_name = "LOBBY"

    def update(self):
        self.input_box.update()

    def draw(self, screen):
        # 1. 배경 그리기
        if self.background:
            screen.blit(self.background, (0,0))
        else:
            screen.fill(BLACK)
        
        mouse_pos = pygame.mouse.get_pos()
        
        # 2. UI 요소 그리기 (재배치 및 스타일 적용)
        # '밝은 종이' 스타일 구현
        pygame.draw.rect(screen, self.paper_color, self.input_box.rect, border_radius=5)
        self.input_box.draw(screen)

        self.submit_button.check_hover(mouse_pos)
        self.submit_button.draw(screen)
        self.back_button.check_hover(mouse_pos)
        self.back_button.draw(screen)

        # 3. 메시지 표시 (입력창 근처로 이동)
        if self.message:
            msg_font = self.shared_data['info_font']
            msg_text = msg_font.render(self.message, True, self.message_color)
            # TODO: 이미지에 맞춰 조정 필요
            screen.blit(msg_text, (self.input_box.rect.left, self.input_box.rect.bottom + 15))

    def submit_coupon(self):
        code = self.input_box.text
        if not code:
            self.message = "코드를 입력해주세요."
            self.message_color = RED
            return

        is_valid, message = self.coupon_manager.redeem_coupon(code, self.user_id)
        
        if is_valid:
            self.message_color = GREEN
        else:
            self.message_color = RED
        self.message = message
        
        self.input_box.text = ""

    def start(self):
        """씬이 시작될 때 메시지와 입력창을 초기화합니다."""
        self.message = ""
        self.input_box.text = ""
        # 씬 전환 시 inputbox가 활성화 상태로 넘어오는 것을 방지
        self.input_box.active = False
        self.input_box.color = self.input_box.color_inactive
