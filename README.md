# AI_CatchMind

**Real-Time AI-Powered CatchMind with Diffusion**

22101169 류진혁 (JinHyeokRyu)<br>
22102472 조강현 (LewisCho7)

## 1. Project Introduction

기존의 캐치마인드(CatchMind) 게임에 Computer Vision과 Generative AI를 결합한 실시간 인터랙티브 드로잉 게임!!

부족한 그림 실력으로 게임이 어려우셨나요?<br>
그림이 지나치게 단순하거나 난해할 때 게임이 재미없지는 않으셨나요?

더 즐겁고 행복한 캐치마인드를 위해, AI가 여러분들의 스케치를 보완해드립니다!!

**목표**: 사용자가 직접 그림을 그리는 과정 자체를 AI가 해석하고, 이를 기반으로 새로운 이미지를 생성함으로써 게임의 만족감과 재미 모두 향상시키자!

### 게임 방법

* **Player 1 (출제자)**: 특정 주제를 보고 그림을 그립니다.
* **AI Model**: 출제자가 그리는 그림을 실시간으로 분석하여 해당 스케치를 기반으로 이미지를 생성합니다.
* **Player 2 (정답자)**: AI가 생성한 결과 이미지를 보고 정답을 맞춥니다.

즉, 정답자는 출제자의 원본 그림이 아닌, AI가 해석하고 생성한 이미지를 통해 답을 맞추게 됩니다.
또한, 빠르게 정답을 맞출수록 더 높은 점수를 획득할 수 있습니다!


## 2. Core Computer Vision Techniques

사용자의 스케치 feature 를 실시간으로 해석하여 고화질 이미지로 변환하는 생성형 AI framework

단순한 이미지 생성을 넘어, 인간의 드로잉 의도와 AI의 생성적 해석 사이의 간극을 좁히는 것이 목표!


### 1. Feature Recognition
사람이 사물을 그릴 때 강조하는 시각적 특징(Edge, Shape)을 Computer Vision 기법으로 실시간 포착합니다.

사용자가 그린 스케치는 노이즈가 많고 선의 정보가 불명확할 수 있습니다.
이를 보완하기 위해 OpenCV 기반 전처리를 수행합니다.

주요 과정은 다음과 같습니다.

* Bilateral Filtering을 통한 노이즈 제거
* Canny Edge Detection을 통한 윤곽선 추출
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


## 3. System Pipeline

전체 시스템은 다음과 같은 흐름으로 동작합니다.

**User Sketch → Preprocessing → Diffusion Inference → Image Generation → GUI Display**

세부적으로는, 사용자가 Pygame Canvas에 그림을 그리면 OpenCV 전처리를 수행하여 노이즈 제거 및 특징을 추출합니다 그 후, StreamDiffusion + ControlNet 기반으로 이미지를 생성하고 결과를 화면에 실시간으로 출력합니다.
