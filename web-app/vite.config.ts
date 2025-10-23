import { sentryVitePlugin } from '@sentry/vite-plugin'
import react from '@vitejs/plugin-react-swc'
import path from 'path'
import { visualizer } from 'rollup-plugin-visualizer'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [
    react(),
    sentryVitePlugin({
      org: 'proximal-energy',
      project: 'javascript-react',
    }),
    visualizer({
      filename: 'rollup-plugin-visualizer-stats.html',
      open: false,
      gzipSize: true,
      brotliSize: true,
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
    dedupe: ['react', 'react-dom'],
  },
  build: {
    sourcemap: 'hidden',
    minify: 'esbuild',
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          if (id.includes('node_modules')) {
            // Keep React ecosystem together
            if (
              id.includes('react') ||
              id.includes('react-dom') ||
              id.includes('react-is')
            ) {
              return 'react-vendor'
            }

            // Sentry
            if (id.includes('@sentry')) {
              return 'sentry'
            }

            // UI libraries (adjust to your stack)
            if (id.includes('mantine') || id.includes('@ant-design')) {
              return 'ui-library'
            }

            // Chart libraries
            if (
              id.includes('plotly') ||
              id.includes('recharts') ||
              id.includes('d3')
            ) {
              return 'charts'
            }

            // Date libraries
            if (
              id.includes('moment') ||
              id.includes('dayjs') ||
              id.includes('date-fns')
            ) {
              return 'date-utils'
            }

            // Icons
            if (id.includes('icons') || id.includes('lucide')) {
              return 'icons'
            }

            // Remaining packages - split by first-level package name
            const match = id.match(/node_modules\/(@[^/]+\/[^/]+|[^/]+)/)
            if (match) {
              const packageName = match[1]
              // Group smaller packages together, but keep large ones separate
              return `vendor-${packageName.replace('@', '').replace('/', '-')}`
            }
          }
        },
      },
    },
  },
  optimizeDeps: {
    exclude: [],
  },
})
