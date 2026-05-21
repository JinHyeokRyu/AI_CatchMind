import torch
import numpy as np
import cv2

from PIL import Image

from diffusers import StableDiffusionControlNetImg2ImgPipeline, ControlNetModel


# -----------------------------
# ControlNet Load
# -----------------------------

controlnet = ControlNetModel.from_pretrained(
    "lllyasviel/control_v11p_sd15_scribble",
    torch_dtype=torch.float16
)

# -----------------------------
# Pipeline Load
# -----------------------------

pipe = StableDiffusionControlNetImg2ImgPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    controlnet=controlnet,
    torch_dtype=torch.float16
).to("cuda")

# Memory optimization
pipe.enable_xformers_memory_efficient_attention()

pipe.safety_checker = None
pipe.requires_safety_checker = False

# -----------------------------
# StreamDiffusion
# -----------------------------

from streamdiffusion import StreamDiffusion

stream = StreamDiffusion(
    pipe=pipe,
    t_index_list=[0, 16, 32]
)

# -----------------------------
# Prompt Prepare
# -----------------------------

stream.prepare(
    prompt="""
    cute cartoon balloon,
    flat colors,
    clean lineart,
    cel shading
    """,

    negative_prompt="""
    realistic,
    blurry,
    low quality,
    deformed
    """
)

# -----------------------------
# Preprocess Function
# -----------------------------

def preprocess(image):

    image = cv2.resize(image, (512, 512))
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    filtered = cv2.bilateralFilter(image, 9, 75, 75)

    gray = cv2.cvtColor(filtered, cv2.COLOR_RGB2GRAY)

    edges = cv2.Canny(gray, 100, 200)

    kernel = np.ones((3,3), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)

    # edge overlay
    overlay = filtered.copy()
    overlay[edges > 0] = [0,0,0]

    # convert edge -> 3 channel
    edges_rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)

    return overlay, edges_rgb

# -----------------------------
# Generate Function
# -----------------------------

def generate(image):

    overlay, edges = preprocess(image)

    overlay_pil = Image.fromarray(overlay)
    edges_pil = Image.fromarray(edges)

    # result = stream(
    #     # image=overlay_pil,
    #     # control_image=edges_pil,

    #     image=image_pil,
    #     control_image=image_pil,

    #     guidance_scale=2,
    #     num_inference_steps=4,
    #     strength=0.7
    # )

    prompt = "dancing, flat colors, clean lineart, cel shading, high quality, white background"
    negative_prompt = "realistic, blurry, low quality, deformed, photographic, shading, shadows"

    result = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,

        image=overlay_pil,
        control_image=edges_pil,

        guidance_scale=3.5,
        num_inference_steps=20,
        strength=0.7
    ).images[0]

    return result


if __name__ == "__main__":
    image = cv2.imread('AnitaDataset/dogmatism/sketch/188_a/0082.png')
    result = generate(image)
    result.save("result1.png")