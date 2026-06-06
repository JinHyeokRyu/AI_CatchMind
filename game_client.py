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
    'airplane','bicycle','motorcycle','truck','helicopter','rocket','sailboat',
    'chair','table','door','window','hat','glasses','hammer','scissors','guitar','violin','umbrella','shoe',
    'flower','tree','volcano','starfish','windmill','castle','cabin','hot air balloon'
]
# 한영 및 동음이의어 매핑
catchmind_map = {
    'cat': ['고양이', '야옹이', 'cat', 'kitten', 'kitty'],
    'dog': ['개', '강아지', 'dog', 'puppy'],
    'bear': ['곰', 'bear'],
    'elephant': ['코끼리', 'elephant'],
    'giraffe': ['기린', 'giraffe'],
    'lion': ['사자', 'lion'],
    'tiger': ['호랑이', 'tiger'],
    'horse': ['말', 'horse', 'pony'],
    'cow': ['소', 'cow', 'cattle', 'bull', 'ox'],
    'pig': ['돼지', 'pig', 'piggy', 'hog'],
    'rabbit': ['토끼', 'rabbit', 'bunny'],
    'duck': ['오리', 'duck'],
    'penguin': ['펭귄', 'penguin'],
    'frog': ['개구리', 'frog'],
    'fish': ['물고기', '생선', 'fish'],
    'apple': ['사과', 'apple'],
    'banana': ['바나나', 'banana'],
    'hamburger': ['햄버거', '버거', 'hamburger', 'burger'],
    'hotdog': ['핫도그', 'hotdog', 'hot dog'],
    'pizza': ['피자', 'pizza'],
    'bread': ['빵', 'bread', 'loaf'],
    'strawberry': ['딸기', 'strawberry'],
    'pineapple': ['파인애플', 'pineapple'],
    'airplane': ['비행기', 'airplane', 'aeroplane', 'plane'],
    'bicycle': ['자전거', 'bicycle', 'bike'],
    'motorcycle': ['오토바이', 'motorcycle', 'motorbike', 'bike'],
    'truck': ['트럭', 'truck', 'lorry'],
    'helicopter': ['헬리콥터', '헬기', 'helicopter', 'copter'],
    'rocket': ['로켓', 'rocket', 'spaceship'],
    'sailboat': ['돛단배', '범선', '돛배', '돋배', 'sailboat', 'sailing boat', 'yacht'],
    'chair': ['의자', 'chair'],
    'table': ['탁자', '테이블', 'table', 'desk'],
    'door': ['문', 'door', 'gate'],
    'window': ['창문', '창', 'window'],
    'hat': ['모자', 'hat', 'cap'],
    'glasses': ['안경', 'glasses', 'spectacles'],
    'hammer': ['망치', 'hammer'],
    'scissors': ['가위', 'scissors'],
    'guitar': ['기타', 'guitar'],
    'violin': ['바이올린', 'violin'],
    'umbrella': ['우산', 'umbrella'],
    'shoe': ['신발', '구두', 'shoe', 'shoes', 'boots'],
    'flower': ['꽃', 'flower', 'blossom'],
    'tree': ['나무', 'tree'],
    'volcano': ['화산', 'volcano'],
    'starfish': ['불가사리', 'starfish'],
    'windmill': ['풍차', 'windmill'],
    'castle': ['성', 'castle', 'fortress'],
    'cabin': ['오두막', '통나무집', 'cabin', 'hut', 'cottage'],
    'hot air balloon': ['열기구', 'hot air balloon', 'balloon']
}
# --- 1. 환경 및 레이아웃 설정 ---
pygame.init()

CANVAS_SIZE = 512
MARGIN_Y_BOTTOM = 80
MARGIN_Y_TOP = 160  

HALF_SCREEN_WIDTH = CANVAS_SIZE + 120  
SCREEN_WIDTH = HALF_SCREEN_WIDTH * 2
SCREEN_HEIGHT = CANVAS_SIZE + MARGIN_Y_TOP + MARGIN_Y_BOTTOM

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("AI Catch-Mind! 🎨")

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
user_canvas_edges = pygame.Surface((CANVAS_SIZE, CANVAS_SIZE))  

user_canvas.fill(CANVAS_BG)
user_canvas_edges.fill(CANVAS_BG)

ai_canvas = pygame.Surface((CANVAS_SIZE, CANVAS_SIZE))
ai_canvas.fill(CANVAS_BG)

# --- ⏱️ 타이머 및 게임 상태 관련 변수 정의 ---
GAME_STATE = "START_SCREEN"  
state_start_time = time.time()  

LIMIT_TIME = 100.0        
COUNTDOWN_DURATION = 4.0  
LOCKOUT_DURATION = 3.0

MAX_SCORE = 100           
current_round_score = MAX_SCORE  
total_score = 0           

TOTAL_ROUNDS = 5           
current_round = 1          

BAR_EMPTY_COLOR = (180, 180, 180)  
BAR_FILL_COLOR = (46, 204, 113)    
BAR_HEIGHT = 12                    

is_solved = False                                                   
pen_active = False  

opponent_guess_text = ""
opponent_guess_time = 0.0
current_stroke_points = []

# 한/영 전환
current_lang_mode = 'EN'
# 현재 한/영 모드 및 게임 상태에 따른 출력 단어 결정 함수
def get_display_word(eng_ans, is_solved_or_playing):
    if not is_solved_or_playing:
        return "???"
    
    if current_lang_mode == 'KO':
        # catchmind_map에서 첫 번째 단어(한글)를 가져옴, 없을 경우 기본 영어 반환
        word_list = catchmind_map.get(eng_ans, [])
        return word_list[0] if word_list else eng_ans
    else:
        return eng_ans

# --중복 방지 단어 풀 초기화--
current_game_pool = catchmind_classes.copy()
random.shuffle(current_game_pool)  

current_answer = current_game_pool.pop()  

# --- 🌐 웹소켓 클라이언트 연동 설정 ---
SERVER_URL = "ws://localhost:8000/ws"
ws = None

def send_canvas_to_server():
    if ws:
        from PIL import Image
        img_bytes_color = pygame.image.tobytes(user_canvas, "RGB") 
        pil_img_color = Image.frombytes("RGB", (CANVAS_SIZE, CANVAS_SIZE), img_bytes_color)
        buffered_color = BytesIO()
        pil_img_color.save(buffered_color, format="PNG")
        img_color_b64 = base64.b64encode(buffered_color.getvalue()).decode('utf-8')
        
        img_bytes_edge = pygame.image.tobytes(user_canvas_edges, "RGB") 
        pil_img_edge = Image.frombytes("RGB", (CANVAS_SIZE, CANVAS_SIZE), img_bytes_edge)
        buffered_edge = BytesIO()
        pil_img_edge.save(buffered_edge, format="PNG")
        img_edge_b64 = base64.b64encode(buffered_edge.getvalue()).decode('utf-8')
        
        payload = {
            "type": "stroke_canvas", 
            "image_edge": img_edge_b64,    
            "image_color": img_color_b64   
        }
        try:
            ws.send(json.dumps(payload))
        except Exception as e:
            print(f"⚠️ 서버 데이터 전송 실패: {e}")

# --- 🔄 Undo / Redo 시스템 ---
undo_stack = [(user_canvas.copy(), user_canvas_edges.copy(), 0)]
redo_stack = []

def save_state(stroke_count=0):
    global undo_stack, redo_stack
    redo_stack.clear()
    undo_stack.append((user_canvas.copy(), user_canvas_edges.copy(), stroke_count))
    if len(undo_stack) > 10:  
        undo_stack.pop(0)

def handle_undo():
    if not pen_active: return  
    if len(undo_stack) > 1:
        state = undo_stack.pop()
        redo_stack.append(state)
        prev_color_surface, prev_edge_surface, prev_stroke_count = undo_stack[-1]
        user_canvas.blit(prev_color_surface, (0, 0))
        user_canvas_edges.blit(prev_edge_surface, (0, 0))
        if prev_stroke_count > 1:
            send_canvas_to_server()

def handle_redo():
    if not pen_active: return  
    if len(redo_stack) > 0:
        state = redo_stack.pop()
        undo_stack.append(state)
        next_color_surface, next_edge_surface, next_stroke_count = state
        user_canvas.blit(next_color_surface, (0, 0))
        user_canvas_edges.blit(next_edge_surface, (0, 0))
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

# 패킷 수신 및 생성된 이미지 표시, 비동기 레이스 문제 해결
def bg_receive_loop():
    global ai_canvas
    while True:
        if ws:
            try:
                response = ws.recv()
                res_data = json.loads(response)
                
                if res_data.get("type") == "ai_response":
                    if GAME_STATE == "PLAYING":
                        res_b64 = res_data.get("image")
                        res_bytes = base64.b64decode(res_b64)
                        
                        img_io = BytesIO(res_bytes)
                        incoming_img = pygame.image.load(img_io, "PNG")
                        
                        scaled_img = pygame.transform.smoothscale(incoming_img, (CANVAS_SIZE, CANVAS_SIZE))
                        ai_canvas.blit(scaled_img, (0, 0))
                    else:
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


# 로고 추가
try:
    title_logo_img = pygame.image.load("src/title_logo.png").convert_alpha()
    
except Exception as e:
    print(f"로고 이미지 로드 실패: {e}")
    title_logo_img = None

# bgm 추가
try:
    pygame.mixer.init()
    pygame.mixer.music.load("src/just_working.mp3") 
    pygame.mixer.music.set_volume(0.4)  # 볼륨 세팅 (0.0 ~ 1.0 사이, 너무 크면 0.2~0.4 추천)
    is_bgm_playing = False # 중복 재생 방지용 플래그
except Exception as e:
    print(f"⚠️ 오디오 파일 로드 실패: {e}")    

# --- UI 레이아웃 리소스 및 폰트 세팅 ---
label_font = pygame.font.SysFont("malgungothic", 24, bold=True)
input_font = pygame.font.SysFont("malgungothic", 20, bold=True)
btn_font = pygame.font.SysFont("malgungothic", 12, bold=True)
game_ui_font = pygame.font.SysFont("malgungothic", 26, bold=True)
popup_font = pygame.font.SysFont("malgungothic", 20, bold=True)
countdown_font = pygame.font.SysFont("cooper black", 72)

# 시작 및 종료화면 전용 폰트
start_title_font = pygame.font.SysFont("malgungothic", 64, bold=True)      
start_desc_title_font = pygame.font.SysFont("malgungothic", 28, bold=True) 
start_desc_body_font = pygame.font.SysFont("malgungothic", 20, bold=True)  
start_btn_font = pygame.font.SysFont("malgungothic", 26, bold=True)
game_over_title_font = pygame.font.SysFont("malgungothic", 72, bold=True) 

# 타자 입력
INPUT_BOX_WIDTH, INPUT_BOX_HEIGHT = 280, 44
input_box_x = RIGHT_CANVAS_X + (CANVAS_SIZE - INPUT_BOX_WIDTH) // 2 + 35
input_box_y = RIGHT_CANVAS_Y + CANVAS_SIZE + 15
input_box_rect = pygame.Rect(input_box_x, input_box_y, INPUT_BOX_WIDTH, INPUT_BOX_HEIGHT)

input_text, editing_text = "", ""

try:
    pygame.start_text_input()
except AttributeError:
    pass

# 버튼
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
btn_lang = pygame.Rect(start_fx_x + 196, fx_y + 28, 50, 24)

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

start_button_rect = pygame.Rect((SCREEN_WIDTH // 2) - 120, SCREEN_HEIGHT - 160, 240, 60)

# 그리기 로직
def is_inside_user_canvas(pos):
    x, y = pos
    return (LEFT_CANVAS_X <= x < LEFT_CANVAS_X + CANVAS_SIZE) and \
           (LEFT_CANVAS_Y <= y < LEFT_CANVAS_Y + CANVAS_SIZE)

def draw_on_canvas(start, end):
    color = CANVAS_BG if is_eraser else current_brush_color
    thick = ERASER_THICKNESS if is_eraser else brush_thickness
    edge_layer_color = CANVAS_BG if is_eraser else (0, 0, 0)
    
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    distance = max(abs(dx), abs(dy))
    if distance == 0:
        pygame.draw.circle(user_canvas, color, start, thick // 2)
        pygame.draw.circle(user_canvas_edges, edge_layer_color, start, thick // 2)
        return
    for i in range(int(distance) + 1):
        t = i / distance
        curr_x = int(start[0] + dx * t)
        curr_y = int(start[1] + dy * t)
        pygame.draw.circle(user_canvas, color, (curr_x, curr_y), thick // 2)
        pygame.draw.circle(user_canvas_edges, edge_layer_color, (curr_x, curr_y), thick // 2)

# --- 재시작 로직 공통 정의 함수 ---
def reset_game_session():
    global total_score, current_round, current_round_score, is_solved, GAME_STATE, state_start_time, current_game_pool, current_answer
    total_score = 0
    current_round = 1
    current_round_score = MAX_SCORE
    is_solved = False
    user_canvas.fill(CANVAS_BG)
    user_canvas_edges.fill(CANVAS_BG)
    ai_canvas.fill(CANVAS_BG)
    save_state(stroke_count=0)
    
    current_game_pool = catchmind_classes.copy()
    random.shuffle(current_game_pool)
    current_answer = current_game_pool.pop() 

    GAME_STATE = "COUNTDOWN"
    state_start_time = time.time()

# --- 2. 게임 메인 루프 ---
clock = pygame.time.Clock()
running = True

while running:
    current_time = time.time()  
    elapsed_in_state = current_time - state_start_time 
    
    # --- ⏱️ 상태 머신 제어 파트 ---
    if GAME_STATE in ["START_SCREEN", "GAME_OVER"]:
        pen_active = False
        drawing = False
        pygame.mouse.set_visible(True)

    elif GAME_STATE == "COUNTDOWN":
        pen_active = False
        current_round_score = MAX_SCORE  
        if elapsed_in_state >= COUNTDOWN_DURATION:
            GAME_STATE = "PLAYING"
            state_start_time = current_time  
            pen_active = True  
            
    elif GAME_STATE == "PLAYING":
        decayed_score = MAX_SCORE * (1.0 - (elapsed_in_state / LIMIT_TIME))
        min_guaranteed_score = MAX_SCORE * 0.1
        current_round_score = int(max(decayed_score, min_guaranteed_score))

        if elapsed_in_state >= LIMIT_TIME:
            GAME_STATE = "LOCKOUT"
            is_solved = False  
            state_start_time = current_time  
            pen_active = False  
            drawing = False
            
    elif GAME_STATE == "LOCKOUT":
        pen_active = False  
        if elapsed_in_state >= LOCKOUT_DURATION:
            if current_round < TOTAL_ROUNDS:
                current_round += 1
                current_answer = current_game_pool.pop()
                is_solved = False
                
                user_canvas.fill(CANVAS_BG)  
                user_canvas_edges.fill(CANVAS_BG)  
                ai_canvas.fill(CANVAS_BG)
                save_state(stroke_count=0) 
                
                GAME_STATE = "COUNTDOWN"
                state_start_time = time.time()  
            else:
                user_canvas.fill(CANVAS_BG)
                user_canvas_edges.fill(CANVAS_BG)
                ai_canvas.fill(CANVAS_BG)
                save_state(stroke_count=0)
                send_canvas_to_server()
                
                GAME_STATE = "GAME_OVER"
                state_start_time = time.time()

                pygame.mixer.music.fadeout(1500) 
                is_bgm_playing = False

    mouse_pos = pygame.mouse.get_pos()
    if pen_active and (is_inside_user_canvas(mouse_pos) or dragging_slider):
        pygame.mouse.set_visible(False)
    elif GAME_STATE not in ["START_SCREEN", "GAME_OVER"]:
        pygame.mouse.set_visible(True)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if GAME_STATE == "START_SCREEN":
                    if start_button_rect.collidepoint(mouse_pos):
                        GAME_STATE = "COUNTDOWN"
                        state_start_time = time.time()
                        if not is_bgm_playing:
                            pygame.mixer.music.play(loops=-1) 
                            is_bgm_playing = True
                    continue

                if GAME_STATE == "GAME_OVER":
                    if start_button_rect.collidepoint(mouse_pos):
                        reset_game_session()
                    continue

                if pen_active:
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
                            user_canvas_edges.fill(CANVAS_BG)
                            save_state(stroke_count=0) 
                            send_canvas_to_server()
                        elif btn_lang.collidepoint(mouse_pos):
                            current_lang_mode = 'KO' if current_lang_mode == 'EN' else 'EN'
                            
                        if slider_handle_rect.collidepoint(mouse_pos) or slider_rect.collidepoint(mouse_pos):
                            dragging_slider = True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and GAME_STATE not in ["START_SCREEN", "GAME_OVER"]:
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
            if GAME_STATE == "START_SCREEN":
                if event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    GAME_STATE = "COUNTDOWN"
                    state_start_time = time.time()
                    if not is_bgm_playing:
                        pygame.mixer.music.play(loops=-1)
                        is_bgm_playing = True
                continue

            if GAME_STATE == "GAME_OVER":
                if event.key == pygame.K_r:  
                    reset_game_session()
                continue

            if event.key == pygame.K_RETURN and GAME_STATE == "PLAYING":
                final_guess = input_text + editing_text
                final_guess = final_guess.strip()
                
                if final_guess:
                    allowed_answers = [ans.lower() for ans in catchmind_map.get(current_answer, [])]
                    
                    is_correct = final_guess.lower() in allowed_answers
                    
                    if is_correct:
                        opponent_guess_text = f"{final_guess} (O)"
                    else:
                        opponent_guess_text = f"{final_guess} (X)"
                        
                    opponent_guess_time = current_time
                    
                    if ws:
                        try: ws.send(json.dumps({"type": "guess", "text": final_guess}))
                        except: pass
                    
                    if is_correct and not is_solved:
                        GAME_STATE = "LOCKOUT"
                        is_solved = True
                        state_start_time = current_time  
                        pen_active = False  
                        drawing = False
                        total_score += current_round_score
                    input_text, editing_text = "", ""
            elif event.key == pygame.K_BACKSPACE and len(editing_text) == 0:
                input_text = input_text[:-1]

    # --- 3. 렌더링 영역 ---
    screen.fill(BACKGROUND_COLOR)
    
    # 1. 왼쪽 캔버스 상단 정답 텍스트 및 마크
    left_center_x = LEFT_CANVAS_X + (CANVAS_SIZE // 2)
    display_left_ans = get_display_word(current_answer, GAME_STATE == "PLAYING" or GAME_STATE == "LOCKOUT")
    ans_text_surf = game_ui_font.render(f"정답: {display_left_ans}", True, (245, 215, 80)) 
    ans_text_rect = ans_text_surf.get_rect(center=(left_center_x, LEFT_CANVAS_Y - 50))
    screen.blit(ans_text_surf, ans_text_rect)
    
    # 2. 오른쪽 캔버스 상단 정답 텍스트 및 마크
    right_center_x = RIGHT_CANVAS_X + (CANVAS_SIZE // 2)
    display_right_ans = current_answer if (is_solved or GAME_STATE == "LOCKOUT") else "???"
    ai_text_surf = game_ui_font.render(f"정답: {display_right_ans}", True, (245, 215, 80))
    ai_text_rect = ai_text_surf.get_rect(center=(right_center_x, RIGHT_CANVAS_Y - 50))
    screen.blit(ai_text_surf, ai_text_rect)

    # 3. 라운드가 종료되었거나 정답을 맞춘 상태일 때 양쪽 정답 텍스트 우측에 마크 배치
    if is_solved:
        result_mark = "O"
    elif GAME_STATE == "LOCKOUT":
        result_mark = "X"

        mark_font = pygame.font.SysFont("malgungothic", 24, bold=True)
        mark_surf = mark_font.render(result_mark, True, (235, 94, 85)) 
        
        left_mark_x = ans_text_rect.right + 12
        right_mark_x = ai_text_rect.right + 12
        
        screen.blit(mark_surf, mark_surf.get_rect(midleft=(left_mark_x, ans_text_rect.centery)))
        screen.blit(mark_surf, mark_surf.get_rect(midleft=(right_mark_x, ai_text_rect.centery)))

    BAR_MARGIN_X = 40  
    REDUCED_BAR_WIDTH = CANVAS_SIZE - (BAR_MARGIN_X * 2)  
    
    for canvas_start_x in [LEFT_CANVAS_X, RIGHT_CANVAS_X]:
        bar_x_pos = canvas_start_x + BAR_MARGIN_X  
        bar_y_pos = LEFT_CANVAS_Y - 90  
        pygame.draw.rect(screen, BAR_EMPTY_COLOR, (bar_x_pos, bar_y_pos, REDUCED_BAR_WIDTH, BAR_HEIGHT), border_radius=4)
        
        if GAME_STATE == "PLAYING":
            time_ratio = max(0.0, min(1.0, (LIMIT_TIME - elapsed_in_state) / LIMIT_TIME))
            current_bar_width = int(REDUCED_BAR_WIDTH * time_ratio)
            if time_ratio >= 0.5:
                dynamic_bar_color = (46, 204, 113)       
            elif time_ratio >= 0.2:
                dynamic_bar_color = (241, 196, 15)       
            else:
                dynamic_bar_color = (231, 76, 60)        
                
            if current_bar_width > 0:
                pygame.draw.rect(screen, dynamic_bar_color, (bar_x_pos, bar_y_pos, current_bar_width, BAR_HEIGHT), border_radius=4)
        elif GAME_STATE in ["COUNTDOWN", "START_SCREEN"]:
            pygame.draw.rect(screen, BAR_FILL_COLOR, (bar_x_pos, bar_y_pos, REDUCED_BAR_WIDTH, BAR_HEIGHT), border_radius=4)

    if opponent_guess_text and (current_time - opponent_guess_time <= 1.0): 
        
        clean_user_guess = opponent_guess_text.split(" (")[0] 
        
        left_base_y = LEFT_CANVAS_Y - 52  
        left_start_x = left_center_x + (game_ui_font.render(f"정답: {display_left_ans}", True, (0,0,0)).get_width() // 2) + 30
        left_max_width = CENTER_LINE_X - left_start_x - 15 
        
        title_text = "상대방 입력:"
        left_full_text = f"{title_text} {clean_user_guess}"
        left_w, _ = popup_font.size(left_full_text)
        
        if left_w <= left_max_width:
            left_surf = popup_font.render(left_full_text, True, (255, 94, 85)) 
            screen.blit(left_surf, (left_start_x, left_base_y))
        else:
            title_surf = popup_font.render(title_text, True, (255, 94, 85))
            screen.blit(title_surf, (left_start_x, left_base_y - 14)) 
            l2_text = ""
            for char in clean_user_guess:
                if popup_font.size(l2_text + char + "...")[0] <= left_max_width:
                    l2_text += char
                else:
                    l2_text += "..."
                    break
            l2_surf = popup_font.render(l2_text, True, (255, 94, 85))
            screen.blit(l2_surf, (left_start_x, left_base_y + 10))


        right_base_y = RIGHT_CANVAS_Y - 52  
        right_start_x = right_center_x + (game_ui_font.render(f"정답: {display_right_ans}", True, (0,0,0)).get_width() // 2) + 30
        right_max_width = SCREEN_WIDTH - right_start_x - 15 
        
        right_full_text = opponent_guess_text 
        right_w, _ = popup_font.size(right_full_text)
        
        if right_w <= right_max_width:
            right_surf = popup_font.render(right_full_text, True, (235, 94, 85)) 
            screen.blit(right_surf, (right_start_x, right_base_y))
        else:
            r2_text = ""
            for char in right_full_text:
                if popup_font.size(r2_text + char + "...")[0] <= right_max_width:
                    r2_text += char
                else:
                    r2_text += "..."
                    break
            r2_surf = popup_font.render(r2_text, True, (235, 94, 85))
            screen.blit(r2_surf, (right_start_x, right_base_y))

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

    if GAME_STATE == "COUNTDOWN":
        if elapsed_in_state < 1.0: count_str = "3"
        elif elapsed_in_state < 2.0: count_str = "2"
        elif elapsed_in_state < 3.0: count_str = "1"
        else: count_str = "Start!"  
            
        text_color = (255, 60, 60) 
        overlay_surf = countdown_font.render(count_str, True, text_color)
        screen.blit(overlay_surf, overlay_surf.get_rect(center=(LEFT_CANVAS_X + CANVAS_SIZE // 2, LEFT_CANVAS_Y + CANVAS_SIZE // 2)))
        screen.blit(overlay_surf, overlay_surf.get_rect(center=(RIGHT_CANVAS_X + CANVAS_SIZE // 2, RIGHT_CANVAS_Y + CANVAS_SIZE // 2)))

        round_font = pygame.font.SysFont("arial", 24, bold=True)
        round_text_surf = round_font.render(f"Round {current_round}", True, (245, 215, 80)) 
        
        screen.blit(round_text_surf, (LEFT_CANVAS_X + 10, LEFT_CANVAS_Y + 10))
        screen.blit(round_text_surf, (RIGHT_CANVAS_X + 10, RIGHT_CANVAS_Y + 10))

    for btn in color_buttons:
        pygame.draw.rect(screen, btn["color"], btn["rect"], border_radius=4)
        if current_brush_color == btn["color"] and not is_eraser and not is_fill_mode:
            pygame.draw.rect(screen, (255, 255, 255), btn["rect"], width=2, border_radius=4)
        else:
            pygame.draw.rect(screen, BORDER_COLOR, btn["rect"], width=1, border_radius=4)

    fx_buttons = [
        (btn_fill, "채우기", is_fill_mode), (btn_eraser, "지우개", is_eraser),
        (btn_undo, "<-", False), (btn_redo, "->", False), (btn_clear, "초기화", False),
        (btn_lang, "한글" if current_lang_mode == 'EN' else "영어",  False)
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

    if GAME_STATE == "GAME_OVER":
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((45, 52, 54, 225)) 
        screen.blit(overlay, (0, 0))
        
        go_title_surf = game_over_title_font.render("Game Over", True, (235, 94, 85)) 
        go_title_rect = go_title_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100))
        screen.blit(go_title_surf, go_title_rect)
        
        final_score_surf = start_title_font.render(f"Final Score: {total_score}", True, (254, 211, 48))
        final_score_rect = final_score_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10))
        screen.blit(final_score_surf, final_score_rect)
        
        if start_button_rect.collidepoint(mouse_pos):
            btn_color = (46, 204, 113)  
        else:
            btn_color = (39, 174, 96)   
            
        pygame.draw.rect(screen, btn_color, start_button_rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), start_button_rect, width=2, border_radius=10)
        
        btn_text = start_btn_font.render("Play Again", True, (255, 255, 255))
        screen.blit(btn_text, btn_text.get_rect(center=start_button_rect.center))

    if GAME_STATE == "START_SCREEN":
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((45, 52, 54, 225)) 
        screen.blit(overlay, (0, 0))
        
        if title_logo_img:
            title_rect = title_logo_img.get_rect(center=(SCREEN_WIDTH // 2, 95))
            screen.blit(title_logo_img, title_rect)
        else:
            title_surf = start_title_font.render("AI Catch-Mind", True, (254, 211, 48))
            title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 95))
            screen.blit(title_surf, title_rect)
        
        layout_box = pygame.Rect(60, 175, SCREEN_WIDTH - 120, SCREEN_HEIGHT - 390)
        pygame.draw.rect(screen, (116, 125, 140), layout_box, width=3, border_radius=10) 
        
        desc_title = start_desc_title_font.render("How to play", True, (245, 215, 80))
        screen.blit(desc_title, (layout_box.x + 40, layout_box.y + 30))
        
        bullet_points = [
            "   출제자가 정답을 보고 왼쪽 도화지에 그림을 그리면 AI 모델이 그림을 보고 어떤 그림인지",
            "   파악하고 출제자의 그림을 반영하여 사실적으로 생성합니다.",
            "   AI가 그린 그림만을 보고 입력창에 답을 적어 정답을 맞추어 보세요!",
            "   빠르게 맞출수록 높은 점수를 줍니다!"
        ]
        
        start_y = layout_box.y + 95
        for line in bullet_points:
            line_surf = start_desc_body_font.render(line, True, (245, 246, 250))
            screen.blit(line_surf, (layout_box.x + 20, start_y))
            start_y += 38 
            
        if start_button_rect.collidepoint(mouse_pos):
            btn_color = (46, 204, 113)  
        else:
            btn_color = (39, 174, 96)   
            
        pygame.draw.rect(screen, btn_color, start_button_rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), start_button_rect, width=2, border_radius=10)
        
        btn_text = start_btn_font.render("Game Start", True, (255, 255, 255))
        screen.blit(btn_text, btn_text.get_rect(center=start_button_rect.center))

    pygame.display.flip()
    clock.tick(120)

pygame.quit()
sys.exit()