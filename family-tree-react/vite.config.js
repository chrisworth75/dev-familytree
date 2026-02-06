import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 4202,
    proxy: {
      '/uploads': {
        target: 'http://localhost:3200',
        changeOrigin: true,
      },
    },
  },
})
