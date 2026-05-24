import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'
import { copyFileSync, mkdirSync } from 'fs'

// After build: copy index.html into Django templates/
function copyIndexToTemplates() {
  return {
    name: 'copy-index-to-templates',
    closeBundle() {
      const src = resolve(__dirname, '../backend/frontend_build/index.html')
      const destDir = resolve(__dirname, '../backend/templates')
      mkdirSync(destDir, { recursive: true })
      copyFileSync(src, resolve(destDir, 'index.html'))
      console.log('✓ Copied index.html to Django templates/')
    }
  }
}

export default defineConfig({
  plugins: [react(), copyIndexToTemplates()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  },
  build: {
    outDir: '../backend/frontend_build',
    emptyOutDir: true,
    assetsDir: 'assets',
  }
})