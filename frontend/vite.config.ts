import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    allowedHosts: ['.ngrok-free.dev'],
    port: 3000,
    watch: {
      usePolling: true
    }
  }
})
