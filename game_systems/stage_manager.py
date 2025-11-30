import random

class StageManager:
    """
    100층 등반 로직 관리자
    - Phase 1 (1~30층): Tier 1 (3개 테마 셔플)
    - Phase 2 (31~60층): Tier 2 (3개 테마 재셔플)
    - Phase 3 (61~90층): Tier 3 (3개 테마 재셔플)
    - Phase 4 (91~100층): Final (고정)
    """
    # [리팩토링] Magic Number들을 클래스 상수로 정의
    PHASE_FLOORS = {
        1: (1, 30),
        2: (31, 60),
        3: (61, 90),
        4: (91, 100)
    }
    FLOORS_PER_BOSS = 10
    FIXED_BOSSES = {
        91: 9090,  # 어둠의 서호
        95: 9095, # 어둠의 아빠
        100: 9100 # 어둠의 엄마
    }

    def __init__(self):
        self.biomes = ["Mario", "Pokemon", "DemonSlayer"]
        self.phase_orders = {}
        self.session_party_data = None
        """등반 세션 동안 파티의 현재 상태(FighterData 리스트)를 저장합니다.
           다음 층으로 이동 시 이 데이터를 사용해 파티 상태를 유지합니다."""
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

    def _get_phase_and_tier(self, floor):
        """[리팩토링] 층수에 맞는 페이즈와 티어를 계산하여 반환"""
        for phase, (start, end) in self.PHASE_FLOORS.items():
            if start <= floor <= end:
                # Final 페이즈(4)는 Tier 3을 사용
                return phase, 3 if phase == 4 else phase
        return None, None # 범위를 벗어난 경우

    def _get_biome(self, floor, phase):
        """[리팩토링] 층수와 페이즈에 맞는 바이옴을 결정하여 반환"""
        if phase == 4:
            return "Final"
        
        # 해당 페이즈의 시작 층수
        phase_start_floor = self.PHASE_FLOORS[phase][0]
        # 페이즈 내에서의 상대적인 층수 계산
        floor_in_phase = floor - phase_start_floor
        # 바이옴 인덱스 계산
        biome_idx = floor_in_phase // self.FLOORS_PER_BOSS
        
        if biome_idx < len(self.phase_orders[phase]):
            return self.phase_orders[phase][biome_idx]
        return None # 잘못된 인덱스 접근 방지

    def _get_fixed_boss_id(self, floor):
        """[리팩토링] 해당 층에 고정 보스가 있는지 확인하여 ID를 반환"""
        return self.FIXED_BOSSES.get(floor, None)

    def get_stage_info(self, floor):
        """[리팩토링] 현재 층의 모든 정보를 종합하여 반환"""
        # [리팩토링] 잘못된 층수 값에 대한 예외 처리
        if not (1 <= floor <= 100):
            raise ValueError(f"유효하지 않은 층입니다: {floor}. 층수는 1에서 100 사이여야 합니다.")
        
        phase, tier = self._get_phase_and_tier(floor)
        current_biome = self._get_biome(floor, phase)
        fixed_boss_id = self._get_fixed_boss_id(floor)

        return {
            "floor": floor,
            "phase": phase,
            "biome": current_biome,
            "tier": tier,
            "fixed_boss_id": fixed_boss_id,
            # [버그 수정] 사용자의 제보에 따라, 보스 층은 5가 아닌 10층 단위로 설정되도록 수정합니다.
            # 이 변경 사항이 적용되도록 강제로 재컴파일합니다.
            "is_boss_floor": (floor % 10 == 0) or (fixed_boss_id is not None)
        }

    def get_current_bgm_name(self, floor):
        """
        현재 층과 바이옴에 맞는 BGM 파일명을 반환합니다.
        - 최종 바이옴 (91-100층): bgm_final.mp3
        - 일반 바이옴 (1-90층): bgm_{theme}_t{tier}.mp3
        """
        stage_info = self.get_stage_info(floor)
        biome = stage_info.get("biome")
        tier = stage_info.get("tier")

        if not biome or not tier:
            return "bgm_lobby.mp3"  # Fallback

        if biome == "Final":
            return "bgm_final.mp3"

        theme_map = {
            "DemonSlayer": "demon", "Mario": "mario", "Pokemon": "pokemon"
        }
        theme_name = theme_map.get(biome, "default")

        return f"bgm_{theme_name}_t{tier}.mp3"