import pygame
import os
from config import SCREEN_WIDTH, SCREEN_HEIGHT, ASSETS_DIR, BIOME_IMAGES, BLACK

class BackgroundManager:
    """
    배경 이미지를 관리, 로드, 렌더링하는 클래스.
    - 현재 바이옴에 맞는 배경 이미지를 동적으로 로드합니다.
    - 로드된 이미지를 캐싱하여 성능을 최적화합니다.
    - 화면 크기에 맞게 이미지 크기를 조절합니다.
    """
    def __init__(self):
        self.backgrounds = {}  # 전투 배경 캐시
        self.ui_backgrounds = {} # UI 전용 배경 캐시
        self.current_background = None
        self._load_all_backgrounds()
        self._load_ui_backgrounds()

    def _load_all_backgrounds(self):
        """미리 정의된 모든 배경 이미지를 로드하고 캐싱합니다."""
        background_dir = os.path.join(ASSETS_DIR, "images", "backgrounds")
        for biome, filename in BIOME_IMAGES.items():
            path = os.path.join(background_dir, filename)
            try:
                image = pygame.image.load(path).convert()
                scaled_image = pygame.transform.scale(image, (SCREEN_WIDTH, SCREEN_HEIGHT))
                self.backgrounds[biome] = scaled_image
            except pygame.error as e:
                print(f"배경 이미지 로드 실패: {path}. 에러: {e}")
                self.backgrounds[biome] = None # 로드 실패 시 None 저장

    def _load_ui_backgrounds(self):
        """UI 전용 배경 이미지들을 로드하고 캐싱합니다."""
        ui_bg_dir = os.path.join(ASSETS_DIR, "images")
        ui_images = {
            "deck": "bg_deck.png",
            "shop": "bg_shop.png",
            "gacha_1": "bg_gacha_1.png",
            "gacha_10": "bg_gacha_10.png",
            "coupon": "bg_coupon.png"
        }
        for name, filename in ui_images.items():
            path = os.path.join(ui_bg_dir, filename)
            try:
                image = pygame.image.load(path).convert()
                scaled_image = pygame.transform.scale(image, (SCREEN_WIDTH, SCREEN_HEIGHT))
                self.ui_backgrounds[name] = scaled_image
            except pygame.error as e:
                print(f"UI 배경 이미지 로드 실패: {path}. 에러: {e}")
                self.ui_backgrounds[name] = None

    def get_ui_background(self, name):
        """지정된 이름의 UI 배경 이미지를 반환합니다."""
        return self.ui_backgrounds.get(name)

    def update_background(self, floor, biome_name):
        """현재 층과 바이옴에 따라 배경 이미지를 설정합니다."""
        # 91층 이상일 경우 'Final' 바이옴으로 강제 설정
        if floor >= 91:
            target_biome = "Final"
        else:
            target_biome = biome_name

        self.current_background = self.backgrounds.get(target_biome)

    def draw(self, surface):
        """현재 설정된 배경을 화면에 그립니다."""
        if self.current_background:
            surface.blit(self.current_background, (0, 0))
        else:
            # 이미지가 없는 경우 검은색으로 화면을 채웁니다.
            surface.fill(BLACK)
