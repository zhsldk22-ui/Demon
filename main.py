import pygame, sys, sqlite3, os
from config import * # (수정) DEFAULT_USER_ID, INITIAL_TICKETS, SYSTEM_MESSAGE_DURATION 추가됨

from database import init_db, start_new_run, update_master_data_from_csv
from ui.components import Button, InputBox
from game_systems.coupon import CouponManager
from game_systems.gacha import GachaManager
from ui.background_manager import BackgroundManager
from ui.audio_manager import AudioManager

# [리팩토링] Scene 기반 아키텍처 도입
from scenes.lobby_scene import LobbyScene
from scenes.gacha_scene import GachaScene
from scenes.deck_scene import DeckScene
from scenes.coupon_scene import CouponScene
from scenes.battle_scene import BattleScene # [수정] BattleScene의 위치 변경

def get_user_tickets():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT tickets FROM users WHERE user_id=?", (DEFAULT_USER_ID,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0



def main():
    pygame.init()
    AudioManager() # 오디오 관리자 초기 생성
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    
    # [수정] main() 함수가 시작될 때 DB 초기화 및 데이터 로딩을 먼저 수행합니다.
    # 이렇게 하면 게임 루프가 시작될 때 DB가 항상 준비된 상태임이 보장됩니다.
    # [리팩토링] DB 초기화 및 데이터 로딩 실패 시 게임을 종료합니다.
    if not init_db() or not update_master_data_from_csv():
        print("[Critical Error] 게임 초기화에 실패하여 프로그램을 종료합니다.")
        pygame.quit()
        sys.exit()

    # [테스트용 임시 코드] 게임 시작 시 티켓 100개 자동 지급
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET tickets = 500 WHERE user_id=?", (DEFAULT_USER_ID,))
    conn.commit()
    conn.close()
    print("[Debug] 테스트용 티켓 100개가 지급되었습니다.")

    # [리팩토링] Scene에서 공유할 자원들을 딕셔너리로 관리
    shared_data = {
        'background_manager': BackgroundManager(),
        'info_font': pygame.font.SysFont("malgungothic", 20),
        'title_font': pygame.font.SysFont("malgungothic", 50, bold=True),
        'system_message': "",
        'system_message_timer': 0,
        'tickets': 0,
    }

    # [리팩토링] 각 시스템 관리자들을 미리 생성
    gacha_manager = GachaManager()

    # [리팩토링] Scene 관리 로직
    scenes = {
        "LOBBY": LobbyScene(screen, shared_data),
        "GACHA_SHOP": GachaScene(screen, shared_data, gacha_manager),
        "DECK_VIEW": DeckScene(screen, shared_data),
        "COUPON": CouponScene(screen, shared_data),
    }
    current_scene = scenes["LOBBY"]

    # [리팩토링] 아래 변수들은 각 Scene으로 모두 이동 예정
    game_state = "LOBBY" # 임시 변수. Scene 전환 로직 완성 후 제거 예정

    while True:
        mouse_pos = pygame.mouse.get_pos()
        shared_data['tickets'] = get_user_tickets()

        # [이벤트 루루프 수정] 이벤트를 하나씩 가져와 현재 씬에 개별적으로 전달합니다.
        # 이 구조는 이벤트 처리의 혼란을 막고 모든 씬의 동작을 일관되게 만듭니다.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            # 1. handle_event(단수형)를 가진 새로운 방식의 씬 처리
            if hasattr(current_scene, 'handle_event'):
                current_scene.handle_event(event, mouse_pos)
            # 2. handle_events(복수형)를 가진 기존 방식의 씬을 위한 호환성 처리
            elif hasattr(current_scene, 'handle_events'):
                current_scene.handle_events([event], mouse_pos)

        current_scene.update()

        # [리팩토링] Scene 전환 로직
        if current_scene.next_scene_name:
            next_scene_name = current_scene.next_scene_name
            current_scene.next_scene_name = None # [버그 수정] 다음 씬으로 넘어가기 전에 현재 씬의 플래그를 먼저 초기화

            if next_scene_name in scenes:
                current_scene = scenes[next_scene_name]
                # [개선] Scene이 바뀔 때마다 필요한 데이터를 다시 로드하도록 처리
                if next_scene_name == "DECK_VIEW":
                    current_scene.load_character_cards()

                game_state = next_scene_name # 임시
            # [수정] '새로 하기' 또는 '이어 하기' 보고를 받으면, '전투 지배인'을 고용
            elif next_scene_name == "BATTLE_NEW":
                current_scene = BattleScene(screen, shared_data, mode='NEW_GAME')
                game_state = "BATTLE" # 임시
            elif next_scene_name == "BATTLE_CONTINUE":
                current_scene = BattleScene(screen, shared_data, mode='CONTINUE')
                game_state = "BATTLE" # 임시
            elif next_scene_name == "LOBBY_SAVE":
                current_scene = scenes["LOBBY"]
                game_state = "LOBBY" # [임시]

            # [핵심 수정] 새로 전환된 씬의 enter 메서드를 호출하여 초기화 로직을 실행합니다.
            if hasattr(current_scene, 'enter') and callable(getattr(current_scene, 'enter')):
                current_scene.enter()

        screen.fill(BLACK) # 기본 배경색
        
        # [리팩토링] 화면 그리기를 현재 Scene에 위임
        current_scene.draw(screen)

        # [수정] 시스템 메시지 UI
        if shared_data['system_message']:
            # 타이머 로직은 임시로 단순화. 추후 update에서 처리
            info_font = shared_data['info_font']
            overlay = pygame.Surface((800, 60))
            overlay.set_alpha(180); overlay.fill(BLACK)
            screen.blit(overlay, (SCREEN_WIDTH//2 - 400, 20))
            msg_surf = info_font.render(shared_data['system_message'], True, WHITE)
            screen.blit(msg_surf, msg_surf.get_rect(center=(SCREEN_WIDTH//2, 50)))
            # 메시지를 한 번만 표시하고 지움 (임시)
            if pygame.time.get_ticks() % 120 == 0:
                 shared_data['system_message'] = ""

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()