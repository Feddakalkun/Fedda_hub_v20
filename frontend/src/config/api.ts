const COMFY_BASE = import.meta.env.VITE_COMFY_URL || '/comfy';
const BACKEND_BASE = import.meta.env.VITE_BACKEND_URL || '';
const WS_PROTO = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_HOST = import.meta.env.VITE_COMFY_WS_URL || `${WS_PROTO}//${window.location.host}/comfy/ws`;

export const COMFY_API = {
  BASE_URL: COMFY_BASE,
  ENDPOINTS: {
    PROMPT: '/prompt',
    QUEUE: '/queue',
    HISTORY: '/history',
    VIEW: '/view',
    UPLOAD_IMAGE: '/upload/image',
    SYSTEM_STATS: '/system_stats',
    OBJECT_INFO: '/object_info',
    INTERRUPT: '/interrupt',
  },
  WS_URL: WS_HOST,
};

export const BACKEND_API = {
  BASE_URL: BACKEND_BASE,
  ENDPOINTS: {
    FILES_LIST: '/api/files/list',
    FILES_DELETE: '/api/files/delete',
    LORA_INSTALLED: '/api/lora/installed',
    SETTINGS_HF_TOKEN: '/api/settings/hf-token',
    SETTINGS_HF_TOKEN_STATUS: '/api/settings/hf-token/status',
    OLLAMA_MODELS: '/api/ollama/models',
    HARDWARE_STATS: '/api/hardware/stats',
    WORKFLOW_LIST: '/api/workflow/list',
    WORKFLOW_MODEL_STATUS: '/api/workflow/model-status',
    GENERATE: '/api/generate',
    GENERATE_STATUS: '/api/generate/status',
    COMFY_REFRESH_MODELS: '/api/comfy/refresh-models',
    LORA_LIST: '/api/lora/list',
  },
};

export const APP_CONFIG = {
  NAME: 'FEDDA Hub',
  VERSION: 'v20',
};