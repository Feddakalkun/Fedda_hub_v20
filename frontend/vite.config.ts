import { createLogger, defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

function quietProxyErrors() {
  return (proxy: any) => {
    // Vite adds a noisy default error logger. Replace it so startup races
    // (backend/comfy still booting) don't spam terminal red errors.
    if (typeof proxy.removeAllListeners === 'function') {
      proxy.removeAllListeners('error')
    }
    proxy.on('error', (_err: any, _req: any, res: any) => {
      if (!res) return
      try {
        // Node http.ServerResponse
        if (typeof res.writeHead === 'function' && typeof res.end === 'function') {
          if (!res.headersSent) {
            res.writeHead(503, { 'Content-Type': 'application/json' })
          }
          res.end(JSON.stringify({ error: 'Service unavailable (starting)' }))
          return
        }

        // Fallback for response-like objects in newer proxy runtimes
        if (typeof res.setHeader === 'function') {
          res.setHeader('Content-Type', 'application/json')
        }
        if (typeof res.statusCode !== 'undefined') {
          res.statusCode = 503
        }
        if (typeof res.end === 'function') {
          res.end(JSON.stringify({ error: 'Service unavailable (starting)' }))
        }
      } catch {
        // Intentionally swallow proxy startup race errors.
      }
    })
  }
}

// https://vite.dev/config/
const viteLogger = createLogger()
const originalError = viteLogger.error
viteLogger.error = (msg, options) => {
  const text = String(msg ?? '')
  if (
    text.includes('[vite] http proxy error') ||
    text.includes('[vite] ws proxy error') ||
    text.includes('ECONNREFUSED 127.0.0.1:8199')
  ) {
    return
  }
  originalError(msg, options)
}

export default defineConfig({
  customLogger: viteLogger,
  plugins: [react()],
  server: {
    open: true,
    proxy: {
      '/comfy': {
        target: 'http://127.0.0.1:8199',
        changeOrigin: true,
        ws: true,
        rewrite: (path) => path.replace(/^\/comfy/, ''),
        configure: quietProxyErrors(),
      },
      '/ollama': {
        target: 'http://127.0.0.1:11434',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/ollama/, '/api'), // Rewrite /ollama/tags -> /api/tags
        configure: quietProxyErrors(),
      },
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: quietProxyErrors(),
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        configure: quietProxyErrors(),
      },
    },
  },
})
