import pygame
import random
import sqlite3
import os
from config import *
from ui.components import Button

class Fighter:
    """전투 객체 (캐릭터 및 적)"""
    def __init__(self, x, y, name, is_enemy, hp, max_hp, atk, agi, image_path=None):
        self.rect = pygame.Rect(x, y, 100, 100)
        self.name = name
        self.is_enemy = is_enemy
        self.hp = hp
        self.max_hp = max_hp
        self.atk = atk
        self.agi = agi
        self.is_dead = False
        self.image = None
        self.offset_x = 0
        self.action_timer = 0

        # 이미지 로딩
        if image_path:
            full_path = os.path.join(ASSETS_DIR, "images", image_path)
            if os.path.exists(full_path):
                try:
                    loaded_img = pygame.image.load(full_path).convert_alpha()
                    self.image = pygame.transform.smoothscale(loaded_img, (100, 100))
                except Exception as e:
                    print(f"[Error] 이미지 로드 실패 ({image_path}): {e}")
                    self.image = None
            else:
                # 이미지가 없으면 그냥 None 처리 (사각형 그려짐)
                self.image = None

    def take_damage(self, damage):
        self.hp -= damage
        if self.hp < 0: self.hp = 0
        self.offset_x = random.randint(-10, 10) # 피격 시 흔들림
        self.action_timer = 15

    def attack_animation(self):
        direction = -1 if self.is_enemy else 1
        self.offset_x = 50 * direction # 공격 시 앞으로 전진
        self.action_timer = 20

    def update(self):
        if self.action_timer > 0:
            self.action_timer -= 1
            if self.action_timer == 0: self.offset_x = 0
        if self.hp == 0: self.is_dead = True

    def draw(self, screen):
        if self.is_dead: return
        
        # 위치 보정 (애니메이션)
        draw_rect = self.rect.copy()
        draw_rect.x += self.offset_x
        
        # 1. 캐릭터 그리기
        if self.image:
            screen.blit(self.image, draw_rect)
        else:
            color = RED if self.is_enemy else BLUE
            pygame.draw.rect(screen, color, draw_rect)
            font = pygame.font.SysFont("malgungothic", 12)
            name_surf = font.render(self.name, True, WHITE)
            screen.blit(name_surf, (draw_rect.x, draw_rect.y + 40))

        # 2. HP 바
        bar_width = 100
        if self.max_hp > 0:
            hp_ratio = self.hp / self.max_hp
            fill_width = int(hp_ratio * bar_width)
        else:
            fill_width = 0
            hp_ratio = 0

        if hp_ratio > 0.6: hp_color = GREEN
        elif hp_ratio > 0.3: hp_color = (255, 255, 0)
        else: hp_color = RED
        
        pygame.draw.rect(screen, GRAY, (draw_rect.x, draw_rect.y - 15, bar_width, 10))
        pygame.draw.rect(screen, hp_color, (draw_rect.x, draw_rect.y - 15, fill_width, 10))
        pygame.draw.rect(screen, WHITE, (draw_rect.x, draw_rect.y - 15, bar_width, 10), 1)

class RewardPopup:
    """승리 보상 팝업"""
    def __init__(self):
        self.font = pygame.font.SysFont("malgungothic", 30, bold=True)
        self.bg_rect = pygame.Rect(SCREEN_WIDTH//2 - 250, 200, 500, 400)
        
        self.btn_heal = Button(SCREEN_WIDTH//2 - 200, 300, 400, 50, "[회복] 체력 30% 회복", "REWARD_HEAL")
        self.btn_hp_up = Button(SCREEN_WIDTH//2 - 200, 370, 400, 50, "[성장] 최대 체력 +20", "REWARD_HP_UP")
        self.btn_atk_up = Button(SCREEN_WIDTH//2 - 200, 440, 400, 50, "[강화] 공격력 +5", "REWARD_ATK_UP")
        
        self.buttons = [self.btn_heal, self.btn_hp_up, self.btn_atk_up]

    def draw(self, screen):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        screen.blit(overlay, (0,0))

        pygame.draw.rect(screen, (50, 50, 50), self.bg_rect, border_radius=15)
        pygame.draw.rect(screen, WHITE, self.bg_rect, 2, border_radius=15)

        title = self.font.render("전투 승리! 보상을 선택하세요", True, (255, 215, 0))
        title_rect = title.get_rect(center=(SCREEN_WIDTH//2, 240))
        screen.blit(title, title_rect)

        mouse_pos = pygame.mouse.get_pos()
        for btn in self.buttons:
            btn.check_hover(mouse_pos)
            btn.draw(screen)

    def handle_click(self, mouse_pos):
        for btn in self.buttons:
            if btn.is_clicked(mouse_pos):
                return btn.action_code
        return None

class BattleScene:
    def __init__(self, screen):
        self.screen = screen
        self.fighters = []
        self.turn_queue = []
        self.turn_timer = 0
        self.log_message = "전투 준비 중..."
        self.font = pygame.font.SysFont("malgungothic", 20)
        
        self.battle_state = "FIGHTING" # FIGHTING, VICTORY, DEFEAT
        self.reward_popup = RewardPopup()
        self.floor = 1 
        
        self.party_data = []
        self.mode = "NORMAL" # NORMAL or TUTORIAL

        # 파티 초기화 및 전투 설정
        self.init_party()
        self.setup_battle()

    def init_party(self):
        """DB에서 내 캐릭터를 불러오거나 튜토리얼 데이터를 주입"""
        self.party_data.clear()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 1. 내 인벤토리 조회
        try:
            cursor.execute("""
                SELECT c.name, c.hp, c.hp, c.atk, c.agi, c.image 
                FROM inventory i
                JOIN characters c ON i.char_id = c.id
                WHERE i.user_id = 'son_01'
            """)
            rows = cursor.fetchall()
            
            if rows:
                self.mode = "NORMAL"
                print(f"[Battle] 일반 모드 진입 - 보유 캐릭터 {len(rows)}명")
                # 최대 3명까지만 참전
                for r in rows[:3]:
                    self.party_data.append({
                        "name": r[0], "hp": r[1], "max_hp": r[2],
                        "atk": r[3], "agi": r[4], "image": r[5]
                    })
            else:
                # 인벤토리가 비어있으면 튜토리얼 강제 실행
                self.mode = "TUTORIAL"
                print("[Battle] 튜토리얼 모드 진입 (인벤토리 없음)")

        except Exception as e:
            print(f"[Error] 파티 로드 실패: {e}")
            self.mode = "TUTORIAL" # 에러나면 튜토리얼로 안전하게 처리
        
        finally:
            conn.close()

        # 2. 튜토리얼 모드일 경우 강제 데이터 주입 (엄마, 아빠, 아들)
        if self.mode == "TUTORIAL":
            self.party_data = [
                {"name": "엄마", "hp": 500, "max_hp": 500, "atk": 100, "agi": 50, "image": "mom.png"},
                {"name": "아빠", "hp": 450, "max_hp": 450, "atk": 95, "agi": 45, "image": "dad.png"},
                {"name": "아들", "hp": 480, "max_hp": 480, "atk": 98, "agi": 48, "image": "son.png"}
            ]

    def save_party_status(self):
        """다음 층으로 갈 때 현재 HP 상태 저장 (메모리 상에서만 유지)"""
        for fighter in self.fighters:
            if not fighter.is_enemy:
                for data in self.party_data:
                    if data["name"] == fighter.name:
                        data["hp"] = fighter.hp
                        break

    def setup_battle(self):
        """아군 및 적군 배치"""
        self.fighters.clear()
        self.battle_state = "FIGHTING"
        
        # 1. 아군 배치
        for idx, data in enumerate(self.party_data):
            current_hp = data["hp"] if data["hp"] > 0 else 1 
            f = Fighter(200, 200 + (idx * 150), 
                        data["name"], False, 
                        current_hp, data["max_hp"], 
                        data["atk"], data["agi"], 
                        data["image"])
            self.fighters.append(f)

        # 2. 적군 배치
        if self.mode == "TUTORIAL":
            # [튜토리얼] 최종 보스 (필패 이벤트)
            self.log_message = "!!! 경고: 강력한 적이 나타났다 !!!"
            boss = Fighter(900, 350, "최종 보스", True, 50000, 50000, 9999, 10, "oni_boss.png")
            self.fighters.append(boss)
        
        else:
            # [일반] 층수에 따른 적 생성
            hp_bonus = (self.floor - 1) * 20
            atk_bonus = (self.floor - 1) * 3
            
            if self.floor % 10 == 0:
                self.log_message = f"!!! {self.floor}층 보스 출현 !!!"
                self.fighters.append(Fighter(900, 350, f"{self.floor}층 보스", True, 500+hp_bonus*2, 500+hp_bonus*2, 30+atk_bonus, 10, "oni_boss.png"))
            else:
                self.log_message = f"{self.floor}층 - 적이 나타났다!"
                enemy_count = random.randint(2, 3)
                for i in range(enemy_count):
                    y_pos = 200 + i * 150
                    self.fighters.append(Fighter(900, y_pos, f"적 {i+1}", True, 80+hp_bonus, 80+hp_bonus, 10+atk_bonus, 8, "oni_low.png"))
        
        # 턴 순서 결정 (AGI 내림차순)
        self.turn_queue = sorted(self.fighters, key=lambda f: f.agi, reverse=True)

    def get_alive_targets(self, is_enemy_team):
        return [f for f in self.fighters if f.is_enemy == is_enemy_team and not f.is_dead]

    def process_reward(self, reward_code):
        # 보상 적용
        for data in self.party_data:
            if reward_code == "REWARD_HEAL":
                heal_amount = int(data["max_hp"] * 0.3)
                data["hp"] = min(data["hp"] + heal_amount, data["max_hp"])
            elif reward_code == "REWARD_HP_UP":
                data["max_hp"] += 20
                data["hp"] += 20
            elif reward_code == "REWARD_ATK_UP":
                data["atk"] += 5

        self.floor += 1
        self.setup_battle() 

    def update(self):
        """전투 로직 루프"""
        if self.battle_state in ["VICTORY", "DEFEAT"]: return

        for f in self.fighters: f.update()
        
        alive_allies = self.get_alive_targets(False)
        alive_enemies = self.get_alive_targets(True)
        
        # 1. 패배 판정
        if not alive_allies:
            self.battle_state = "DEFEAT"
            if self.mode == "TUTORIAL":
                self.log_message = "압도적인 힘 앞에 패배했습니다..."
            else:
                self.log_message = f"패배... {self.floor}층에서 전멸했습니다."
            return

        # 2. 승리 판정
        if not alive_enemies:
            if self.battle_state != "VICTORY":
                self.battle_state = "VICTORY"
                self.save_party_status()
            return

        # 3. 턴 처리
        self.turn_timer += 1
        if self.turn_timer < 30: return 
        
        if not self.turn_queue:
            self.turn_queue = sorted([f for f in self.fighters if not f.is_dead], key=lambda f: f.agi, reverse=True)
        if not self.turn_queue: return 

        attacker = self.turn_queue.pop(0)
        if attacker.is_dead: return

        targets = self.get_alive_targets(not attacker.is_enemy)
        if targets:
            target = random.choice(targets)
            damage = attacker.atk
            
            # [크리티컬] 튜토리얼 보스는 무조건 치명타
            if self.mode == "TUTORIAL" and attacker.is_enemy:
                damage = 9999
                self.log_message = f"최종 보스의 필살기! > {target.name} 즉사!"
            else:
                self.log_message = f"{attacker.name}의 공격! > {target.name} {damage} 피해"
                
            target.take_damage(damage)
            attacker.attack_animation()
            self.turn_timer = 0
            
    def handle_event(self, event):
        # 승리 시 보상 선택
        if self.battle_state == "VICTORY":
            if event.type == pygame.MOUSEBUTTONDOWN:
                reward = self.reward_popup.handle_click(event.pos)
                if reward: self.process_reward(reward)
        
        # 패배 시 로비로 돌아가기 (클릭 시)
        elif self.battle_state == "DEFEAT":
            if event.type == pygame.MOUSEBUTTONDOWN:
                # main.py에서 이 값을 확인하여 로비로 전환함
                pass 

    def draw(self):
        self.screen.fill((30, 30, 30))
        
        # 층수 표시
        floor_text = "TUTORIAL" if self.mode == "TUTORIAL" else f"{self.floor}F"
        floor_surf = self.font.render(f"현재 층: {floor_text}", True, (255, 255, 0))
        self.screen.blit(floor_surf, (20, 20))

        # 로그 메시지
        msg_surf = self.font.render(self.log_message, True, WHITE)
        msg_rect = msg_surf.get_rect(center=(SCREEN_WIDTH//2, 80))
        self.screen.blit(msg_surf, msg_rect)

        # 캐릭터 그리기
        for fighter in self.fighters:
            fighter.draw(self.screen)

        # 결과 창
        if self.battle_state == "VICTORY":
            self.reward_popup.draw(self.screen)
        elif self.battle_state == "DEFEAT":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(200)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0,0))
            
            txt = "패배했습니다... (클릭하여 로비로)"
            lose_surf = self.font.render(txt, True, RED)
            lose_rect = lose_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            self.screen.blit(lose_surf, lose_rect)