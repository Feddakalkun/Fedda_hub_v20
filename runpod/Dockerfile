# ============================================================================
# FEDDA RUNPOD IMAGE (GPU-flexible, CUDA 12.4, PyTorch cu124)
# ============================================================================

FROM node:22-alpine AS frontend-builder
COPY . /app
WORKDIR /app/frontend
RUN npm ci --no-audit --no-fund && npm run build

FROM nvidia/cuda:12.4.1-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    CUDA_HOME=/usr/local/cuda \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH} \
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    COMFY_PORT=8199 \
    BACKEND_PORT=8000 \
    FRONTEND_PORT=3000 \
    JUPYTER_PORT=8888

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3.11-dev python3-pip \
    git git-lfs curl wget nginx supervisor ffmpeg rsync \
    build-essential cmake ninja-build \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxrender1 libxext6 \
    libffi-dev libssl-dev jq ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3 \
    && ln -sf /usr/bin/python3 /usr/bin/python

RUN python3 -m pip install --no-cache-dir --upgrade pip wheel setuptools

# PyTorch cu124 works across common RunPod NVIDIA GPUs (30/40/ADA/50 where supported by drivers)
RUN python3 -m pip install --no-cache-dir \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu124

# Optional acceleration (never fail whole build)
RUN python3 -m pip install --no-cache-dir xformers --index-url https://download.pytorch.org/whl/cu124 || true
RUN python3 -m pip install --no-cache-dir torchao || true
RUN python3 -m pip install --no-cache-dir sageattention || true

# Clone ComfyUI at latest master to support newest LTX nodes (cache-bust: 2026-04-11)
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /app/ComfyUI \
    && cd /app/ComfyUI \
    && python3 -m pip install --no-cache-dir -r requirements.txt

WORKDIR /app/ComfyUI/custom_nodes
RUN set -eux; \
    clone_required() { \
      repo="$1"; name="$2"; \
      echo "[FEDDA] Cloning required node: ${name}"; \
      git clone --depth 1 "${repo}" "${name}"; \
    }; \
    clone_optional() { \
      repo="$1"; name="$2"; \
      echo "[FEDDA] Cloning optional node: ${name}"; \
      if ! git clone --depth 1 "${repo}" "${name}"; then \
        echo "[FEDDA] WARN: optional node clone failed: ${name} (${repo})"; \
        rm -rf "${name}"; \
      fi; \
    }; \
    clone_required https://github.com/ltdrdata/ComfyUI-Manager.git ComfyUI-Manager; \
    clone_required https://github.com/rgthree/rgthree-comfy.git rgthree-comfy; \
    clone_required https://github.com/comfyanonymous/ComfyUI_bitsandbytes_NF4.git ComfyUI_bitsandbytes_NF4; \
    clone_required https://github.com/city96/ComfyUI-GGUF.git ComfyUI-GGUF; \
    clone_required https://github.com/ltdrdata/ComfyUI-Impact-Pack.git ComfyUI-Impact-Pack; \
    clone_required https://github.com/kijai/ComfyUI-WanVideoWrapper.git ComfyUI-WanVideoWrapper; \
    clone_required https://github.com/kijai/ComfyUI-WanAnimatePreprocess.git ComfyUI-WanAnimatePreprocess; \
    clone_required https://github.com/kijai/ComfyUI-KJNodes.git ComfyUI-KJNodes; \
    clone_required https://github.com/yolain/ComfyUI-Easy-Use.git ComfyUI-Easy-Use; \
    clone_required https://github.com/pythongosssss/ComfyUI-Custom-Scripts.git ComfyUI-Custom-Scripts; \
    clone_required https://github.com/comfyuistudio/ComfyUI-Studio-nodes.git ComfyUI-Studio-nodes; \
    clone_required https://github.com/theUpsider/ComfyUI-Styles_CSV_Loader.git ComfyUI-Styles_CSV_Loader; \
    clone_required https://github.com/lquesada/ComfyUI-Inpaint-CropAndStitch.git ComfyUI-Inpaint-CropAndStitch; \
    clone_required https://github.com/Suzie1/ComfyUI_Comfyroll_CustomNodes.git ComfyUI_Comfyroll_CustomNodes; \
    clone_optional https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git ComfyUI-VideoHelperSuite; \
    clone_optional https://github.com/jtydhr88/ComfyUI-qwenmultiangle.git ComfyUI-qwenmultiangle; \
    clone_optional https://github.com/kijai/ComfyUI-Florence2.git ComfyUI-Florence2; \
    clone_optional https://github.com/kijai/ComfyUI-SeedVR2_VideoUpscaler.git ComfyUI-SeedVR2_VideoUpscaler; \
    clone_optional https://github.com/Fannovel16/ComfyUI-Frame-Interpolation.git ComfyUI-Frame-Interpolation; \
    clone_optional https://github.com/Saganaki22/ComfyUI-FishAudioS2.git ComfyUI-FishAudioS2

RUN cd /app/ComfyUI/custom_nodes/ComfyUI-Manager && python3 -m pip install --no-cache-dir -r requirements.txt || true
RUN cd /app/ComfyUI/custom_nodes/ComfyUI-Impact-Pack && python3 -m pip install --no-cache-dir -r requirements.txt || true
RUN cd /app/ComfyUI/custom_nodes/ComfyUI-WanVideoWrapper && python3 -m pip install --no-cache-dir -r requirements.txt || true
RUN cd /app/ComfyUI/custom_nodes/ComfyUI-WanAnimatePreprocess && python3 -m pip install --no-cache-dir -r requirements.txt || true
RUN set -eux; \
    for req in \
      /app/ComfyUI/custom_nodes/ComfyUI-KJNodes/requirements.txt \
      /app/ComfyUI/custom_nodes/ComfyUI-Easy-Use/requirements.txt \
      /app/ComfyUI/custom_nodes/ComfyUI-Studio-nodes/requirements.txt \
      /app/ComfyUI/custom_nodes/ComfyUI-Styles_CSV_Loader/requirements.txt \
      /app/ComfyUI/custom_nodes/ComfyUI-Inpaint-CropAndStitch/requirements.txt \
      /app/ComfyUI/custom_nodes/ComfyUI_Comfyroll_CustomNodes/requirements.txt \
      /app/ComfyUI/custom_nodes/ComfyUI-VideoHelperSuite/requirements.txt \
      /app/ComfyUI/custom_nodes/ComfyUI-qwenmultiangle/requirements.txt \
      /app/ComfyUI/custom_nodes/ComfyUI-Florence2/requirements.txt \
      /app/ComfyUI/custom_nodes/ComfyUI-SeedVR2_VideoUpscaler/requirements.txt \
      /app/ComfyUI/custom_nodes/ComfyUI-Frame-Interpolation/requirements.txt \
      /app/ComfyUI/custom_nodes/ComfyUI-FishAudioS2/requirements.txt; do \
      if [ -f "$req" ]; then python3 -m pip install --no-cache-dir -r "$req" || true; fi; \
    done

RUN python3 -m pip install --no-cache-dir \
    insightface \
    diffusers transformers accelerate safetensors sentencepiece \
    onnxruntime-gpu opencv-python-headless pillow tqdm requests psutil \
    fastapi "uvicorn[standard]" python-multipart httpx \
    jupyterlab ipykernel terminado jupyter_server_terminals

COPY --from=frontend-builder /app/backend /app/backend
COPY --from=frontend-builder /app/config /app/config
COPY --from=frontend-builder /app/assets /app/assets
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

COPY runpod/nginx/nginx.conf /etc/nginx/nginx.conf
COPY runpod/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY runpod/runpod_start.sh /app/runpod_start.sh
COPY runpod/start_comfy.sh /app/start_comfy.sh
RUN chmod +x /app/runpod_start.sh /app/start_comfy.sh

WORKDIR /app
EXPOSE 3000 8199 8888 8000

LABEL org.opencontainers.image.source=https://github.com/Feddakalkun/Fedda_hub_v15
LABEL org.opencontainers.image.description="FEDDA RunPod Studio (ComfyUI + Backend + Frontend)"

ENTRYPOINT ["/app/runpod_start.sh"]
