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

  // 代码分割优化
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id: string) => {
          // React 核心库
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom') || id.includes('node_modules/react-router')) {
            return 'vendor'
          }
          // 状态管理 + HTTP 客户端
          if (id.includes('node_modules/zustand') || id.includes('node_modules/axios')) {
            return 'state'
          }
          // 图表库
          if (id.includes('node_modules/recharts')) {
            return 'charts'
          }
          // 流程图库
          if (id.includes('node_modules/reactflow')) {
            return 'flow'
          }
          // 动画库
          if (id.includes('node_modules/framer-motion')) {
            return 'animation'
          }
          // Lucide 图标库
          if (id.includes('node_modules/lucide-react')) {
            return 'icons'
          }
        },
      },
    },
    // 调整 chunk 大小警告限制
    chunkSizeWarningLimit: 600,
  },
})
