// frontend/vite.config.ts
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173, 
    host: true, 
    allowedHosts: ['jetplan.site'],
    proxy: {
      '/api': {
        // Указываем имя сервиса бэкенда и его внутренний порт
        target: 'http://backend:8000', 
        changeOrigin: true
      }
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})
