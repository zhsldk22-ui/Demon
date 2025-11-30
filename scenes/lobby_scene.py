import pygame, os, sqlite3
from scenes.base_scene import BaseScene
from ui.components import Button, Action
from ui.audio_manager import AudioManager
from config import *

def get_current_floor():
    """[임시] main.py에 있던 함수를 그대로 가져옴. 추후 User 모델로 통합 필요."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT current_floor FROM users WHERE user_id=?", (DEFAULT_USER_ID,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] is not None else 1

def get_selected_character_count():
    """[신규] DB에서 현재 선택된 캐릭터 수를 확인하는 함수"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM inventory WHERE user_id=? AND is_selected=1", (DEFAULT_USER_ID,))
    count = cur.fetchone()[0]
    conn.close()
    return count

class LobbyScene(BaseScene):
    """
    로비 화면의 모든 UI, 이벤트 처리, 그리기를 책임지는 '로비 담당 직원'.
    """
    def __init__(self, screen, shared_data):
        super().__init__()
        self.screen = screen
        self.shared_data = shared_data # main.py와 공유할 데이터 (예: 폰트)
        
        # 로비 직원이 직접 자기 버튼들을 만듭니다.
        self.btn_new_game = Button(SCREEN_WIDTH//2 - 100, 300, 200, 50, "새로 하기", "NEW_GAME")
        self.btn_continue = Button(SCREEN_WIDTH//2 - 100, 370, 200, 50, "이어 하기", "CONTINUE")
        self.btn_deck = Button(SCREEN_WIDTH//2 - 100, 440, 200, 50, "내 덱 보기", "VIEW_DECK")
        self.btn_gacha_shop = Button(SCREEN_WIDTH//2 - 100, 510, 200, 50, "소환상점", "GACHA_SHOP")
        self.btn_coupon = Button(SCREEN_WIDTH//2 - 100, 580, 200, 50, "쿠폰입력", "OPEN_COUPON")
        self.buttons = [self.btn_new_game, self.btn_continue, self.btn_deck, self.btn_gacha_shop, self.btn_coupon]

        # 로비 직원이 직접 자기 배경 이미지를 불러옵니다.
        lobby_bg_path = os.path.join(ASSETS_DIR, "images", "lobby_background.png")
        self.bg_image = pygame.image.load(lobby_bg_path).convert()
        self.bg_image = pygame.transform.scale(self.bg_image, (SCREEN_WIDTH, SCREEN_HEIGHT))

        # 팝업 관련 상태는 로비 직원이 직접 관리합니다.
        self.popup_message = None
        self.popup_buttons = []

    def enter(self):
        """씬에 진입할 때 로비 BGM을 재생합니다."""
        super().enter()
        AudioManager().play_bgm("bgm_lobby.mp3")

    def handle_event(self, event, mouse_pos):
        # 팝업이 활성화된 상태에서는 팝업 관련 이벤트만 처리합니다.
        if self.popup_message:
            for btn in self.popup_buttons:
                action = btn.handle_event(event)
                if action and action != Action.NO_ACTION:
                    if action == "CONFIRM_NEW_GAME":
                        if get_selected_character_count() == 2:
                            self.next_scene_name = "BATTLE_NEW"
                        else:
                            self.shared_data['system_message'] = "덱 보기에서 2명을 선택해야 시작할 수 있습니다!"
                    
                    self.popup_message = None
                    self.popup_buttons = []
            return

        # 일반 로비 버튼 이벤트 처리
        for btn in self.buttons:
            action = btn.handle_event(event)
            if not action or action == Action.NO_ACTION:
                continue

            if action == "CONTINUE":
                if get_current_floor() > 1:
                    self.next_scene_name = "BATTLE_CONTINUE"
                else:
                    self.shared_data['system_message'] = "저장된 게임이 없습니다!"
            elif action == "NEW_GAME":
                if get_current_floor() > 1:
                    self.popup_message = "기존 플레이가 삭제됩니다. 계속할까요?"
                    self.popup_buttons = [
                        Button(SCREEN_WIDTH//2 - 160, 400, 150, 50, "예", "CONFIRM_NEW_GAME"),
                        Button(SCREEN_WIDTH//2 + 10, 400, 150, 50, "아니오", "CANCEL")
                    ]
                    # [BUGFIX] 팝업 생성 직후, 혹시 모를 후속 MOUSEBUTTONDOWN 이벤트를 모두 제거하여
                    # 다음 프레임에서 팝업 버튼이 바로 눌리는 타이밍 문제를 원천 방지합니다.
                    pygame.event.clear(pygame.MOUSEBUTTONDOWN)
                    return
                else:
                    if get_selected_character_count() == 2:
                        self.next_scene_name = "BATTLE_NEW"
                    else:
                        self.shared_data['system_message'] = "덱 보기에서 2명을 선택해야 시작할 수 있습니다!"
            elif action == "VIEW_DECK":
                self.next_scene_name = "DECK_VIEW"
            elif action == "GACHA_SHOP":
                self.next_scene_name = "GACHA_SHOP"
            elif action == "OPEN_COUPON":
                self.next_scene_name = "COUPON"
            
            return

    def update(self):
        # 이 화면에서는 특별히 매 프레임마다 업데이트할 내용이 없습니다.
        pass

    def draw(self, screen):
        # 1. 배경 그리기
        screen.blit(self.bg_image, (0, 0))
        
        # 2. UI 요소 그리기
        tickets = self.shared_data.get('tickets', 0)
        info_font = self.shared_data['info_font']
        screen.blit(info_font.render(f"티켓: {tickets}", True, (255, 255, 0)), (SCREEN_WIDTH - 150, 20))
        
        # '이어하기' 버튼 활성화/비활성화
        self.btn_continue.color = (50, 50, 200) if get_current_floor() > 1 else GRAY

        mouse_pos = pygame.mouse.get_pos()
        for btn in self.buttons:
            btn.check_hover(mouse_pos)
            btn.draw(screen)

        # 3. 팝업 그리기
        if self.popup_message:
            self._draw_popup(screen, mouse_pos)

    def _draw_popup(self, screen, mouse_pos):
        """팝업창을 그리는 내부 함수"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); overlay.set_alpha(180); overlay.fill(BLACK)
        screen.blit(overlay, (0,0))
        popup_rect = pygame.Rect(SCREEN_WIDTH//2 - 250, 300, 500, 200)
        pygame.draw.rect(screen, (50,50,50), popup_rect, border_radius=15)
        pygame.draw.rect(screen, WHITE, popup_rect, 2, border_radius=15)
        
        info_font = self.shared_data['info_font']
        msg_surf = info_font.render(self.popup_message, True, WHITE)
        screen.blit(msg_surf, msg_surf.get_rect(center=(popup_rect.centerx, 350)))
        
        for btn in self.popup_buttons:
            btn.check_hover(mouse_pos)
            btn.draw(screen)