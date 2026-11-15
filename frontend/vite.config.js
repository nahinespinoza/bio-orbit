import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  envDir: '..', // el .env vive en la raíz del monorepo (solo se exponen las VITE_*)
  server: {
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: loadEnv(mode, '..', '').PITAGORAS_PROXY_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
}))
