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
        // Если есть переменная API_URL (на проде), берем её. Иначе (на локалке) стучимся в localhost
        target: process.env.API_URL || 'http://127.0.0.1:8008', 
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