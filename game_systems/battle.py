import pygame
import random
from config import *

class Fighter:
    """전투에 참여하는 개별 캐릭터/몬스터 객체"""
    def __init__(self, x, y, name, is_enemy, hp, max_hp, image_path=None):
        self.rect = pygame.Rect(x, y, 100, 100) # 캐릭터 크기 (100x100)
        self.name = name
        self.is_enemy = is_enemy
        self.hp = hp
        self.max_hp = max_hp
        self.image = None
        
        # 이미지 로딩 시도 (없으면 색깔 사각형으로 대체)
        if image_path:
            try:
                # assets/images/ 경로에서 로드
                full_path = os.path.join(ASSETS_DIR, "images", image_path)
                loaded_img = pygame.image.load(full_path)
                self.image = pygame.transform.scale(loaded_img, (100, 100))
            except:
                self.image = None # 로드 실패 시 None

    def draw(self, screen):
        # 1. 캐릭터 본체 그리기
        if self.image:
            screen.blit(self.image, self.rect)
        else:
            # 이미지가 없으면 아군은 파랑, 적군은 빨강 사각형
            color = RED if self.is_enemy else BLUE
            pygame.draw.rect(screen, color, self.rect)
            
            # 이름 표시 (이미지 없을 때 구분용)
            font = pygame.font.SysFont("malgungothic", 12)
            name_surf = font.render(self.name, True, WHITE)
            screen.blit(name_surf, (self.rect.x, self.rect.y + 40))

        # 2. HP 바 그리기 (머리 위)
        bar_width = 100
        bar_height = 10
        fill_width = int((self.hp / self.max_hp) * bar_width)
        
        # 배경바 (회색)
        pygame.draw.rect(screen, GRAY, (self.rect.x, self.rect.y - 15, bar_width, bar_height))
        # 체력바 (초록)
        pygame.draw.rect(screen, GREEN, (self.rect.x, self.rect.y - 15, fill_width, bar_height))
        # 테두리 (검정)
        pygame.draw.rect(screen, WHITE, (self.rect.x, self.rect.y - 15, bar_width, bar_height), 1)

class BattleScene:
    """전투 화면 전체를 관리하는 매니저"""
    def __init__(self, screen):
        self.screen = screen
        self.fighters = []
        self.setup_battle()
        
        # 폰트
        self.font = pygame.font.SysFont("malgungothic", 20)

    def setup_battle(self):
        """DB에서 데이터를 가져와 아군/적군 배치 (지금은 더미 데이터)"""
        self.fighters.clear()
        
        # 아군 배치 (왼쪽: x=200 근처)
        # 나중에는 DB의 inventory에서 선택된 3명을 가져와야 함
        self.fighters.append(Fighter(200, 200, "마리오", False, 100, 100, "mario.png"))
        self.fighters.append(Fighter(150, 350, "탄지로", False, 150, 150, "tanjiro.png"))
        self.fighters.append(Fighter(200, 500, "피카츄", False, 80, 80, "pikachu.png"))

        # 적군 배치 (오른쪽: x=900 근처)
        # 나중에는 DB의 enemies 테이블에서 biome에 맞는 적을 랜덤 로드
        self.fighters.append(Fighter(900, 200, "오니1", True, 80, 80, "oni_low.png"))
        self.fighters.append(Fighter(950, 350, "오니 대장", True, 200, 200, "oni_boss.png"))
        self.fighters.append(Fighter(900, 500, "오니2", True, 80, 80, "oni_low.png"))

    def update(self):
        """전투 로직 업데이트 (턴 계산 등) - Phase 3-2에서 구현"""
        pass

    def draw(self):
        """전투 화면 그리기"""
        # 배경 (어두운 회색)
        self.screen.fill((30, 30, 30))
        
        # UI: VS 글자
        vs_surf = self.font.render("--- BATTLE START ---", True, WHITE)
        self.screen.blit(vs_surf, (SCREEN_WIDTH//2 - 100, 50))

        # 모든 캐릭터 그리기
        for fighter in self.fighters:
            fighter.draw(self.screen)