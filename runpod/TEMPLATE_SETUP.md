# FEDDA RunPod Template Setup

This setup is designed so you can create one RunPod template and run on different NVIDIA GPU classes with minimal changes.

## 1. Build Source
Use this repo with:
- `Dockerfile`: `runpod/Dockerfile`
- Build context: repo root

Recommended image tags:
- Stable (`main`): `ghcr.io/feddakalkun/fedda-runpod:latest`
- Dev (`codex/runpod-template-setup`): `ghcr.io/feddakalkun/fedda-runpod:runpod-dev`

## 2. RunPod Template Fields
Set these in the template:
- `Container Start Command`: leave empty (image uses entrypoint `/app/runpod_start.sh`)
- `Expose HTTP Ports`: `3000`
- `Volume Mount`: `/workspace` (Network Volume recommended)
- `GPU`: any CUDA-capable NVIDIA GPU supported by RunPod drivers

## 3. Recommended Env Vars
- `COMFY_PORT=8199`
- `BACKEND_PORT=8000`
- `FRONTEND_PORT=3000`
- `JUPYTER_PORT=8888`

Optional tuning:
- `COMFY_RESERVE_VRAM_GB=1|2|3|4|6`
- `COMFY_EXTRA_ARGS=--disable-cuda-malloc` (or your own Comfy flags)

If `COMFY_RESERVE_VRAM_GB` is not set, startup auto-selects a safe value based on detected VRAM.

## 4. URLs
After pod is running:
- Main app: `https://<pod-id>-3000.proxy.runpod.net`
- Comfy API (proxied): `https://<pod-id>-3000.proxy.runpod.net/comfy/`
- Backend API: `https://<pod-id>-3000.proxy.runpod.net/api/`
- Jupyter (proxied): `https://<pod-id>-3000.proxy.runpod.net/jupyter/`

## 5. Health Checks
Inside the pod container:
- Backend: `curl -fsS http://127.0.0.1:8000/health`
- ComfyUI: `curl -fsS http://127.0.0.1:8199/system_stats`

## 6. Persistence
Models and IO are symlinked to `/workspace` by startup script:
- `/workspace/models/*`
- `/workspace/input`
- `/workspace/output`

This keeps checkpoints/loras/outputs across pod restarts.

## 7. GPU Compatibility Notes
- Image uses PyTorch `cu124` wheels for broad compatibility.
- `xformers`, `torchao`, and `sageattention` install best-effort (non-fatal fallback).
- For very low VRAM cards, increase reserve VRAM and reduce workload batch/steps.
