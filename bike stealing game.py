import pygame
import sys
import random
import time
import math

# 1. 게임 시스템 및 윈도우 초기화
pygame.init()
WIDTH, HEIGHT = 600, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("자전거 강탈자: 데스 매치 (산악 지옥 편)")
clock = pygame.time.Clock()

# --- 자전거 기본 크기 (90x180) ---
MAX_W, MAX_H = 90, 180


def load_bike_image(filename):
    try:
        img = pygame.image.load(filename).convert_alpha()
        orig_w, orig_h = img.get_size()
        ratio = min(MAX_W / orig_w, MAX_H / orig_h)
        if ratio < 1.0:
            new_w = int(orig_w * ratio)
            new_h = int(orig_h * ratio)
            return pygame.transform.scale(img, (new_w, new_h))
        return img
    except:
        return None


normal_bike_img = load_bike_image('normal_bike.png')
fixie_bike_img = load_bike_image('fixie_bike.png')
mountain_bike_img = load_bike_image('mountain_bike.png')

# --- 그래픽용 색상 설정 ---
WHITE = (255, 255, 255)
BLUE = (30, 144, 255)
CITY_ROAD_COLOR, MOUNTAIN_ROAD_COLOR = (40, 40, 40), (100, 60, 20)
LANE_CITY, LANE_MOUNTAIN = (100, 100, 100), (200, 200, 200)
PLAYER_COLOR, FIXIE_COLOR, MTB_COLOR, NPC_COLOR = (0, 150, 255), (255, 0, 255), (0, 230, 100), (180, 180, 180)
CAR_COLOR = (220, 30, 30)
ERROR_COLOR, SKIN_COLOR = (255, 50, 50), (255, 200, 150)
CABLECAR_COLOR = (200, 50, 50)
CLIFF_COLOR = (20, 10, 5)
RAMP_COLOR = (220, 160, 20)

# --- 안전한 기본 내장 폰트 생성 ---
ui_font = pygame.font.Font(None, 32)
count_font = pygame.font.Font(None, 90)
go_font = pygame.font.Font(None, 50)


# --- 게임 데이터 초기화 함수 ---
def reset_game():
    return {
        "lane": 1, "is_jumping": False, "jump_y": 0, "jump_v": 0,
        "jump_gravity": 0.6,
        "bikes": [[300, 650, True, 0, False, "NORMAL"]],
        "bumps": [],
        "cliffs": [],
        "ramps": [],
        "victims": [],
        "last_jump": 0, "game_over": False, "score": 0,
        "police_present": False, "police_start_time": 0, "police_wobble": 0,
        "jump_penalty_end_time": 0, "stage": "CITY", "scroll_y": 0, "time_scale": 1.0,
        "current_bike_type": "NORMAL",

        "puddle_slip_end": 0,
        "hijack_success": False,
        "crash_type": "WASTED",

        "slope": "FLAT",
        "slope_timer": 0,
        "last_cliff_spawn": 0,

        # --- 오프닝/엔딩 애니메이션 제어 변수 ---
        "transition_state": "START_ANIM",
        "start_p_x": -50,
        "start_p_y": 650,
        "start_anim_phase": "WALK_IN",
        "start_countdown_timer": 0,

        # --- 케이블카 엔딩 시네마틱 변수 ---
        "end_anim_phase": "STOP_AND_DISMOUNT",
        "end_p_x": 300,
        "end_p_y": 650,
        "cablecar_x": -120,
        "cablecar_y": 550,
        "transition_timer": 0
    }


g = reset_game()
lanes = [100, 300, 500]
TARGET_SCORE = 30000

# ==================== 메인 게임 루프 ====================
while True:
    current_time = time.time()
    keys = pygame.key.get_pressed()

    is_slipping = current_time < g["puddle_slip_end"]

    if g["stage"] == "MOUNTAIN" and g["transition_state"] == "NONE" and not g["game_over"]:
        if current_time - g["slope_timer"] > 7.0:
            g["slope"] = random.choice(["FLAT", "UPHILL", "DOWNHILL"])
            g["slope_timer"] = current_time

    # --- 1. 실시간 제동 및 가속 로직 ---
    if g["transition_state"] == "NONE":
        if is_slipping:
            g["time_scale"] = min(1.6, g["time_scale"] + 0.08)
        else:
            if g["current_bike_type"] == "NORMAL":
                if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                    g["time_scale"] = max(0.3, g["time_scale"] - 0.1)
                else:
                    g["time_scale"] = min(1.0, g["time_scale"] + 0.1)

            elif g["current_bike_type"] == "FIXIE":
                if keys[pygame.K_s]:
                    g["time_scale"] = max(0.25, g["time_scale"] - 0.008)
                else:
                    g["time_scale"] = min(1.5, g["time_scale"] + 0.015)

            elif g["current_bike_type"] == "MOUNTAIN":
                if keys[pygame.K_s]:
                    g["time_scale"] = max(0.2, g["time_scale"] - 0.025)
                else:
                    g["time_scale"] = min(1.2, g["time_scale"] + 0.02)

            if g["stage"] == "MOUNTAIN":
                if g["slope"] == "UPHILL":
                    penalty = 0.004 if g["current_bike_type"] == "MOUNTAIN" else 0.012
                    g["time_scale"] = max(0.3, g["time_scale"] - penalty)
                elif g["slope"] == "DOWNHILL" and not keys[pygame.K_s] and not keys[pygame.K_LSHIFT] and not keys[
                    pygame.K_RSHIFT]:
                    g["time_scale"] = min(1.8, g["time_scale"] + 0.01)
    else:
        g["time_scale"] = 0.0

        # --- 2. 키보드 이벤트 핸들링 ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT: pygame.quit(); sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r: g = reset_game()

            if not g["game_over"] and g["transition_state"] == "NONE":
                if not is_slipping:
                    if event.key == pygame.K_a and g["lane"] > 0:
                        g["lane"] -= 1
                    elif event.key == pygame.K_d and g["lane"] < 2:
                        g["lane"] += 1

                if event.key == pygame.K_SPACE and not g["is_jumping"]:
                    current_cd = 1.8 if g["stage"] == "MOUNTAIN" else 3.0
                    if (current_time - g["last_jump"] >= current_cd) and (current_time >= g["jump_penalty_end_time"]):
                        g["is_jumping"], g["jump_v"], g["last_jump"] = True, -18, current_time
                        g["jump_gravity"] = 0.6
                        g["hijack_success"] = False

                        # --- 3. 스타트 애니메이션 단계 제어 ---
    if g["transition_state"] == "START_ANIM":
        if g["start_anim_phase"] == "WALK_IN":
            g["start_p_x"] += 3.5
            if g["start_p_x"] >= lanes[1] - 40:
                g["start_p_x"] = lanes[1] - 40
                g["start_anim_phase"] = "MOUNT"
                g["transition_timer"] = current_time

        elif g["start_anim_phase"] == "MOUNT":
            if g["start_p_x"] < lanes[1]:
                g["start_p_x"] += 1.5
            else:
                g["start_p_x"] = lanes[1]
                g["start_anim_phase"] = "READY"
                g["start_countdown_timer"] = current_time

        elif g["start_anim_phase"] == "READY":
            if current_time - g["start_countdown_timer"] >= 3.0:
                g["transition_state"] = "NONE"
                g["slope_timer"] = current_time

                # --- 3-2. 시티 스테이지 종료 케이블카 애니메이션 단계 제어 ---
    elif g["transition_state"] == "END_ANIM":
        if g["end_anim_phase"] == "STOP_AND_DISMOUNT":
            if g["cablecar_x"] < 30:
                g["cablecar_x"] += 4

            g["end_p_x"] -= 2.5
            if g["end_p_x"] <= lanes[g["lane"]] - 45:
                g["end_p_x"] = lanes[g["lane"]] - 45
                g["end_anim_phase"] = "ENTER_CABLECAR"

        elif g["end_anim_phase"] == "ENTER_CABLECAR":
            if g["end_p_x"] > 70:
                g["end_p_x"] -= 3.0
            else:
                g["end_anim_phase"] = "ASCEND"
                g["transition_timer"] = current_time

        elif g["end_anim_phase"] == "ASCEND":
            g["cablecar_y"] -= 5
            if g["cablecar_y"] < -180:
                g["stage"] = "MOUNTAIN"
                g["lane"] = 1
                g["bikes"] = [[300, 650, True, 0, False, "MOUNTAIN"]]
                g["transition_state"] = "NONE"
                g["slope_timer"] = current_time
                g["last_cliff_spawn"] = current_time

    # --- 4. 물리 및 오브젝트 상태 업데이트 ---
    if not g["game_over"]:
        if g["current_bike_type"] == "FIXIE":
            base_speed = 12
        elif g["current_bike_type"] == "MOUNTAIN":
            base_speed = 9
        else:
            base_speed = 7

        move_speed = base_speed * g["time_scale"] if g["transition_state"] == "NONE" else 0

        if g["transition_state"] == "NONE":
            g["scroll_y"] = (g["scroll_y"] + move_speed) % 60
            g["score"] += int(move_speed * 0.5)

            if g["stage"] == "CITY" and g["score"] >= TARGET_SCORE:
                g["transition_state"] = "END_ANIM"
                g["end_anim_phase"] = "STOP_AND_DISMOUNT"
                g["end_p_x"] = lanes[g["lane"]]
                g["end_p_y"] = 650
                g["police_present"] = False
                g["bumps"].clear()
                g["bikes"] = [b for b in g["bikes"] if b[2]]

                # 오브젝트 제어 및 스폰 시스템
        if g["transition_state"] == "NONE":
            if g["stage"] == "CITY":
                bike_spawn_chance = 0.018
                if random.random() < bike_spawn_chance:
                    s_x = random.choice(lanes)
                    if not any(abs(b[1] - (-150)) < 300 and b[0] == s_x for b in g["bikes"]):
                        if random.random() < 0.20:
                            car_speed = random.randint(6, 9)
                            g["bikes"].append([s_x, -180, False, car_speed, False, "CAR"])
                        else:
                            b_type = "FIXIE" if random.random() < 0.3 else "NORMAL"
                            npc_speed = random.randint(3, 5)
                            g["bikes"].append([s_x, -150, False, npc_speed, False, b_type])

            # 절벽 및 점프대 스폰 연산
            elif g["stage"] == "MOUNTAIN" and (current_time - g["last_cliff_spawn"] > 3.8):
                if random.random() < 0.025:
                    ch = 650
                    cliff_lane_x = random.choice(lanes)
                    is_all_lane_cliff = (cliff_lane_x == lanes[1])

                    if is_all_lane_cliff:
                        cw = 650
                        center_x = WIDTH // 2
                    else:
                        cw = 220
                        center_x = cliff_lane_x

                    offsets = {
                        "top": [random.randint(-15, 15) for _ in range(5)],
                        "right": [random.randint(-20, 20) for _ in range(9)],
                        "bottom": [random.randint(-15, 15) for _ in range(5)],
                        "left": [random.randint(-20, 20) for _ in range(9)]
                    }

                    cliff_y_start = -750
                    g["cliffs"].append([center_x, cliff_y_start, cw, ch, offsets])

                    if is_all_lane_cliff:
                        ramp_y = cliff_y_start + ch + 180
                        ramp_w = 150
                        ramp_h = 50
                        g["ramps"].append([WIDTH // 2, ramp_y, ramp_w, ramp_h])

                    g["last_cliff_spawn"] = current_time

            # ★ [수정] 과속방지턱 확률을 완전 제거하고 물웅덩이와 바위 위주로 스폰 재배정
            bump_chance = 0.012 if g["stage"] == "CITY" else 0.020
            if random.random() < bump_chance * (g["time_scale"] if g["time_scale"] > 0 else 1.0):
                if not g["is_jumping"] or g["stage"] == "MOUNTAIN":
                    b_x = random.choice(lanes)
                    if g["stage"] == "CITY":
                        b_type = 2  # 도시 스테이지는 100% 물 웅덩이만 생성
                    else:
                        # 산악 스테이지: 1 (바위낙하 60% 확률) / 2 (산악웅덩이 40% 확률)
                        b_type = 1 if random.random() < 0.6 else 2

                    if g["stage"] == "MOUNTAIN":
                        can_spawn = True
                        for c in g["cliffs"]:
                            if c[1] < 400:
                                cliff_left = c[0] - c[2] // 2
                                cliff_right = c[0] + c[2] // 2
                                if cliff_left <= b_x <= cliff_right:
                                    can_spawn = False
                                    break
                        if can_spawn:
                            g["bumps"].append([b_x, -50, b_type])
                    else:
                        g["bumps"].append([b_x, -50, b_type])

            for vic in g["victims"][:]:
                vic["x"] += vic["vx"]
                vic["y"] += vic["vy"] - move_speed
                vic["rot"] += vic["rot_speed"]
                if vic["y"] > HEIGHT + 100 or vic["x"] < -100 or vic["x"] > WIDTH + 100:
                    g["victims"].remove(vic)

        # 지형 스크롤 연산
        for c in g["cliffs"][:]:
            c[1] += move_speed
            if c[1] > HEIGHT + 750: g["cliffs"].remove(c)

        for r in g["ramps"][:]:
            r[1] += move_speed
            if r[1] > HEIGHT + 100: g["ramps"].remove(r)

        # 오브젝트 위치 동기화
        for i, b in enumerate(g["bikes"][:]):
            if b[2]:
                if g["transition_state"] == "NONE":
                    if not g["is_jumping"] or g["stage"] == "MOUNTAIN":
                        b[0], b[1] = lanes[g["lane"]], 650
                        g["current_bike_type"] = b[5]
                    else:
                        b[1] += move_speed
                elif g["transition_state"] == "START_ANIM":
                    b[0], b[1] = lanes[1], 650
                elif g["transition_state"] == "END_ANIM":
                    b[0], b[1] = lanes[g["lane"]], 650
            else:
                b[1] += (b[3] * 0.7) + (move_speed * 0.6)

            if not b[2] and b[1] > HEIGHT + 250:
                g["bikes"].remove(b)

        # 인게임 충돌 및 상호작용 판정
        if g["transition_state"] == "NONE":
            player_rect = pygame.Rect(lanes[g["lane"]] - 40, 650 + g["jump_y"] - 45, 80, 90)
            my_bike_rect = pygame.Rect(lanes[g["lane"]] - 40, 650 - 80, 80, 160)

            # 점프대 접촉 검사
            if g["stage"] == "MOUNTAIN" and g["jump_y"] == 0:
                for r in g["ramps"]:
                    ramp_rect = pygame.Rect(r[0] - r[2] // 2, r[1] - r[3] // 2, r[2], r[3])
                    player_center_pos = (lanes[g["lane"]], 650)
                    if ramp_rect.collidepoint(player_center_pos):
                        g["is_jumping"] = True
                        g["jump_v"] = -20
                        g["jump_gravity"] = 0.32
                        g["last_jump"] = current_time

            hijack_triggered = False
            for b in g["bikes"][:]:
                if not b[2]:
                    if b[5] == "CAR":
                        npc_rect = pygame.Rect(b[0] - 48, b[1] - 85, 96, 170)
                    else:
                        npc_rect = pygame.Rect(b[0] - 40, b[1] - 80, 80, 160)

                    if player_rect.colliderect(npc_rect) or my_bike_rect.colliderect(npc_rect):
                        if b[5] == "CAR":
                            g["crash_type"] = "CAR CRASH! (WASTED)"
                            g["game_over"] = True
                            break

                        if g["is_jumping"] and g["stage"] == "CITY":
                            push_direction = random.choice([-1, 1])
                            g["victims"].append({
                                "x": b[0], "y": b[1], "vx": push_direction * random.randint(8, 14),
                                "vy": random.randint(-6, -2),
                                "rot": 0, "rot_speed": push_direction * random.randint(10, 20)
                            })
                            g["bikes"] = [bk for bk in g["bikes"] if not bk[2]]
                            b[2] = True
                            g["current_bike_type"] = b[5]
                            g["is_jumping"], g["jump_y"] = False, 0
                            g["hijack_success"] = True
                            g["score"] += 2000
                            hijack_triggered = True
                            break
                        else:
                            if not hijack_triggered:
                                g["crash_type"] = "BIKE CRASH!"
                                g["game_over"] = True
                                break

            # ★ [수정] 감속 유발하는 b_type == 0 검사 코드를 빼고 물웅덩이와 바위낙하 충돌만 유지
            for b in g["bumps"][:]:
                b[1] += (move_speed if move_speed > 0 else 2)

                # 물웅덩이(2) 및 바위낙하(1) 판정 박스
                bump_rect = pygame.Rect(b[0] - 40, b[1] - 20, 80, 40)
                if g["jump_y"] == 0 and player_rect.colliderect(bump_rect):
                    if b[2] == 2:  # 물 웅덩이 진입 시
                        g["puddle_slip_end"] = current_time + 1.2
                        g["bumps"].remove(b)
                    elif b[2] == 1:  # 산악 바위 낙하물 충돌 시 즉사
                        g["crash_type"] = "ROCK CRASH! (WASTED)"
                        g["game_over"] = True
                        break
                elif b[1] > HEIGHT + 50:
                    g["bumps"].remove(b)

            # 절벽 낙하 검사
            if g["stage"] == "MOUNTAIN" and g["jump_y"] == 0:
                for c in g["cliffs"]:
                    cliff_rect = pygame.Rect(c[0] - c[2] // 2, c[1], c[2], c[3])
                    player_center_pos = (lanes[g["lane"]], 650)
                    if cliff_rect.collidepoint(player_center_pos):
                        g["crash_type"] = "FALL CLIFF! (WASTED)"
                        g["game_over"] = True
                        break

            # 점프 동적 궤적 연산
            if g["is_jumping"]:
                ts = g["time_scale"] if g["time_scale"] > 0 else 0.5
                g["jump_y"] += g["jump_v"] * ts
                g["jump_v"] += g["jump_gravity"] * ts

                if g["jump_y"] >= 0:
                    if g["stage"] == "CITY" and not g["hijack_success"]:
                        g["crash_type"] = "FALL CRASH! (WASTED)"
                        g["game_over"] = True
                    else:
                        g["jump_y"] = 0
                        g["is_jumping"] = False

    # --- 5. 렌더링 파트 ---
    shake_x, shake_y = 0, 0
    if g["stage"] == "MOUNTAIN" and g["slope"] == "DOWNHILL" and not g["game_over"]:
        brake_active = keys[pygame.K_s] or keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        mult = 0.5 if brake_active else 2.0
        shake_x = random.randint(-int(g["time_scale"] * mult), int(g["time_scale"] * mult))
        shake_y = random.randint(-int(g["time_scale"] * mult), int(g["time_scale"] * mult))

    screen.fill(CITY_ROAD_COLOR if g["stage"] == "CITY" else MOUNTAIN_ROAD_COLOR)

    # 점프대 레이어 렌더링
    if g["stage"] == "MOUNTAIN":
        for r in g["ramps"]:
            rx, ry, rw, rh = r[0] + shake_x, r[1] + shake_y, r[2], r[3]
            pygame.draw.rect(screen, RAMP_COLOR, (rx - rw // 2, ry - rh // 2, rw, rh), border_radius=3)
            pygame.draw.rect(screen, (50, 40, 10), (rx - rw // 2, ry - rh // 2, rw, rh), 3, border_radius=3)
            for step in range(-rw // 2, rw // 2, 20):
                pygame.draw.line(screen, (0, 0, 0), (rx + step, ry - rh // 2), (rx + step + 10, ry + rh // 2), 4)

    # 장애물 그래픽 드로잉 파트 (방지턱 그래픽 완전히 제거)
    for b in g["bumps"]:
        bx, by = b[0] + shake_x, b[1] + shake_y
        if b[2] == 2:  # 물 웅덩이
            pygame.draw.ellipse(screen, BLUE, (bx - 40, by - 20, 80, 40))
            pygame.draw.ellipse(screen, (20, 100, 220), (bx - 35, by - 16, 70, 32), 2)
        elif b[2] == 1:  # 산악 낙석 바위 형상
            pygame.draw.circle(screen, (80, 85, 90), (bx, by), 22)
            pygame.draw.circle(screen, (50, 50, 50), (bx, by), 22, 3)

    # 절벽 다각형 렌더링
    if g["stage"] == "MOUNTAIN":
        for c in g["cliffs"]:
            cx, cy, cw, ch, offs = c[0] + shake_x, c[1] + shake_y, c[2], c[3], c[4]
            left_x = cx - cw // 2
            right_x = cx + cw // 2

            poly_points = []
            for idx in range(5):
                poly_points.append((left_x + (cw * idx // 4), cy + offs["top"][idx]))
            for idx in range(1, 9):
                poly_points.append((right_x + offs["right"][idx], cy + (ch * idx // 8)))
            for idx in range(3, -1, -1):
                poly_points.append((left_x + (cw * idx // 4), cy + ch + offs["bottom"][idx]))
            for idx in range(7, 0, -1):
                poly_points.append((left_x + offs["left"][idx], cy + (ch * idx // 8)))

            if len(poly_points) >= 3:
                pygame.draw.polygon(screen, CLIFF_COLOR, poly_points)
                pygame.draw.polygon(screen, (75, 45, 15), poly_points, 4)
                pygame.draw.line(screen, (55, 25, 5), poly_points[0], poly_points[4], 4)

    for x in [200, 400]:
        scroll_val = g["scroll_y"] if g["transition_state"] == "NONE" else 0
        for y in range(int(scroll_val) - 60, HEIGHT, 60):
            is_inside_cliff = False
            if g["stage"] == "MOUNTAIN":
                for c in g["cliffs"]:
                    if (c[0] - c[2] // 2 <= x <= c[0] + c[2] // 2) and (c[1] <= y <= c[1] + c[3]):
                        is_inside_cliff = True
                        break
            if not is_inside_cliff:
                pygame.draw.line(screen, LANE_CITY if g["stage"] == "CITY" else LANE_MOUNTAIN,
                                 (x + shake_x, y + shake_y), (x + shake_x, y + 30 + shake_y), 3)

    if g["transition_state"] == "END_ANIM":
        cx, cy = g["cablecar_x"], g["cablecar_y"]
        pygame.draw.rect(screen, CABLECAR_COLOR, (cx, cy, 110, 150), border_radius=10)
        pygame.draw.rect(screen, (50, 50, 50), (cx + 15, cy + 20, 80, 50))
        pygame.draw.line(screen, (150, 150, 150), (cx + 55, cy), (cx + 55, 0), 4)

    for vic in g["victims"]:
        v_surf = pygame.Surface((50, 50), pygame.SRCALPHA)
        pygame.draw.circle(v_surf, SKIN_COLOR, (25, 15), 12)
        pygame.draw.rect(v_surf, (50, 50, 50), (13, 27, 24, 20), border_radius=4)
        rot_surf = pygame.transform.rotate(v_surf, vic["rot"])
        screen.blit(rot_surf, (int(vic["x"] - rot_surf.get_width() // 2), int(vic["y"] - rot_surf.get_height() // 2)))

    # 자전거 및 자동차 객체 렌더링 파트
    for b in g["bikes"]:
        if b[2] and g["is_jumping"] and g["stage"] == "CITY": continue

        if b[2] and g["transition_state"] == "START_ANIM" and g["start_anim_phase"] == "WALK_IN":
            target_img = fixie_bike_img if b[5] == "FIXIE" else (
                mountain_bike_img if b[5] == "MOUNTAIN" else normal_bike_img)
            if target_img:
                screen.blit(target_img,
                            (int(b[0] - target_img.get_width() // 2), int(b[1] - target_img.get_height() // 2)))
            else:
                pygame.draw.rect(screen, PLAYER_COLOR, (int(b[0] - 45), int(b[1] - 90), 90, 180), border_radius=5)
            continue

        bx, by = b[0] + shake_x, b[1] + shake_y
        if b[2] and g["stage"] == "MOUNTAIN":
            by += g["jump_y"]
            if g["slope"] == "UPHILL": by += 3

        if b[5] == "CAR":
            pygame.draw.rect(screen, CAR_COLOR, (int(bx - 48), int(by - 85), 96, 170), border_radius=12)
            pygame.draw.rect(screen, (200, 235, 255), (int(bx - 38), int(by - 50), 76, 35), border_radius=4)
            pygame.draw.circle(screen, (255, 255, 180), (int(bx - 30), int(by - 75)), 10)
            pygame.draw.circle(screen, (255, 255, 180), (int(bx + 30), int(by - 75)), 10)
        else:
            if b[5] == "FIXIE":
                target_img = fixie_bike_img
            elif b[5] == "MOUNTAIN":
                target_img = mountain_bike_img
            else:
                target_img = normal_bike_img

            if target_img:
                if b[2] and g["is_jumping"]:
                    sf = 1.3
                    z_img = pygame.transform.scale(target_img, (int(target_img.get_width() * sf),
                                                                int(target_img.get_height() * sf)))
                    screen.blit(z_img, (int(bx - z_img.get_width() // 2), int(by - z_img.get_height() // 2)))
                else:
                    screen.blit(target_img,
                                (int(bx - target_img.get_width() // 2), int(by - target_img.get_height() // 2)))
            else:
                if b[5] == "FIXIE":
                    color = FIXIE_COLOR
                elif b[5] == "MOUNTAIN":
                    color = MTB_COLOR
                else:
                    color = PLAYER_COLOR if b[2] else NPC_COLOR
                pygame.draw.rect(screen, color, (int(bx - 45), int(by - 90), 90, 180), border_radius=5)

        if not b[2] and b[5] != "CAR":
            pygame.draw.circle(screen, SKIN_COLOR, (int(bx), int(by - 75)), 22)
            pygame.draw.rect(screen, (50, 50, 50), (int(bx - 20), int(by - 55), 40, 35), border_radius=5)

    if g["transition_state"] == "START_ANIM":
        if g["start_anim_phase"] in ["WALK_IN", "MOUNT"]:
            walk_sway = math.sin(time.time() * 14) * 5
            p_x, p_y = g["start_p_x"], g["start_p_y"] + walk_sway
            pygame.draw.circle(screen, SKIN_COLOR, (int(p_x), int(p_y - 65)), 20)
            pygame.draw.rect(screen, ERROR_COLOR, (int(p_x - 16), int(p_y - 45), 32, 45), border_radius=4)
        elif g["start_anim_phase"] == "READY":
            p_x, p_y = lanes[1], 650
            pygame.draw.circle(screen, SKIN_COLOR, (int(p_x), int(p_y - 75)), 22)
            pygame.draw.rect(screen, ERROR_COLOR, (int(p_x - 20), int(p_y - 55), 40, 35), border_radius=5)

            elapsed = current_time - g["start_countdown_timer"]
            txt = count_font.render("3" if elapsed < 1.0 else ("2" if elapsed < 2.0 else "1"), True, (255, 200, 50))
            screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 - 100))

    elif g["transition_state"] == "END_ANIM":
        if g["end_anim_phase"] in ["STOP_AND_DISMOUNT", "ENTER_CABLECAR"]:
            walk_sway = math.sin(time.time() * 12) * 4
            p_x, p_y = g["end_p_x"], g["end_p_y"] + walk_sway
            pygame.draw.circle(screen, SKIN_COLOR, (int(p_x), int(p_y - 65)), 20)
            pygame.draw.rect(screen, ERROR_COLOR, (int(p_x - 16), int(p_y - 45), 32, 45), border_radius=4)
        elif g["end_anim_phase"] == "ASCEND":
            pygame.draw.circle(screen, SKIN_COLOR, (g["cablecar_x"] + 55, g["cablecar_y"] + 45), 14)
            pygame.draw.rect(screen, ERROR_COLOR, (g["cablecar_x"] + 43, g["cablecar_y"] + 60, 24, 20), border_radius=3)

    elif g["transition_state"] == "NONE" or g["is_jumping"]:
        p_x, p_y = lanes[g["lane"]] + shake_x, 650 + g["jump_y"] + shake_y
        scale_factor = 1.4 if g["is_jumping"] else 1.0

        if is_slipping:
            p_x += math.sin(time.time() * 25) * 12

        pygame.draw.circle(screen, SKIN_COLOR, (int(p_x), int(p_y - 75 * scale_factor)), int(22 * scale_factor))
        pygame.draw.rect(screen, ERROR_COLOR,
                         (int(p_x - 20 * scale_factor), int(p_y - 55 * scale_factor), int(40 * scale_factor),
                          int(35 * scale_factor)), border_radius=5)

    # UI 레이아웃
    score_txt = ui_font.render(f"SCORE: {format(g['score'], ',')}", True, WHITE)
    stage_txt = ui_font.render(f"STAGE: {g['stage']}", True, WHITE)
    screen.blit(score_txt, (20, 20))
    screen.blit(stage_txt, (WIDTH - stage_txt.get_width() - 20, 20))

    b_color = MTB_COLOR if g["current_bike_type"] == "MOUNTAIN" else (
        FIXIE_COLOR if g["current_bike_type"] == "FIXIE" else PLAYER_COLOR)
    bike_txt = ui_font.render(f"BIKE: {g['current_bike_type']}", True, b_color)
    screen.blit(bike_txt, (20, 55))

    if g["stage"] == "MOUNTAIN":
        slope_colors = {"FLAT": WHITE, "UPHILL": (255, 100, 100), "DOWNHILL": (100, 255, 100)}
        slope_texts = {"FLAT": "SLOPE: FLAT", "UPHILL": "SLOPE: UPHILL", "DOWNHILL": "SLOPE: DOWNHILL"}
        slope_txt = ui_font.render(slope_texts[g["slope"]], True, slope_colors[g["slope"]])
        screen.blit(slope_txt, (20, 90))

    if is_slipping and not g["game_over"]:
        slip_txt = ui_font.render("⚠️ SLIPPERY PUDDLE!!", True, BLUE)
        screen.blit(slip_txt, (WIDTH // 2 - slip_txt.get_width() // 2, 140))

    if g["game_over"]:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA);
        overlay.fill((0, 0, 0, 180));
        screen.blit(overlay, (0, 0))
        reason = g["crash_type"]
        reason_txt = go_font.render(reason, True, ERROR_COLOR)
        restart_txt = ui_font.render("Press 'R' to Restart", True, WHITE)
        screen.blit(reason_txt, (WIDTH // 2 - reason_txt.get_width() // 2, HEIGHT // 2 - 60))
        screen.blit(restart_txt, (WIDTH // 2 - restart_txt.get_width() // 2, HEIGHT // 2 + 20))

    pygame.display.flip()
    clock.tick(60)
