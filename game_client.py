# client.py
import pygame
import sys
import json
import base64
import threading
import time  
import random  
from io import BytesIO
from websocket import create_connection

# 정답 단어 풀
catchmind_classes = [
    'cat','dog','bear','elephant','giraffe','lion','tiger',
    'horse','cow','pig','rabbit','duck','penguin','frog','fish',
    'apple','banana','hamburger','hotdog','pizza','bread','strawberry','pineapple',
    'airplane','bicycle','motorcycle','pickup truck','helicopter','rocket','sailboat',
    'chair','table','door','window','hat','eyeglasses','hammer','scissors','guitar','violin','umbrella','shoe',
    'flower','tree','volcano','starfish','windmill','castle','cabin','hot air balloon'
]

# --- 1. 환경 및 레이아웃 설정 ---
pygame.init()

CANVAS_SIZE = 512
MARGIN_Y_BOTTOM = 80
MARGIN_Y_TOP = 160  

HALF_SCREEN_WIDTH = CANVAS_SIZE + 120  
SCREEN_WIDTH = HALF_SCREEN_WIDTH * 2
SCREEN_HEIGHT = CANVAS_SIZE + MARGIN_Y_TOP + MARGIN_Y_BOTTOM

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("AI Catch-Mind! 🎨 (Timer & Countdown Mode)")

BACKGROUND_COLOR = (74, 144, 226)   
CANVAS_BG = (255, 255, 255)         
BORDER_COLOR = (29, 63, 107)        
SPRING_COLOR = (200, 200, 200)      

COLOR_PALETTE = {
    "검정": (40, 40, 40), "빨강": (235, 94, 85), "주황": (245, 150, 75),
    "노랑": (245, 215, 80), "초록": (80, 185, 120), "파랑": (74, 144, 226),
    "남색": (53, 73, 143), "보라": (155, 89, 182), "갈색": (139, 69, 19)   
}

current_brush_color = COLOR_PALETTE["검정"]
is_eraser = False
is_fill_mode = False  
brush_thickness = 6
ERASER_THICKNESS = 24

CENTER_LINE_X = SCREEN_WIDTH // 2
LEFT_CANVAS_X = (CENTER_LINE_X // 2) - (CANVAS_SIZE // 2)
LEFT_CANVAS_Y = MARGIN_Y_TOP
RIGHT_CANVAS_X = (CENTER_LINE_X + (SCREEN_WIDTH - CENTER_LINE_X) // 2) - (CANVAS_SIZE // 2)
RIGHT_CANVAS_Y = MARGIN_Y_TOP

user_canvas = pygame.Surface((CANVAS_SIZE, CANVAS_SIZE))
user_canvas.fill(CANVAS_BG)
ai_canvas = pygame.Surface((CANVAS_SIZE, CANVAS_SIZE))
ai_canvas.fill(CANVAS_BG)

# --- ⏱️ 타이머 및 게임 상태 관련 변수 정의 ---
GAME_STATE = "COUNTDOWN"  
state_start_time = time.time()  

# 타이머 규칙 설정
LIMIT_TIME = 100.0        
COUNTDOWN_DURATION = 4.0  # ⏳ [수정] 3초(숫자) + 1초(Start! 대기) = 총 4초로 변경
LOCKOUT_DURATION = 3.0

# 🎯 [추가] 스코어링 규칙 및 누적 변수 설정
MAX_SCORE = 100           # 라운드당 최대 점수 (M)
current_round_score = MAX_SCORE  # 실시간으로 깎여서 화면에 보여줄 현재 점수
total_score = 0           # 게임 전체 누적 총점

# 라운드 규칙 추가
TOTAL_ROUNDS = 5           # R = 총 5라운드 진행으로 가정
current_round = 1          # 현재 라운드 추적 변수

# 타이머 바 디자인 설정 변수
BAR_EMPTY_COLOR = (180, 180, 180)  
BAR_FILL_COLOR = (46, 204, 113)    
BAR_HEIGHT = 12                    

# 기존 게임 변수
is_solved = False                                  
pen_active = False  

opponent_guess_text = ""
opponent_guess_time = 0.0
current_stroke_points = []

# --중복 방지 단어 풀 초기화--
# 원본 리스트를 복사하여 이번 판에 사용할 가변 주머니를 만듭니다.
current_game_pool = catchmind_classes.copy()
random.shuffle(current_game_pool)  # 미리 한 번 무작위로 섞어둡니다.

# 첫 번째 문제 추출 (가장 뒤의 단어를 뽑으면서 리스트에서 제거)
current_answer = current_game_pool.pop()  


# --- 🌐 웹소켓 클라이언트 연동 설정 ---
SERVER_URL = "ws://localhost:8000/ws"
ws = None

def send_canvas_to_server():
    if ws:
        from PIL import Image
        img_bytes = pygame.image.tobytes(user_canvas, "RGB") 
        pil_img = Image.frombytes("RGB", (CANVAS_SIZE, CANVAS_SIZE), img_bytes)
        buffered = BytesIO()
        pil_img.save(buffered, format="PNG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        payload = {"type": "stroke_canvas", "image": img_b64}
        try:
            ws.send(json.dumps(payload))
        except Exception as e:
            print(f"⚠️ 서버 데이터 전송 실패: {e}")

# --- 🔄 Undo / Redo 시스템 ---
undo_stack = [(user_canvas.copy(), 0)]
redo_stack = []

def save_state(stroke_count=0):
    global undo_stack, redo_stack
    redo_stack.clear()
    undo_stack.append((user_canvas.copy(), stroke_count))
    if len(undo_stack) > 10:  
        undo_stack.pop(0)

def handle_undo():
    if not pen_active: return  
    if len(undo_stack) > 1:
        state = undo_stack.pop()
        redo_stack.append(state)
        prev_surface, prev_stroke_count = undo_stack[-1]
        user_canvas.blit(prev_surface, (0, 0))
        if prev_stroke_count > 1:
            send_canvas_to_server()

def handle_redo():
    if not pen_active: return  
    if len(redo_stack) > 0:
        state = redo_stack.pop()
        undo_stack.append(state)
        next_surface, next_stroke_count = state
        user_canvas.blit(next_surface, (0, 0))
        if next_stroke_count > 1:
            send_canvas_to_server()

# --- 🪣 채우기 (Flood Fill) ---
def flood_fill(surface, start_pos, fill_color):
    width, height = surface.get_size()
    pixels = pygame.PixelArray(surface)
    start_x, start_y = start_pos
    target_color = pixels[start_x, start_y]
    if target_color == surface.map_rgb(fill_color):
        pixels.close()
        return
    queue = [(start_x, start_y)]
    while queue:
        cx, cy = queue.pop(0)
        if pixels[cx, cy] == target_color:
            pixels[cx, cy] = fill_color
            if cx > 0: queue.append((cx - 1, cy))
            if cx < width - 1: queue.append((cx + 1, cy))
            if cy > 0: queue.append((cx, cy - 1))
            if cy < height - 1: queue.append((cx, cy + 1))
    pixels.close()

def bg_receive_loop():
    global ai_canvas
    while True:
        if ws:
            try:
                response = ws.recv()
                res_data = json.loads(response)
                
                if res_data.get("type") == "ai_response":
                    # 🛑 [핵심 버그 수정] 오직 플레이 중일 때만 서버에서 온 그림을 반영합니다.
                    # 시간초과(LOCKOUT)되거나 카운트다운(COUNTDOWN) 중일 때는 서버 응답을 무시(드롭)합니다.
                    if GAME_STATE == "PLAYING":
                        res_b64 = res_data.get("image")
                        res_bytes = base64.b64decode(res_b64)
                        
                        img_io = BytesIO(res_bytes)
                        incoming_img = pygame.image.load(img_io, "PNG")
                        
                        scaled_img = pygame.transform.smoothscale(incoming_img, (CANVAS_SIZE, CANVAS_SIZE))
                        ai_canvas.blit(scaled_img, (0, 0))
                    else:
                        # 플레이 중이 아닐 때 온 패킷은 로그만 남기거나 조용히 폐기합니다.
                        print("🐾 [패킷 폐기] 플레이 시간이 종료된 후 도착한 이미지이므로 화면 반영을 차단합니다.")
                        
            except Exception as e:
                print(f"🔌 서버 수신 스레드 종료 혹은 에러: {e}")
                break

try:
    from PIL import Image 
    ws = create_connection(SERVER_URL)
    print("🚀 FastAPI 서버와 웹소켓 연결 완료!")
    rx_thread = threading.Thread(target=bg_receive_loop, daemon=True)
    rx_thread.start()
except Exception as e:
    print(f"⚠️ 오프라인 모드로 실행됩니다. 서버 에러: {e}")

# --- UI 레이아웃 리소스 및 폰트 세팅 ---
label_font = pygame.font.SysFont("malgungothic", 24, bold=True)
input_font = pygame.font.SysFont("malgungothic", 20, bold=True)
btn_font = pygame.font.SysFont("malgungothic", 12, bold=True)
game_ui_font = pygame.font.SysFont("malgungothic", 26, bold=True)
popup_font = pygame.font.SysFont("malgungothic", 20, bold=True)
countdown_font = pygame.font.SysFont("arial", 72, bold=True)
game_over_font = pygame.font.SysFont("arial", 40, bold=True)

INPUT_BOX_WIDTH, INPUT_BOX_HEIGHT = 280, 44
input_box_x = RIGHT_CANVAS_X + (CANVAS_SIZE - INPUT_BOX_WIDTH) // 2 + 35
input_box_y = RIGHT_CANVAS_Y + CANVAS_SIZE + 15
input_box_rect = pygame.Rect(input_box_x, input_box_y, INPUT_BOX_WIDTH, INPUT_BOX_HEIGHT)

input_text, editing_text = "", ""

try:
    pygame.start_text_input()
except AttributeError:
    pass

COLOR_BTN_SIZE = 24
color_buttons = []
for i, (name, rgb) in enumerate(COLOR_PALETTE.items()):
    bx = LEFT_CANVAS_X + (i * (COLOR_BTN_SIZE + 6))
    by = LEFT_CANVAS_Y + CANVAS_SIZE + 18
    color_buttons.append({"rect": pygame.Rect(bx, by, COLOR_BTN_SIZE, COLOR_BTN_SIZE), "color": rgb, "name": name})

start_fx_x = LEFT_CANVAS_X + (len(COLOR_PALETTE) * (COLOR_BTN_SIZE + 6)) + 12
fx_y = LEFT_CANVAS_Y + CANVAS_SIZE + 18

btn_fill = pygame.Rect(start_fx_x, fx_y, 50, 24)
btn_eraser = pygame.Rect(start_fx_x + 54, fx_y, 50, 24)
btn_undo = pygame.Rect(start_fx_x + 108, fx_y, 40, 24)    
btn_redo = pygame.Rect(start_fx_x + 152, fx_y, 40, 24)    
btn_clear = pygame.Rect(start_fx_x + 196, fx_y, 50, 24)

SLIDER_X, SLIDER_Y = LEFT_CANVAS_X, LEFT_CANVAS_Y + CANVAS_SIZE + 54
SLIDER_WIDTH, SLIDER_HEIGHT = 220, 8
slider_rect = pygame.Rect(SLIDER_X, SLIDER_Y, SLIDER_WIDTH, SLIDER_HEIGHT)

MIN_THICK, MAX_THICK = 2, 30
def get_handle_x():
    ratio = (brush_thickness - MIN_THICK) / (MAX_THICK - MIN_THICK)
    return SLIDER_X + int(ratio * SLIDER_WIDTH)

slider_handle_rect = pygame.Rect(get_handle_x() - 6, SLIDER_Y - 4, 12, 16)
dragging_slider = False
drawing = False
last_pos = None

def is_inside_user_canvas(pos):
    x, y = pos
    return (LEFT_CANVAS_X <= x < LEFT_CANVAS_X + CANVAS_SIZE) and \
           (LEFT_CANVAS_Y <= y < LEFT_CANVAS_Y + CANVAS_SIZE)

def draw_on_canvas(start, end):
    color = CANVAS_BG if is_eraser else current_brush_color
    thick = ERASER_THICKNESS if is_eraser else brush_thickness
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    distance = max(abs(dx), abs(dy))
    if distance == 0:
        pygame.draw.circle(user_canvas, color, start, thick // 2)
        return
    for i in range(int(distance) + 1):
        t = i / distance
        curr_x = int(start[0] + dx * t)
        curr_y = int(start[1] + dy * t)
        pygame.draw.circle(user_canvas, color, (curr_x, curr_y), thick // 2)

# --- 2. 게임 메인 루프 ---
clock = pygame.time.Clock()
running = True

while running:
    current_time = time.time()  
    elapsed_in_state = current_time - state_start_time 
    
    # --- ⏱️ 상태 머신 제어 파트 ---
    if GAME_STATE == "COUNTDOWN":
        pen_active = False
        current_round_score = MAX_SCORE  # 카운트다운 중에는 항상 만점 상태 유지  
        if elapsed_in_state >= COUNTDOWN_DURATION:
            GAME_STATE = "PLAYING"
            state_start_time = current_time  
            pen_active = True  
            
    elif GAME_STATE == "PLAYING":
        decayed_score = MAX_SCORE * (1.0 - (elapsed_in_state / LIMIT_TIME))

        # 최소 10% 점수 보장 (하한선 배치)
        min_guaranteed_score = MAX_SCORE * 0.1
        current_round_score = int(max(decayed_score, min_guaranteed_score))

        if elapsed_in_state >= LIMIT_TIME:
            GAME_STATE = "LOCKOUT"
            is_solved = True  
            state_start_time = current_time  
            pen_active = False  
            drawing = False

            print("\n========================================")
            print(f"⏰ [시간 초과] 제한 시간 {LIMIT_TIME}초가 경과했습니다.")
            print(f"❌ 획득 점수: 0 점 (종료 직전 점수: {current_round_score}점)")
            print(f"🏆 누적 총점: {total_score} 점 (변동 없음)")
            print("========================================\n")
            
    elif GAME_STATE == "LOCKOUT":
        pen_active = False  
        if elapsed_in_state >= LOCKOUT_DURATION:
            # 🏁 [라운드 종료 체크]
            if current_round < TOTAL_ROUNDS:
                # 다음 라운드 진입 전초 작업
                current_round += 1
                # 🎯 [수정] 중복 없는 주머니에서 다음 단어 꺼내기
                current_answer = current_game_pool.pop()
                is_solved = False
                user_canvas.fill(CANVAS_BG)  
                ai_canvas.fill(CANVAS_BG)
                save_state(stroke_count=0) 
                
                GAME_STATE = "COUNTDOWN"
                state_start_time = time.time()  
            else:
                # 🏆 모든 라운드가 끝났다면 최종 종료 상태로 전환!
                GAME_STATE = "GAME_OVER"
                state_start_time = time.time()
                print(f"🏁 게임 오버! 총 {TOTAL_ROUNDS}라운드 종료. 최종 누적 점수: {total_score}점")

    mouse_pos = pygame.mouse.get_pos()
    if pen_active and (is_inside_user_canvas(mouse_pos) or dragging_slider):
        pygame.mouse.set_visible(False)
    else:
        pygame.mouse.set_visible(True)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and pen_active:  
                if is_inside_user_canvas(mouse_pos):
                    canvas_pos = (mouse_pos[0] - LEFT_CANVAS_X, mouse_pos[1] - LEFT_CANVAS_Y)
                    if is_fill_mode:
                        flood_fill(user_canvas, canvas_pos, current_brush_color)
                        save_state(stroke_count=999) 
                        send_canvas_to_server() 
                    else:
                        drawing = True
                        last_pos = canvas_pos
                        current_stroke_points = [canvas_pos] 
                        draw_on_canvas(last_pos, last_pos)
                else:
                    for btn in color_buttons:
                        if btn["rect"].collidepoint(mouse_pos):
                            current_brush_color = btn["color"]
                            is_eraser, is_fill_mode = False, False
                            
                    if btn_fill.collidepoint(mouse_pos):
                        is_fill_mode, is_eraser = True, False
                    elif btn_eraser.collidepoint(mouse_pos):
                        is_eraser, is_fill_mode = True, False
                    elif btn_undo.collidepoint(mouse_pos):
                        handle_undo()
                    elif btn_redo.collidepoint(mouse_pos):
                        handle_redo()
                    elif btn_clear.collidepoint(mouse_pos):
                        user_canvas.fill(CANVAS_BG)
                        save_state(stroke_count=0) 
                        
                    if slider_handle_rect.collidepoint(mouse_pos) or slider_rect.collidepoint(mouse_pos):
                        dragging_slider = True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if drawing:
                    drawing = False
                    last_pos = None
                    stroke_pts_len = len(current_stroke_points)
                    save_state(stroke_count=stroke_pts_len) 
                    if stroke_pts_len > 1:
                        send_canvas_to_server()
                    current_stroke_points = [] 
                dragging_slider = False

        elif event.type == pygame.MOUSEMOTION:
            if pen_active:  
                if drawing and last_pos:
                    if is_inside_user_canvas(mouse_pos):
                        curr_canvas_pos = (mouse_pos[0] - LEFT_CANVAS_X, mouse_pos[1] - LEFT_CANVAS_Y)
                        current_stroke_points.append(curr_canvas_pos) 
                        draw_on_canvas(last_pos, curr_canvas_pos)
                        last_pos = curr_canvas_pos
                    else:
                        last_pos = None
                
                if dragging_slider:
                    val_x = max(SLIDER_X, min(mouse_pos[0], SLIDER_X + SLIDER_WIDTH))
                    ratio = (val_x - SLIDER_X) / SLIDER_WIDTH
                    brush_thickness = int(MIN_THICK + ratio * (MAX_THICK - MIN_THICK))

        elif event.type == pygame.TEXTINPUT:
            if GAME_STATE == "PLAYING":  
                input_text += event.text
                editing_text = ""
        elif event.type == pygame.TEXTEDITING:
            if GAME_STATE == "PLAYING":
                editing_text = event.text
        elif event.type == pygame.KEYDOWN:
            if GAME_STATE == "GAME_OVER":
                if event.key == pygame.K_r:  # 'R' 키를 누르면 리스타트!
                    total_score = 0
                    current_round = 1
                    current_round_score = MAX_SCORE
                    is_solved = False
                    user_canvas.fill(CANVAS_BG)
                    ai_canvas.fill(CANVAS_BG)
                    save_state(stroke_count=0)
                    
                    # 🎯 [추가] 새 게임을 위해 단어 주머니 리셋 및 셔플
                    current_game_pool = catchmind_classes.copy()
                    random.shuffle(current_game_pool)
                    current_answer = current_game_pool.pop() # 새 첫 문제

                    GAME_STATE = "COUNTDOWN"
                    state_start_time = time.time()
                    print("🔄 게임을 처음부터 다시 시작합니다!")
            if event.key == pygame.K_RETURN and GAME_STATE == "PLAYING":
                final_guess = input_text + editing_text
                final_guess = final_guess.strip()
                
                if final_guess:
                    opponent_guess_text = final_guess
                    opponent_guess_time = current_time
                    if ws:
                        try:
                            ws.send(json.dumps({"type": "guess", "text": final_guess}))
                        except: pass
                    
                    if final_guess == current_answer and not is_solved:
                        GAME_STATE = "LOCKOUT"
                        is_solved = True
                        state_start_time = current_time  
                        pen_active = False  
                        drawing = False

                        # 🎯 [추가] 맞춘 순간 정지된 라운드 점수를 총점에 누적!
                        total_score += current_round_score
                        print("\n========================================")
                        print(f"🥇 [정답 돌파] 제시어: '{current_answer}'")
                        print(f"✨ 획득 점수: +{current_round_score} 점")
                        print(f"🏆 누적 총점: {total_score} 점")
                        print("========================================\n")

                    input_text, editing_text = "", ""
            elif event.key == pygame.K_BACKSPACE and len(editing_text) == 0:
                input_text = input_text[:-1]

    # --- 3. 렌더링 영역 ---
    screen.fill(BACKGROUND_COLOR)
    
    left_center_x = LEFT_CANVAS_X + (CANVAS_SIZE // 2)
    ans_text_surf = game_ui_font.render(f"정답: {current_answer}", True, (245, 215, 80)) 
    screen.blit(ans_text_surf, ans_text_surf.get_rect(center=(left_center_x, LEFT_CANVAS_Y - 50)))
    
    right_center_x = RIGHT_CANVAS_X + (CANVAS_SIZE // 2)
    display_right_ans = current_answer if is_solved else "???"
    ai_text_surf = game_ui_font.render(f"정답: {display_right_ans}", True, (245, 215, 80))
    screen.blit(ai_text_surf, ai_text_surf.get_rect(center=(right_center_x, RIGHT_CANVAS_Y - 50)))

    # 📏 [슬림형 타이머 바 연산 반영]
    BAR_MARGIN_X = 40  
    REDUCED_BAR_WIDTH = CANVAS_SIZE - (BAR_MARGIN_X * 2)  
    
    for canvas_start_x in [LEFT_CANVAS_X, RIGHT_CANVAS_X]:
        bar_x_pos = canvas_start_x + BAR_MARGIN_X  
        bar_y_pos = LEFT_CANVAS_Y - 90  
        
        pygame.draw.rect(screen, BAR_EMPTY_COLOR, (bar_x_pos, bar_y_pos, REDUCED_BAR_WIDTH, BAR_HEIGHT), border_radius=4)
        
        if GAME_STATE == "PLAYING":
            time_ratio = max(0.0, min(1.0, (LIMIT_TIME - elapsed_in_state) / LIMIT_TIME))
            current_bar_width = int(REDUCED_BAR_WIDTH * time_ratio)
            if current_bar_width > 0:
                pygame.draw.rect(screen, BAR_FILL_COLOR, (bar_x_pos, bar_y_pos, current_bar_width, BAR_HEIGHT), border_radius=4)
        elif GAME_STATE == "COUNTDOWN":
            pygame.draw.rect(screen, BAR_FILL_COLOR, (bar_x_pos, bar_y_pos, REDUCED_BAR_WIDTH, BAR_HEIGHT), border_radius=4)

    if opponent_guess_text and (current_time - opponent_guess_time <= 1.0):
        popup_surf = popup_font.render(f"상대방 입력: {opponent_guess_text}", True, (255, 94, 85)) 
        popup_x = left_center_x + (ans_text_surf.get_width() // 2) + 20
        screen.blit(popup_surf, (popup_x, LEFT_CANVAS_Y - 60))

    # 도화지 아웃라인 박스 및 스프링 드로잉
    BORDER_THICK = 8
    pygame.draw.rect(screen, BORDER_COLOR, (LEFT_CANVAS_X - BORDER_THICK, LEFT_CANVAS_Y - BORDER_THICK, CANVAS_SIZE + (BORDER_THICK*2), CANVAS_SIZE + (BORDER_THICK*2)), border_radius=4)
    pygame.draw.rect(screen, BORDER_COLOR, (RIGHT_CANVAS_X - BORDER_THICK, RIGHT_CANVAS_Y - BORDER_THICK, CANVAS_SIZE + (BORDER_THICK*2), CANVAS_SIZE + (BORDER_THICK*2)), border_radius=4)

    screen.blit(user_canvas, (LEFT_CANVAS_X, LEFT_CANVAS_Y))
    screen.blit(ai_canvas, (RIGHT_CANVAS_X, RIGHT_CANVAS_Y))

    for cx in [LEFT_CANVAS_X, RIGHT_CANVAS_X]:
        for idx in range(12):
            ring_x = cx + 25 + (idx * 42)
            ring_y = LEFT_CANVAS_Y - 8
            pygame.draw.rect(screen, SPRING_COLOR, (ring_x, ring_y - 12, 10, 16), border_radius=3)
            pygame.draw.rect(screen, (50, 50, 50), (ring_x, ring_y - 12, 10, 16), width=1, border_radius=3)

    for dot_y in range(0, SCREEN_HEIGHT, 20):
        pygame.draw.circle(screen, BORDER_COLOR, (CENTER_LINE_X, dot_y), 3)

    # ⏱️ [수정] 4초 구조에 대응하는 3, 2, 1, Start! 실시간 텍스트 오버레이 매핑
    if GAME_STATE == "COUNTDOWN":
        if elapsed_in_state < 1.0:
            count_str = "3"
        elif elapsed_in_state < 2.0:
            count_str = "2"
        elif elapsed_in_state < 3.0:
            count_str = "1"
        else:
            count_str = "Start!"  # 3.0초 ~ 4.0초 구간 동안 온전하게 화면에 머묾
            
        text_color = (255, 60, 60) 
        overlay_surf = countdown_font.render(count_str, True, text_color)
        
        screen.blit(overlay_surf, overlay_surf.get_rect(center=(LEFT_CANVAS_X + CANVAS_SIZE // 2, LEFT_CANVAS_Y + CANVAS_SIZE // 2)))
        screen.blit(overlay_surf, overlay_surf.get_rect(center=(RIGHT_CANVAS_X + CANVAS_SIZE // 2, RIGHT_CANVAS_Y + CANVAS_SIZE // 2)))

    # 컬러 팔레트 및 컨트롤러 UI 렌더링
    for btn in color_buttons:
        pygame.draw.rect(screen, btn["color"], btn["rect"], border_radius=4)
        if current_brush_color == btn["color"] and not is_eraser and not is_fill_mode:
            pygame.draw.rect(screen, (255, 255, 255), btn["rect"], width=2, border_radius=4)
        else:
            pygame.draw.rect(screen, BORDER_COLOR, btn["rect"], width=1, border_radius=4)

    fx_buttons = [
        (btn_fill, "채우기", is_fill_mode), (btn_eraser, "지우개", is_eraser),
        (btn_undo, "<-", False), (btn_redo, "->", False), (btn_clear, "초기화", False)
    ]
    for rect, label, active in fx_buttons:
        bg_col = (255, 213, 0) if active else (240, 240, 240)
        pygame.draw.rect(screen, bg_col, rect, border_radius=4)
        pygame.draw.rect(screen, BORDER_COLOR, rect, width=1, border_radius=4)
        text_surf = btn_font.render(label, True, (0, 0, 0))
        screen.blit(text_surf, text_surf.get_rect(center=rect.center))

    slider_handle_rect.x = get_handle_x() - 6  
    pygame.draw.rect(screen, (40, 60, 90), slider_rect, border_radius=3)
    pygame.draw.rect(screen, (240, 240, 240), slider_handle_rect, border_radius=3)
    pygame.draw.rect(screen, BORDER_COLOR, slider_handle_rect, width=1, border_radius=3)

    label_surf = label_font.render("정답:", True, (255, 255, 255))
    screen.blit(label_surf, (input_box_rect.x - label_surf.get_width() - 15, input_box_rect.y + (INPUT_BOX_HEIGHT - label_surf.get_height()) // 2))
    pygame.draw.rect(screen, (255, 255, 255), input_box_rect, border_radius=6)
    pygame.draw.rect(screen, BORDER_COLOR, input_box_rect, width=2, border_radius=6)

    full_display_text = input_text + editing_text
    text_surface = input_font.render(full_display_text, True, (30, 30, 30))
    screen.blit(text_surface, (input_box_rect.x + 12, input_box_rect.y + (INPUT_BOX_HEIGHT - text_surface.get_height()) // 2))

    if pen_active and is_inside_user_canvas(mouse_pos):
        if is_fill_mode:
            pygame.draw.line(screen, (40, 40, 40), (mouse_pos[0]-8, mouse_pos[1]), (mouse_pos[0]+8, mouse_pos[1]), 2)
            pygame.draw.line(screen, (40, 40, 40), (mouse_pos[0], mouse_pos[1]-8), (mouse_pos[0], mouse_pos[1]+8), 2)
        elif is_eraser:
            pygame.draw.circle(screen, (40, 40, 40), mouse_pos, ERASER_THICKNESS // 2, width=1)
        else:
            pygame.draw.circle(screen, current_brush_color, mouse_pos, brush_thickness // 2)
            pygame.draw.circle(screen, (255, 255, 255), mouse_pos, brush_thickness // 2, width=1)

    # --- 렌더링 파트 최하단 ---
    if GAME_STATE == "GAME_OVER":
        # 파란색 (R: 30, G: 80, B: 220) 또는 선명한 파란색
        FINAL_SCORE_COLOR = (30, 144, 255) 
        
        # 표시할 문자열 생성
        final_text = f"Final Score: {total_score}"
        text_overlay = game_over_font.render(final_text, True, FINAL_SCORE_COLOR)
        
        # 각 캔버스의 정중앙 좌표 계산 후 반투명 사각형이나 텍스트를 덮어씌움
        # 캔버스 중앙 = 시작X + (CANVAS_SIZE // 2) , 시작Y + (CANVAS_SIZE // 2)
        left_canvas_center = (LEFT_CANVAS_X + CANVAS_SIZE // 2, LEFT_CANVAS_Y + CANVAS_SIZE // 2)
        right_canvas_center = (RIGHT_CANVAS_X + CANVAS_SIZE // 2, RIGHT_CANVAS_Y + CANVAS_SIZE // 2)
        
        screen.blit(text_overlay, text_overlay.get_rect(center=left_canvas_center))
        screen.blit(text_overlay, text_overlay.get_rect(center=right_canvas_center))

    pygame.display.flip()
    clock.tick(120)

pygame.quit()
sys.exit()