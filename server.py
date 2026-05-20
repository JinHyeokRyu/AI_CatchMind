# server.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import base64
from io import BytesIO
from PIL import Image

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

# AI 모델이 요구하는 가상의 입력 해상도 설정 
AI_INPUT_SIZE = 256

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # 클라이언트로부터 텍스트 데이터(JSON)를 받습니다.
            data = await websocket.receive_text()
            event_data = json.loads(data)
            
            event_type = event_data.get("type")
            
            # 유저가 획을 마쳐서 캔버스 전체 이미지가 날아왔을 때
            if event_type == "stroke_canvas":
                # Base64 문자열로 인코딩된 이미지 데이터를 복원합니다.
                img_b64 = event_data.get("image")
                img_bytes = base64.b64decode(img_b64)
                
                # 1. PIL 라이브러리로 원본 이미지(512x512) 로드
                pil_image = Image.open(BytesIO(img_bytes))
                
                # 2. [핵심] AI 모델에 들어갈 크기(예: 64x64)로 리사이즈!
                # (추후 이 변환된 'resized_image'를 팀원의 AI 모델 입력값으로 넣게 됩니다)
                resized_image = pil_image.resize((AI_INPUT_SIZE, AI_INPUT_SIZE))
                print(f"📐 이미지 리사이즈 완료: {pil_image.size} -> {resized_image.size}")
                
                # 3. 클라이언트에게 돌려주기 위해 다시 Base64 문자열로 패키징
                buffered = BytesIO()
                resized_image.save(buffered, format="PNG")
                response_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                # 4. 클라이언트로 전송 (Echo)
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