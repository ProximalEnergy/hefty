import { expect, expectNoConsoleErrors, test } from '../fixtures'

test.describe('Navigation Flows - Authenticated User', () => {
  test.beforeEach(async ({ pageWithConsoleTracking: page }) => {
    // Note: In a real test environment, you would set up authentication here
    // This could involve logging in with test credentials or using auth tokens
    await page.goto('/')
  })

  test('should navigate through portfolio pages without console errors', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    // Navigate to portfolio
    await page.goto('/portfolio')
    await expect(page).toHaveURL('/portfolio')
    await page.waitForLoadState('networkidle')

    // Navigate to portfolio list
    await page.goto('/portfolio/list')
    await expect(page).toHaveURL('/portfolio/list')
    await page.waitForLoadState('networkidle')

    // Navigate to portfolio map
    await page.goto('/portfolio/map')
    await expect(page).toHaveURL('/portfolio/map')
    await page.waitForLoadState('networkidle')

    // Navigate to portfolio KPIs
    await page.goto('/portfolio/kpis')
    await expect(page).toHaveURL('/portfolio/kpis')
    await page.waitForLoadState('networkidle')

    // Navigate to portfolio settings
    await page.goto('/portfolio/settings')
    await expect(page).toHaveURL('/portfolio/settings')
    await page.waitForLoadState('networkidle')

    // Check for console errors across all navigations
    expectNoConsoleErrors(consoleErrors)
  })

  test('should navigate through development pages without console errors', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    // Navigate to development home
    await page.goto('/development')
    await expect(page).toHaveURL('/development')
    await page.waitForLoadState('networkidle')

    // Navigate to development resources
    await page.goto('/development/resources')
    await expect(page).toHaveURL('/development/resources')
    await page.waitForLoadState('networkidle')

    // Navigate to development prices
    await page.goto('/development/prices')
    await expect(page).toHaveURL('/development/prices')
    await page.waitForLoadState('networkidle')

    // Check for console errors across all navigations
    expectNoConsoleErrors(consoleErrors)
  })

  test('should navigate to account and application settings without console errors', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    // Navigate to account settings
    await page.goto('/account-settings')
    await expect(page).toHaveURL('/account-settings')
    await page.waitForLoadState('networkidle')

    // Navigate to application settings
    await page.goto('/application-settings')
    await expect(page).toHaveURL('/application-settings')
    await page.waitForLoadState('networkidle')

    // Check for console errors across all navigations
    expectNoConsoleErrors(consoleErrors)
  })
})

test.describe('Navigation Flows - Project Pages', () => {
  const mockProjectId = 'test-project-123'

  test('should navigate through main project sections without console errors', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    // Project home
    await page.goto(`/projects/${mockProjectId}`)
    await expect(page).toHaveURL(`/projects/${mockProjectId}`)
    await page.waitForLoadState('networkidle')

    // Real-time data
    await page.goto(`/projects/${mockProjectId}/real-time`)
    await expect(page).toHaveURL(`/projects/${mockProjectId}/real-time`)
    await page.waitForLoadState('networkidle')

    // Battery health
    await page.goto(`/projects/${mockProjectId}/battery-health`)
    await expect(page).toHaveURL(`/projects/${mockProjectId}/battery-health`)
    await page.waitForLoadState('networkidle')

    // Project settings
    await page.goto(`/projects/${mockProjectId}/settings`)
    await expect(page).toHaveURL(`/projects/${mockProjectId}/settings`)
    await page.waitForLoadState('networkidle')

    // Check for console errors across all navigations
    expectNoConsoleErrors(consoleErrors)
  })

  test('should navigate through project KPI sections without console errors', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    // KPI home
    await page.goto(`/projects/${mockProjectId}/kpis`)
    await expect(page).toHaveURL(`/projects/${mockProjectId}/kpis`)
    await page.waitForLoadState('networkidle')

    // KPI alerts
    await page.goto(`/projects/${mockProjectId}/kpis/alerts`)
    await expect(page).toHaveURL(`/projects/${mockProjectId}/kpis/alerts`)
    await page.waitForLoadState('networkidle')

    // Check for console errors across all navigations
    expectNoConsoleErrors(consoleErrors)
  })

  test('should navigate through project events sections without console errors', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    // Events home
    await page.goto(`/projects/${mockProjectId}/events`)
    await expect(page).toHaveURL(`/projects/${mockProjectId}/events`)
    await page.waitForLoadState('networkidle')

    // Uptime table
    await page.goto(`/projects/${mockProjectId}/events/uptime`)
    await expect(page).toHaveURL(`/projects/${mockProjectId}/events/uptime`)
    await page.waitForLoadState('networkidle')

    // Meta analysis
    await page.goto(`/projects/${mockProjectId}/events/meta-analysis`)
    await expect(page).toHaveURL(
      `/projects/${mockProjectId}/events/meta-analysis`,
    )
    await page.waitForLoadState('networkidle')

    // Check for console errors across all navigations
    expectNoConsoleErrors(consoleErrors)
  })

  test('should navigate through project reports sections without console errors', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    // Reports home
    await page.goto(`/projects/${mockProjectId}/reports`)
    await expect(page).toHaveURL(`/projects/${mockProjectId}/reports`)
    await page.waitForLoadState('networkidle')

    // DC Amperage report
    await page.goto(`/projects/${mockProjectId}/reports/dc-amperage`)
    await expect(page).toHaveURL(
      `/projects/${mockProjectId}/reports/dc-amperage`,
    )
    await page.waitForLoadState('networkidle')

    // Custom report
    await page.goto(`/projects/${mockProjectId}/reports/custom`)
    await expect(page).toHaveURL(`/projects/${mockProjectId}/reports/custom`)
    await page.waitForLoadState('networkidle')

    // Check for console errors across all navigations
    expectNoConsoleErrors(consoleErrors)
  })

  test('should navigate through project GIS sections without console errors', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    // BESS enclosure GIS
    await page.goto(`/projects/${mockProjectId}/gis/bess-enclosure`)
    await expect(page).toHaveURL(
      `/projects/${mockProjectId}/gis/bess-enclosure`,
    )
    await page.waitForLoadState('networkidle')

    // PV DC combiner GIS
    await page.goto(`/projects/${mockProjectId}/gis/pv-dc-combiner`)
    await expect(page).toHaveURL(
      `/projects/${mockProjectId}/gis/pv-dc-combiner`,
    )
    await page.waitForLoadState('networkidle')

    // Tracker GIS
    await page.goto(`/projects/${mockProjectId}/gis/tracker`)
    await expect(page).toHaveURL(`/projects/${mockProjectId}/gis/tracker`)
    await page.waitForLoadState('networkidle')

    // Check for console errors across all navigations
    expectNoConsoleErrors(consoleErrors)
  })

  test('should navigate through project quality sections without console errors', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    // Quality home
    await page.goto(`/projects/${mockProjectId}/quality`)
    await expect(page).toHaveURL(`/projects/${mockProjectId}/quality`)
    await page.waitForLoadState('networkidle')

    // Inspections
    await page.goto(`/projects/${mockProjectId}/quality/inspections`)
    await expect(page).toHaveURL(
      `/projects/${mockProjectId}/quality/inspections`,
    )
    await page.waitForLoadState('networkidle')

    // Observations
    await page.goto(`/projects/${mockProjectId}/quality/observations`)
    await expect(page).toHaveURL(
      `/projects/${mockProjectId}/quality/observations`,
    )
    await page.waitForLoadState('networkidle')

    // Check for console errors across all navigations
    expectNoConsoleErrors(consoleErrors)
  })
})

test.describe('Navigation Flows - Error Handling', () => {
  test('should handle non-existent pages gracefully without console errors', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    // Navigate to a non-existent page
    await page.goto('/this-page-does-not-exist')

    // The app should either show a 404 page or redirect to a valid route
    // This behavior depends on your router configuration
    await expect(page.locator('body')).toBeVisible()
    await page.waitForLoadState('networkidle')

    // Check for console errors - we might allow certain routing errors here
    // but unexpected JavaScript errors should still fail the test
    expectNoConsoleErrors(consoleErrors)
  })

  test('should handle invalid project IDs gracefully without console errors', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    // Test navigation with invalid project ID
    await page.goto('/projects/invalid-project-id')

    // The app should handle this gracefully - either show an error or redirect
    await expect(page.locator('body')).toBeVisible()
    await page.waitForLoadState('networkidle')

    // Check for console errors
    expectNoConsoleErrors(consoleErrors)
  })

  test('should handle invalid resource IDs gracefully without console errors', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    // Test navigation with invalid resource ID
    await page.goto('/development/resources/invalid-resource-id')

    // The app should handle this gracefully
    await expect(page.locator('body')).toBeVisible()
    await page.waitForLoadState('networkidle')

    // Check for console errors
    expectNoConsoleErrors(consoleErrors)
  })
})

test.describe('Navigation Flows - Deep Linking', () => {
  const mockProjectId = 'test-project-123'
  const mockDeviceId = 'test-device-456'
  const mockBlockId = 'test-block-789'

  test('should handle deep links to project sub-pages without console errors', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    // Test direct navigation to deeply nested project pages
    const deepPages = [
      `/projects/${mockProjectId}/device-details/single/${mockDeviceId}`,
      `/projects/${mockProjectId}/gis/pv-dc-combiner/${mockBlockId}`,
      `/projects/${mockProjectId}/device-details/tracker-row/${mockDeviceId}`,
    ]

    for (const pagePath of deepPages) {
      await page.goto(pagePath)
      // Should either load the page or redirect to an appropriate location
      await expect(page.locator('body')).toBeVisible()
      await page.waitForLoadState('networkidle')
    }

    // Check for console errors across all deep link navigations
    expectNoConsoleErrors(consoleErrors)
  })

  test('should handle deep links to onboarding pages without console errors', async ({
    pageWithConsoleTracking: page,
    consoleErrors,
  }) => {
    // Test direct navigation to onboarding pages
    const onboardingPages = [
      `/onboarding/create-pv-system/${mockProjectId}`,
      `/onboarding/upload-gis-data/${mockProjectId}`,
      `/onboarding/${mockProjectId}/device-types/inverters`,
    ]

    for (const pagePath of onboardingPages) {
      await page.goto(pagePath)
      await expect(page.locator('body')).toBeVisible()
      await page.waitForLoadState('networkidle')
    }

    // Check for console errors across all onboarding navigations
    expectNoConsoleErrors(consoleErrors)
  })
})
