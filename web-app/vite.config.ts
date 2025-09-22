import { sentryVitePlugin } from '@sentry/vite-plugin'
import react from '@vitejs/plugin-react-swc'
import path from 'path'
import { visualizer } from 'rollup-plugin-visualizer'
import { defineConfig } from 'vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    sentryVitePlugin({
      org: 'proximal-energy',
      project: 'javascript-react',
    }),
    visualizer({
      filename: 'rollup-plugin-visualizer-stats.html',
      open: true, // Automatically open the report in your browser
      gzipSize: true, // Show gzip sizes
      brotliSize: true, // Show Brotli sizes
    }),
  ],

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  build: {
    sourcemap: true,
  },
})
