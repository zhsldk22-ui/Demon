import random

class StageManager:
    """
    100층 등반 로직 관리자
    - Phase 1 (1~30층): Tier 1 (3개 테마 셔플)
    - Phase 2 (31~60층): Tier 2 (3개 테마 재셔플)
    - Phase 3 (61~90층): Tier 3 (3개 테마 재셔플)
    - Phase 4 (91~100층): Final (고정)
    """
    def __init__(self):
        self.biomes = ["Mario", "Pokemon", "DemonSlayer"]
        self.phase_orders = {}
        self._shuffle_biomes()

    def _shuffle_biomes(self):
        """각 페이즈별 바이옴 순서를 미리 섞어서 저장"""
        # Phase 1, 2, 3 각각에 대해 순서를 랜덤하게 섞음
        for phase in [1, 2, 3]:
            order = self.biomes.copy()
            random.shuffle(order)
            self.phase_orders[phase] = order
        
        # Phase 4는 Final 고정
        self.phase_orders[4] = ["Final"]
        
        print(f"[Stage] 바이옴 순서 결정: {self.phase_orders}")

    def get_stage_info(self, floor):
        """현재 층의 바이옴, 티어, 특수 보스 ID 반환"""
        
        # 1. 페이즈 및 티어 계산
        if floor <= 30:
            phase = 1
            tier = 1
            # 1~10층: 첫번째, 11~20층: 두번째, 21~30층: 세번째 바이옴
            biome_idx = (floor - 1) // 10
        elif floor <= 60:
            phase = 2
            tier = 2
            biome_idx = (floor - 31) // 10
        elif floor <= 90:
            phase = 3
            tier = 3
            biome_idx = (floor - 61) // 10
        else:
            phase = 4
            tier = 3 # Final은 기본 Tier 3
            biome_idx = 0 # Final only

        # 2. 현재 바이옴 결정
        if phase == 4:
            current_biome = "Final"
        else:
            current_biome = self.phase_orders[phase][biome_idx]

        # 3. 고정 보스 체크 (91, 95, 100층)
        fixed_boss_id = None
        if floor == 91: fixed_boss_id = 9090  # 어둠의 서호
        elif floor == 95: fixed_boss_id = 9095 # 어둠의 아빠
        elif floor == 100: fixed_boss_id = 9100 # 어둠의 엄마

        return {
            "floor": floor,
            "phase": phase,
            "biome": current_biome,
            "tier": tier,
            "fixed_boss_id": fixed_boss_id,
            "is_boss_floor": (floor % 10 == 0) or (fixed_boss_id is not None)
        }