import pygame
import random
import sqlite3
import os
from config import *
from ui.components import Button 
from game_systems.stage_manager import StageManager 

def add_tickets(amount):
    """DB의 티켓 수를 증가/감소시키는 함수"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET tickets = tickets + ? WHERE user_id='son_01'", (amount,))
    conn.commit(); conn.close()

class Fighter:
    def __init__(self, x, y, name, is_enemy, hp, max_hp, mp, max_mp, sp_max, atk, agi, image_path=None, description=""):
        self.rect = pygame.Rect(x, y, 100, 100)
        self.name = name
        self.is_enemy = is_enemy
        
        # --- Stats ---
        self.hp = hp
        self.max_hp = max_hp
        self.mp = mp
        self.max_mp = max_mp
        self.sp = 0 # SP는 0부터 시작 (전투 중 충전)
        self.max_sp = sp_max
        self.atk = atk
        self.agi = agi
        self.description = description # 필살기 대사
        
        # --- State ---
        self.is_dead = False
        self.dying = False # 페이드아웃 연출용
        self.alpha = 255   # 페이드아웃 연출용
        self.image = None
        self.offset_x = 0
        self.action_timer = 0
        self.effect_text = "" # 데미지나 스킬명 띄우기용
        self.effect_timer = 0
        
        # 이미지 로드
        if image_path:
            full_path = os.path.join(ASSETS_DIR, "images", image_path)
            if os.path.exists(full_path):
                try:
                    loaded_img = pygame.image.load(full_path).convert_alpha()
                    self.image = pygame.transform.smoothscale(loaded_img, (100, 100))
                except: self.image = None
            else: self.image = None

    def take_damage(self, damage):
        self.hp -= damage
        if self.hp < 0: self.hp = 0

        # [피격 리액션]
        self.offset_x = random.randint(-10, 10)
        self.action_timer = 15

        # [SP 충전] 맞으면 분노 게이지 상승! (최대치의 10% + 랜덤)
        charge = int(self.max_sp * 0.1) + random.randint(1, 5)
        self.sp = min(self.sp + charge, self.max_sp)

        # [버그 수정] SP 충전 로직이 실행된 후 데미지를 표시해야 정상 작동
        self.show_effect(f"-{damage}", RED)

    def show_effect(self, text, color=WHITE):
        self.effect_text = text
        self.effect_color = color
        self.effect_timer = 90 # 1.5초 정도로 표시 시간 늘림

    def attack_animation(self):
        direction = -1 if self.is_enemy else 1
        self.offset_x = 50 * direction
        self.action_timer = 20

    def use_skill(self, target):
        """액티브 스킬: MP 소모, 1.5배 데미지"""
        cost = 20 # 스킬 코스트 (나중에 DB에서 가져오도록 확장 가능)
        self.mp -= cost
        dmg = int(self.atk * 1.5)
        target.take_damage(dmg)
        self.attack_animation()
        return dmg

    def use_ultimate(self, target):
        """필살기: SP 모두 소모, 2.5배 데미지"""
        self.sp = 0
        dmg = int(self.atk * 2.5)
        target.take_damage(dmg)
        self.attack_animation()
        return dmg

    def normal_attack(self, target):
        """일반 공격: MP 소량 회복"""
        dmg = self.atk
        target.take_damage(dmg)
        self.mp = min(self.mp + 5, self.max_mp) # 평타 치면 MP 5 회복
        self.attack_animation()
        return dmg

    def update(self):
        # 애니메이션 타이머
        if self.action_timer > 0:
            self.action_timer -= 1
            if self.action_timer == 0: self.offset_x = 0
        
        # 플로팅 텍스트 타이머
        if self.effect_timer > 0:
            self.effect_timer -= 1
        else:
            self.effect_text = ""

        # [수정] 페이드아웃 로직
        if self.hp == 0 and not self.dying:
            self.dying = True

        if self.dying:
            self.alpha -= 5 # 투명도 감소
            if self.alpha < 0:
                self.alpha = 0
                self.is_dead = True # 완전히 사라지면 사망 처리

    def draw(self, screen):
        # 완전히 사라진 캐릭터는 그리지 않음
        if self.is_dead and self.alpha == 0: return
        
        draw_rect = self.rect.copy()
        draw_rect.x += self.offset_x
        
        # 캐릭터 그리기
        if self.image:
            # [수정] 페이드아웃 효과 적용
            temp_image = self.image.copy()
            temp_image.set_alpha(self.alpha)
            screen.blit(temp_image, draw_rect)
        else:
            color = RED if self.is_enemy else BLUE
            pygame.draw.rect(screen, color, draw_rect)
            font = pygame.font.SysFont("malgungothic", 12)
            screen.blit(font.render(self.name, True, WHITE), (draw_rect.x, draw_rect.y + 40))

        # --- UI Bars (HP/MP/SP) ---
        bar_width = 100
        
        # 1. HP Bar (Green/Red)
        hp_ratio = self.hp / self.max_hp if self.max_hp > 0 else 0
        hp_color = GREEN if hp_ratio > 0.5 else (RED if hp_ratio < 0.2 else (255, 255, 0))
        pygame.draw.rect(screen, GRAY, (draw_rect.x, draw_rect.y - 15, bar_width, 8))
        pygame.draw.rect(screen, hp_color, (draw_rect.x, draw_rect.y - 15, int(bar_width * hp_ratio), 8))
        pygame.draw.rect(screen, BLACK, (draw_rect.x, draw_rect.y - 15, bar_width, 8), 1)

        # 2. MP Bar (Blue) - HP 바로 아래
        mp_ratio = self.mp / self.max_mp if self.max_mp > 0 else 0
        pygame.draw.rect(screen, GRAY, (draw_rect.x, draw_rect.y - 6, bar_width, 4))
        pygame.draw.rect(screen, (0, 100, 255), (draw_rect.x, draw_rect.y - 6, int(bar_width * mp_ratio), 4))
        
        # 3. SP Bar (Orange/Yellow) - MP 바로 아래
        sp_ratio = self.sp / self.max_sp if self.max_sp > 0 else 0
        sp_color = (255, 165, 0) if self.sp < self.max_sp else (255, 215, 0) # 꽉 차면 금색
        pygame.draw.rect(screen, GRAY, (draw_rect.x, draw_rect.y - 2, bar_width, 4))
        pygame.draw.rect(screen, sp_color, (draw_rect.x, draw_rect.y - 2, int(bar_width * sp_ratio), 4))

        # --- Floating Text (데미지 등) ---
        if self.effect_text:
            font = pygame.font.SysFont("malgungothic", 20, bold=True)
            text_surf = font.render(self.effect_text, True, self.effect_color)
            screen.blit(text_surf, (draw_rect.centerx - 20, draw_rect.y - 40))


class RewardPopup:
    def __init__(self):
        self.font = pygame.font.SysFont("malgungothic", 30, bold=True)
        self.bg_rect = pygame.Rect(SCREEN_WIDTH//2 - 250, 200, 500, 400) # 높이 조절
        self.buttons = []

    def generate_rewards(self, is_boss_floor):
        """스테이지 종류에 따라 보상 목록을 생성"""
        self.buttons.clear()
        
        # [수정] 전체 보상 풀 정의
        all_rewards = {
            "REWARD_HEAL": "[회복] 체력 30% 회복",
            "REWARD_HP_UP": "[성장] 최대 체력 +20",
            "REWARD_MP": "[회복] 마력(MP) 50% 회복",
            "REWARD_ATK_UP": "[강화] 공격력 +5",
            "REWARD_SP": "[충전] 시작 SP +30%",
            "REWARD_TICKET": "[행운] 뽑기 쿠폰 1개"
        }
        
        if is_boss_floor:
            all_rewards["REWARD_TICKET"] = "[대박] 뽑기 쿠폰 5개" # 보스 보상 강화

        # 3개의 보상을 랜덤으로 선택
        selected_codes = random.sample(list(all_rewards.keys()), 3)
        
        for i, code in enumerate(selected_codes):
            self.buttons.append(Button(SCREEN_WIDTH//2 - 200, 280 + i * 70, 400, 50, all_rewards[code], code))

        # [추가] 저장하고 나가기 버튼
        self.buttons.append(Button(SCREEN_WIDTH//2 - 200, 510, 400, 50, "[시스템] 저장하고 메인으로", "SAVE_AND_EXIT", color=(80, 80, 80), hover_color=(120, 120, 120)))


    def draw(self, screen):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180); overlay.fill(BLACK); screen.blit(overlay, (0,0))
        pygame.draw.rect(screen, (50, 50, 50), self.bg_rect, border_radius=15)
        pygame.draw.rect(screen, WHITE, self.bg_rect, 2, border_radius=15)
        title = self.font.render("전투 승리! 보상을 선택하세요", True, (255, 215, 0))
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, 240)))
        for btn in self.buttons: btn.check_hover(pygame.mouse.get_pos()); btn.draw(screen)

    def handle_click(self, mouse_pos):
        for btn in self.buttons:
            if btn.is_clicked(mouse_pos): return btn.action_code
        return None

class BattleScene:
    def __init__(self, screen):
        self.screen = screen
        self.fighters, self.turn_queue = [], []
        self.turn_timer = 0
        self.victory_timer = 0
        self.log_message = "전투 준비 중..."
        self.font = pygame.font.SysFont("malgungothic", 20) 
        self.battle_state = "FIGHTING"
        self.reward_popup = RewardPopup()
        self.floor = 1 
        self.party_data = []
        self.mode = "NORMAL"
        self.stage_manager = StageManager()
        self.init_party()
        self.setup_battle()

    def init_party(self):
        self.party_data.clear()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            # [DB 연동] mp, sp_max, description 컬럼 추가 로드
            # [수정] 필살기 대사는 description 대신 skill_name 컬럼을 사용
            # [수정] 저장된 현재 스탯(current_hp 등)을 불러오도록 쿼리 변경
            party_select_query = """
                SELECT c.name, c.hp, c.mp, c.sp_max, c.atk, c.agi, c.image, c.skill_name,
                       i.current_hp, i.current_mp, i.current_sp, i.current_atk, i.current_max_hp, i.id
                FROM inventory i JOIN characters c ON i.char_id = c.id
                WHERE i.user_id = 'son_01' AND i.is_selected = 1
            """
            cursor.execute(party_select_query)
            rows = cursor.fetchall()
            
            if not rows: # 선택된 캐릭터가 없으면
                # 인벤토리에서 2명을 강제로 선택 상태로 만듦
                cursor.execute("SELECT id FROM inventory WHERE user_id='son_01' LIMIT 2")
                chars_to_select = cursor.fetchall()
                if chars_to_select:
                    for char_id in chars_to_select:
                        cursor.execute("UPDATE inventory SET is_selected=1 WHERE id=?", (char_id[0],))
                    conn.commit()
                    # 캐릭터 정보를 다시 불러옴
                    cursor.execute(party_select_query) # [버그 수정] 저장된 쿼리 변수로 재실행
                    rows = cursor.fetchall()


            if rows:
                self.mode = "NORMAL"
                for r in rows[:2]: 
                    # 저장된 값이 있으면 사용, 없으면(None) 기본값 사용
                    max_hp = r[12] if r[12] is not None else r[1]
                    hp = r[8] if r[8] is not None else max_hp
                    mp = r[9] if r[9] is not None else r[2]
                    sp = r[10] if r[10] is not None else 0
                    atk = r[11] if r[11] is not None else r[4]

                    self.party_data.append({
                        "inv_id": r[13], # 인벤토리 ID 저장
                        "name": r[0], "hp": hp, "max_hp": max_hp, 
                        "mp": mp, "max_mp": r[2], "sp": sp, "sp_max": r[3],
                        "atk": atk, "agi": r[5], "image": r[6], "description": r[7] or r[0]
                    })
            else:
                self.mode = "TUTORIAL"
        except Exception as e:
            print(f"Party Init Error: {e}")
            self.mode = "TUTORIAL"
        finally: conn.close()

        if self.mode == "TUTORIAL":
            # 튜토리얼용 스펙
            self.party_data = [{"inv_id": -1, "name": "아들", "hp": 100, "max_hp": 100, "mp": 50, "max_mp": 50, "sp": 0, "sp_max": 100, "atk": 20, "agi": 15, "image": "son.png", "description": "아빠찬스!"}]

        # 현재 층 불러오기
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT current_floor FROM users WHERE user_id='son_01'")
        floor_data = cursor.fetchone()
        self.floor = floor_data[0] if floor_data else 1
        conn.close()


    def save_party_status(self):
        for fighter in self.fighters:
            if not fighter.is_enemy:
                for data in self.party_data:
                    if data["name"] == fighter.name: 
                        data["hp"] = fighter.hp
                        data["mp"] = fighter.mp
                        data["sp"] = fighter.sp
                        break

    def full_restore_party(self):
        for data in self.party_data:
            data["hp"] = data["max_hp"]
            data["mp"] = data["max_mp"]
        self.log_message = "보스 클리어! 파티가 완전 회복되었습니다!"

    def setup_battle(self):
        if (self.floor - 1) % 10 == 0 and self.floor > 1:
            self.full_restore_party()

        self.fighters.clear()
        self.battle_state = "FIGHTING"
        
        # 1. 아군 배치
        start_y = 350 if len(self.party_data) == 1 else 300
        for idx, data in enumerate(self.party_data):
            current_hp = data["hp"]
            if self.mode != "TUTORIAL" and current_hp <= 0: continue
            if self.mode == "TUTORIAL" and current_hp <= 0: current_hp = 1

            # Fighter 생성자에 mp, max_mp, sp_max, description 전달
            f = Fighter(200, start_y + (idx * 150), data["name"], False, 
                        current_hp, data["max_hp"], data["mp"], data["max_mp"], data["sp_max"], 
                        data["atk"], data["agi"], data["image"], data["description"])
            
            # 저장된 MP/SP 적용
            f.mp = data["mp"]
            f.sp = data["sp"]
            self.fighters.append(f)

        # 2. 적군 배치
        if self.mode == "TUTORIAL":
            self.log_message = "!!! 최종 보스 출현 !!!"
            # 보스도 MP/SP 가짐 (강력함)
            self.fighters.append(Fighter(900, 350, "최종 보스", True, 50000, 50000, 1000, 1000, 200, 9999, 10, "oni_boss.png", "세계멸망"))
        else:
            stage_info = self.stage_manager.get_stage_info(self.floor)
            biome, tier = stage_info['biome'], stage_info['tier']
            conn = sqlite3.connect(DB_PATH)
            # [개선] 인덱스 대신 컬럼 이름으로 접근하기 위해 row_factory 설정
            conn.row_factory = sqlite3.Row 
            cursor = conn.cursor()
            enemies_to_spawn = []

            # 보스/몹 로직 (기존과 동일)
            if stage_info['fixed_boss_id']:
                cursor.execute("SELECT * FROM enemies WHERE id=?", (stage_info['fixed_boss_id'],))
                boss_data = cursor.fetchone()
                if boss_data: enemies_to_spawn.append(boss_data)
            elif stage_info['is_boss_floor']:
                cursor.execute("SELECT * FROM enemies WHERE biome=? AND tier=? AND role='BOSS' ORDER BY RANDOM() LIMIT 1", (biome, tier))
                boss_data = cursor.fetchone()
                if not boss_data:
                     cursor.execute("SELECT * FROM enemies WHERE biome=? AND role='BOSS' ORDER BY tier ASC LIMIT 1", (biome,))
                     boss_data = cursor.fetchone()
                if boss_data:
                    self.log_message = f"!!! {boss_data['name']} (BOSS) 출현 !!!"
                    enemies_to_spawn.append(boss_data)
                else: 
                    cursor.execute("SELECT * FROM enemies WHERE biome=? AND tier=? AND role='MOB' ORDER BY RANDOM() LIMIT 2", (biome, tier))
                    enemies_to_spawn = cursor.fetchall()
            else: 
                self.log_message = f"{self.floor}층 [{biome}]"
                cursor.execute("SELECT * FROM enemies WHERE biome=? AND tier=? AND role='MOB' ORDER BY RANDOM() LIMIT 2", (biome, tier))
                enemies_to_spawn = cursor.fetchall()
            
            conn.close()

            scale = 1 + (self.floor - 1) * 0.05
            for i, e in enumerate(enemies_to_spawn):
                # Enemies 테이블엔 MP 컬럼이 없으므로 티어 기반 자동 생성
                # [개선] 인덱스(e[1]) 대신 컬럼명(e['name'])으로 데이터 접근
                name = e['name']
                hp = int(e['hp'] * scale)
                atk = int(e['atk'] * scale)
                agi = e['agi']
                img = e['image']
                role = e['role'] # [버그 수정] role 컬럼을 가져옴
                
                # 적 MP/SP 자동 설정
                enemy_mp = 50 * tier
                enemy_sp = 100
                
                y_pos = 350 if len(enemies_to_spawn) == 1 else 300 + i * 150
                # [버그 수정] 필살기 대사로 role 값을 전달
                self.fighters.append(Fighter(900, y_pos, name, True, hp, hp, enemy_mp, enemy_mp, enemy_sp, atk, agi, img, role))
        
        self.turn_queue = sorted(self.fighters, key=lambda f: f.agi, reverse=True)

    def get_alive_targets(self, is_enemy_team):
        return [f for f in self.fighters if f.is_enemy == is_enemy_team and not f.is_dead]

    def process_reward(self, reward_code):
        # [수정] 티켓 보상 처리 로직 추가
        if reward_code == "REWARD_TICKET":
            is_boss = self.stage_manager.get_stage_info(self.floor)['is_boss_floor']
            ticket_amount = 5 if is_boss else 1
            add_tickets(ticket_amount)

        for data in self.party_data:
            if data["hp"] <= 0: continue
            if reward_code == "REWARD_HEAL":
                heal = int(data["max_hp"] * 0.3)
                data["hp"] = min(data["hp"] + heal, data["max_hp"])
            elif reward_code == "REWARD_HP_UP": data["max_hp"] += 20; data["hp"] += 20
            elif reward_code == "REWARD_ATK_UP": data["atk"] += 5
            elif reward_code == "REWARD_SP":
                data["sp"] = min(data["sp"] + int(data["sp_max"] * 0.3), data["sp_max"])
            elif reward_code == "REWARD_MP":
                heal_mp = int(data["max_mp"] * 0.5)
                data["mp"] = min(data["mp"] + heal_mp, data["max_mp"])

        self.floor += 1
        self.setup_battle()

    def update(self):
        # [버그 수정] 페이드아웃이 정상 작동하도록 항상 모든 fighter를 업데이트
        for f in self.fighters:
            f.update()

        # [수정] 승리/패배 상태에서는 타이머 로직만 처리
        if self.battle_state in ["VICTORY", "DEFEAT", "VICTORY_TRANSITION"]:
            if self.battle_state == "VICTORY_TRANSITION":
                self.victory_timer += 1
                if self.victory_timer == 30: # 0.5초 후
                    self.log_message = "승리했습니다!"
                    # [수정] 보상 목록 생성
                    is_boss = self.stage_manager.get_stage_info(self.floor)['is_boss_floor']
                    self.reward_popup.generate_rewards(is_boss)
                elif self.victory_timer >= 60: # 1초 후
                    self.battle_state = "VICTORY"
            return # 아래 턴 로직 실행 방지

        # --- 승패 판정 ---
        alive_enemies = self.get_alive_targets(True)
        alive_party = self.get_alive_targets(False)

        if not alive_party:
            if self.battle_state == "FIGHTING":
                self.battle_state = "DEFEAT"
                self.log_message = "패배..." if self.mode != "TUTORIAL" else "..."
            return
        
        if not alive_enemies:
            if self.battle_state == "FIGHTING":
                self.battle_state = "VICTORY_TRANSITION" # 승리 연출 상태로 전환
                self.victory_timer = 0
                self.save_party_status()
            return

        # --- 턴 처리 ---
        self.turn_timer += 1
        if self.turn_timer < 120: return # 턴 딜레이를 2초로 늘림 (연출 감상용)
        
        if not self.turn_queue: self.turn_queue = sorted([f for f in self.fighters if not f.is_dead], key=lambda f: f.agi, reverse=True)
        if not self.turn_queue: return 

        attacker = self.turn_queue.pop(0)
        if attacker.is_dead: return
        
        targets = self.get_alive_targets(not attacker.is_enemy)
        if targets:
            target = random.choice(targets)
            
            # --- [AI 로직: 스킬 사용 결정] ---
            # 우선순위: 1.필살기 > 2.액티브 스킬 > 3.일반 공격
            dmg = 0 
            skill_name = "공격" # [버그 수정] 매 턴 시작 시 기본값으로 초기화
            
            # [AI 조건 0] 튜토리얼 보스는 즉사기 사용
            if self.mode == "TUTORIAL" and attacker.is_enemy:
                dmg = 9999
                target.take_damage(dmg)
                self.log_message = "최종 보스의 즉사 공격!"
            else:
                # [AI 조건 1] 필살기: SP가 100% 찼을 때 발동
                if attacker.sp >= attacker.max_sp:
                    dmg = attacker.use_ultimate(target)
                    skill_name = f"[{attacker.description}]" # 기술명 출력
                    attacker.show_effect("ULTIMATE!", (255, 215, 0)) # 금색 텍스트
                    
                # [AI 조건 2] 액티브 스킬: MP가 20 이상이고, 50% 확률을 통과했을 때 발동
                elif attacker.mp >= 20 and random.random() < 0.5:
                    dmg = attacker.use_skill(target)
                    skill_name = "강한 공격"
                    attacker.show_effect("SKILL!", (0, 100, 255)) # 파란 텍스트
                    
                # [AI 조건 3] 일반 공격: 위 조건에 모두 해당하지 않을 때 발동 (MP 회복)
                else:
                    dmg = attacker.normal_attack(target)
                    skill_name = "공격"
                
                self.log_message = f"{attacker.name}의 {skill_name}! -> {target.name} ({dmg})"
            
            self.turn_timer = 0
            
    def handle_event(self, event):
        if self.battle_state == "VICTORY" and event.type == pygame.MOUSEBUTTONDOWN:
            reward = self.reward_popup.handle_click(event.pos)
            if reward == "SAVE_AND_EXIT":
                return "SAVE_AND_EXIT" # main.py로 액션 코드 전달
            
            if reward: # 일반 보상 선택 시
                self.process_reward(reward)
                return None
        return None

    def draw(self):
        self.screen.fill((30, 30, 30))
        txt = "TUTORIAL" if self.mode == "TUTORIAL" else f"{self.floor}F"
        
        # 층수 표시
        floor_font = pygame.font.SysFont("malgungothic", 24, bold=True)
        self.screen.blit(floor_font.render(f"Floor: {txt}", True, (255, 255, 0)), (20, 20))
        
        # 중앙 로그 메시지 (배경 박스 추가해서 가독성 높임)
        msg = self.font.render(self.log_message, True, WHITE)
        msg_rect = msg.get_rect(center=(SCREEN_WIDTH//2, 80))
        pygame.draw.rect(self.screen, (0,0,0), (msg_rect.x-10, msg_rect.y-5, msg_rect.width+20, msg_rect.height+10), border_radius=5)
        self.screen.blit(msg, msg_rect)
        
        for f in self.fighters: f.draw(self.screen)
        
        if self.battle_state == "VICTORY": self.reward_popup.draw(self.screen)
        elif self.battle_state == "DEFEAT":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); overlay.set_alpha(200); overlay.fill(BLACK)
            self.screen.blit(overlay, (0,0))
            lose = self.font.render("패배... (클릭하여 로비로)", True, RED)
            self.screen.blit(lose, lose.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))
