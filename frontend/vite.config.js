import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  envDir: '..', // el .env vive en la raíz del monorepo (solo se exponen las VITE_*)
})
