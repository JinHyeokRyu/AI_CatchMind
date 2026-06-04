# AI_CatchMind

**Real-Time AI-Powered CatchMind with Diffusion**

22101169 류진혁 (JinHyeokRyu)<br>
22102472 조강현 (LewisCho7)

## 1. Game Introduction

기존의 캐치마인드(CatchMind) 게임에 Computer Vision과 Generative AI를 결합한 실시간 인터랙티브 드로잉 게임!!

부족한 그림 실력으로 게임이 어려우셨나요?<br>
단순한 캐치마인드에 질리지는 않으셨나요?

더 즐겁고 행복한 캐치마인드를 위해, AI가 여러분들의 스케치를 재해석합니다!!

**목표**: 사용자가 직접 그림을 그리는 과정 자체를 AI가 해석하고, 이를 기반으로 새로운 이미지를 생성함으로써 게임의 만족감과 재미 모두 향상시키자!

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

게임 구현 설명

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



