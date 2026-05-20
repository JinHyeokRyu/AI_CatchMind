# client.py
import pygame
import sys
import json
import base64
import threading
from io import BytesIO
from websocket import create_connection

# --- 1. 환경 및 레이아웃 설정 ---
pygame.init()

CANVAS_SIZE = 512
MARGIN_X = 60
MARGIN_Y = 80

SCREEN_WIDTH = (CANVAS_SIZE * 2) + (MARGIN_X * 3)
SCREEN_HEIGHT = CANVAS_SIZE + (MARGIN_Y * 2)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("AI Catch-Mind! 🎨 (Network Test Mode)")

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

LEFT_CANVAS_X = MARGIN_X
LEFT_CANVAS_Y = MARGIN_Y
RIGHT_CANVAS_X = (MARGIN_X * 2) + CANVAS_SIZE
RIGHT_CANVAS_Y = MARGIN_Y

user_canvas = pygame.Surface((CANVAS_SIZE, CANVAS_SIZE))
user_canvas.fill(CANVAS_BG)

# 🌟 [오른쪽 캔버스 생성] 서버에서 가공해 올 결과 이미지가 얹어질 도화지입니다.
ai_canvas = pygame.Surface((CANVAS_SIZE, CANVAS_SIZE))
ai_canvas.fill(CANVAS_BG)

# --- 🔄 Undo / Redo ---
undo_stack = [user_canvas.copy()]
redo_stack = []

def save_state():
    global undo_stack, redo_stack
    redo_stack.clear()
    undo_stack.append(user_canvas.copy())
    if len(undo_stack) > 5:
        undo_stack.pop(0)

def handle_undo():
    global undo_stack, redo_stack
    if len(undo_stack) > 1:
        state = undo_stack.pop()
        redo_stack.append(state)
        user_canvas.blit(undo_stack[-1], (0, 0))
        send_canvas_to_server() # 변경 사항 서버 전송

def handle_redo():
    global undo_stack, redo_stack
    if len(redo_stack) > 0:
        state = redo_stack.pop()
        undo_stack.append(state)
        user_canvas.blit(state, (0, 0))
        send_canvas_to_server() # 변경 사항 서버 전송

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

# --- 🌐 웹소켓 클라이언트 연동 설정 ---
SERVER_URL = "ws://localhost:8000/ws"
ws = None

def send_canvas_to_server():
    """현재 왼쪽 도화지 전체를 바이트로 변환해 서버로 쏩니다."""
    if ws:

        # --- ✨ 수정된 코드 ---
        img_bytes = pygame.image.tobytes(user_canvas, "RGB") # to_string 대신 tobytes 사용
        pil_img = Image.frombytes("RGB", (CANVAS_SIZE, CANVAS_SIZE), img_bytes)
        
        buffered = BytesIO()
        pil_img.save(buffered, format="PNG")
        
        # 네트워크 송신용 Base64 인코딩
        img_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        payload = {
            "type": "stroke_canvas",
            "image": img_b64
        }
        try:
            ws.send(json.dumps(payload))
        except Exception as e:
            print(f"⚠️ 서버 데이터 전송 실패: {e}")

def bg_receive_loop():
    """서버가 돌려주는 데이터를 게임 끊김 없이 받아주는 백그라운드 스레드 함수"""
    global ai_canvas
    while True:
        if ws:
            try:
                response = ws.recv()
                res_data = json.loads(response)
                
                if res_data.get("type") == "ai_response":
                    res_b64 = res_data.get("image")
                    res_bytes = base64.b64decode(res_b64)
                    
                    # 수신된 바이트 데이터를 다시 Pygame 이미지 서페이스로 빌드
                    img_io = BytesIO(res_bytes)
                    incoming_img = pygame.image.load(img_io, "PNG")
                    
                    # 🌟 [해상도 복구] 서버가 리사이즈해서 보낸 작은 이미지를 우측 캔버스 크기(512x512)로 다시 복구 확대
                    scaled_img = pygame.transform.smoothscale(incoming_img, (CANVAS_SIZE, CANVAS_SIZE))
                    
                    # 우측 전용 도화지에 복사
                    ai_canvas.blit(scaled_img, (0, 0))
            except Exception as e:
                print(f"🔌 서버 수신 스레드 종료 혹은 에러: {e}")
                break

try:
    from PIL import Image # 이미지 수신 파싱용
    ws = create_connection(SERVER_URL)
    print("🚀 FastAPI 서버와 웹소켓 연결 완료!")
    # 서버 대답을 실시간 감시할 백그라운드 멀티스레드 가동
    rx_thread = threading.Thread(target=bg_receive_loop, daemon=True)
    rx_thread.start()
except Exception as e:
    print(f"⚠️ 오프라인 모드로 실행됩니다. 서버 에러: {e}")

# --- UI 레이아웃 리소스 설정 ---
label_font = pygame.font.SysFont("malgungothic", 24, bold=True)
input_font = pygame.font.SysFont("malgungothic", 20, bold=True)
btn_font = pygame.font.SysFont("malgungothic", 12, bold=True)

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
    mouse_pos = pygame.mouse.get_pos()
    if is_inside_user_canvas(mouse_pos) or dragging_slider:
        pygame.mouse.set_visible(False)
    else:
        pygame.mouse.set_visible(True)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if is_inside_user_canvas(mouse_pos):
                    canvas_pos = (mouse_pos[0] - LEFT_CANVAS_X, mouse_pos[1] - LEFT_CANVAS_Y)
                    if is_fill_mode:
                        flood_fill(user_canvas, canvas_pos, current_brush_color)
                        save_state()
                        send_canvas_to_server() # 채우기 후 서버 전송
                    else:
                        drawing = True
                        last_pos = canvas_pos
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
                        save_state()
                        send_canvas_to_server() # 초기화 후 서버 전송
                        
                    if slider_handle_rect.collidepoint(mouse_pos) or slider_rect.collidepoint(mouse_pos):
                        dragging_slider = True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if drawing:
                    drawing = False
                    last_pos = None
                    save_state()
                    # 🌟 한 획을 마쳤으므로 완성된 캔버스 상황을 서버로 스트리밍 전송합니다.
                    send_canvas_to_server()
                dragging_slider = False

        elif event.type == pygame.MOUSEMOTION:
            if drawing and last_pos:
                if is_inside_user_canvas(mouse_pos):
                    curr_canvas_pos = (mouse_pos[0] - LEFT_CANVAS_X, mouse_pos[1] - LEFT_CANVAS_Y)
                    draw_on_canvas(last_pos, curr_canvas_pos)
                    last_pos = curr_canvas_pos
                else:
                    last_pos = None
            
            if dragging_slider:
                val_x = max(SLIDER_X, min(mouse_pos[0], SLIDER_X + SLIDER_WIDTH))
                ratio = (val_x - SLIDER_X) / SLIDER_WIDTH
                brush_thickness = int(MIN_THICK + ratio * (MAX_THICK - MIN_THICK))

        elif event.type == pygame.TEXTINPUT:
            input_text += event.text
            editing_text = ""
        elif event.type == pygame.TEXTEDITING:
            editing_text = event.text
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                final_guess = input_text + editing_text
                if final_guess.strip():
                    if ws:
                        ws.send(json.dumps({"type": "guess", "text": final_guess.strip()}))
                    input_text, editing_text = "", ""
            elif event.key == pygame.K_BACKSPACE and len(editing_text) == 0:
                input_text = input_text[:-1]

    # --- 3. 렌더링 영역 ---
    screen.fill(BACKGROUND_COLOR)
    
    BORDER_THICK = 8
    pygame.draw.rect(screen, BORDER_COLOR, (LEFT_CANVAS_X - BORDER_THICK, LEFT_CANVAS_Y - BORDER_THICK, CANVAS_SIZE + (BORDER_THICK*2), CANVAS_SIZE + (BORDER_THICK*2)), border_radius=4)
    pygame.draw.rect(screen, BORDER_COLOR, (RIGHT_CANVAS_X - BORDER_THICK, RIGHT_CANVAS_Y - BORDER_THICK, CANVAS_SIZE + (BORDER_THICK*2), CANVAS_SIZE + (BORDER_THICK*2)), border_radius=4)

    # 내 그리기 도화지 블릿
    screen.blit(user_canvas, (LEFT_CANVAS_X, LEFT_CANVAS_Y))
    
    # 🌟 [오른쪽 캔버스 렌더링] 원래의 하얀 공백 대신, 서버가 리사이즈해서 돌려보낸 동적 서페이스를 화면에 그립니다.
    screen.blit(ai_canvas, (RIGHT_CANVAS_X, RIGHT_CANVAS_Y))

    # UI 장식 (스프링 고리 및 점선)
    for cx in [LEFT_CANVAS_X, RIGHT_CANVAS_X]:
        for idx in range(12):
            ring_x = cx + 25 + (idx * 42)
            ring_y = LEFT_CANVAS_Y - 8
            pygame.draw.rect(screen, SPRING_COLOR, (ring_x, ring_y - 12, 10, 16), border_radius=3)
            pygame.draw.rect(screen, (50, 50, 50), (ring_x, ring_y - 12, 10, 16), width=1, border_radius=3)

    CENTER_LINE_X = (LEFT_CANVAS_X + CANVAS_SIZE) + (MARGIN_X // 2)
    for dot_y in range(0, SCREEN_HEIGHT, 20):
        pygame.draw.circle(screen, BORDER_COLOR, (CENTER_LINE_X, dot_y), 3)

    # 팔레트 버튼군
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

    # 커서 가이드 선 렌더링
    if is_inside_user_canvas(mouse_pos):
        if is_fill_mode:
            pygame.draw.line(screen, (40, 40, 40), (mouse_pos[0]-8, mouse_pos[1]), (mouse_pos[0]+8, mouse_pos[1]), 2)
            pygame.draw.line(screen, (40, 40, 40), (mouse_pos[0], mouse_pos[1]-8), (mouse_pos[0], mouse_pos[1]+8), 2)
        elif is_eraser:
            pygame.draw.circle(screen, (40, 40, 40), mouse_pos, ERASER_THICKNESS // 2, width=1)
        else:
            pygame.draw.circle(screen, current_brush_color, mouse_pos, brush_thickness // 2)
            pygame.draw.circle(screen, (255, 255, 255), mouse_pos, brush_thickness // 2, width=1)

    pygame.display.flip()
    clock.tick(120)

pygame.quit()
sys.exit()