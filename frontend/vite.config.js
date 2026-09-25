import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  // Runs locally, so one ~650 kB bundle is fine; no need for the size warning.
  build: { chunkSizeWarningLimit: 1500 },
})
