import * as icons from '@tabler/icons-react'
import React from 'react'

type Link = {
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
  requiresQualityIntegration?: boolean
  requiresDroneIntegration?: boolean
  requiresQSEIntegration?: boolean
  underDevelopment?: boolean
  userTypeRequired?: string
}

export type DropdownLink = {
  icon: React.ElementType
  label: string
  to?: string | ((arg: string) => string)
  requiresEventIntegration?: boolean
  requiresReportIntegration?: boolean
  requiresQualityIntegration?: boolean
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
  {
    to: (projectId: string) => `/projects/${projectId}`,
    label: 'Home',
    icon: icons.IconHome,
  },
  // {
  //   link: (projectId: string) => `/projects/${projectId}/single-line`,
  //   label: "Single Line",
  //   icon: icons.IconCircuitCellPlus,
  //   underDevelopment: true,
  // },
  {
    to: (projectId: string) => `/projects/${projectId}/custom-dash`,
    label: 'Custom Dashboards',
    icon: icons.IconLayoutDashboard,
    requiresPV: true,
  },
  {
    to: (projectId: string) => `/projects/${projectId}/real-time`,
    label: 'Real Time',
    icon: icons.IconClock,
    requiresRealTimeData: true,
  },
  {
    label: 'Current Day',
    icon: icons.IconCalendarEvent,
    links: [
      {
        to: (projectId: string) => `/projects/${projectId}/equipment-analysis`,
        label: 'Devices',
      },
      {
        to: (projectId: string) =>
          `/projects/${projectId}/device-details/data-availability`,
        label: 'Data Availability',
        requiresRealTimeData: true,
      },
    ],
  },
  {
    label: 'Historic',
    icon: icons.IconHistory,
    links: [
      {
        to: (projectId: string) =>
          `/projects/${projectId}/device-details/horizontal/bess`,
        label: 'BESS',
        requiresBESS: true,
      },
      {
        to: (projectId: string) =>
          `/projects/${projectId}/device-details/horizontal/pv`,
        label: 'PV',
        requiresPV: true,
      },
      {
        to: (projectId: string) => `/projects/${projectId}/battery-health`,
        label: 'Battery Health',
        requiresBESS: true,
      },
      {
        to: (projectId: string) => `/projects/${projectId}/bess-operation`,
        label: 'BESS Operation',
        requiresBESS: true,
      },
      {
        to: (projectId: string) => `/projects/${projectId}/energy-waterfall`,
        label: 'Energy Waterfall',
        requiresBESS: true,
      },
      {
        to: (projectId: string) => `/projects/${projectId}/events/uptime`,
        label: 'Uptime',
      },
      {
        to: (projectId: string) =>
          `/projects/${projectId}/events/meta-analysis`,
        label: 'Events Meta-Analysis',
      },
      {
        to: (projectId: string) => `/projects/${projectId}/reports`,
        label: 'Reports',
        requiresReportIntegration: true,
      },
    ],
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
    to: (projectId: string) => `/projects/${projectId}/contracts`,
    label: 'Contracts',
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
    ],
  },
  {
    to: (projectId: string) => `/projects/${projectId}/data-browsing`,
    label: 'Data Browsing',
    icon: icons.IconDatabaseSearch,
  },
  {
    label: 'Maintenance',
    icon: icons.IconTool,
    links: [
      {
        to: (projectId: string) => `/projects/${projectId}/cmms/ticket-display`,
        label: 'CMMS',
      },
      {
        to: (projectId: string) => `/projects/${projectId}/drone-inspections`,
        label: 'Drone Inspections',
        requiresDroneIntegration: true,
      },
      {
        to: (projectId: string) =>
          `/projects/${projectId}/maintenance/spare-parts`,
        label: 'Spare Parts',
      },
    ],
  },
  {
    to: (projectId: string) => `/projects/${projectId}/loss-waterfall`,
    label: 'Loss Waterfall',
    icon: icons.IconBucketDroplet,
    underDevelopment: true,
  },
  {
    to: (projectId: string) => `/projects/${projectId}/quality`,
    label: 'Quality',
    icon: icons.IconHexagonLetterQFilled,
    requiresQualityIntegration: true,
  },
  {
    label: 'Administrative',
    icon: icons.IconSettings,
    links: [
      {
        to: (projectId: string) => `/projects/${projectId}/calendar`,
        label: 'Calendar',
      },
      {
        to: (projectId: string) => `/projects/${projectId}/settings`,
        label: 'Settings',
      },
    ],
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
        to: (projectId: string) => `/projects/${projectId}/utility/backfill`,
        label: 'Backfill',
      },
      {
        to: (projectId: string) =>
          `/projects/${projectId}/utility/project-tag-explorer`,
        label: 'Tag Explorer',
      },
      {
        to: (projectId: string) =>
          `/projects/${projectId}/utility/company-view`,
        label: 'Company View',
      },
    ],
  },
  // {
  //   link: (projectId: string) => `/projects/${projectId}/availability-analysis`,
  //   label: "Availability Analysis",
  //   icon: icons.IconClockHour5,
  //   underDevelopment: true,
  // },
  // {
  //   link: (projectId: string) => `/projects/${projectId}/data`,
  //   label: "Data",
  //   icon: icons.IconChartAreaLineFilled,
  // },
  // {
  //   link: (projectId: string) => `/projects/${projectId}/capacity`,
  //   label: "Capacity",
  //   icon: icons.IconBattery3,
  //   bessOnly: true,
  // },
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
