import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'
import { copyFileSync, mkdirSync } from 'fs'

// Plugin to copy built index.html into Django templates/ after every build
function copyIndexToTemplates() {
  return {
    name: 'copy-index-to-templates',
    closeBundle() {
      const src = resolve(__dirname, '../backend/staticfiles/frontend/index.html')
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
    outDir: '../backend/staticfiles/frontend',
    emptyOutDir: true,
    assetsDir: 'assets',
  }
})