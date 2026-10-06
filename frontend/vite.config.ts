import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/verify": "http://127.0.0.1:8000",
      "/extract": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
})
