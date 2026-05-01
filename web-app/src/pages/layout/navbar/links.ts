import * as icons from '@tabler/icons-react'
import React from 'react'

export type Link = {
  label: string
  to: string | ((arg: string) => string)
  requiresPV?: boolean
  requiresBESS?: boolean
  requiresMetStations?: boolean
  requiresPVDCCombiners?: boolean
  requiresTrackers?: boolean
  requiresBESSBlocks?: boolean
  requiresBESSEnclosures?: boolean
  requiresBESSPCSs?: boolean
  requiresRealTimeData?: boolean
  requiresEventIntegration?: boolean
  requiresReportIntegration?: boolean
  requiresDroneIntegration?: boolean
  requiresQSEIntegration?: boolean
  underDevelopment?: boolean
  userTypeRequired?: string
  tooltip?: string
}

export type DropdownLink = {
  icon: React.ElementType
  label: string
  to?: string | ((arg: string) => string)
  requiresEventIntegration?: boolean
  requiresReportIntegration?: boolean
  requiresRealTimeData?: boolean
  requiresDroneIntegration?: boolean
  requiresPV?: boolean
  requiresQSEIntegration?: boolean
  links?: Link[]
  underDevelopment?: boolean
  userTypeRequired?: string
  dropdownBehavior?: 'full' | 'arrow-only'
}

export const portfolioLinks: DropdownLink[] = [
  {
    to: '/portfolio',
    label: 'Home',
    icon: icons.IconHome,
  },
  {
    to: '/portfolio/list',
    label: 'List',
    icon: icons.IconList,
  },
  {
    to: '/portfolio/map',
    label: 'Map',
    icon: icons.IconMap,
  },
  {
    to: '/portfolio/kpis',
    label: 'KPIs',
    icon: icons.IconChartLine,
  },
  {
    label: 'Administrative',
    icon: icons.IconSettings,
    links: [
      {
        to: '/portfolio/calendar',
        label: 'Calendar',
      },
      {
        to: '/portfolio/settings',
        label: 'Settings',
      },
    ],
  },
]

export const projectLinks: DropdownLink[] = [
  // Home is handled separately via HomeLinkWithDashboards component
  {
    to: (projectId: string) =>
      `/projects/${projectId}/device-details/horizontal/pv`, // Will be overridden in NavbarNested based on project type
    label: 'StackTrace',
    icon: icons.IconStackMiddle,
  },
  // Performance links are generated dynamically based on project.spec.used_device_type_ids
  {
    label: 'Performance',
    icon: icons.IconChartBar,
    links: [], // Will be populated dynamically in NavbarNested
  },
  {
    to: (projectId: string) => `/projects/${projectId}/events`,
    label: 'Events',
    icon: icons.IconExclamationCircle,
    requiresEventIntegration: true,
  },
  {
    to: (projectId: string) => `/projects/${projectId}/kpis`,
    label: 'KPIs',
    icon: icons.IconChartLine,
  },
  {
    to: (projectId: string) => `/projects/${projectId}/contracts/`,
    label: 'Contracts',
    icon: icons.IconContract,
  },
  {
    to: (projectId: string) => `/projects/${projectId}/reports`,
    label: 'Reports',
    icon: icons.IconFileText,
  },
  {
    label: 'Finances',
    icon: icons.IconCurrencyDollar,
    requiresQSEIntegration: true,
    links: [
      {
        to: (projectId: string) =>
          `/projects/${projectId}/finances/battery-settlement`,
        label: 'Battery Settlement',
      },
      {
        to: (projectId: string) =>
          `/projects/${projectId}/finances/market-performance`,
        label: 'Market Performance',
      },
      {
        to: (projectId: string) => `/projects/${projectId}/finances/ptp-data`,
        label: 'PTP Data',
        userTypeRequired: 'superadmin',
      },
    ],
  },
  {
    label: 'Maintenance',
    icon: icons.IconTool,
    links: [
      {
        to: (projectId: string) => `/projects/${projectId}/cmms/ticket-display`,
        label: 'Tickets',
      },
      {
        to: (projectId: string) =>
          `/projects/${projectId}/maintenance/spare-parts`,
        label: 'Spare Parts',
      },
      {
        to: (projectId: string) => `/projects/${projectId}/drone-inspections`,
        label: 'Drone Inspections',
        requiresPV: true,
      },
      {
        to: (projectId: string) =>
          `/projects/${projectId}/maintenance/warranty-claims`,
        label: 'Warranty Claims',
      },
    ],
  },
  {
    to: (projectId: string) => `/projects/${projectId}/calendar`,
    label: 'Calendar',
    icon: icons.IconCalendar,
  },
  {
    to: (projectId: string) => `/projects/${projectId}/data-browsing`,
    label: 'Data Browsing',
    icon: icons.IconDatabaseSearch,
  },
  {
    to: (projectId: string) => `/projects/${projectId}/settings`,
    label: 'Settings',
    icon: icons.IconSettings,
  },
  {
    label: 'Other',
    icon: icons.IconDots,
    links: [
      {
        to: (projectId: string) =>
          `/projects/${projectId}/events/meta-analysis`,
        label: 'Events Meta Analysis',
        requiresEventIntegration: true,
      },
      {
        to: (projectId: string) => `/projects/${projectId}/events/uptime`,
        label: 'Uptime',
        requiresEventIntegration: true,
        requiresPV: true,
      },
      {
        to: (projectId: string) =>
          `/projects/${projectId}/device-details/data-availability`,
        label: 'Data Availability',
      },
      {
        to: (projectId: string) => `/projects/${projectId}/battery-health`,
        label: 'Battery Health',
        requiresBESS: true,
      },
      {
        to: (projectId: string) => `/projects/${projectId}/energy-waterfall`,
        label: 'BESS Energy Waterfall',
        requiresBESS: true,
      },
      {
        to: (projectId: string) => `/projects/${projectId}/bess-operation`,
        label: 'BESS Operations',
        requiresBESS: true,
      },
    ],
  },
  // Legacy/Development items kept for reference
  {
    to: (projectId: string) => `/projects/${projectId}/real-time`,
    label: 'Real Time',
    icon: icons.IconClock,
    requiresRealTimeData: true,
    underDevelopment: true,
  },
  {
    label: 'Superadmin Utility',
    icon: icons.IconEyeOff,
    userTypeRequired: 'superadmin',
    links: [
      {
        to: (projectId: string) => `/projects/${projectId}/utility/expected`,
        label: 'Expected Plotting',
      },
      {
        to: (projectId: string) =>
          `/projects/${projectId}/equipment-analysis/single-line-diagram`,
        label: 'Snapshot',
        requiresBESS: true,
      },
      {
        to: (projectId: string) => `/projects/${projectId}/utility/backfill`,
        label: 'Backfill',
      },
      {
        to: (projectId: string) =>
          `/projects/${projectId}/utility/project-tag-explorer`,
        label: 'Tag Explorer',
      },
    ],
  },
]

export const developmentLinks: DropdownLink[] = [
  {
    to: '/development',
    label: 'Map',
    icon: icons.IconMap,
  },
  {
    to: '/development/resources',
    label: 'Resources',
    icon: icons.IconChartTreemap,
  },
  {
    to: '/development/prices',
    label: 'Prices',
    icon: icons.IconLocationDollar,
  },
]
