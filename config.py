import os

# --- 화면 설정 ---
SCREEN_WIDTH = 1280  # 게임 화면 가로 크기 (16:9 HD)
SCREEN_HEIGHT = 720  # 게임 화면 세로 크기
FPS = 60             # 초당 프레임 수 (높을수록 부드러움)
TITLE = "DGFS: Dad's Game For Son (Ver 0.1)"

# --- 색상 정의 (R, G, B) ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0) # 기본 배경색
RED = (255, 0, 0) # 데미지, 경고
GREEN = (0, 255, 0) # 회복, 활성화
BLUE = (0, 0, 255) # 마나, 스킬
GRAY = (128, 128, 128) # 비활성 상태
GOLD = (255, 215, 0) # 보상, 특별 아이템

# --- 플로팅 텍스트 색상 ---
DAMAGE_TEXT_COLOR = RED
HEAL_TEXT_COLOR = GREEN
STAT_UP_TEXT_COLOR = BLUE
REWARD_TEXT_COLOR = GOLD

# --- 등급별 색상 정의 ---
GRADE_COLORS = {
    "COMMON": (255, 255, 255), # 하얀색
    "RARE": (100, 100, 255),   # 파란색
    "SPECIAL": (180, 0, 255),  # 보라색
    "LEGEND": (255, 165, 0),   # 주황색
    "MYTHIC": (255, 0, 255),   # 마젠타 (무지개색 대용)
}

# --- UI 색상 설정 ---
COLOR_BUTTON_NORMAL = (50, 50, 200)
COLOR_BUTTON_HOVER = (100, 100, 255)
COLOR_INPUT_INACTIVE = GRAY
COLOR_INPUT_ACTIVE = GREEN

# --- UI 컴포넌트 설정 ---
FONT_SIZE_BUTTON = 24
FONT_SIZE_INPUT = 32
BUTTON_BORDER_RADIUS = 10
BUTTON_BORDER_THICKNESS = 2
INPUT_MAX_LENGTH = 15
INPUT_TEXT_PADDING = 5

# --- 기본 게임 설정 ---
DEFAULT_USER_ID = 'son_01'      # 게임의 주인공 ID
INITIAL_TICKETS = 10            # 게임 최초 시작 시 지급되는 뽑기권 (10연차 1회분)
SYSTEM_MESSAGE_DURATION = 120   # 시스템 메시지 표시 시간 (120프레임 = 2초 @ 60fps)

# 전투 설정
TURN_DELAY = 120 # 턴 사이의 딜레이 (60 = 1초)
EFFECT_DURATION = 90 # 데미지/효과 텍스트 표시 시간

SKILL_MP_COST = 20
NORMAL_ATTACK_MP_REGEN = 5

SKILL_MULTIPLIER = 1.5
ULTIMATE_MULTIPLIER = 2.5

AI_SKILL_CHANCE = 0.5 # 적 AI가 스킬을 사용할 확률

# --- 쿠폰 설정 ---
COUPON_MIN_LENGTH = 10
COUPON_SENDER_LENGTH = 3
COUPON_DATE_LENGTH = 6
COUPON_REWARDS = {
    'N': 10, # Normal 등급 보상
    'P': 20, # Premium 등급 보상
    'S': 30  # Special 등급 보상
}
COUPON_VALID_SENDERS = ["DAD", "MOM"]

# --- 뽑기(가챠) 설정 ---
GACHA_MULTI_DRAW_COUNT = 10 # 10연차 뽑기 횟수

# 파일 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "dgfs.db")
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# --- 바이옴 배경 이미지 설정 ---
BIOME_IMAGES = {
    "Mario": "mario.png",
    "Pokemon": "pokemon.png",
    "DemonSlayer": "demon_slayer.png", # 'DemonSlayer' -> 'demon_slayer.png' corrected
    "Final": "final.png"
}

# --- 사운드 설정 ---
SOUND_ON = True # True: 사운드 켜기, False: 사운드 끄기
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds") # 모든 사운드 파일의 기본 경로
BGM_PATH = os.path.join(SOUNDS_DIR, "bgm") # BGM 파일 경로
SFX_PATH = os.path.join(SOUNDS_DIR, "sfx") # SFX 파일 경로

# --- 성장 시스템 설정 ---
MAX_LEVEL = 50  # 레벨 제한
EXP_PER_LEVEL_COEFF = 100  # 레벨업 요구 경험치 계수 (공식: 현재 레벨 * 100)
BATTLE_EXP_REWARD_COEFF = 10  # 전투 경험치 보상 계수 (공식: 층수 * 10)
LEVEL_PENALTY_THRESHOLD = 5  # 레벨 페널티 임계값 (캐릭터 레벨 > 층수 + 5 이면 경험치 0)

# 등급별 뽑기 중복 획득 시 경험치 보상
GACHA_DUPLICATE_EXP = {
    "COMMON": 10,
    "RARE": 50,
    "SPECIAL": 200,
    "LEGEND": 1000,
    "MYTHIC": 5000
}

# 등급별 레벨업 시 총 스탯 상승량
STAT_GROWTH_RATE = {
    "COMMON": 4,
    "RARE": 6,
    "SPECIAL": 8,
    "LEGEND": 10,
    "MYTHIC": 15
}
