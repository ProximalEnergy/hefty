import { expect, test } from '@playwright/test'

test.describe('Admin Pages - Smoke Tests', () => {
  const adminPages = [
    { name: 'User Management', path: '/admin/users' },
    { name: 'Sensor Types', path: '/admin/sensor-types' },
    { name: 'Drone Integrations', path: '/admin/drone-integrations' },
    { name: 'Drone Providers', path: '/admin/drone-providers' },
    { name: 'Drone Permissions', path: '/admin/drone-permissions' },
  ]

  for (const page of adminPages) {
    test(`should load ${page.name} page`, async ({ page: testPage }) => {
      await testPage.goto(page.path)
      // Note: These pages require admin permissions and may redirect
      // if the user doesn't have the required permissions
      await expect(testPage).toHaveURL(
        new RegExp(page.path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')),
      )
    })
  }
})

test.describe('Development Resource Pages - Smoke Tests', () => {
  const mockResourceId = 'test-resource-123'

  const resourcePages = [
    {
      name: 'Development Resource Detail',
      path: `/development/resources/${mockResourceId}`,
    },
  ]

  for (const page of resourcePages) {
    test(`should load ${page.name} page`, async ({ page: testPage }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(
        new RegExp(page.path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')),
      )
    })
  }
})
