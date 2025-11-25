import pygame
import random
import sqlite3
import os
from config import *
from ui.components import Button
from game_systems.stage_manager import StageManager 

class Fighter:
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
        self.offset_x = random.randint(-10, 10)
        self.action_timer = 15

    def attack_animation(self):
        direction = -1 if self.is_enemy else 1
        self.offset_x = 50 * direction
        self.action_timer = 20

    def update(self):
        if self.action_timer > 0:
            self.action_timer -= 1
            if self.action_timer == 0: self.offset_x = 0
        if self.hp == 0: self.is_dead = True

    def draw(self, screen):
        if self.is_dead: return
        draw_rect = self.rect.copy()
        draw_rect.x += self.offset_x
        
        if self.image: screen.blit(self.image, draw_rect)
        else:
            color = RED if self.is_enemy else BLUE
            pygame.draw.rect(screen, color, draw_rect)
            font = pygame.font.SysFont("malgungothic", 12)
            screen.blit(font.render(self.name, True, WHITE), (draw_rect.x, draw_rect.y + 40))

        bar_width = 100
        fill_width = int((self.hp / self.max_hp) * bar_width) if self.max_hp > 0 else 0
        hp_color = GREEN if (self.hp/self.max_hp) > 0.6 else (RED if (self.hp/self.max_hp) < 0.3 else (255, 255, 0))
        
        pygame.draw.rect(screen, GRAY, (draw_rect.x, draw_rect.y - 15, bar_width, 10))
        pygame.draw.rect(screen, hp_color, (draw_rect.x, draw_rect.y - 15, fill_width, 10))
        pygame.draw.rect(screen, WHITE, (draw_rect.x, draw_rect.y - 15, bar_width, 10), 1)

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
            cursor.execute("""
                SELECT c.name, c.hp, c.hp, c.atk, c.agi, c.image 
                FROM inventory i JOIN characters c ON i.char_id = c.id
                WHERE i.user_id = 'son_01' AND i.is_selected = 1
            """)
            rows = cursor.fetchall()
            
            # 선택된 캐릭터가 없으면 랜덤 2명
            if not rows:
                cursor.execute("""
                    SELECT c.name, c.hp, c.hp, c.atk, c.agi, c.image 
                    FROM inventory i JOIN characters c ON i.char_id = c.id
                    WHERE i.user_id = 'son_01' LIMIT 2
                """)
                rows = cursor.fetchall()

            if rows:
                self.mode = "NORMAL"
                for r in rows[:2]: 
                    self.party_data.append({"name": r[0], "hp": r[1], "max_hp": r[2], "atk": r[3], "agi": r[4], "image": r[5]})
            else:
                self.mode = "TUTORIAL"
        except: self.mode = "TUTORIAL"
        finally: conn.close()

        if self.mode == "TUTORIAL":
            self.party_data = [{"name": "아들", "hp": 100, "max_hp": 100, "atk": 20, "agi": 15, "image": "son.png"}]

    def save_party_status(self):
        for fighter in self.fighters:
            if not fighter.is_enemy:
                for data in self.party_data:
                    if data["name"] == fighter.name: data["hp"] = fighter.hp; break

    def full_restore_party(self):
        for data in self.party_data:
            data["hp"] = data["max_hp"]
        self.log_message = "보스 클리어! 파티가 완전 회복되었습니다!"

    def setup_battle(self):
        # 10층 단위 보스전 직후 완전 회복
        if (self.floor - 1) % 10 == 0 and self.floor > 1:
            self.full_restore_party()

        self.fighters.clear()
        self.battle_state = "FIGHTING"
        
        # 1. 아군 배치
        start_y = 350 if len(self.party_data) == 1 else 300
        for idx, data in enumerate(self.party_data):
            # [버그 수정] HP가 0 이하면 제외 (HP 1 강제 변환 로직 제거)
            current_hp = data["hp"]
            
            # 일반 모드에서 죽은 캐릭터는 스폰하지 않음
            if self.mode != "TUTORIAL" and current_hp <= 0:
                continue
            
            # 튜토리얼 등 특수 상황용 안전장치
            if self.mode == "TUTORIAL" and current_hp <= 0:
                current_hp = 1

            f = Fighter(200, start_y + (idx * 150), data["name"], False, current_hp, data["max_hp"], data["atk"], data["agi"], data["image"])
            self.fighters.append(f)

        # 2. 적군 배치
        if self.mode == "TUTORIAL":
            self.log_message = "!!! 최종 보스 출현 !!!"
            self.fighters.append(Fighter(900, 350, "최종 보스", True, 50000, 50000, 9999, 10, "oni_boss.png"))
        else:
            stage_info = self.stage_manager.get_stage_info(self.floor)
            biome, tier = stage_info['biome'], stage_info['tier']
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            enemies_to_spawn = []

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
                name, hp, atk, agi, img = e[1], int(e[6]*scale), int(e[7]*scale), int(e[9]), e[11]
                y_pos = 350 if len(enemies_to_spawn) == 1 else 300 + i * 150
                self.fighters.append(Fighter(900, y_pos, name, True, hp, hp, atk, agi, img))
        
        self.turn_queue = sorted(self.fighters, key=lambda f: f.agi, reverse=True)

    def get_alive_targets(self, is_enemy_team):
        return [f for f in self.fighters if f.is_enemy == is_enemy_team and not f.is_dead]

    def process_reward(self, reward_code):
        for data in self.party_data:
            # 사망자는 보상 제외
            if data["hp"] <= 0:
                continue

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
        
        if not self.get_alive_targets(False):
            self.battle_state = "DEFEAT"
            self.log_message = "패배..." if self.mode != "TUTORIAL" else "..."
            return

        if not self.get_alive_targets(True):
            if self.battle_state != "VICTORY":
                self.battle_state = "VICTORY"
                self.save_party_status()
            return

        self.turn_timer += 1
        if self.turn_timer < 30: return 
        if not self.turn_queue: self.turn_queue = sorted([f for f in self.fighters if not f.is_dead], key=lambda f: f.agi, reverse=True)
        if not self.turn_queue: return 

        attacker = self.turn_queue.pop(0)
        if attacker.is_dead: return
        targets = self.get_alive_targets(not attacker.is_enemy)
        if targets:
            target = random.choice(targets)
            dmg = attacker.atk if not (self.mode=="TUTORIAL" and attacker.is_enemy) else 9999
            target.take_damage(dmg)
            attacker.attack_animation()
            self.log_message = f"{attacker.name} -> {target.name} ({dmg})"
            self.turn_timer = 0
            
    def handle_event(self, event):
        if self.battle_state == "VICTORY" and event.type == pygame.MOUSEBUTTONDOWN:
            reward = self.reward_popup.handle_click(event.pos)
            if reward: self.process_reward(reward)

    def draw(self):
        self.screen.fill((30, 30, 30))
        txt = "TUTORIAL" if self.mode == "TUTORIAL" else f"{self.floor}F"
        self.screen.blit(self.font.render(f"Floor: {txt}", True, (255, 255, 0)), (20, 20))
        
        msg = self.font.render(self.log_message, True, WHITE)
        self.screen.blit(msg, msg.get_rect(center=(SCREEN_WIDTH//2, 80)))
        
        for f in self.fighters: f.draw(self.screen)
        
        if self.battle_state == "VICTORY": self.reward_popup.draw(self.screen)
        elif self.battle_state == "DEFEAT":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); overlay.set_alpha(200); overlay.fill(BLACK)
            self.screen.blit(overlay, (0,0))
            lose = self.font.render("패배... (클릭하여 로비로)", True, RED)
            self.screen.blit(lose, lose.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))