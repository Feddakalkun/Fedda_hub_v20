#!/bin/bash
# Downloads required models to /workspace network volume
# Runs in background during startup so the UI is available immediately
# Uses curl with resume support (-C -)

MODELS="/workspace/models/comfyui"

download_if_missing() {
    local url="$1"
    local dest="$2"
    local name="$3"

    if [ -f "$dest" ]; then
        echo "[MODEL] Already exists: $name"
        return 0
    fi

    echo "[MODEL] Downloading $name..."
    mkdir -p "$(dirname "$dest")"

    if curl -L -C - -o "$dest" --connect-timeout 30 --retry 3 --retry-delay 5 -# "$url"; then
        echo "[MODEL] Done: $name"
    else
        echo "[MODEL] FAILED: $name (will retry on next startup)"
        rm -f "$dest"  # Remove partial file
    fi
}

echo "========================================="
echo "  Model Download Manager"
echo "========================================="

# ===== Z-IMAGE MODELS (core image generation) =====

download_if_missing \
    "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/diffusion_models/z_image_turbo_bf16.safetensors" \
    "$MODELS/diffusion_models/z_image_turbo_bf16.safetensors" \
    "Z-Image Turbo UNet (11.5 GB)"

download_if_missing \
    "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors" \
    "$MODELS/clip/qwen_3_4b.safetensors" \
    "Qwen 3 4B CLIP (7.5 GB)"

download_if_missing \
    "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/vae/ae.safetensors" \
    "$MODELS/vae/z-image-vae.safetensors" \
    "Z-Image VAE (312 MB)"

download_if_missing \
    "https://huggingface.co/alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union/resolve/main/Z-Image-Turbo-Fun-Controlnet-Union.safetensors" \
    "$MODELS/model_patches/Z-Image-Turbo-Fun-Controlnet-Union.safetensors" \
    "Z-Image ControlNet Union (2.89 GB)"

download_if_missing \
    "https://huggingface.co/jingheya/lotus-depth-g-v2-0-disparity/resolve/main/unet/diffusion_pytorch_model.safetensors" \
    "$MODELS/diffusion_models/lotus-depth-g-v2-0-disparity.safetensors" \
    "Lotus Depth (3.23 GB)"

download_if_missing \
    "https://huggingface.co/stabilityai/sd-vae-ft-mse-original/resolve/main/vae-ft-mse-840000-ema-pruned.safetensors" \
    "$MODELS/vae/vae-ft-mse-840000-ema-pruned.safetensors" \
    "SD VAE MSE (319 MB)"

download_if_missing \
    "https://huggingface.co/Bingsu/adetailer/resolve/main/face_yolov8m.pt" \
    "$MODELS/ultralytics/bbox/face_yolov8m.pt" \
    "Face YOLOv8 Detector (52 MB)"

download_if_missing \
    "https://huggingface.co/scenario-labs/sam_vit/resolve/main/sam_vit_b_01ec64.pth" \
    "$MODELS/sams/sam_vit_b_01ec64.pth" \
    "SAM ViT-B (375 MB)"

# ===== QWEN MULTI-ANGLE MODELS =====

download_if_missing \
    "https://huggingface.co/1038lab/Qwen-Image-Edit-2511-FP8/resolve/main/Qwen-Image-Edit-2511-FP8_e4m3fn.safetensors" \
    "$MODELS/diffusion_models/Qwen-Image-Edit-2511-FP8_e4m3fn.safetensors" \
    "Qwen Image Edit FP8 (19.03 GB)"

download_if_missing \
    "https://huggingface.co/Comfy-Org/HunyuanVideo_1.5_repackaged/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors" \
    "$MODELS/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors" \
    "Qwen 2.5 VL 7B CLIP (8.74 GB)"

download_if_missing \
    "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors" \
    "$MODELS/vae/qwen_image_vae.safetensors" \
    "Qwen Image VAE (242 MB)"

download_if_missing \
    "https://huggingface.co/fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA/resolve/main/qwen-image-edit-2511-multiple-angles-lora.safetensors" \
    "$MODELS/loras/qwen-image-edit-2511-multiple-angles-lora.safetensors" \
    "Qwen Multi-Angle LoRA (281 MB)"

download_if_missing \
    "https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning/resolve/main/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors" \
    "$MODELS/loras/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors" \
    "Qwen Lightning LoRA (810 MB)"

# ===== LLM MODELS via IF_AI_tools =====
echo ""
echo "[LLM] IF_AI_tools will download models on first chat use"

echo ""
echo "========================================="
echo "  All model downloads complete!"
echo "========================================="
