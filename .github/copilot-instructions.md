# FEDDA - Copilot Instructions

## Project Overview
FEDDA is a portable AI studio: ComfyUI + React frontend + FastAPI backend.
- **Local deployment**: Embedded Python, Node, Git — one-click Windows installer
- **RunPod/Docker deployment**: Dockerfile builds Linux/CUDA image with nginx reverse proxy

## Tech Stack

### Frontend (`frontend/`)
- React 19 + TypeScript + Vite 7 + Tailwind CSS 3
- Icons: lucide-react (never use other icon libs)
- Animation: framer-motion
- Markdown: react-markdown
- No router — single-page app with tab-based navigation via `activeTab`/`activeSubTab` state in App.tsx
- State: React hooks only (useState, useEffect, useCallback, useRef). No Redux/Zustand
- All API config in `frontend/src/config/api.ts` — use `BACKEND_API.BASE_URL` and `COMFY_API.BASE_URL`

### Backend (`backend/`)
- Python FastAPI (`server.py` is the main entry point)
- Services split into: `audio_service.py`, `lipsync_service.py`, `lora_service.py`, `tiktok_service.py`
- ComfyUI runs separately (port 8199 on RunPod, 8188 on local)
- Backend proxies to ComfyUI for workflow execution
- Model downloads managed by `server.py` (`REQUIRED_MODELS` dict, `download_progress` tracking)

### Deployment
- **Local (Windows)**: `scripts/install.ps1` sets up everything, `run.bat` starts services
- **Docker (RunPod)**: `runpod/Dockerfile` + `runpod/supervisord.conf` + `runpod/nginx/nginx.conf`
- nginx reverse proxy: port 3000 → `/api` (backend :8000), `/comfy` (ComfyUI :8199), `/jupyter` (JupyterLab)
- `.dockerignore` excludes Windows files (*.bat, *.ps1, python_embeded/)

## Architecture

### Frontend Structure
```
frontend/src/
├── App.tsx              — Main app shell, tab routing, header
├── config/api.ts        — All API URLs and model definitions
├── pages/               — One page per tab (ImagePage, VideoPage, AudioPage, etc.)
├── components/
│   ├── layout/          — Sidebar.tsx (navigation with CREATE/MANAGE/SYSTEM sections)
│   ├── ui/              — Reusable UI components (CatalogShell, CatalogCard, PageTabs, Toast, etc.)
│   ├── image/           — Image generation tabs (ZImageTab, etc.)
│   ├── video/           — Video generation tabs (LipsyncTab, SceneBuilderTab)
│   ├── tiktok/          — TikTok Studio components
│   ├── ModelDownloader  — Downloads required ComfyUI models per group
│   ├── HFTokenSettings  — HuggingFace token management (localStorage)
│   ├── SystemMonitor    — GPU/CPU/RAM stats display
│   └── PromptLibrary    — Saved prompts system
├── hooks/               — Custom React hooks (useOllamaManager, useComfyStatus, etc.)
└── services/            — assistantService.ts (LLM prompt building)
```

### Key Patterns
- **Model groups**: `z-image`, `qwen-angle`, `ace-step`, `lipsync`, `scene-builder` — defined in `REQUIRED_MODELS` in server.py
- **Workflows**: ComfyUI workflow JSONs live in `frontend/public/workflows/` — loaded by frontend, sent to ComfyUI via `/prompt` API
- **Polling pattern**: Frontend polls backend status endpoints with adaptive intervals (fast during downloads, slow when idle, backoff when backend is down)
- **Toast notifications**: Use `useToast()` hook → `toast(message, 'success' | 'error' | 'info')`
- **Shell components**: Pages use `CatalogShell` (full page wrapper) and `CatalogCard` (content sections)

## Coding Style

### TypeScript/React
- Functional components with arrow functions: `export const Component = () => { ... }`
- Prefer `interface` over `type` for component props
- Use Tailwind utility classes inline — no separate CSS files
- Dark theme: backgrounds `bg-[#0a0a0f]`, `bg-[#121218]`, `bg-[#1a1a24]`; text `text-white`, `text-slate-400`, `text-slate-500`
- Active/selected state: white background with black text (`bg-white text-black`)
- Font sizes: `text-[9px]` for labels, `text-[10px]` for meta, `text-[11px]` for buttons, `text-xs`/`text-sm` for content
- Uppercase tracking for labels: `font-bold uppercase tracking-widest` or `tracking-[0.2em]`
- No emojis in code unless explicitly requested

### Python/Backend
- FastAPI with CORS middleware (allow all origins)
- Return `{"success": True/False, ...}` JSON from all endpoints (never raise HTTPException — it loses CORS headers)
- Use `requests` for HTTP calls to ComfyUI
- Background downloads use `threading.Thread`
- Model download progress tracked in `download_progress` dict (global)

## Important Rules
- **Never break existing functionality** when adding features
- **No over-engineering** — keep solutions simple and focused
- **Don't add comments/docstrings** to code you didn't change
- **ComfyUI has NO built-in model download API** — all model management is custom
- **Local uses Ollama** (port 11434) for LLM; **RunPod uses IF_AI_tools** ComfyUI node (no Ollama in Docker)
- **HF token** stored in localStorage under key `fedda_hf_token`, retrieved via `getStoredHFToken()`
- When polling endpoints that may be down, use silent error handling (no console.error spam) with backoff intervals
