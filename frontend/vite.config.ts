import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  // 开发服务器代理：将 /api 请求转发到后端，解决 CORS 问题
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // 不重写路径，后端路由也是 /api/v1/...
      },
    },
  },
})
