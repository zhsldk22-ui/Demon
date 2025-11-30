import pygame
import random
import os
from config import *
from game_systems.stage_manager import StageManager
from ui.audio_manager import AudioManager
from scenes.base_scene import BaseScene
from game_systems.battle_data_handler import BattleDataHandler
from game_systems.battle_system import BattleSystem
from ui.battle_view import BattleView # Import the new View
from game_systems.fighter_data import FighterData


class BattleScene(BaseScene):
    """
    [Controller]
    Model(BattleSystem)과 View(BattleView)를 연결하고 게임의 핵심 흐름을 제어.
    - `BattleSystem`에 명령을 내리고, 그 결과를 `BattleView`에 전달.
    - 직접 그리거나, 마우스 좌표를 계산하지 않음.
    """
    def __init__(self, screen, shared_data, mode='NEW_GAME'):
        super().__init__()
        self.screen = screen
        self.shared_data = shared_data
        self.mode = mode
        
        # --- [Task 2] Get or create a persistent StageManager ---
        self.stage_manager = shared_data.get('stage_manager')
        if not self.stage_manager:
            self.stage_manager = StageManager()
            shared_data['stage_manager'] = self.stage_manager

        # --- Model and View ---
        self.data_handler = BattleDataHandler(self.stage_manager)
        self.battle_system = None # Will be initialized in setup_battle
        self.view = BattleView(screen, shared_data)

        # --- Scene State ---
        self.battle_state = "PREPARING" 
        self.fighter_data_list = []
        self.party_data = []
        self.floor = self.shared_data.get('current_floor', 1)
        
        self.turn_delay_timer = 0
        self.reward_display_timer = 0
        self.log_message = "전투 준비 중..."


    def enter(self):
        """씬에 진입할 때 호출됩니다. 전투를 설정하고 뷰를 업데이트합니다."""
        self.setup_battle()
        self.view.update_background(self.floor, self.data_handler.stage_manager)

    def setup_battle(self):
        """[MODIFIED] 세션 데이터를 확인하여 전투를 준비하거나, 새로 데이터를 로드합니다."""
        try:
            # BGM 재생
            bgm_name = self.stage_manager.get_current_bgm_name(self.floor)
            AudioManager().play_bgm(bgm_name)

            # 기존 전투 준비 로직
            self.fighter_data_list.clear() # [Fix] vfx_manager로 변경
            self.view.vfx_manager.clear()

            session_fighters = self.stage_manager.session_party_data

            if session_fighters:
                # 세션 데이터가 있으면, 파티 정보는 그대로 사용하고 적만 새로 로드
                print(f"[System] {self.floor}층. 세션 데이터로 전투를 속행합니다.")
                self.fighter_data_list.extend(session_fighters)
                self.stage_manager.session_party_data = None  # 데이터 사용 후 초기화

                # 파티 로드를 건너뛰고 적 정보만 가져오는 기능이 없으므로, 기존 함수를 호출하되 파티 데이터는 무시
                _, enemy_list, self.floor = self.data_handler.setup_battle_data(self.floor, 'CONTINUE_FIGHT')
                
            else:
                # 세션 데이터가 없으면(첫 층), DB에서 모든 데이터를 로드
                print(f"[System] {self.floor}층. DB에서 새 데이터를 로드합니다.")
                party_data, enemy_list, new_floor = self.data_handler.setup_battle_data(self.floor, self.mode)
                
                self.party_data = party_data
                self.floor = new_floor
                self._place_party_fighters() # self.fighter_data_list에 아군 FighterData 추가
            
            # 공통 로직: 적 생성 및 시스템 초기화
            self._spawn_enemies_from_data(enemy_list)
            
            if self.mode == 'NEW_GAME':
                self.mode = 'CONTINUE' 

            self.battle_system = BattleSystem(self.fighter_data_list, self.view)
            self.view.set_fighters(self.fighter_data_list)
            self.battle_state = self.battle_system.state
            self.log_message = self.battle_system.log_message

        except Exception as e:
            print(f"[Critical Error] 전투 준비 중 오류 발생: {e}")
            self.battle_state = "ERROR"
            self.log_message = "전투 준비에 실패했습니다. 로비로 돌아갑니다."

    def update(self):
        """매 프레임 호출되는 메인 업데이트 로직."""
        self.view.update(0) # dt is not used yet, but good practice

        if self.turn_delay_timer > 0:
            self.turn_delay_timer -= 1
            return

        if self.battle_system and self.battle_system.state != "BATTLE_ENDED":
            result = self.battle_system.update()
            self.log_message = self.battle_system.log_message

            if result == "TURN_DELAY":
                self.turn_delay_timer = TURN_DELAY // 2
            
            if self.battle_system.state == "BATTLE_ENDED":
                if self.battle_system.outcome == 'win':
                    self.battle_state = "VICTORY_FADE_OUT" # 바로 승리 화면으로 가지 않고, 페이드 아웃 상태로 전환
                    self.log_message = "승리!"
                    self.battle_system.process_victory(self.floor) # [신규] 경험치 분배 로직 호출
                    self.save_party_status()
                    is_boss = self.data_handler.stage_manager.get_stage_info(self.floor)['is_boss_floor']
                    self.view.reward_popup.generate_rewards(is_boss) # Tell view to generate rewards
                else: # 'loss'
                    self.battle_state = "DEFEAT"
                    self.log_message = "패배..."
        
        if self.battle_state == "VICTORY_FADE_OUT":
            # View에게 모든 사망 애니메이션이 끝났는지 확인 요청
            if self.view.are_death_animations_finished():
                self.battle_state = "VICTORY" # 애니메이션이 끝나면 실제 승리 상태로 전환

        if self.battle_state == "REWARD_APPLIED":
            self.reward_display_timer -= 1
            if self.reward_display_timer <= 0:
                self.setup_battle()
                self.view.update_background(self.floor, self.data_handler.stage_manager)

    def handle_events(self, events, mouse_pos):
        """View로부터 받은 Action에 따라 Model(System)을 제어합니다."""
        if not self.battle_system: return
        
        for event in events:
            # 1. 이벤트를 View에 보내 Action으로 변환
            action = self.view.process_event(event, self.battle_state, self.battle_system)

            if not action:
                continue

            # 2. 변환된 Action에 따라 시스템 상태 변경
            action_type = action.get("type")
            action_code = action.get("action")

            if action_type == "SCENE_ACTION" and action_code == "GO_LOBBY":
                self.next_scene_name = "LOBBY"
                return

            if self.battle_state in ["VICTORY", "VICTORY_FADE_OUT"]:
                if action_code == "REWARD_SELECTED":
                    pass # 리워드 선택은 View/Controller에서 처리하고 System에 영향 없음
                elif action_code in ["NEXT_FLOOR", "SAVE_AND_EXIT"]:
                    if action.get("reward"): self.process_reward(action.get("reward"))
                    
                    player_fighters = self.battle_system.get_player_fighters()
                    
                    if action_code == "NEXT_FLOOR":
                        self.stage_manager.session_party_data = player_fighters
                        self.floor += 1
                        self.shared_data['current_floor'] = self.floor
                        self.save_run_state(self.floor)
                        self.battle_state = "REWARD_APPLIED"
                        self.reward_display_timer = 90
                    elif action_code == "SAVE_AND_EXIT":
                        self.stage_manager.session_party_data = None
                        self.shared_data['current_floor'] = 1
                        self.save_run_state(self.floor + 1)
                        self.next_scene_name = "LOBBY_SAVE"
                return

            if action_type == "BATTLE_ACTION":
                # [Task 3] 행동할 캐릭터를 선택하는 상태
                if self.battle_system.state == "WAIT_FOR_ACTOR":
                    if action_code == "ACTOR_CLICK":
                        clicked_fighter = action.get("fighter")
                        self.battle_system.select_actor_for_command(clicked_fighter)

                # [Task 3] 행동을 선택하는 상태
                elif self.battle_system.state == "COMMAND_INPUT":
                    if action_code: # attack, skill 등 버튼 액션
                        self.battle_system.start_targeting_phase(action_code)

                # [Task 3] 타겟을 선택하는 상태
                elif self.battle_system.state == "TARGET_SELECTION":
                    if action_code == "TARGET_CLICK":
                        clicked_fighter = action.get("fighter")
                        self.battle_system.select_target_and_confirm(clicked_fighter)
                    elif action_code == "CANCEL_TARGETING":
                        # 취소 시, 새 로직에 맞는 cancel_command_selection 호출
                        self.battle_system.cancel_command_selection()


    def draw(self, screen):
        """View에 그리기를 위임합니다."""
        self.view.draw(self.battle_system, self.floor, self.battle_state)
    
    # --- Data Handling Methods (Controller's Role) ---
    def save_party_status(self):
        """전투가 끝난 후, 살아남은 아군의 현재 스탯을 party_data에 저장합니다."""
        # This uses self.fighter_data_list, which is okay as controller holds this state
        alive_fighters = {f_data.inv_id: f_data for f_data in self.fighter_data_list if f_data.is_alive}
        for p_data in self.party_data:
            if p_data["inv_id"] in alive_fighters:
                f_data = alive_fighters[p_data["inv_id"]]
                p_data.update({"hp": f_data.hp, "mp": f_data.mp, "sp": f_data.sp, "atk": f_data.atk, "max_hp": f_data.max_hp})
            else: # 죽은 캐릭터 처리
                p_data["hp"] = 0

    def _place_party_fighters(self):
        """
        [MODIFIED] party_data를 기반으로 Fighter 객체를 생성하고 배치합니다.
        [Task 2] 이제 사망한 캐릭터도 생성하여 전투 세션에 포함시킵니다.
        """
        start_y = 350 if len(self.party_data) == 1 else 300
        for idx, data in enumerate(self.party_data):
            # [Task 2 Fix] 'hp <= 0' 체크를 제거하여 사망한 캐릭터도 FighterData로 만듦
            f_data = FighterData(200, start_y + (idx * 150), data["name"], False,
                        data["hp"], data["max_hp"], data["mp"], data["max_mp"], data["sp_max"],
                        data["atk"], data["agi"], data["image"], data["description"], data["inv_id"],
                        level=data["level"], exp=data["exp"], grade=data["grade"],
                        sfx_type=data["sfx_type"], skill_name=data["skill_name"], ult_name=data["ult_name"]
                        )
            f_data.sp = data["sp"]
            self.fighter_data_list.append(f_data)

    def _spawn_enemies_from_data(self, enemy_data_list):
        """data_handler로부터 받은 데이터로 적을 생성합니다."""
        stage_info = self.data_handler.stage_manager.get_stage_info(self.floor)
        
        if stage_info['is_boss_floor'] and enemy_data_list:
            self.log_message = f"!!! {enemy_data_list[0]['name']} (BOSS) 출현 !!!"
        else:
            self.log_message = f"{self.floor}층 [{stage_info['biome']}]"
            
        scale = 1 + (self.floor - 1) * 0.05
        for i, e_data in enumerate(enemy_data_list):
            hp, atk = int(e_data['hp'] * scale), int(e_data['atk'] * scale)
            y_pos = 350 if len(enemy_data_list) == 1 else 300 + i * 150
            self.fighter_data_list.append(FighterData(900, y_pos, e_data['name'], True, hp, hp, 50*stage_info['tier'], 50*stage_info['tier'], 100, atk, e_data['agi'], e_data['image'], e_data['role']))

    def process_reward(self, reward_code):
        """[FIXED] 선택된 보상을 '실제' 파티 데이터(FighterData 객체)에 적용합니다."""
        vfx_manager = self.view.vfx_manager # [Fix] vfx_manager로 변경
        
        if reward_code == "REWARD_TICKET":
            is_boss_floor = self.data_handler.stage_manager.get_stage_info(self.floor)['is_boss_floor']
            ticket_amount = self.data_handler.grant_ticket_reward(is_boss_floor)
            vfx_manager.add_text(SCREEN_WIDTH/2 - 100, SCREEN_HEIGHT/2, f"뽑기 쿠폰 +{ticket_amount}!", GOLD)
            return

        # [Fix] self.party_data(dict) 대신 self.battle_system의 실제 FighterData 객체를 수정합니다.
        player_fighters = self.battle_system.get_player_fighters()

        for fighter in player_fighters:
            # 살아있는 캐릭터에게만 보상 적용
            if not fighter.is_alive:
                continue

            fighter_view = self.view.get_fighter_view(fighter.inv_id)
            
            if reward_code == "REWARD_HEAL":
                heal_amount = int(fighter.max_hp * 0.3)
                # 최대 체력을 초과하지 않도록 실제 회복량 계산
                healed_amount = min(heal_amount, fighter.max_hp - fighter.hp)
                fighter.hp += healed_amount
                if fighter_view and healed_amount > 0:
                    vfx_manager.add_text(fighter_view.rect.centerx, fighter_view.rect.y, f"+{healed_amount}", GREEN)
            
            elif reward_code == "REWARD_HP_UP":
                fighter.max_hp += 20
                fighter.hp += 20 # 최대 체력이 늘어난만큼 현재 체력도 채워줌
                if fighter_view:
                    vfx_manager.add_text(fighter_view.rect.centerx, fighter_view.rect.y, "MAX HP +20", GOLD)
            
            elif reward_code == "REWARD_ATK_UP":
                fighter.atk += 5
                if fighter_view:
                    vfx_manager.add_text(fighter_view.rect.centerx, fighter_view.rect.y, "ATK +5", GOLD)

    def save_run_state(self, floor_to_save):
        """[수정] `FighterData` 객체 리스트를 전달하여 `agi`를 포함한 모든 스탯을 DB에 저장합니다."""
        player_fighters = self.battle_system.get_player_fighters()
        self.data_handler.save_run_state(floor_to_save, player_fighters)
