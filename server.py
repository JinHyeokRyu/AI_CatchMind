# server.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import base64
from io import BytesIO
from PIL import Image
import asyncio

import torch
from models.stable_diffusion import init_pipe, StableDiffusion
from models.resnet import resnet_classifier, img_transformer

# 실행 명령어
# uvicorn server:app --reload

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"📡 클라이언트 연결 성공! (현재 연결 수: {len(self.active_connections)}명)")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"🔌 클라이언트 연결 종료. (현재 연결 수: {len(self.active_connections)}명)")

manager = ConnectionManager()


# 빈 캔버스인지 확인하는 함수
def is_pure_white_image(b64_str: str) -> bool:
    try:
        img_bytes = base64.b64decode(b64_str)
        img = Image.open(BytesIO(img_bytes)).convert("RGB")
        
        # 이미지의 최소/최대 픽셀 값을 가져옴
        extrema = img.getextrema()
        # 모든 채널(R, G, B)의 최솟값이 255라면 완전히 흰색인 상태입니다.
        if extrema[0][0] == 255 and extrema[1][0] == 255 and extrema[2][0] == 255:
            return True
    except Exception as e:
        print(f"이미지 검사 중 에러: {e}")
    return False


# 모델이 요구하는 입력 해상도 설정 
INPUT_SIZE = 512
device = "cuda" if torch.cuda.is_available() else "cpu"

print('Stable Diffusion 모델을 불러오는 중...')
pipe = init_pipe(device)

# define classification model
catchmind_classes = [
    # 동물
    'cat','dog','bear','elephant','giraffe','lion','tiger',
    'horse','cow','pig','rabbit','duck','penguin','frog','fish',

    # 음식
    'apple','banana','hamburger','hotdog',
    'pizza','bread','strawberry','pineapple',

    # 교통
    'airplane','bicycle','motorcycle',
    'pickup truck','helicopter','rocket','sailboat',

    # 사물
    'chair','table','door','window','hat','eyeglasses',
    'hammer','scissors','guitar','violin','umbrella','shoe',

    # 자연/기타
    'flower','tree','volcano','starfish','windmill',
    'castle','cabin','hot air balloon'
]

classification_model = resnet_classifier('./weights/resnet34.pth', device=device, num_classes=len(catchmind_classes))
transform = img_transformer()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # classification 결과값 초기화
        classification_result = None
        temp_result = None

        while True:
            # 클라이언트로부터 텍스트 데이터(JSON)를 받습니다.
            data = await websocket.receive_text()

            # 쌓여있는 buffer 비우고 가장 최신의 데이터만 사용
            while True:
                try:
                    newer_data = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=0.001
                    )
                    data = newer_data

                except asyncio.TimeoutError:
                    break

            event_data = json.loads(data)
            
            event_type = event_data.get("type")
            
            # 유저가 획을 마쳐서 캔버스 전체 이미지가 날아왔을 때
            if event_type == "stroke_canvas":
                # Base64 문자열로 인코딩된 이미지 데이터를 복원합니다.
                img_edge = event_data.get("image_edge")
                
                if is_pure_white_image(img_edge):          
                    await websocket.send_text(json.dumps({
                        "type": "ai_response",
                        "image": img_edge
                    }))
                    continue
                
                img_color = event_data.get("image_color")

                img_edge_bytes = base64.b64decode(img_edge)
                img_color_bytes = base64.b64decode(img_color)
                
                # PIL 라이브러리로 원본 이미지(512x512) 로드
                pil_edge = Image.open(BytesIO(img_edge_bytes))
                pil_color = Image.open(BytesIO(img_color_bytes))
 
                input_edge = transform(pil_edge).unsqueeze(0).to(device)

                with torch.no_grad():
                    outputs = classification_model(input_edge)

                _, pred = torch.max(outputs, 1)
                classification_result = catchmind_classes[pred.item()]
                print(classification_result)

                if (temp_result is None) or classification_result != temp_result:

                    prompt = classification_result + ", photorealistic, best quality"
                    print(prompt)
                    negative_prompt = "low quality"
                    temp_result = classification_result

                    prompt_embeds, negative_prompt_embeds = pipe.encode_prompt(
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        device=device,
                        num_images_per_prompt=1,
                        do_classifier_free_guidance=True,
                    )
                

                result = StableDiffusion(pipe, pil_color, INPUT_SIZE, prompt_embeds, negative_prompt_embeds)


                # 클라이언트에게 돌려주기 위해 다시 Base64 문자열로 패키징
                buffered = BytesIO()
                result.save(buffered, format="PNG")
                response_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                # 클라이언트로 전송 (Echo)
                response_payload = {
                    "type": "ai_response",
                    "image": response_b64
                }
                await websocket.send_text(json.dumps(response_payload))
                
            elif event_type == "guess":
                print(f"💬 [채팅/정답 수신]: {event_data.get('text')}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"❌ 서버 에러 발생: {e}")
        manager.disconnect(websocket)