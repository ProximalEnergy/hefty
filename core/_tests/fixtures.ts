import { test as base, expect } from '@playwright/test'

export type ConsoleMessage = {
  type: string
  text: string
  url?: string
  lineNumber?: number
  columnNumber?: number
}

type TestFixtures = {
  pageWithConsoleTracking: import('@playwright/test').Page
  consoleErrors: ConsoleMessage[]
}

export const test = base.extend<TestFixtures>({
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  consoleErrors: async ({}, use) => {
    const consoleMessages: ConsoleMessage[] = []
    await use(consoleMessages)
  },

  pageWithConsoleTracking: async ({ page, consoleErrors }, use) => {
    // Track console messages
    page.on('console', (msg) => {
      const message: ConsoleMessage = {
        type: msg.type(),
        text: msg.text(),
        url: msg.location().url,
        lineNumber: msg.location().lineNumber,
        columnNumber: msg.location().columnNumber,
      }

      // Capture errors only (ignore warnings)
      if (msg.type() === 'error') {
        consoleErrors.push(message)
        console.log(`🔴 Console ${msg.type()}: ${msg.text()}`)
        if (message.url) {
          console.log(
            `   at ${message.url}:${message.lineNumber}:${message.columnNumber}`,
          )
        }
      }
    })

    // Track uncaught exceptions
    page.on('pageerror', (error) => {
      const message: ConsoleMessage = {
        type: 'exception',
        text: error.message,
      }
      consoleErrors.push(message)
      console.log(`🔴 Uncaught exception: ${error.message}`)
      console.log(`   Stack: ${error.stack}`)
    })

    // Track failed network requests
    page.on('requestfailed', (request) => {
      const message: ConsoleMessage = {
        type: 'network-error',
        text: `Failed to load: ${request.url()} - ${request.failure()?.errorText}`,
        url: request.url(),
      }
      consoleErrors.push(message)
      console.log(
        `🔴 Network error: ${request.url()} - ${request.failure()?.errorText}`,
      )
    })

    await use(page)
  },
})

export { expect }

// Helper function to assert no console errors
export function expectNoConsoleErrors(consoleErrors: ConsoleMessage[]) {
  if (consoleErrors.length > 0) {
    console.log('\n📋 Console Errors Summary:')
    consoleErrors.forEach((error, index) => {
      console.log(`${index + 1}. [${error.type.toUpperCase()}] ${error.text}`)
      if (error.url) {
        console.log(
          `   Location: ${error.url}:${error.lineNumber}:${error.columnNumber}`,
        )
      }
    })
    console.log('\n')
  }

  expect(
    consoleErrors,
    `Found ${consoleErrors.length} console errors`,
  ).toHaveLength(0)
}

// Helper function to check for specific types of errors
export function getConsoleErrorsByType(
  consoleErrors: ConsoleMessage[],
  type: string,
): ConsoleMessage[] {
  return consoleErrors.filter((error) => error.type === type)
}

// Helper function to ignore specific known errors
export function filterIgnoredErrors(
  consoleErrors: ConsoleMessage[],
  ignoredPatterns: string[],
): ConsoleMessage[] {
  return consoleErrors.filter((error) => {
    return !ignoredPatterns.some((pattern) => error.text.includes(pattern))
  })
}
