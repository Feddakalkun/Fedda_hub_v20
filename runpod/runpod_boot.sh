#!/bin/bash

# ============================================================================
# FEDDA HYBRID BOOTSTRAPPER (v1.0)
# Optimized for: RTX 5090 / 4090 / 6000 Ada
# Target: RunPod (Ubuntu 22.04 + CUDA 12.4 + PyTorch 2.5)
# ============================================================================

set -e

echo "ðŸš€ [FEDDA] Starting Universal Bootstrapper..."

# â”€â”€ 1. ENVIRONMENT CONFIG â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
WORKSPACE="/workspace"
MODELS_DIR="$WORKSPACE/models"
COMFY_DIR="$WORKSPACE/ComfyUI"
FEDDA_REPO="https://github.com/Feddakalkun/Fedda_hub_v20"

cd "$WORKSPACE"

# â”€â”€ 2. SYSTEM DEPENDENCIES â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
echo "ðŸ“¦ [FEDDA] Installing system dependencies..."
DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 ffmpeg build-essential cmake ninja-build \
    libffi-dev libssl-dev git curl wget htop > /dev/null 2>&1

# â”€â”€ 3. PYTHON SETUP (PyTorch 2.5 / CUDA 12.4) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
echo "ðŸ [FEDDA] Configuring Python environment..."
# We use the system python but upgrade pip
python3 -m pip install --upgrade pip wheel setuptools > /dev/null 2>&1

# Check if we need to upgrade Torch (for 5090 compatibility)
TORCH_VER=$(python3 -c "import torch; print(torch.__version__)" 2>/dev/null || echo "none")
if [[ "$TORCH_VER" != 2.5* ]]; then
    echo "âš¡ [FEDDA] Upgrading to PyTorch 2.5 + CUDA 12.4 (RTX 50-series support)..."
    python3 -m pip install --no-cache-dir torch torchvision torchaudio \
        --index-url https://download.pytorch.org/whl/cu124
fi

# Essential speedups for Wan2.2/LTX
echo "ðŸ”¥ [FEDDA] Installing acceleration kits (torchao, xformers)..."
python3 -m pip install --no-cache-dir torchao xformers --index-url https://download.pytorch.org/whl/cu124
python3 -m pip install --no-cache-dir sageattention || true

# â”€â”€ 4. REPO SYNC â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if [ ! -d "feddafront" ]; then
    echo "ðŸ“‚ [FEDDA] Cloning Fedda core..."
    git clone $FEDDA_REPO feddafront
else
    echo "ðŸ”„ [FEDDA] Updating Fedda core..."
    cd feddafront && git pull && cd ..
fi

# â”€â”€ 5. COMFYUI CORE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if [ ! -d "$COMFY_DIR" ]; then
    echo "ðŸŽ¬ [FEDDA] Installing ComfyUI..."
    git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFY_DIR"
    cd "$COMFY_DIR" && pip install -r requirements.txt && cd ..
else
    echo "ðŸŽ¬ [FEDDA] ComfyUI already present."
    cd "$COMFY_DIR" && git pull && pip install -r requirements.txt && cd ..
fi

# â”€â”€ 6. PERSISTENT MODELS (Network Volume) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
echo "ðŸ’¾ [FEDDA] Linking Persistent Storage..."
mkdir -p "$MODELS_DIR"/{checkpoints,diffusion_models,clip,text_encoders,vae,loras,sams,upscale_models,unet}

# Symlink Comfy models to the Network Volume
for dir in checkpoints diffusion_models clip text_encoders vae loras sams unet; do
    if [ -d "$COMFY_DIR/models/$dir" ] && [ ! -L "$COMFY_DIR/models/$dir" ]; then
        rm -rf "$COMFY_DIR/models/$dir"
        ln -sf "$MODELS_DIR/$dir" "$COMFY_DIR/models/$dir"
    fi
done

# â”€â”€ 7. CUSTOM NODES SETUP â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
echo "ðŸ§© [FEDDA] Installing Custom Nodes..."
NODE_DIR="$COMFY_DIR/custom_nodes"
mkdir -p "$NODE_DIR"

# List of essential nodes
NODES=(
    "https://github.com/ltdrdata/ComfyUI-Manager"
    "https://github.com/rgthree/rgthree-comfy"
    "https://github.com/comfyanonymous/ComfyUI_bitsandbytes_NF4"
    "https://github.com/city96/ComfyUI-GGUF"
    "https://github.com/Feddakalkun/comfyuifeddafront-lite"
)

for url in "${NODES[@]}"; do
    folder=$(basename "$url")
    if [ ! -d "$NODE_DIR/$folder" ]; then
        echo "  - Cloning $folder..."
        git clone --depth 1 "$url" "$NODE_DIR/$folder"
        if [ -f "$NODE_DIR/$folder/requirements.txt" ]; then
            pip install --no-cache-dir -r "$NODE_DIR/$folder/requirements.txt" || true
        fi
    fi
done

# â”€â”€ 8. LTX & WAN2.2 SPECIFIC DEPS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
echo "ðŸŽžï¸ [FEDDA] Installing Video AI dependencies (insightface, etc)..."
python3 -m pip install --no-cache-dir insightface --prefer-binary || true
python3 -m pip install --no-cache-dir diffusers transformers accelerate safetensors sentencepiece

# â”€â”€ 9. LAUNCH â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
echo "âœ¨ [FEDDA] Setup Complete!"
echo "ðŸ“¡ [FEDDA] Starting ComfyUI on port 8199..."

cd "$COMFY_DIR"
# Run with --listen 0.0.0.0 for RunPod proxy access
python3 main.py --listen 0.0.0.0 --port 8199 --preview-method auto
