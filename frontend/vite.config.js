import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  // 本地开发时把 /api 转发到本机后端（api.js 使用相对路径 baseURL）
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:15000',
        changeOrigin: true
      }
    }
  }
})
