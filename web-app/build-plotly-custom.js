import { execSync } from 'child_process'
import path, { dirname } from 'path'
import process from 'process'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const plotlyDir = path.join(__dirname, 'node_modules', 'plotly.js')
try {
  // Navigate to Plotly.js directory and install dependencies
  execSync('pnpm install', { stdio: 'inherit', cwd: plotlyDir })

  // Create a custom Plotly.js bundle
  execSync(
    'pnpm run custom-bundle -- --traces scatter,bar,waterfall,heatmap,sunburst,icicle,box,histogram',
    {
      stdio: 'inherit',
      cwd: plotlyDir,
    },
  )
} catch (error) {
  console.error('Failed to create custom Plotly.js bundle:', error)
  process.exit(1)
}
