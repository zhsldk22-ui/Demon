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
        
        # [NEW] 파티 데이터를 별도로 관리 (전투가 끝나도 유지되도록)
        self.party_data = []
        self.init_party() # 1층 시작 전 파티 초기화
        
        self.setup_battle()

    def init_party(self):
        """게임 시작 시 최초 파티 구성 (나중엔 로비에서 가져와야 함)"""
        # 딕셔너리 형태로 상태 관리
        self.party_data = [
            {"name": "마리오", "hp": 120, "max_hp": 120, "atk": 20, "agi": 10, "img": "mario.png"},
            {"name": "탄지로", "hp": 150, "max_hp": 150, "atk": 25, "agi": 15, "img": "tanjiro.png"},
            {"name": "피카츄", "hp": 100, "max_hp": 100, "atk": 35, "agi": 25, "img": "pikachu.png"}
        ]

    def save_party_status(self):
        """전투 종료 후 현재 체력을 party_data에 저장"""
        for fighter in self.fighters:
            if not fighter.is_enemy: # 아군인 경우만
                # 이름으로 매칭해서 데이터 업데이트
                for data in self.party_data:
                    if data["name"] == fighter.name:
                        data["hp"] = fighter.hp # 현재 남은 체력 저장
                        break

    def setup_battle(self):
        """전투 초기화"""
        self.fighters.clear()
        self.battle_state = "FIGHTING"
        self.log_message = f"{self.floor}층 - 적이 나타났다!"

        # [NEW] 저장된 party_data를 기반으로 아군 생성
        for data in self.party_data:
            # 죽은 캐릭터(HP 0)는 체력 1로 부활? 아니면 제외? -> 일단 1로 부활시켜서 데려감 (로그라이크 힐 선택 유도)
            current_hp = data["hp"] if data["hp"] > 0 else 1 
            
            f = Fighter(200, 200 + (self.party_data.index(data)*150), # Y좌표 자동 배치 
                        data["name"], False, 
                        current_hp, data["max_hp"], # 현재HP, 최대HP
                        data["atk"], data["agi"], 
                        data["img"])
            self.fighters.append(f)

        # 적군 (층수에 비례해 강해짐)
        hp_bonus = (self.floor - 1) * 20
        atk_bonus = (self.floor - 1) * 3
        
        # 10층 단위 보스전 로직 (간단 구현)
        if self.floor % 10 == 0:
            self.fighters.append(Fighter(900, 350, f"{self.floor}층 보스", True, 500+hp_bonus, 500+hp_bonus, 30+atk_bonus, 10, "oni_boss.png"))
            self.log_message = f"!!! {self.floor}층 보스 출현 !!!"
        else:
            # 일반 몬스터 2~3마리 랜덤 등장
            enemy_count = random.randint(2, 3)
            for i in range(enemy_count):
                y_pos = 200 + i * 150
                self.fighters.append(Fighter(900, y_pos, f"적 {i+1}", True, 80+hp_bonus, 80+hp_bonus, 10+atk_bonus, 8, "oni_low.png"))
        
        self.turn_queue = sorted(self.fighters, key=lambda f: f.agi, reverse=True)

    def get_alive_targets(self, is_enemy_team):
        return [f for f in self.fighters if f.is_enemy == is_enemy_team and not f.is_dead]

    def process_reward(self, reward_code):
        print(f"[System] 보상 선택: {reward_code}")
        
        # [NEW] 보상 효과를 party_data에 영구 적용
        for data in self.party_data:
            if reward_code == "REWARD_HEAL":
                # 30% 회복 (단, MaxHP 넘지 않게)
                heal_amount = int(data["max_hp"] * 0.3)
                data["hp"] = min(data["hp"] + heal_amount, data["max_hp"])
            
            elif reward_code == "REWARD_HP_UP":
                data["max_hp"] += 20
                data["hp"] += 20 # 늘어난 만큼 현재 체력도 회복
            
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
                self.save_party_status() # [중요] 승리 확정 시 현재 체력 저장!
            return

        # 턴 로직
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
            
    # handle_event와 draw는 기존과 동일하게 유지
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
        for fighter in self.fighters: fighter.draw(self.screen)
        if self.battle_state == "VICTORY": self.reward_popup.draw(self.screen)