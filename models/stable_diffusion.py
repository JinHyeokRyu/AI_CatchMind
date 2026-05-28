import torch
import numpy as np
import cv2
from PIL import Image
# LCM 스케줄러 로드
from diffusers import StableDiffusionControlNetImg2ImgPipeline, ControlNetModel, LCMScheduler, AutoencoderTiny

# initalize
def init_pipe(device):

    # 가벼운 ControlNet Scribble 로드
    controlnet = ControlNetModel.from_pretrained(
        # "lllyasviel/control_v11p_sd15_scribble",
        "lllyasviel/control_v11p_sd15_softedge", 
        torch_dtype=torch.float16
    )

    # SD 1.5 기본 파이프라인 로드
    pipe = StableDiffusionControlNetImg2ImgPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        controlnet=controlnet,
        torch_dtype=torch.float16
    )

    # Tiny VAE 적용
    pipe.vae = AutoencoderTiny.from_pretrained(
        "madebyollin/taesd",
        torch_dtype=torch.float16
    ).to(device)

    # 고속 생성을 위한 LCM LoRA 다운로드 및 병합
    pipe.load_lora_weights("latent-consistency/lcm-lora-sdv1-5")
    pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)

    # 메모리 최적화 기법
    pipe.enable_xformers_memory_efficient_attention()
    # pipe.enable_attention_slicing()  # 메모리 부하를 줄이기 위해 어텐션을 쪼개서 계산
    pipe.enable_vae_slicing()

    pipe.safety_checker = None
    pipe.requires_safety_checker = False
    pipe.to(device)

    return pipe


# -----------------------------
# 2. RTX 3050용 전처리 (경량화 및 흑백 반전)
# -----------------------------
def preprocess(image, size):
    # 3050 Laptop을 위해 해상도를 320x320으로 타협 (연산량 급감)
    target_size = (size, size)
    image = cv2.resize(image, target_size)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # 그림판의 흰색 배경(255)에 검은 선(0)을 감지하기 위한 그레이스케일
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 200보다 밝은 부분(배경)은 검게, 어두운 부분(사용자 선)은 하얗게 이진화 반전
    _, alpha = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    
    # RTX 3050에서 320 해상도일 때 선이 너무 얇으면 인식을 못 하므로 약간 두껍게 만듭니다.
    kernel = np.ones((3,3), np.uint8)
    edges = cv2.dilate(alpha, kernel, iterations=1)
    
    # ControlNet Scribble 표준 입력 형태인 (검은 배경 + 흰색 선) 완성
    edges_rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)

    return image_rgb, edges_rgb

# -----------------------------
# 3. 이미지 생성 함수 (LCM 4 Step 고속 생성)
# -----------------------------
def StableDiffusion(pipe, image, target_size, prompt_embeds, negative_prompt_embeds):

    cv_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    overlay, edges = preprocess(cv_img, target_size)

    overlay_pil = Image.fromarray(overlay)
    edges_pil = Image.fromarray(edges)

    print('추론 시작!')
    # 추론 수행
    with torch.inference_mode():
        result = pipe(
            prompt_embeds=prompt_embeds,
            negative_prompt_embeds=negative_prompt_embeds,
            image=overlay_pil,       # 채색 가이드용 원본 스케치
            control_image=edges_pil, # 형태 고정용 흑백 반전 엣지
            guidance_scale=1.5,      # LCM LoRA 사용 시 1.0 ~ 2.0 사이가 최적입니다.
            num_inference_steps=4,   # [핵심] 단 4번만 연산하여 RTX 3050에서도 속도 확보
            strength=0.9,             # 0.7~0.8 정도로 설정해야 스케치 형태를 유지하면서 AI가 이쁘게 채색합니다.
            controlnet_conditioning_scale=0.3   # controlnet 반영 정도 (낮을 수록 반영 x)
        ).images[0]

    return result


if __name__ == "__main__":
    # 테스트 실행
    image = cv2.imread('AnitaDataset/dogmatism/sketch/188_a/0082.png')  
    if image is None:
        print("이미지 파일을 찾을 수 없습니다.")
        exit()

    StableDiffusion(image)