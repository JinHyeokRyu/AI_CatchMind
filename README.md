# AI_CatchMind

**Real-Time AI-Powered CatchMind with Diffusion**

22101169 류진혁 (JinHyeokRyu)<br>
22102472 조강현 (LewisCho7)

## 1. Game Introduction

기존의 캐치마인드(CatchMind) 게임에 Computer Vision과 Generative AI를 결합한 실시간 인터랙티브 드로잉 게임!!

부족한 그림 실력으로 게임이 어려우셨나요?<br>
단순한 캐치마인드에 질리지는 않으셨나요?

더 즐겁고 행복한 캐치마인드를 위해, AI가 여러분들의 스케치를 재해석합니다!!

**목표**: 사용자가 직접 그림을 그리는 과정 자체를 AI가 해석하고, 이를 기반으로 실시간으로 새로운 이미지를 생성함으로써 게임의 만족감과 재미 모두 향상시키자!

### 게임 방법

* **Player 1 (출제자)**: 특정 주제를 보고 그림을 그립니다.
* **AI Model**: 출제자가 그리는 그림을 실시간으로 분석하여 해당 스케치를 기반으로 이미지를 생성합니다.
* **Player 2 (정답자)**: AI가 생성한 결과 이미지를 보고 정답을 맞춥니다.

즉, 정답자는 출제자의 원본 그림이 아닌, AI가 해석하고 생성한 이미지를 통해 답을 맞추게 됩니다.
또한, 빠르게 정답을 맞출수록 더 높은 점수를 획득할 수 있습니다.


### 실행 환경 설정

본 repository를 clone 후, 터미널에 아래의 명령어를 입력합니다. (Python version=3.10.20)

```bash
pip install -r requirements.txt
```

### 게임 실행 방법

**서버 시작**: 가상환경 실행 후, 터미널에 아래의 명령어를 입력합니다.

```bash
uvicorn server:app --reload
```

**게임 실행**: 서버가 활성화되면, game_client.py를 실행합니다.

## 2. Demo

(시연 영상)

설명

## 3. Game Pipeline

게임의 전체 시스템은 다음과 같은 흐름으로 동작합니다.

**User Sketch → (서버 전송) → ResNet Classification → Preprocessing → Diffusion Inference(Image Generation) → (클라이언트 전송) → GUI Display**

구체적으로는, 사용자가 Pygame Canvas에 그림을 그리면 ResNet 기반 classification 모델이 어떤 그림인지 인식합니다. 인식 결과를 바탕으로, 생성형 모델을 위한 prompting과 OpenCV 전처리를 수행하여 노이즈 제거 및 특징을 추출합니다. 최종적으로 Stable Diffusion을 이용하여 이미지를 생성하고 결과를 화면에 실시간으로 출력합니다.

## 4. PyGame Implementation

## Game 구현

### Game GUI

Pygame을 이용한 직관적이고 완성도 높은 게임 인터페이스를 구현하였습니다.

- 도화지 레이아웃
    - 출제자가 그림을 그리는 왼쪽 ⁠User Canvas⁠와, 실시간 변환된 AI 그림을 보고 정답을 유추하는 오른쪽 ⁠AI Canvas⁠를 분리.
    - 스케치북 모양으로 도화지 디자인
- Input interface 구성 및 점수 구현
    - 정답을 입력할 수 있는 입력창
    - 상대방(출제자)의 왼쪽 화면 상단에 입력했던 오답이 1초간 실시간으로 노출되어, 출제자가 상대방의 유추 과정을 확인하며 게임의 재미를 느낄 수 있도록 유도
    - 정답을 맞히기까지 걸린 시간을 계산하여, 빠르게 맞출수록 더 높은 점수를 부여하는 시간 비례 점수 시스템 적용
    - 5 Round 이후 게임 종료 시 누적 점수 표시
- 다양한 Drawing 툴킷 지원
    - 9가지 색상의 컬러 팔레트, 슬라이더 기반의 브러쉬 두께 조절 기능 탑재
    - 잘못 그린 선을 되돌리는 Undo(<-) / Redo(->) 기능, 면을 통째로 채우는 Flood-Fill 기반 채우기 기능, 지우개 및 전체 도화지 초기화(Clear) 기능 제공
- State Machine 제어
    - State machine 도입으로 복잡한 분기문 없이 게임 진행상태 제어 및 time 관리

### Client - Server

FastAPI 및 WebSocket을 이용한 양방향 비동기 서버 통신을 구현하였습니다.

- Pygame 메인 스레드 freezing 방지 및 프레임 유지
    - 고용량 Diffusion 모델을 client에 직접 로드하고 추론 연산을 수행시 이미지 생성 시간 동안 Pygame의 메인 루프가 완전히 멈춰버려 화면이 얼어붙거나 프로그램이 강제 종료되는 멀티스레딩 충돌 문제 방지
    - 분류 및 생성 AI 연산 로직과 이미지 전처리 과정을 FastAPI 백엔드 서버로 분리
    - 그래픽 연산을 수행하는 중에도 클라이언트에서는 마우스 입력 및 Game UI 랜더링 유지
- 웹소켓 기반 실시간성 확보
    - 연결되면 영구적인 파이프라인을 유지하는 웹소켓 프로토콜 채택
    - Latency를 최소화하고, 출제자의 드로잉 입력에 따른 이미지 데이터를 서버로 즉각적이고 연속성 있게 스트리밍 전송
- 레이어 분리 및 서버 타겟팅 메커니즘
    - 분류를 위해 외곽선들만 담는 edge layer와, 생성을 위해 색상(color) 정보와 채우기가 적용된 color layer를 분리
    - 각각의 layer를 client에서 server로 하나의 패킷으로 묶어서 동시 전송
    - 서버에서 model의 역할에 따라 layer를 각각 매칭
- 이미지 인코딩 및 데이터 경량화
    - 클라이언트에서 픽셀 데이터를 binary 형태로 추출하여 Base64 문자열로 전송
    - 서버에서 image data로 디코딩하여 모델에 전달
- AI 추론 오버헤드 최적화
    - .

## 5. Model Implementation
### 5.1. Sketch Classification
사용자의 그림을 인식하기 위해, sketch classification 모델을 학습하였습니다.

**Dataset**: [SketchDatabase](https://github.com/CDOTAD/SketchyDatabase)
* 총 125개의 클래스 중, 캐치마인드에 적합한 50개의 클래스 선별 (클래스당 200장)
* RandomAffine(degrees=10, translate=(0.05, 0.05))
* RandomHorizontalFlip(0.5)
* train(8) : val(1) : test(1) split 

**Classification Model**
* ResNet34
* ImageNet pretrained weight

**Implementation Details**
* batch size = 32
* Adam optimizer (learning_rate=3e-4, weight_decay=1e-4)
* ReduceLROnPlateau

### 5.2. Prompt Generation
Sketch classification 모델의 결과를 바탕으로, Stable Diffusion에 사용할 prompt를 생성합니다.

**Prompt Format**<br>

prompt = "{class}, photorealistic, best quality"<br>
negative_prompt = "low quality"



### 5.3. Feature Recognition
사람이 사물을 그릴 때 강조하는 시각적 특징(Edge, Shape)을 Computer Vision 기법으로 실시간 포착합니다.

사용자가 그린 스케치는 노이즈가 많고 선의 정보가 불명확할 수 있습니다.
이를 보완하기 위해 OpenCV 기반 전처리를 수행합니다.

주요 과정은 다음과 같습니다.

* Edge Thickening을 통한 선 강조
* RGB 이미지와 Edge 정보를 함께 활용

이를 통해 Diffusion Model이 보다 안정적으로 사용자의 의도를 이해할 수 있도록 합니다

### 2. Structural Constraint

실시간 생성을 위해 Stable Diffusion 1.5 기반의 StreamDiffusion을 사용합니다.

구성 요소는 다음과 같습니다.

* Stable Diffusion 1.5
* ControlNet (Lineart / SoftEdge)
* StreamDiffusion

ControlNet은 사용자의 선 정보를 유지하도록 도와주며,
StreamDiffusion은 반복적인 inference latency를 줄여
실시간 생성이 가능하도록 합니다.

이를 통해 AI가 사용자의 원래 의도를 훼손하지 않으면서도
보다 직관적이고 풍부한 결과를 생성할 수 있도록 합니다.



