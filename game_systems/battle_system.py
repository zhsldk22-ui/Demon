import sqlite3
import random
import config
from game_systems.level_manager import LevelManager

class BattleSystem:
    def __init__(self, fighter_data_list, battle_view):
        self.fighter_data_list = fighter_data_list
        self.battle_view = battle_view

        # --- 상태 변수 ---
        self.state = "PREPARING"
        self.log_message = ""
        self.player_actions = []
        self.turn_queue = []
        
        # [Task 3] 캐릭터 자유 선택을 위한 상태 변수
        self.commandable_fighters = [] # 이번 라운드에 명령 가능한 아군
        self.current_fighter = None    # 현재 명령을 내리고 있는 아군
        
        self.selected_action = None
        self.current_turn_fighter = None # 현재 턴을 실행 중인 캐릭터
        self.outcome = None # 'win', 'loss'

        self.start_player_command_round() # 초기 상태 진입

    def get_player_fighters(self, alive_only=False):
        return [f for f in self.fighter_data_list if not f.is_enemy and (not alive_only or f.is_alive)]

    def get_enemy_fighters(self, alive_only=False):
        return [f for f in self.fighter_data_list if f.is_enemy and (not alive_only or f.is_alive)]

    def _change_state(self, new_state):
        if self.state != new_state:
            print(f"[State Change] {self.state} -> {new_state}")
            self.state = new_state

    # [Task 3] Method to start the entire player command round.
    def start_player_command_round(self):
        """플레이어가 아군에게 명령을 내리는 라운드를 시작합니다."""
        for f in self.fighter_data_list:
            if f.is_alive:
                f.sp = min(f.sp + 5, f.max_sp)

        self.commandable_fighters = self.get_player_fighters(alive_only=True)
        if not self.commandable_fighters:
             self.start_battle_phase()
             return

        self._change_state("WAIT_FOR_ACTOR")
        self.current_fighter = None
        self.log_message = "명령할 아군을 선택하세요."

    # [Task 3] Method called by Scene when a fighter is clicked for command.
    def select_actor_for_command(self, actor):
        """플레이어가 선택한 캐릭터의 커맨드 입력을 시작합니다."""
        if self.state != "WAIT_FOR_ACTOR": return False
        if actor not in self.commandable_fighters:
            self.battle_view.request_floating_text(actor.inv_id, "명령 완료", (200, 200, 0))
            return False

        self.current_fighter = actor
        self._change_state("COMMAND_INPUT")
        self.log_message = f"{self.current_fighter.name}의 행동을 선택하세요."
        return True

    # [Task 3] Method to cancel the current action/targeting.
    def cancel_command_selection(self):
        """행동 선택을 취소하고 다시 캐릭터 선택 상태로 돌아갑니다."""
        # 타겟팅 중이었다면 커맨드 선택으로
        if self.state == "TARGET_SELECTION":
            self._change_state("COMMAND_INPUT")
            self.log_message = f"{self.current_fighter.name}의 행동을 선택하세요."
        # 커맨드 선택 중이었다면 캐릭터 선택으로
        elif self.state == "COMMAND_INPUT":
            self._change_state("WAIT_FOR_ACTOR")
            self.current_fighter = None
            self.log_message = "명령할 아군을 선택하세요."

    # [Task 3] Modified to use self.current_fighter.
    def start_targeting_phase(self, action):
        """타겟 선택 단계를 시작합니다."""
        if not self.current_fighter: return False
        
        if action == 'skill' and self.current_fighter.mp < config.SKILL_MP_COST:
            self.log_message = "MP가 부족합니다!"
            self.battle_view.request_floating_text(self.current_fighter.inv_id, "MP 부족", (255, 0, 0))
            return False
        elif action == 'ultimate' and self.current_fighter.sp < self.current_fighter.max_sp:
            self.log_message = "SP가 부족합니다!"
            self.battle_view.request_floating_text(self.current_fighter.inv_id, "SP 부족", (255, 0, 0))
            return False

        self.selected_action = action
        self._change_state("TARGET_SELECTION")
        self.log_message = "공격할 대상을 선택하세요. (우클릭: 취소)"
        return True

    # [Task 3] Modified to handle the new free-selection flow.
    def select_target_and_confirm(self, target_character):
        """View에서 전달받은 타겟으로 행동을 확정하고, 다음 입력을 준비합니다."""
        if self.state != "TARGET_SELECTION" or not self.current_fighter:
            return False

        enemy_fighters = self.get_enemy_fighters(alive_only=True)
        if target_character not in enemy_fighters:
            return False
            
        actor = self.current_fighter
        target = target_character

        self.player_actions.append((actor, self.selected_action, target))
        self.log_message = f"{actor.name} → {target.name} ({self.selected_action}) 행동 확정!"
        
        self.commandable_fighters.remove(actor)
        self.current_fighter = None

        if not self.commandable_fighters:
            self.start_battle_phase()
        else:
            self._change_state("WAIT_FOR_ACTOR")
            self.log_message = "명령할 아군을 선택하세요."
        return True

    def start_battle_phase(self):
        """배틀 실행 단계를 시작합니다."""
        self._change_state("BATTLE_EXECUTION")
        self.log_message = "전투 시작!"

        enemy_actions = []
        player_fighters = self.get_player_fighters(alive_only=True)
        if player_fighters:
            for enemy in self.get_enemy_fighters(alive_only=True):
                target = random.choice(player_fighters)
                action = "skill" if enemy.mp >= config.SKILL_MP_COST and random.random() < config.AI_SKILL_CHANCE else "attack"
                enemy_actions.append((enemy, action, target))

        all_actions = self.player_actions + enemy_actions
        self.turn_queue = sorted(all_actions, key=lambda x: x[0].agi, reverse=True)
        self.player_actions = []
        
        self.next_turn()

    def execute_turn(self):
        """큐에서 하나의 행동을 꺼내 실행합니다."""
        if not self.turn_queue:
            self.next_turn()
            return

        actor, action, target = self.turn_queue.pop(0)
        self.current_turn_fighter = actor

        if not actor.is_alive:
            self.next_turn()
            return

        # 만약 타겟이 죽었다면, 새로운 타겟을 찾음
        if not target.is_alive:
            new_targets = self.get_enemy_fighters(alive_only=True) if not actor.is_enemy else self.get_player_fighters(alive_only=True)
            if new_targets:
                target = random.choice(new_targets)
            else:
                self.next_turn() # 공격할 대상이 없으면 턴 종료
                return

        dmg = 0
        action_name = ""
        
        if action == "attack":
            self.battle_view.request_attack_sfx(actor, 'attack')
            dmg = actor.normal_attack(target)
            action_name = "공격"
        elif action == "skill":
            if actor.mp >= config.SKILL_MP_COST:
                self.battle_view.request_attack_sfx(actor, 'skill')
                dmg = actor.use_skill(target)
                action_name = "스킬"
                self.battle_view.request_floating_text(actor.inv_id, "SKILL!", (0, 100, 255))
            else:
                self.battle_view.request_attack_sfx(actor, 'attack')
                dmg = actor.normal_attack(target)
                action_name = "공격(MP부족)"
        elif action == "ultimate":
            if actor.sp >= actor.max_sp:
                self.battle_view.request_attack_sfx(actor, 'ultimate')
                dmg = actor.use_ultimate(target)
                action_name = f"[{actor.description}]"
                self.battle_view.request_floating_text(actor.inv_id, "ULTIMATE!", (255, 215, 0))
            else:
                self.battle_view.request_attack_sfx(actor, 'attack')
                dmg = actor.normal_attack(target)
                action_name = "공격(SP부족)"
        
        if dmg > 0:
            target.take_damage(dmg)
            self.battle_view.request_floating_text(target.inv_id, f"-{dmg}", (255, 0, 0))
            self.battle_view.request_damage_animation(target.inv_id)

        self.battle_view.request_attack_animation(actor.inv_id)
        
        self.log_message = f"{actor.name}의 {action_name}! → {target.name} ({dmg} 데미지)"
        return True

    def next_turn(self):
        """다음 턴을 준비합니다."""
        self.current_turn_fighter = None
        if not self.turn_queue:
            self._change_state("ROUND_OVER")
        else:
            self._change_state("BATTLE_EXECUTION")

    def check_battle_end(self):
        """전투 종료 조건을 확인하고 결과를 반환합니다."""
        if self.outcome: return True
        if not self.get_player_fighters(alive_only=True):
            self.outcome = 'loss'
        elif not self.get_enemy_fighters(alive_only=True):
            self.outcome = 'win'
        
        if self.outcome:
            self._change_state("BATTLE_ENDED")
            self.log_message = "승리!" if self.outcome == 'win' else "패배..."
            return True
        return False

    def process_victory(self, floor):
        """전투 승리 시 세션 경험치를 분배합니다."""
        base_exp = floor * config.BATTLE_EXP_REWARD_COEFF
        print(f"[Victory] 기본 경험치 {base_exp} 분배 시작.")

        survivors = self.get_player_fighters(alive_only=True)
        for fighter in survivors:
            exp_gain = base_exp
            if fighter.level > floor + config.LEVEL_PENALTY_THRESHOLD:
                exp_gain = 0
                print(f"[EXP Penalty] {fighter.name}(Lv.{fighter.level})는 {floor}층 보상을 받기에 레벨이 너무 높습니다.")
            
            if exp_gain > 0:
                level_ups = LevelManager.gain_session_exp(fighter, int(exp_gain))
                for lu_info in level_ups:
                    self.battle_view.request_floating_text(fighter.inv_id, "LEVEL UP!", (255, 215, 0))

        print("[Victory] 세션 경험치 분배 완료.")

    def update(self):
        """메인 로직 루프. Scene에서 호출됩니다."""
        if self.state == "BATTLE_ENDED":
            return None

        if self.state == "ROUND_OVER":
            if not self.check_battle_end():
                self.start_player_command_round()
        
        elif self.state == "BATTLE_EXECUTION":
            if self.execute_turn():
                return "TURN_DELAY"
        
        return None
