import { expect, filterIgnoredErrors, test } from '../fixtures'

test.describe('Smoke tests with filtered warnings - Public Pages', () => {
  const publicPages = [
    { name: 'Home', path: '/' },
    { name: 'Sign In', path: '/sign-in' },
  ]

  for (const page of publicPages) {
    test(`should load ${page.name} page without unexpected console errors`, async ({
      pageWithConsoleTracking: testPage,
      consoleErrors,
    }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(page.path)

      // Wait for page to fully load
      await testPage.waitForLoadState('networkidle')

      // Filter out known development warnings
      const ignoredPatterns = [
        'React Router Future Flag Warning',
        'Clerk: Clerk has been loaded with development keys',
        'React DevTools',
        'Download the React DevTools',
        'favicon.ico',
        'Warning: componentWillMount',
        'Warning: componentWillReceiveProps',
        'Warning: componentWillUpdate',
        'Clerk:', // General Clerk development warnings
        'React Router will begin wrapping state updates', // React Router v7 migration warnings
        'Relative route resolution within Splat routes is changing', // React Router v7 migration warnings
      ]

      const filteredErrors = filterIgnoredErrors(consoleErrors, ignoredPatterns)

      if (filteredErrors.length > 0) {
        console.log(
          `\n❌ ${page.name} page has ${filteredErrors.length} unexpected console issues:`,
        )
        filteredErrors.forEach((error, index) => {
          console.log(
            `  ${index + 1}. [${error.type.toUpperCase()}] ${error.text}`,
          )
          if (error.url) {
            console.log(
              `     Location: ${error.url}:${error.lineNumber}:${error.columnNumber}`,
            )
          }
        })
      } else {
        console.log(`✅ ${page.name} page has no unexpected console errors`)
      }

      expect(
        filteredErrors,
        `Found ${filteredErrors.length} unexpected console errors on ${page.name} page`,
      ).toHaveLength(0)
    })
  }
})

test.describe('Smoke tests with filtered warnings - Account Pages', () => {
  const accountPages = [{ name: 'Account Settings', path: '/account-settings' }]

  for (const page of accountPages) {
    test(`should load ${page.name} page without unexpected console errors`, async ({
      pageWithConsoleTracking: testPage,
      consoleErrors,
    }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(page.path)

      // Wait for page to fully load
      await testPage.waitForLoadState('networkidle')

      // Filter out known development warnings
      const ignoredPatterns = [
        'React Router Future Flag Warning',
        'Clerk: Clerk has been loaded with development keys',
        'React DevTools',
        'Download the React DevTools',
        'favicon.ico',
        'Warning: componentWillMount',
        'Warning: componentWillReceiveProps',
        'Warning: componentWillUpdate',
        'Clerk:',
        'React Router will begin wrapping state updates',
        'Relative route resolution within Splat routes is changing',
      ]

      const filteredErrors = filterIgnoredErrors(consoleErrors, ignoredPatterns)

      if (filteredErrors.length > 0) {
        console.log(
          `\n❌ ${page.name} page has ${filteredErrors.length} unexpected console issues:`,
        )
        filteredErrors.forEach((error, index) => {
          console.log(
            `  ${index + 1}. [${error.type.toUpperCase()}] ${error.text}`,
          )
          if (error.url) {
            console.log(
              `     Location: ${error.url}:${error.lineNumber}:${error.columnNumber}`,
            )
          }
        })
      } else {
        console.log(`✅ ${page.name} page has no unexpected console errors`)
      }

      expect(
        filteredErrors,
        `Found ${filteredErrors.length} unexpected console errors on ${page.name} page`,
      ).toHaveLength(0)
    })
  }
})

test.describe('Smoke tests with filtered warnings - Portfolio Pages', () => {
  const portfolioPages = [
    { name: 'Portfolio Home', path: '/portfolio' },
    { name: 'Portfolio List', path: '/portfolio/list' },
    { name: 'Portfolio Map', path: '/portfolio/map' },
    { name: 'Portfolio KPIs', path: '/portfolio/kpis' },
    { name: 'Portfolio Settings', path: '/portfolio/settings' },
    { name: 'Portfolio Calendar', path: '/portfolio/calendar' },
    { name: 'Create Project', path: '/portfolio/create-project' },
  ]

  for (const page of portfolioPages) {
    test(`should load ${page.name} page without unexpected console errors`, async ({
      pageWithConsoleTracking: testPage,
      consoleErrors,
    }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(page.path)

      // Wait for page to fully load
      await testPage.waitForLoadState('networkidle')

      // Filter out known development warnings
      const ignoredPatterns = [
        'React Router Future Flag Warning',
        'Clerk: Clerk has been loaded with development keys',
        'React DevTools',
        'Download the React DevTools',
        'favicon.ico',
        'Warning: componentWillMount',
        'Warning: componentWillReceiveProps',
        'Warning: componentWillUpdate',
        'Clerk:',
        'React Router will begin wrapping state updates',
        'Relative route resolution within Splat routes is changing',
      ]

      const filteredErrors = filterIgnoredErrors(consoleErrors, ignoredPatterns)

      if (filteredErrors.length > 0) {
        console.log(
          `\n❌ ${page.name} page has ${filteredErrors.length} unexpected console issues:`,
        )
        filteredErrors.forEach((error, index) => {
          console.log(
            `  ${index + 1}. [${error.type.toUpperCase()}] ${error.text}`,
          )
          if (error.url) {
            console.log(
              `     Location: ${error.url}:${error.lineNumber}:${error.columnNumber}`,
            )
          }
        })
      } else {
        console.log(`✅ ${page.name} page has no unexpected console errors`)
      }

      expect(
        filteredErrors,
        `Found ${filteredErrors.length} unexpected console errors on ${page.name} page`,
      ).toHaveLength(0)
    })
  }
})

test.describe('Smoke tests with filtered warnings - Development Pages', () => {
  const developmentPages = [
    { name: 'Development Home (ERCOT Map)', path: '/development' },
    { name: 'Development Resources', path: '/development/resources' },
    { name: 'Development Prices', path: '/development/prices' },
  ]

  for (const page of developmentPages) {
    test(`should load ${page.name} page without unexpected console errors`, async ({
      pageWithConsoleTracking: testPage,
      consoleErrors,
    }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(page.path)

      // Wait for page to fully load
      await testPage.waitForLoadState('networkidle')

      // Filter out known development warnings
      const ignoredPatterns = [
        'React Router Future Flag Warning',
        'Clerk: Clerk has been loaded with development keys',
        'React DevTools',
        'Download the React DevTools',
        'favicon.ico',
        'Warning: componentWillMount',
        'Warning: componentWillReceiveProps',
        'Warning: componentWillUpdate',
        'Clerk:',
        'React Router will begin wrapping state updates',
        'Relative route resolution within Splat routes is changing',
      ]

      const filteredErrors = filterIgnoredErrors(consoleErrors, ignoredPatterns)

      if (filteredErrors.length > 0) {
        console.log(
          `\n❌ ${page.name} page has ${filteredErrors.length} unexpected console issues:`,
        )
        filteredErrors.forEach((error, index) => {
          console.log(
            `  ${index + 1}. [${error.type.toUpperCase()}] ${error.text}`,
          )
          if (error.url) {
            console.log(
              `     Location: ${error.url}:${error.lineNumber}:${error.columnNumber}`,
            )
          }
        })
      } else {
        console.log(`✅ ${page.name} page has no unexpected console errors`)
      }

      expect(
        filteredErrors,
        `Found ${filteredErrors.length} unexpected console errors on ${page.name} page`,
      ).toHaveLength(0)
    })
  }
})

test.describe('Smoke tests with filtered warnings - Admin & Application Pages', () => {
  const adminPages = [
    { name: 'Application Settings', path: '/application-settings' },
    { name: 'API', path: '/api' },
    { name: 'Loom Testing', path: '/loom-testing' },
  ]

  for (const page of adminPages) {
    test(`should load ${page.name} page without unexpected console errors`, async ({
      pageWithConsoleTracking: testPage,
      consoleErrors,
    }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(page.path)

      // Wait for page to fully load
      await testPage.waitForLoadState('networkidle')

      // Filter out known development warnings
      const ignoredPatterns = [
        'React Router Future Flag Warning',
        'Clerk: Clerk has been loaded with development keys',
        'React DevTools',
        'Download the React DevTools',
        'favicon.ico',
        'Warning: componentWillMount',
        'Warning: componentWillReceiveProps',
        'Warning: componentWillUpdate',
        'Clerk:',
        'React Router will begin wrapping state updates',
        'Relative route resolution within Splat routes is changing',
      ]

      const filteredErrors = filterIgnoredErrors(consoleErrors, ignoredPatterns)

      if (filteredErrors.length > 0) {
        console.log(
          `\n❌ ${page.name} page has ${filteredErrors.length} unexpected console issues:`,
        )
        filteredErrors.forEach((error, index) => {
          console.log(
            `  ${index + 1}. [${error.type.toUpperCase()}] ${error.text}`,
          )
          if (error.url) {
            console.log(
              `     Location: ${error.url}:${error.lineNumber}:${error.columnNumber}`,
            )
          }
        })
      } else {
        console.log(`✅ ${page.name} page has no unexpected console errors`)
      }

      expect(
        filteredErrors,
        `Found ${filteredErrors.length} unexpected console errors on ${page.name} page`,
      ).toHaveLength(0)
    })
  }
})
