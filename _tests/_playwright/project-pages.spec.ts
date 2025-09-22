import { expect, test } from '@playwright/test'

test.describe('Project Pages - Smoke Tests', () => {
  // Using a mock project ID for testing
  const mockProjectId = 'test-project-123'

  const projectPages = [
    { name: 'Project Home', path: `/projects/${mockProjectId}` },
    { name: 'Real Time', path: `/projects/${mockProjectId}/real-time` },
    {
      name: 'Battery Health',
      path: `/projects/${mockProjectId}/battery-health`,
    },
    { name: 'Data Browsing', path: `/projects/${mockProjectId}/data-browsing` },
    {
      name: 'Drone Inspections',
      path: `/projects/${mockProjectId}/drone-inspections`,
    },
    { name: 'Project Settings', path: `/projects/${mockProjectId}/settings` },
    { name: 'Project Admin', path: `/projects/${mockProjectId}/admin` },
    { name: 'Project Calendar', path: `/projects/${mockProjectId}/calendar` },
    {
      name: 'Loss Waterfall',
      path: `/projects/${mockProjectId}/loss-waterfall`,
    },
    {
      name: 'Availability Analysis',
      path: `/projects/${mockProjectId}/availability-analysis`,
    },
  ]

  for (const page of projectPages) {
    test(`should load ${page.name} page`, async ({ page: testPage }) => {
      await testPage.goto(page.path)
      // Note: These pages may redirect if project doesn't exist
      // In a real test environment, you'd want to create test data first
      await expect(testPage).toHaveURL(
        new RegExp(page.path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')),
      )
    })
  }
})

test.describe('Project GIS Pages - Smoke Tests', () => {
  const mockProjectId = 'test-project-123'
  const mockBlockId = 'test-block-456'

  const gisPages = [
    {
      name: 'BESS Enclosure GIS',
      path: `/projects/${mockProjectId}/gis/bess-enclosure`,
    },
    {
      name: 'PV DC Combiner GIS',
      path: `/projects/${mockProjectId}/gis/pv-dc-combiner`,
    },
    {
      name: 'PV DC Combiner Block GIS',
      path: `/projects/${mockProjectId}/gis/pv-dc-combiner/${mockBlockId}`,
    },
    { name: 'PCS GIS', path: `/projects/${mockProjectId}/gis/pv-pcs` },
    { name: 'Tracker GIS', path: `/projects/${mockProjectId}/gis/tracker` },
    {
      name: 'Tracker Block GIS',
      path: `/projects/${mockProjectId}/gis/tracker/${mockBlockId}`,
    },
  ]

  for (const page of gisPages) {
    test(`should load ${page.name} page`, async ({ page: testPage }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(
        new RegExp(page.path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')),
      )
    })
  }
})

test.describe('Project Equipment Analysis Pages - Smoke Tests', () => {
  const mockProjectId = 'test-project-123'

  const equipmentPages = [
    {
      name: 'Equipment Analysis Home',
      path: `/projects/${mockProjectId}/equipment-analysis`,
    },
    {
      name: 'Equipment Analysis PV DC Combiner Block',
      path: `/projects/${mockProjectId}/equipment-analysis/pv-dc-combiner/block`,
    },
    {
      name: 'Equipment Analysis Tracker Block',
      path: `/projects/${mockProjectId}/equipment-analysis/tracker/block`,
    },
  ]

  for (const page of equipmentPages) {
    test(`should load ${page.name} page`, async ({ page: testPage }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(
        new RegExp(page.path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')),
      )
    })
  }
})

test.describe('Project Device Details Pages - Smoke Tests', () => {
  const mockProjectId = 'test-project-123'
  const mockDeviceId = 'test-device-789'

  const devicePages = [
    {
      name: 'Data Availability',
      path: `/projects/${mockProjectId}/device-details/data-availability`,
    },
    {
      name: 'Device Details BESS Horizontal',
      path: `/projects/${mockProjectId}/device-details/horizontal/bess`,
    },
    {
      name: 'Device Details PV Horizontal',
      path: `/projects/${mockProjectId}/device-details/horizontal/pv`,
    },
    {
      name: 'Device Details Single',
      path: `/projects/${mockProjectId}/device-details/single/${mockDeviceId}`,
    },
    {
      name: 'Vertical Device Details',
      path: `/projects/${mockProjectId}/device-details/vertical`,
    },
    {
      name: 'Tracker Row Detail',
      path: `/projects/${mockProjectId}/device-details/tracker-row/${mockDeviceId}`,
    },
  ]

  for (const page of devicePages) {
    test(`should load ${page.name} page`, async ({ page: testPage }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(
        new RegExp(page.path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')),
      )
    })
  }
})

test.describe('Project Events Pages - Smoke Tests', () => {
  const mockProjectId = 'test-project-123'

  const eventsPages = [
    { name: 'Project Events', path: `/projects/${mockProjectId}/events` },
    { name: 'Event Page', path: `/projects/${mockProjectId}/events/event` },
    { name: 'Uptime Table', path: `/projects/${mockProjectId}/events/uptime` },
    {
      name: 'Events Meta Analysis',
      path: `/projects/${mockProjectId}/events/meta-analysis`,
    },
  ]

  for (const page of eventsPages) {
    test(`should load ${page.name} page`, async ({ page: testPage }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(
        new RegExp(page.path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')),
      )
    })
  }
})

test.describe('Project CMMS & Maintenance Pages - Smoke Tests', () => {
  const mockProjectId = 'test-project-123'

  const cmmsPages = [
    {
      name: 'Ticket Display',
      path: `/projects/${mockProjectId}/cmms/ticket-display`,
    },
    {
      name: 'Spare Parts',
      path: `/projects/${mockProjectId}/maintenance/spare-parts`,
    },
  ]

  for (const page of cmmsPages) {
    test(`should load ${page.name} page`, async ({ page: testPage }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(
        new RegExp(page.path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')),
      )
    })
  }
})

test.describe('Project KPI Pages - Smoke Tests', () => {
  const mockProjectId = 'test-project-123'
  const mockNameShort = 'test-contract'
  const mockKpiTypeId = 'test-kpi-type-123'

  const kpiPages = [
    { name: 'Project KPI Home', path: `/projects/${mockProjectId}/kpis` },
    {
      name: 'Project KPI Alerts',
      path: `/projects/${mockProjectId}/kpis/alerts`,
    },
    {
      name: 'Project KPI Contractual',
      path: `/projects/${mockProjectId}/kpis/contractual/${mockNameShort}`,
    },
    {
      name: 'Project KPI Template',
      path: `/projects/${mockProjectId}/kpis/type/${mockKpiTypeId}`,
    },
  ]

  for (const page of kpiPages) {
    test(`should load ${page.name} page`, async ({ page: testPage }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(
        new RegExp(page.path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')),
      )
    })
  }
})

test.describe('Project Reports Pages - Smoke Tests', () => {
  const mockProjectId = 'test-project-123'

  const reportsPages = [
    { name: 'Project Reports', path: `/projects/${mockProjectId}/reports` },
    {
      name: 'DC Amperage Report',
      path: `/projects/${mockProjectId}/reports/dc-amperage`,
    },
    {
      name: 'Module Degradation Report',
      path: `/projects/${mockProjectId}/reports/module-degradation`,
    },
    {
      name: 'Tracker Availability Report',
      path: `/projects/${mockProjectId}/reports/tracker-availability`,
    },
    {
      name: 'Inverter Availability Report',
      path: `/projects/${mockProjectId}/reports/inverter-availability`,
    },
    {
      name: 'PCS Apparent vs Voltage Report',
      path: `/projects/${mockProjectId}/reports/pcs-apparent-vs-voltage`,
    },
    {
      name: 'Custom Report',
      path: `/projects/${mockProjectId}/reports/custom`,
    },
  ]

  for (const page of reportsPages) {
    test(`should load ${page.name} page`, async ({ page: testPage }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(
        new RegExp(page.path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')),
      )
    })
  }
})

test.describe('Project Contracts Pages - Smoke Tests', () => {
  const mockProjectId = 'test-project-123'
  const mockContractId = 'test-contract-456'

  const contractPages = [
    { name: 'Project Contracts', path: `/projects/${mockProjectId}/contracts` },
    {
      name: 'Project Contract Detail',
      path: `/projects/${mockProjectId}/contracts/${mockContractId}`,
    },
  ]

  for (const page of contractPages) {
    test(`should load ${page.name} page`, async ({ page: testPage }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(
        new RegExp(page.path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')),
      )
    })
  }
})

test.describe('Project Quality Pages - Smoke Tests', () => {
  const mockProjectId = 'test-project-123'

  const qualityPages = [
    { name: 'Quality Home', path: `/projects/${mockProjectId}/quality` },
    {
      name: 'Inspections',
      path: `/projects/${mockProjectId}/quality/inspections`,
    },
    {
      name: 'Inspections GIS',
      path: `/projects/${mockProjectId}/quality/inspections/gis`,
    },
    {
      name: 'Observations',
      path: `/projects/${mockProjectId}/quality/observations`,
    },
    {
      name: 'Observations GIS',
      path: `/projects/${mockProjectId}/quality/observations/gis`,
    },
  ]

  for (const page of qualityPages) {
    test(`should load ${page.name} page`, async ({ page: testPage }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(
        new RegExp(page.path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')),
      )
    })
  }
})

test.describe('Project Utility Pages - Smoke Tests', () => {
  const mockProjectId = 'test-project-123'

  const utilityPages = [
    {
      name: 'Expected Plotting',
      path: `/projects/${mockProjectId}/utility/expected`,
    },
    { name: 'Backfill', path: `/projects/${mockProjectId}/utility/backfill` },
    {
      name: 'Project Tag Explorer',
      path: `/projects/${mockProjectId}/utility/project-tag-explorer`,
    },
  ]

  for (const page of utilityPages) {
    test(`should load ${page.name} page`, async ({ page: testPage }) => {
      await testPage.goto(page.path)
      await expect(testPage).toHaveURL(
        new RegExp(page.path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')),
      )
    })
  }
})
