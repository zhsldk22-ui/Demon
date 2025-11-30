import pygame
import os
from config import BGM_PATH, SFX_PATH, SOUND_ON

class AudioManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AudioManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        if SOUND_ON:
            try:
                pygame.mixer.init()
            except pygame.error as e:
                print(f"[ERROR] Failed to initialize pygame.mixer: {e}")

        self.current_bgm = None
        self.sfx_cache = {} # SFX 사운드 객체를 캐싱하여 재사용
        self.bgm_muted = False
        self.sfx_muted = False
        self._initialized = True

    def play_bgm(self, filename, volume=0.5, fade_ms=2000):
        """
        스트리밍 방식으로 BGM을 재생합니다.
        - 중복 방지: 이미 같은 곡이 재생 중이면 아무것도 하지 않습니다.
        - 크로스페이드: 다른 곡이 재생 중이면 페이드 아웃 후 새 곡을 페이드 인합니다.
        - 예외 처리: 파일이 없으면 로그만 남깁니다.
        """
        if not SOUND_ON or not pygame.mixer.get_init():
            return

        # 중복 재생 방지
        if self.current_bgm == filename:
            return

        path = os.path.join(BGM_PATH, filename)
        if not os.path.exists(path):
            print(f"[Audio Error] BGM file not found: {path}. Skipping.")
            return

        try:
            # 다른 음악이 재생 중일 경우 크로스페이드
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(fade_ms)

            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops=-1, fade_ms=fade_ms)
            self.current_bgm = filename
        except pygame.error as e:
            print(f"[ERROR] Could not play BGM '{filename}': {e}")
            self.current_bgm = None

    def stop_bgm(self):
        if not SOUND_ON or not pygame.mixer.get_init():
            return
        pygame.mixer.music.fadeout(1000)
        self.current_bgm = None

    def toggle_bgm(self):
        """BGM 음소거 상태를 토글합니다."""
        self.bgm_muted = not self.bgm_muted
        if self.bgm_muted: # 음소거
            pygame.mixer.music.pause()
        else:
            # 음소거 해제
            pygame.mixer.music.unpause()
        print(f"[Audio] BGM Muted: {self.bgm_muted}")

    def toggle_sfx(self):
        """SFX 음소거 상태를 토글합니다."""
        self.sfx_muted = not self.sfx_muted
        print(f"[Audio] SFX Muted: {self.sfx_muted}")

    def play_sfx(self, filename, volume=0.8):
        """
        효과음(SFX)을 재생합니다.
        - 캐싱: 로드한 사운드 객체는 재사용하여 오버헤드를 줄입니다.
        - 예외 처리: 파일이 없어도 게임이 멈추지 않고 로그만 남깁니다.
        """
        if not SOUND_ON or not pygame.mixer.get_init() or self.sfx_muted:
            return

        # 캐시에서 사운드 객체 확인
        if filename in self.sfx_cache:
            sound = self.sfx_cache[filename]
        else:
            path = os.path.join(SFX_PATH, filename)
            if not os.path.exists(path):
                print(f"[SFX Missing] {filename}")
                return
            
            try:
                sound = pygame.mixer.Sound(path)
                self.sfx_cache[filename] = sound
            except pygame.error as e:
                print(f"[ERROR] Could not load SFX '{filename}': {e}")
                return
        
        # 사운드 재생
        try:
            sound.set_volume(volume)
            sound.play()
        except pygame.error as e:
            print(f"[ERROR] Could not play SFX '{filename}': {e}")
