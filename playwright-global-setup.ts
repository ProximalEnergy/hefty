import { FullConfig, chromium } from '@playwright/test'

async function waitForServer(
  url: string,
  maxRetries = 30,
  retryDelay = 1000,
): Promise<boolean> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const browser = await chromium.launch()
      const context = await browser.newContext()
      const page = await context.newPage()

      await page.goto(url, { waitUntil: 'load', timeout: 5000 })
      await browser.close()
      return true
    } catch (error) {
      console.log(
        `Attempt ${i + 1}/${maxRetries}: Server not ready, retrying in ${retryDelay}ms...`,
      )
      await new Promise((resolve) => setTimeout(resolve, retryDelay))
    }
  }
  return false
}

async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL || 'http://localhost:5173'

  console.log('🌐 Waiting for development server to be ready...')
  console.log(`Expected server at: ${baseURL}`)

  const isServerReady = await waitForServer(baseURL)

  if (isServerReady) {
    console.log('✅ Server is running and accessible')
  } else {
    console.error('❌ Server is not accessible after 30 attempts.')
    console.error(
      'Make sure your development server is running with: npm run dev',
    )
    console.error(`Expected server at: ${baseURL}`)
    throw new Error(`Development server is not accessible at ${baseURL}`)
  }
}

export default globalSetup
