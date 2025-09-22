import {
  type ConsoleMessage,
  expect,
  expectNoConsoleErrors,
  filterIgnoredErrors,
  getConsoleErrorsByType,
  test,
} from '../fixtures'

test.describe('Console Error Handling Examples', () => {
  test('should demonstrate console error detection', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // This will fail if there are any console errors
    expectNoConsoleErrors(consoleErrors)
  })

  test('should demonstrate filtering known console errors', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Example of ignoring specific known errors/warnings
    const ignoredPatterns = [
      'React DevTools', // Ignore React DevTools warnings
      'Download the React DevTools', // Common development warning
      'Warning: componentWillMount', // Ignore deprecated lifecycle warnings
      'favicon.ico', // Ignore favicon 404s
      'Clerk:', // Ignore specific Clerk warnings if expected
    ]

    const filteredErrors = filterIgnoredErrors(consoleErrors, ignoredPatterns)

    // Only check for errors after filtering out known issues
    expect(
      filteredErrors,
      `Found ${filteredErrors.length} unexpected console errors`,
    ).toHaveLength(0)
  })

  test('should demonstrate checking specific error types', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Check only for JavaScript errors (not warnings or network errors)
    const jsErrors = getConsoleErrorsByType(consoleErrors, 'error')
    const exceptions = getConsoleErrorsByType(consoleErrors, 'exception')

    // Combine critical errors
    const criticalErrors = [...jsErrors, ...exceptions]

    if (criticalErrors.length > 0) {
      console.log('\n🔴 Critical JavaScript errors found:')
      criticalErrors.forEach((error, index) => {
        console.log(`${index + 1}. ${error.text}`)
      })
    }

    expect(
      criticalErrors,
      'No critical JavaScript errors should occur',
    ).toHaveLength(0)
  })

  test('should demonstrate allowing warnings but failing on errors', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Get only errors and exceptions (allow warnings)
    const errors = getConsoleErrorsByType(consoleErrors, 'error')
    const exceptions = getConsoleErrorsByType(consoleErrors, 'exception')
    const networkErrors = getConsoleErrorsByType(consoleErrors, 'network-error')

    const allErrors = [...errors, ...exceptions, ...networkErrors]

    // Log warnings for visibility but don't fail the test
    const warnings = getConsoleErrorsByType(consoleErrors, 'warning')
    if (warnings.length > 0) {
      console.log(
        `\n⚠️  Found ${warnings.length} console warnings (not failing test):`,
      )
      warnings.forEach((warning, index) => {
        console.log(`${index + 1}. ${warning.text}`)
      })
    }

    // Only fail on actual errors
    expect(allErrors, `Found ${allErrors.length} console errors`).toHaveLength(
      0,
    )
  })

  test('should demonstrate custom error handling logic', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    await page.goto('/portfolio')
    await page.waitForLoadState('networkidle')

    // Custom logic to handle different types of errors differently
    const handleConsoleErrors = (errors: ConsoleMessage[]) => {
      const criticalErrors: ConsoleMessage[] = []
      const acceptableWarnings: ConsoleMessage[] = []

      for (const error of errors) {
        // Define your own rules for what's acceptable
        if (error.type === 'warning' && error.text.includes('React')) {
          // React warnings are often acceptable in development
          acceptableWarnings.push(error)
        } else if (
          error.type === 'network-error' &&
          error.text.includes('favicon')
        ) {
          // Favicon 404s are often acceptable
          acceptableWarnings.push(error)
        } else if (error.type === 'error' || error.type === 'exception') {
          // JavaScript errors are never acceptable
          criticalErrors.push(error)
        } else {
          // Unknown error types should be investigated
          criticalErrors.push(error)
        }
      }

      if (acceptableWarnings.length > 0) {
        console.log(
          `\n📝 Acceptable warnings found: ${acceptableWarnings.length}`,
        )
      }

      return criticalErrors
    }

    const criticalErrors = handleConsoleErrors(consoleErrors)
    expect(criticalErrors, 'No critical errors should occur').toHaveLength(0)
  })
})

test.describe('Page-specific Console Error Tests', () => {
  test('should check portfolio pages for console errors', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    const portfolioPages = ['/portfolio', '/portfolio/list', '/portfolio/map']

    for (const pagePath of portfolioPages) {
      console.log(`\n🔍 Testing ${pagePath} for console errors...`)

      // Clear previous console errors
      consoleErrors.length = 0

      await page.goto(pagePath)
      await page.waitForLoadState('networkidle')

      // Check this specific page
      if (consoleErrors.length > 0) {
        console.log(`❌ ${pagePath} has ${consoleErrors.length} console issues`)
        consoleErrors.forEach((error, index) => {
          console.log(`  ${index + 1}. [${error.type}] ${error.text}`)
        })
      } else {
        console.log(`✅ ${pagePath} has no console errors`)
      }

      expectNoConsoleErrors(consoleErrors)
    }
  })

  test('should handle pages that might have expected errors', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    // Some pages might have expected console messages
    await page.goto('/development/resources/non-existent-id')
    await page.waitForLoadState('networkidle')

    // Filter out expected 404-related errors for this specific test
    const unexpectedErrors = consoleErrors.filter((error) => {
      // Allow 404 errors for non-existent resources
      if (error.text.includes('404') || error.text.includes('Not Found')) {
        return false
      }
      // Allow network errors for invalid resource requests
      if (
        error.type === 'network-error' &&
        error.text.includes('non-existent-id')
      ) {
        return false
      }
      return true
    })

    expect(
      unexpectedErrors,
      'Only expected 404 errors should occur',
    ).toHaveLength(0)
  })
})
