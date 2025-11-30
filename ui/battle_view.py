import pygame
from config import *
from ui.components import Button, ToggleButton
from ui.audio_manager import AudioManager
from ui.vfx import VFXManager
from ui.battle_panel import BattlePanel
from ui.background_manager import BackgroundManager
from ui.fighter_view import FighterView
import random # For RewardPopup

# battle_scene.py 에서 View 역할을 하는 RewardPopup 클래스를 이전
class RewardPopup:
    def __init__(self, shared_data):
        self.font = pygame.font.SysFont("malgungothic", 30, bold=True)
        self.bg_rect = pygame.Rect(SCREEN_WIDTH//2 - 250, 200, 500, 400)
        self.reward_buttons = []
        self.action_buttons = []
        self.reward_selected = False
        self.selected_reward_code = None

    def generate_rewards(self, is_boss_floor):
        self.reward_buttons.clear()
        self.action_buttons.clear()
        self.reward_selected = False
        self.selected_reward_code = None
        all_rewards = {
            "REWARD_HEAL": "[회복] 체력 30% 회복",
            "REWARD_HP_UP": "[성장] 최대 체력 +20",
            "REWARD_ATK_UP": "[강화] 공격력 +5",
            "REWARD_TICKET": "[행운] 뽑기 쿠폰 1개"
        }
        if is_boss_floor:
            all_rewards["REWARD_TICKET"] = "[대박] 뽑기 쿠폰 5개"
        selected_codes = random.sample(list(all_rewards.keys()), 3)
        for i, code in enumerate(selected_codes):
            self.reward_buttons.append(Button(SCREEN_WIDTH//2 - 200, 280 + i * 70, 400, 50, all_rewards[code], code))
        self.action_buttons.append(Button(SCREEN_WIDTH//2 - 200, 480, 190, 60, "다음 층으로 가기", "NEXT_FLOOR", color=GRAY))
        self.action_buttons.append(Button(SCREEN_WIDTH//2 + 10, 480, 190, 60, "저장하고 나가기", "SAVE_AND_EXIT", color=GRAY))

    def select_reward(self, selected_button):
        self.reward_selected = True
        self.selected_reward_code = selected_button.action_code
        for btn in self.reward_buttons:
            btn.color = (0, 100, 0) if btn is selected_button else GRAY
        self.action_buttons[0].color = (50, 50, 200)
        self.action_buttons[1].color = (80, 80, 80)

    def draw(self, screen):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180); overlay.fill(BLACK); screen.blit(overlay, (0,0))
        pygame.draw.rect(screen, (50, 50, 50), self.bg_rect, border_radius=15)
        pygame.draw.rect(screen, WHITE, self.bg_rect, 2, border_radius=15)
        title_text = "보상 획득! 다음은?" if self.reward_selected else "전투 승리! 보상을 선택하세요"
        title = self.font.render(title_text, True, (255, 215, 0))
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, 240)))
        mouse_pos = pygame.mouse.get_pos()
        for btn in self.reward_buttons: btn.check_hover(mouse_pos); btn.draw(screen)
        for btn in self.action_buttons: btn.check_hover(mouse_pos); btn.draw(screen)

    def handle_click(self, mouse_pos):
        for btn in self.reward_buttons:
            if btn.is_clicked(mouse_pos):
                self.select_reward(btn)
                # 보상 선택은 즉각적인 액션이 아니므로 None 반환
                return {"type": "UI_ACTION", "action": "REWARD_SELECTED"}
        
        if self.reward_selected:
            for btn in self.action_buttons:
                if btn.is_clicked(mouse_pos):
                    # '다음' 또는 '저장' 버튼 클릭 시 최종 액션 반환
                    return {"type": "UI_ACTION", "action": btn.action_code, "reward": self.selected_reward_code}
        return None

class BattleView:
    """
    [View]
    화면 렌더링과 UI 입력의 1차 가공을 담당하는 '똑똑한 UI 관리자'.
    - 역할 1 (Output): BattleSystem의 데이터를 받아 화면의 모든 요소를 그린다.
    - 역할 2 (Input): 마우스/키보드 입력을 "어떤 버튼이 눌렸다"와 같은 의미있는 행동(Action)으로 변환하여 Controller에게 보고한다.
    """
    def __init__(self, screen, shared_data):
        self.screen = screen
        self.font = shared_data['info_font']
        
        # --- UI Components (owned by View) ---
        self.background_manager = BackgroundManager()
        self.vfx_manager = VFXManager()
        self.battle_panel = BattlePanel()
        self.reward_popup = RewardPopup(shared_data)
        
        # --- [New] 사운드 제어 버튼 ---
        self.btn_mute_bgm = ToggleButton(
            SCREEN_WIDTH - 150, 20, 60, 40, "BGM OFF", "BGM ON", font_size=12
        )
        self.btn_mute_sfx = ToggleButton(
            SCREEN_WIDTH - 80, 20, 60, 40, "SFX OFF", "SFX ON", font_size=12
        )
        # ---

        self.fighter_views = []
        self.hovered_target_view = None # [Fix] 타겟 커서를 위해 추가

    def set_fighters(self, fighter_data_list):
        """Controller로부터 FighterData 리스트를 받아 FighterView를 생성/초기화합니다."""
        self.fighter_views.clear()
        for data in fighter_data_list:
            self.fighter_views.append(FighterView(data))

    def get_fighter_view(self, inv_id):
        """inv_id로 특정 FighterView를 찾습니다."""
        return next((v for v in self.fighter_views if v.data.inv_id == inv_id), None)

    def request_floating_text(self, inv_id, text, color):
        """BattleSystem의 요청에 따라 플로팅 텍스트를 생성합니다."""
        view = self.get_fighter_view(inv_id)
        if view:
            self.vfx_manager.add_text(view.rect.centerx, view.rect.y, text, color)

    def request_attack_animation(self, inv_id):
        view = self.get_fighter_view(inv_id)
        if view: view.attack_animation()

    def request_attack_sfx(self, attacker, action_type):
        """[New] 공격자의 sfx_type과 행동 종류에 따라 효과음을 재생합니다."""
        sfx_type = attacker.sfx_type.upper()
        volume = 0.8 # 기본 볼륨
        
        if action_type == 'attack':
            if attacker.is_enemy:
                filename = 'sfx_atk_hit_enemy.wav'
            elif sfx_type == 'SWORD':
                filename = 'sfx_atk_sword.wav'
            else:
                filename = 'sfx_atk_hit.wav'
        elif action_type == 'skill':
            volume = 1.0 # 스킬은 더 큰 소리로
            if sfx_type == 'SWORD':
                filename = 'sfx_skill_sword.wav'
            else:
                filename = 'sfx_skill_hit.wav'
        elif action_type == 'ultimate':
            volume = 1.2 # 필살기는 가장 큰 소리로
            if sfx_type == 'SWORD':
                filename = 'sfx_ult_sword.wav'
            else:
                filename = 'sfx_ult_hit.wav'
        else:
            return # 알 수 없는 액션 타입
        
        AudioManager().play_sfx(filename, volume=volume)

    def request_damage_animation(self, inv_id):
        view = self.get_fighter_view(inv_id)
        if view:
            view.take_damage_animation()
            self.vfx_manager.add_hit_effect(view.rect) # Placeholder 히트 이펙트 추가

    def are_death_animations_finished(self):
        """죽은 캐릭터들의 사라지는 애니메이션이 모두 끝났는지 확인합니다."""
        for f_view in self.fighter_views:
            # 데이터는 죽었는데(is_alive=False), 뷰의 알파값이 아직 남아있다면(alpha > 0)
            if not f_view.data.is_alive and f_view.alpha > 0:
                return False # 아직 애니메이션이 끝나지 않음
        return True # 모든 사망 애니메이션이 끝남

    def update_background(self, floor, stage_manager):
        """현재 층 정보에 따라 배경을 업데이트합니다."""
        stage_info = stage_manager.get_stage_info(floor)
        self.background_manager.update_background(floor, stage_info['biome'])


    def process_event(self, event, battle_state, battle_system):
        """Pygame 이벤트를 가공하여 Controller가 이해할 수 있는 Action으로 변환"""
        if event.type != pygame.MOUSEBUTTONDOWN:
            return None
        
        # --- [New] 사운드 버튼 클릭 처리 ---
        if self.btn_mute_bgm.rect.collidepoint(event.pos):
            AudioManager().toggle_bgm()
            self.btn_mute_bgm.toggle()
            return {"type": "UI_ACTION", "action": "TOGGLE_BGM"}
        if self.btn_mute_sfx.rect.collidepoint(event.pos):
            AudioManager().toggle_sfx()
            self.btn_mute_sfx.toggle()
            return {"type": "UI_ACTION", "action": "TOGGLE_SFX"}
        # ---

        mouse_pos = event.pos
        is_right_click = (event.button == 3)

        # 패배/에러 화면에서는 로비로 돌아가는 액션만 처리
        if battle_state in ["DEFEAT", "ERROR"]:
            return {"type": "SCENE_ACTION", "action": "GO_LOBBY"}

        # 보상 팝업 처리
        if battle_state in ["VICTORY", "VICTORY_FADE_OUT"]:
            return self.reward_popup.handle_click(mouse_pos)

        # [Task 3] 행동할 아군 캐릭터 선택 처리
        if battle_system.state == "WAIT_FOR_ACTOR" and not is_right_click:
            for f_view in self.fighter_views:
                if not f_view.data.is_enemy and f_view.data.is_alive and f_view.rect.collidepoint(mouse_pos):
                    return {"type": "BATTLE_ACTION", "action": "ACTOR_CLICK", "fighter": f_view.data}

        # 전투 커맨드 패널 버튼 처리 (좌클릭 전용)
        if battle_system.state == "COMMAND_INPUT" and not is_right_click:
            action = self.battle_panel.handle_event(event)
            if action:
                return {"type": "BATTLE_ACTION", "action": action}
        
        # 타겟팅 처리
        elif battle_system.state == "TARGET_SELECTION":
            if is_right_click:
                return {"type": "BATTLE_ACTION", "action": "CANCEL_TARGETING"}
            else:
                for f_view in self.fighter_views:
                    if f_view.data.is_enemy and f_view.data.is_alive and f_view.rect.collidepoint(mouse_pos):
                        return {"type": "BATTLE_ACTION", "action": "TARGET_CLICK", "fighter": f_view.data}
        
        return None

    def _update_battle_panel(self, battle_system):
        """ [FIXED] battle_panel에 최신 정보를 업데이트합니다. """
        if not battle_system: return
        
        # [Fix] 'active_fighter_idx' 대신 'current_fighter'를 사용합니다.
        active_fighter = battle_system.current_fighter

        # [Fix] 'is_targeting' 및 'target_cursor_idx'가 제거되었으므로,
        # 타겟 정보는 일단 비워두어 크래시를 방지합니다.
        target_fighter = None

        self.battle_panel.update_info(
            battle_system.get_player_fighters(), 
            battle_system.get_enemy_fighters(), 
            active_fighter=active_fighter, 
            target_fighter=target_fighter
        )

    def update(self, dt):
        """화면에 표시되는 모든 View 컴포넌트를 업데이트합니다."""
        self.vfx_manager.update()
        for f_view in self.fighter_views:
            f_view.update(dt)
        
        # --- [New] 사운드 버튼 상태 동기화 ---
        audio_manager = AudioManager()
        self.btn_mute_bgm.is_on = audio_manager.bgm_muted
        self.btn_mute_sfx.is_on = audio_manager.sfx_muted
        # ---


    def draw(self, battle_system, floor, battle_state):
        """Controller로부터 받은 데이터를 기반으로 화면의 모든 요소를 그립니다."""
        # 그리기 전, 최신 시스템 상태를 기반으로 UI 컴포넌트 정보 업데이트
        self._update_battle_panel(battle_system)

        # [Fix] 타겟 커서를 위해 마우스 호버 상태를 매 프레임 확인
        self.hovered_target_view = None
        if battle_system and battle_system.state == "TARGET_SELECTION":
            mouse_pos = pygame.mouse.get_pos()
            for f_view in self.fighter_views:
                if f_view.data.is_enemy and f_view.data.is_alive and f_view.rect.collidepoint(mouse_pos):
                    self.hovered_target_view = f_view
                    break

        self.background_manager.draw(self.screen)
        
        # 기본 정보 (층, 로그 메시지)
        floor_font = pygame.font.SysFont("malgungothic", 24, bold=True)
        self.screen.blit(floor_font.render(f"Floor: {floor}F", True, GOLD), (20, 20))

        # --- [New] 사운드 버튼 그리기 ---
        mouse_pos = pygame.mouse.get_pos()
        self.btn_mute_bgm.check_hover(mouse_pos)
        self.btn_mute_sfx.check_hover(mouse_pos)
        self.btn_mute_bgm.draw(self.screen)
        self.btn_mute_sfx.draw(self.screen)
        # ---
        
        log_msg_text = battle_system.log_message if battle_system else "Loading..."
        msg = self.font.render(log_msg_text, True, WHITE)
        msg_rect = msg.get_rect(center=(SCREEN_WIDTH//2, 40))
        pygame.draw.rect(self.screen, (0,0,0,150), (msg_rect.x-10, msg_rect.y-5, msg_rect.width+20, msg_rect.height+10), border_radius=5)
        self.screen.blit(msg, msg_rect)

        # 캐릭터(Fighter) 그리기 및 레벨 HUD
        for f_view in self.fighter_views:
            f_view.draw(self.screen)
            # Draw level HUD
            if f_view.data.is_alive:
                level_text = f"[Lv.{f_view.data.level}]"
                level_font = pygame.font.SysFont("malgungothic", 18, bold=True)
                level_surf = level_font.render(level_text, True, WHITE)
                level_rect = level_surf.get_rect(center=(f_view.rect.centerx, f_view.rect.top - 20))
                
                bg_rect = level_rect.inflate(8, 4)
                pygame.draw.rect(self.screen, (0,0,0,180), bg_rect, border_radius=5)

                self.screen.blit(level_surf, level_rect)

        # 타겟팅 커서 그리기
        self._draw_target_cursor(battle_system)
        
        # 전투 UI 패널 그리기 (특정 상태에서는 숨김)
        if battle_state not in ["VICTORY", "DEFEAT", "ERROR", "REWARD_APPLIED"]:
                self.battle_panel.draw(self.screen)

        # VFX(플로팅 텍스트, 히트 이펙트 등) 그리기
        self.vfx_manager.draw(self.screen)

        # 결과 팝업 그리기
        if battle_state == "VICTORY":
            self.reward_popup.draw(self.screen)
        elif battle_state == "DEFEAT":
            self._draw_end_screen("패배... (클릭하여 로비로)", RED)
        elif battle_state == "ERROR":
            self._draw_end_screen("오류 발생 (클릭하여 로비로)", RED)

    def _draw_target_cursor(self, battle_system):
        """[FIXED] 마우스 위치를 기반으로 타겟팅 커서를 그립니다."""
        if not battle_system or battle_system.state != "TARGET_SELECTION" or not self.hovered_target_view:
            return
            
        target_rect = self.hovered_target_view.rect
        pos = (target_rect.centerx, target_rect.top - 20)
        points = [(pos[0], pos[1]), (pos[0] - 10, pos[1] - 15), (pos[0] + 10, pos[1] - 15)]
        pygame.draw.polygon(self.screen, GOLD, points)

    def _draw_end_screen(self, text, color):
        """게임 종료(패배, 에러) 화면을 그립니다."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); overlay.set_alpha(200); overlay.fill(BLACK)
        self.screen.blit(overlay, (0,0))
        msg = self.font.render(text, True, color)
        self.screen.blit(msg, msg.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))
