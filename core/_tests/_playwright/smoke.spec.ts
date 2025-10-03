import { expect, expectNoConsoleErrors, test } from '../fixtures'

test.describe('Smoke tests - Public Pages', () => {
  const publicPages = [
    { name: 'Home', path: '/' },
    { name: 'Sign In', path: '/sign-in' },
  ]

  for (const page of publicPages) {
    test(`should load ${page.name} page without console errors`, async ({
      pageWithConsoleTracking: testPage,
      consoleErrors,
    }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(page.path)

      // Wait for page to fully load
      await testPage.waitForLoadState('networkidle')

      // Check for console errors
      expectNoConsoleErrors(consoleErrors)
    })
  }
})

test.describe('Smoke tests - Account Pages', () => {
  const accountPages = [{ name: 'Account Settings', path: '/account-settings' }]

  for (const page of accountPages) {
    test(`should load ${page.name} page without console errors`, async ({
      pageWithConsoleTracking: testPage,
      consoleErrors,
    }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(page.path)

      // Wait for page to fully load
      await testPage.waitForLoadState('networkidle')

      // Check for console errors
      expectNoConsoleErrors(consoleErrors)
    })
  }
})

test.describe('Smoke tests - Portfolio Pages', () => {
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
    test(`should load ${page.name} page without console errors`, async ({
      pageWithConsoleTracking: testPage,
      consoleErrors,
    }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(page.path)

      // Wait for page to fully load
      await testPage.waitForLoadState('networkidle')

      // Check for console errors
      expectNoConsoleErrors(consoleErrors)
    })
  }
})

test.describe('Smoke tests - Development Pages', () => {
  const developmentPages = [
    { name: 'Development Home (ERCOT Map)', path: '/development' },
    { name: 'Development Resources', path: '/development/resources' },
    { name: 'Development Prices', path: '/development/prices' },
  ]

  for (const page of developmentPages) {
    test(`should load ${page.name} page without console errors`, async ({
      pageWithConsoleTracking: testPage,
      consoleErrors,
    }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(page.path)

      // Wait for page to fully load
      await testPage.waitForLoadState('networkidle')

      // Check for console errors
      expectNoConsoleErrors(consoleErrors)
    })
  }
})

test.describe('Smoke tests - Admin & Application Pages', () => {
  const adminPages = [
    { name: 'Application Settings', path: '/application-settings' },
    { name: 'API', path: '/api' },
    { name: 'Loom Testing', path: '/loom-testing' },
  ]

  for (const page of adminPages) {
    test(`should load ${page.name} page without console errors`, async ({
      pageWithConsoleTracking: testPage,
      consoleErrors,
    }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(page.path)

      // Wait for page to fully load
      await testPage.waitForLoadState('networkidle')

      // Check for console errors
      expectNoConsoleErrors(consoleErrors)
    })
  }
})

// Note: The following pages require project IDs and would need to be tested
// with actual project data or mocked data in separate test files:

// Project-specific pages (require projectId parameter):
// - /projects/:projectId - Project Home
// - /projects/:projectId/real-time - Real Time
// - /projects/:projectId/battery-health - Battery Health
// - /projects/:projectId/gis/* - GIS pages
// - /projects/:projectId/equipment-analysis/* - Equipment Analysis
// - /projects/:projectId/device-details/* - Device Details
// - /projects/:projectId/events/* - Events
// - /projects/:projectId/cmms/* - CMMS
// - /projects/:projectId/maintenance/* - Maintenance
// - /projects/:projectId/kpis/* - Project KPIs
// - /projects/:projectId/reports/* - Reports
// - /projects/:projectId/contracts/* - Contracts
// - /projects/:projectId/drone-inspections - Drone Inspections
// - /projects/:projectId/data-browsing - Data Browsing
// - /projects/:projectId/quality/* - Quality pages
// - /projects/:projectId/settings - Project Settings
// - /projects/:projectId/admin - Project Admin
// - /projects/:projectId/calendar - Project Calendar
// - /projects/:projectId/utility/* - Utility pages
// - /projects/:projectId/loss-waterfall - Loss Waterfall
// - /projects/:projectId/availability-analysis - Availability Analysis

// Onboarding pages (require projectId parameter):
// - /onboarding/create-pv-system/:projectId
// - /onboarding/upload-gis-data/:projectId
// - /onboarding/:projectId/devices
// - /onboarding/:projectId/device-types/*

// Admin pages (require admin permissions):
// - /admin/users - User Management
// - /admin/sensor-types - Sensor Types
// - /admin/drone-integrations - Drone Integrations
// - /admin/drone-providers - Drone Providers
// - /admin/drone-permissions - Drone Permissions

// Development resource pages (require resourceId parameter):
// - /development/resources/:resourceId
