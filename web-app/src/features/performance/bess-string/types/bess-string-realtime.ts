export type StatsData = {
  poiPowerMW: string | null
  poiPowerTimestamp: string | null
  poiPowerStatus: 'Charging' | 'Discharging' | 'Idling' | null
  cumulativeStringPowerMW: string
  cumulativeStringPowerTimestamp: string | null
  cumulativeStringPowerFreshnessTier: 'fresh' | 'delayed' | 'stale' | 'missing'
  stringPowerIncludedCount: number
  stringPowerTotalCount: number
  totalEventsCount: number
  dailyRevenueLoss: string
  dailyEventLossEnergyMWh: number
  openCMMSTickets: number
  cmmsHoverTickets: CMMSTicketHoverItem[]
  staleDeviceIds: number[]
  staleDeviceNames: string[]
  staleDevicesCount: number
  isCharging: boolean
  isDischarging: boolean
  balanceScoreOverallPct: number | null
  balanceScoreSystemPct: number | null
  balanceScoreIntraPcsPct: number | null
}

export type ActiveEventsHoverSection = {
  label: string
  count: number
  events: Array<{
    eventId: number
    label: string
  }>
  remainingCount: number
}

export type CMMSTicketHoverItem = {
  key: string
  summary: string
  status?: string
}

export type NextMaintenanceData = {
  formattedDate: string
  calendarItemId: string
  occurrenceDateStr: string
  scopeLabel: string
  hoverContent: {
    title: string
    description?: string
    assignees?: string
  }
}
