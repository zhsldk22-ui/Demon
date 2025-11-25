import pygame
import random
import sqlite3
import os
from config import *
from ui.components import Button
from game_systems.stage_manager import StageManager 

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

        # [플로팅 텍스트] 데미지 표시
        self.show_effect(f"-{damage}", RED)

    def show_effect(self, text, color=WHITE):
        self.effect_text = text
        self.effect_color = color
        self.effect_timer = 30 # 0.5초 정도 표시

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

        if self.hp == 0: self.is_dead = True

    def draw(self, screen):
        if self.is_dead: return
        
        draw_rect = self.rect.copy()
        draw_rect.x += self.offset_x
        
        # 캐릭터 그리기
        if self.image: screen.blit(self.image, draw_rect)
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
        self.bg_rect = pygame.Rect(SCREEN_WIDTH//2 - 250, 200, 500, 400)
        self.buttons = [
            Button(SCREEN_WIDTH//2 - 200, 300, 400, 50, "[회복] 체력 30% 회복", "REWARD_HEAL"),
            Button(SCREEN_WIDTH//2 - 200, 370, 400, 50, "[성장] 최대 체력 +20", "REWARD_HP_UP"),
            Button(SCREEN_WIDTH//2 - 200, 440, 400, 50, "[강화] 공격력 +5", "REWARD_ATK_UP")
        ]

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
            cursor.execute("""
                SELECT c.name, c.hp, c.hp, c.mp, c.mp, c.sp_max, c.atk, c.agi, c.image, c.description 
                FROM inventory i JOIN characters c ON i.char_id = c.id
                WHERE i.user_id = 'son_01' AND i.is_selected = 1
            """)
            rows = cursor.fetchall()
            
            if not rows: # 없으면 랜덤 2명
                cursor.execute("""
                    SELECT c.name, c.hp, c.hp, c.mp, c.mp, c.sp_max, c.atk, c.agi, c.image, c.description 
                    FROM inventory i JOIN characters c ON i.char_id = c.id
                    WHERE i.user_id = 'son_01' LIMIT 2
                """)
                rows = cursor.fetchall()

            if rows:
                self.mode = "NORMAL"
                for r in rows[:2]: 
                    # DB 순서: name(0), hp(1), max_hp(2), mp(3), max_mp(4), sp_max(5), atk(6), agi(7), img(8), desc(9)
                    self.party_data.append({
                        "name": r[0], "hp": r[1], "max_hp": r[2], 
                        "mp": r[3], "max_mp": r[4], "sp_max": r[5],
                        "atk": r[6], "agi": r[7], "image": r[8], "description": r[9]
                    })
            else:
                self.mode = "TUTORIAL"
        except Exception as e:
            print(f"Party Init Error: {e}")
            self.mode = "TUTORIAL"
        finally: conn.close()

        if self.mode == "TUTORIAL":
            # 튜토리얼용 스펙
            self.party_data = [{"name": "아들", "hp": 100, "max_hp": 100, "mp": 50, "max_mp": 50, "sp_max": 100, "atk": 20, "agi": 15, "image": "son.png", "description": "아빠찬스!"}]

    def save_party_status(self):
        for fighter in self.fighters:
            if not fighter.is_enemy:
                for data in self.party_data:
                    if data["name"] == fighter.name: 
                        data["hp"] = fighter.hp
                        data["mp"] = fighter.mp
                        # SP는 다음 층 가면 초기화? 아니면 유지? -> 일단 로그라이크니까 유지!
                        # data["sp"] = fighter.sp (구조상 복잡하니 일단 HP/MP만 유지)
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
            
            # [기존 MP 연동]
            f.mp = data["mp"] 
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
                    self.log_message = f"!!! {boss_data[1]} (BOSS) 출현 !!!"
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
                # name(1), hp(6), atk(7), agi(9), img(11) - 인덱스 확인 필요 (csv 기준)
                # 여기서는 database.py 스키마 기준: id(0), name(1), biome(2), attr(3), hp(4), atk(5), def(6), agi(7), exp(8), img(9)
                # !!! 주의: CSV와 DB 컬럼 순서가 다를 수 있으니 안전하게 이름으로 매핑하는게 좋으나 일단 인덱스 추정
                
                # DB 스키마: id, name, biome, attribute, hp, atk, def, agi, exp_reward, image_path
                name = e[1]
                hp = int(e[4]*scale)
                atk = int(e[5]*scale)
                agi = int(e[7])
                img = e[9]
                
                # 적 MP/SP 자동 설정
                enemy_mp = 50 * tier
                enemy_sp = 100
                
                y_pos = 350 if len(enemies_to_spawn) == 1 else 300 + i * 150
                self.fighters.append(Fighter(900, y_pos, name, True, hp, hp, enemy_mp, enemy_mp, enemy_sp, atk, agi, img, "강한 공격"))
        
        self.turn_queue = sorted(self.fighters, key=lambda f: f.agi, reverse=True)

    def get_alive_targets(self, is_enemy_team):
        return [f for f in self.fighters if f.is_enemy == is_enemy_team and not f.is_dead]

    def process_reward(self, reward_code):
        for data in self.party_data:
            if data["hp"] <= 0: continue
            if reward_code == "REWARD_HEAL":
                heal = int(data["max_hp"] * 0.3)
                data["hp"] = min(data["hp"] + heal, data["max_hp"])
            elif reward_code == "REWARD_HP_UP": data["max_hp"] += 20; data["hp"] += 20
            elif reward_code == "REWARD_ATK_UP": data["atk"] += 5
        self.floor += 1
        self.setup_battle() 

    def update(self):
        if self.battle_state in ["VICTORY", "DEFEAT"]: return
        for f in self.fighters: f.update()
        
        # 승패 판정
        if not self.get_alive_targets(False):
            self.battle_state = "DEFEAT"
            self.log_message = "패배..." if self.mode != "TUTORIAL" else "..."
            return
        if not self.get_alive_targets(True):
            if self.battle_state != "VICTORY":
                self.battle_state = "VICTORY"
                self.save_party_status()
            return

        # 턴 처리
        self.turn_timer += 1
        if self.turn_timer < 60: return # 턴 딜레이를 좀 늘림 (연출 감상용)
        
        if not self.turn_queue: self.turn_queue = sorted([f for f in self.fighters if not f.is_dead], key=lambda f: f.agi, reverse=True)
        if not self.turn_queue: return 

        attacker = self.turn_queue.pop(0)
        if attacker.is_dead: return
        
        targets = self.get_alive_targets(not attacker.is_enemy)
        if targets:
            target = random.choice(targets)
            
            # --- [AI 로직: 스킬 사용 결정] ---
            dmg = 0
            skill_name = "공격"
            
            # 1. 튜토리얼 적은 그냥 즉사기
            if self.mode == "TUTORIAL" and attacker.is_enemy:
                dmg = 9999
                target.take_damage(dmg)
                self.log_message = "최종 보스의 즉사 공격!"
            else:
                # 2. 필살기 (SP 100%)
                if attacker.sp >= attacker.max_sp:
                    dmg = attacker.use_ultimate(target)
                    skill_name = f"[{attacker.description}]" # 기술명 출력
                    attacker.show_effect("ULTIMATE!", (255, 215, 0)) # 금색 텍스트
                    
                # 3. 액티브 스킬 (MP 20 이상, 50% 확률)
                elif attacker.mp >= 20 and random.random() < 0.5:
                    dmg = attacker.use_skill(target)
                    skill_name = "강한 공격"
                    attacker.show_effect("SKILL!", (0, 100, 255)) # 파란 텍스트
                    
                # 4. 일반 공격
                else:
                    dmg = attacker.normal_attack(target)
                    skill_name = "공격"
                
                self.log_message = f"{attacker.name}의 {skill_name}! -> {target.name} ({dmg})"
            
            self.turn_timer = 0
            
    def handle_event(self, event):
        if self.battle_state == "VICTORY" and event.type == pygame.MOUSEBUTTONDOWN:
            reward = self.reward_popup.handle_click(event.pos)
            if reward: self.process_reward(reward)

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