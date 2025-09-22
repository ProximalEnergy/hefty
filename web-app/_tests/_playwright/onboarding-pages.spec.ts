import { expect, test } from '@playwright/test'

test.describe('Onboarding Pages - Smoke Tests', () => {
  const mockProjectId = 'test-project-123'

  const onboardingPages = [
    {
      name: 'Create PV System Definition',
      path: `/onboarding/create-pv-system/${mockProjectId}`,
    },
    {
      name: 'Upload GIS Data',
      path: `/onboarding/upload-gis-data/${mockProjectId}`,
    },
    {
      name: 'Onboarding Devices',
      path: `/onboarding/${mockProjectId}/devices`,
    },
  ]

  for (const page of onboardingPages) {
    test(`should load ${page.name} page`, async ({ page: testPage }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(
        new RegExp(page.path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')),
      )
    })
  }
})

test.describe('Onboarding Device Types Pages - Smoke Tests', () => {
  const mockProjectId = 'test-project-123'

  const deviceTypePages = [
    {
      name: 'Met Stations',
      path: `/onboarding/${mockProjectId}/device-types/met-stations`,
    },
    {
      name: 'Transformers',
      path: `/onboarding/${mockProjectId}/device-types/transformers`,
    },
    {
      name: 'Inverters',
      path: `/onboarding/${mockProjectId}/device-types/inverters`,
    },
    {
      name: 'Combiners',
      path: `/onboarding/${mockProjectId}/device-types/combiners`,
    },
    {
      name: 'Trackers',
      path: `/onboarding/${mockProjectId}/device-types/trackers`,
    },
  ]

  for (const page of deviceTypePages) {
    test(`should load ${page.name} page`, async ({ page: testPage }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(
        new RegExp(page.path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')),
      )
    })
  }
})
