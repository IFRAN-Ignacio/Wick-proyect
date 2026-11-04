import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// En dev, Vite hace de proxy hacia el backend: mismo origen, sin CORS.
const backend = process.env.WICK_BACKEND ?? 'http://127.0.0.1:8765'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  server: {
    port: 5173,
    strictPort: true,
    proxy: { '/api': { target: backend, changeOrigin: false } },
  },
})
