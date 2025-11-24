import pygame
import random
import os
from config import *
from ui.components import Button

class Fighter:
    """전투 객체"""
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

        # [이미지 로딩 로직 개선]
        if image_path:
            full_path = os.path.join(ASSETS_DIR, "images", image_path)
            
            # 파일이 실제로 있는지 확인
            if os.path.exists(full_path):
                try:
                    loaded_img = pygame.image.load(full_path).convert_alpha() # 투명 배경 지원
                    # [품질 개선] scale -> smoothscale로 변경 (훨씬 부드럽게 나옴)
                    self.image = pygame.transform.smoothscale(loaded_img, (100, 100))
                    print(f"[System] 이미지 로드 성공: {name} -> {image_path}")
                except Exception as e:
                    print(f"[Error] 이미지 로드 실패 ({image_path}): {e}")
                    self.image = None
            else:
                print(f"[Warning] 이미지를 찾을 수 없음: {full_path} (CSV 파일명과 확장자 .jpg/.png를 확인하세요)")
                self.image = None

    def take_damage(self, damage):
        self.hp -= damage
        if self.hp < 0: self.hp = 0
        self.offset_x = random.randint(-5, 5)
        self.action_timer = 10

    def attack_animation(self):
        direction = -1 if self.is_enemy else 1
        self.offset_x = 30 * direction
        self.action_timer = 20

    def update(self):
        if self.action_timer > 0:
            self.action_timer -= 1
            if self.action_timer == 0: self.offset_x = 0
        if self.hp == 0: self.is_dead = True

    def draw(self, screen):
        if self.is_dead: return
        
        # 흔들림 효과 적용 좌표
        draw_rect = self.rect.copy()
        draw_rect.x += self.offset_x
        
        # 1. 그림 그리기 (이미지가 있으면 이미지, 없으면 사각형)
        if self.image:
            screen.blit(self.image, draw_rect)
        else:
            # 이미지가 없을 때 (Placeholder)
            color = RED if self.is_enemy else BLUE
            pygame.draw.rect(screen, color, draw_rect)
            
            # 이름 표시
            font = pygame.font.SysFont("malgungothic", 12)
            name_surf = font.render(self.name, True, WHITE)
            screen.blit(name_surf, (draw_rect.x, draw_rect.y + 40))

        # 2. HP 바 그리기
        bar_width = 100
        # 최대 체력이 0인 경우 방어 로직
        if self.max_hp > 0:
            hp_ratio = self.hp / self.max_hp
            fill_width = int(hp_ratio * bar_width)
        else:
            fill_width = 0
            hp_ratio = 0

        # 체력 상태에 따른 색상 (초록 -> 노랑 -> 빨강)
        if hp_ratio > 0.6: hp_color = GREEN
        elif hp_ratio > 0.3: hp_color = (255, 255, 0) # Yellow
        else: hp_color = RED
        
        # 바 배경
        pygame.draw.rect(screen, GRAY, (draw_rect.x, draw_rect.y - 15, bar_width, 10))
        # 바 채우기
        pygame.draw.rect(screen, hp_color, (draw_rect.x, draw_rect.y - 15, fill_width, 10))
        # 바 테두리
        pygame.draw.rect(screen, WHITE, (draw_rect.x, draw_rect.y - 15, bar_width, 10), 1)

class RewardPopup:
    """보상 선택 창"""
    def __init__(self):
        self.font = pygame.font.SysFont("malgungothic", 30, bold=True)
        self.bg_rect = pygame.Rect(SCREEN_WIDTH//2 - 250, 200, 500, 400)
        
        # 버튼 설정
        self.btn_heal = Button(SCREEN_WIDTH//2 - 200, 300, 400, 50, "[회복] 체력 30% 회복", "REWARD_HEAL")
        self.btn_hp_up = Button(SCREEN_WIDTH//2 - 200, 370, 400, 50, "[성장] 최대 체력 +20", "REWARD_HP_UP")
        self.btn_atk_up = Button(SCREEN_WIDTH//2 - 200, 440, 400, 50, "[강화] 공격력 +5", "REWARD_ATK_UP")
        
        self.buttons = [self.btn_heal, self.btn_hp_up, self.btn_atk_up]

    def draw(self, screen):
        # 반투명 배경
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        screen.blit(overlay, (0,0))

        # 팝업 박스
        pygame.draw.rect(screen, (50, 50, 50), self.bg_rect, border_radius=15)
        pygame.draw.rect(screen, WHITE, self.bg_rect, 2, border_radius=15)

        # 타이틀
        title = self.font.render("승리! 보상을 선택하세요", True, (255, 215, 0))
        title_rect = title.get_rect(center=(SCREEN_WIDTH//2, 240))
        screen.blit(title, title_rect)

        # 버튼 그리기
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
        self.log_message = "전투 시작!"
        self.font = pygame.font.SysFont("malgungothic", 20)
        
        self.battle_state = "FIGHTING" 
        self.reward_popup = RewardPopup()
        
        self.floor = 1 
        
        self.party_data = []
        self.init_party()
        
        self.setup_battle()

    def init_party(self):
        """초기 파티 구성 (CSV 파일명과 일치해야 함!)"""
        # [중요] 여기 있는 img 값이 CSV 파일명과 똑같아야 합니다.
        self.party_data = [
            {"name": "마리오", "hp": 120, "max_hp": 120, "atk": 20, "agi": 10, "img": "mario.jpg"},
            {"name": "탄지로", "hp": 150, "max_hp": 150, "atk": 25, "agi": 15, "img": "tanjiro.jpg"}, # 여기도 tanjiro.jpg로 바꿔야 할 수 있음
            {"name": "피카츄", "hp": 100, "max_hp": 100, "atk": 35, "agi": 25, "img": "pikachu.jpg"}  # 여기도 pikachu.jpg로 바꿔야 할 수 있음
        ]

    def save_party_status(self):
        """전투 종료 시 현재 체력 저장"""
        for fighter in self.fighters:
            if not fighter.is_enemy:
                for data in self.party_data:
                    if data["name"] == fighter.name:
                        data["hp"] = fighter.hp
                        break

    def setup_battle(self):
        """전투 배치"""
        self.fighters.clear()
        self.battle_state = "FIGHTING"
        self.log_message = f"{self.floor}층 - 적이 나타났다!"

        # 아군 생성
        for idx, data in enumerate(self.party_data):
            current_hp = data["hp"] if data["hp"] > 0 else 1 
            
            f = Fighter(200, 200 + (idx * 150), 
                        data["name"], False, 
                        current_hp, data["max_hp"], 
                        data["atk"], data["agi"], 
                        data["img"]) # 여기서 이미지를 로드함
            self.fighters.append(f)

        # 적군 생성 (임시 이미지 사용)
        hp_bonus = (self.floor - 1) * 20
        atk_bonus = (self.floor - 1) * 3
        
        # 적군 이미지가 없으면 사각형으로 나오게 됨
        if self.floor % 10 == 0:
            self.fighters.append(Fighter(900, 350, f"{self.floor}층 보스", True, 500+hp_bonus, 500+hp_bonus, 30+atk_bonus, 10, "oni_boss.png"))
            self.log_message = f"!!! {self.floor}층 보스 출현 !!!"
        else:
            enemy_count = random.randint(2, 3)
            for i in range(enemy_count):
                y_pos = 200 + i * 150
                self.fighters.append(Fighter(900, y_pos, f"적 {i+1}", True, 80+hp_bonus, 80+hp_bonus, 10+atk_bonus, 8, "oni_low.png"))
        
        self.turn_queue = sorted(self.fighters, key=lambda f: f.agi, reverse=True)

    def get_alive_targets(self, is_enemy_team):
        return [f for f in self.fighters if f.is_enemy == is_enemy_team and not f.is_dead]

    def process_reward(self, reward_code):
        print(f"[System] 보상 선택: {reward_code}")
        
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
        if self.battle_state == "VICTORY": return

        for f in self.fighters: f.update()
        
        alive_allies = self.get_alive_targets(False)
        alive_enemies = self.get_alive_targets(True)
        
        if not alive_allies:
            self.battle_state = "DEFEAT"
            self.log_message = f"패배... {self.floor}층에서 전멸했습니다."
            return

        if not alive_enemies:
            if self.battle_state != "VICTORY":
                self.battle_state = "VICTORY"
                self.save_party_status()
            return

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
            target.take_damage(damage)
            attacker.attack_animation()
            self.log_message = f"{attacker.name}의 공격! > {target.name} {damage} 피해"
            self.turn_timer = 0
            
    def handle_event(self, event):
        if self.battle_state == "VICTORY":
            if event.type == pygame.MOUSEBUTTONDOWN:
                reward = self.reward_popup.handle_click(event.pos)
                if reward: self.process_reward(reward)

    def draw(self):
        self.screen.fill((30, 30, 30))
        
        floor_surf = self.font.render(f"현재 층: {self.floor}F", True, (255, 255, 0))
        self.screen.blit(floor_surf, (20, 20))

        msg_surf = self.font.render(self.log_message, True, WHITE)
        self.screen.blit(msg_surf, (SCREEN_WIDTH//2 - 150, 50))

        for fighter in self.fighters:
            fighter.draw(self.screen)

        if self.battle_state == "VICTORY":
            self.reward_popup.draw(self.screen)