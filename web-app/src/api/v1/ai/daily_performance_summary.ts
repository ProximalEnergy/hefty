interface EventData {
  device_type_name: string
  count: number
  revenue_loss: number
  status: string // 'open' or 'closed'
}

export interface DailyPerformanceStats {
  project_name: string
  date: string
  actual_energy_mwh: number
  budgeted_energy_mwh: number
  energy_difference_mwh: number
  energy_performance_percent: number
  trailing_30_day_actual: number
  trailing_30_day_budgeted: number
  trailing_30_day_difference: number
  trailing_30_day_performance_percent: number
  // Revenue data
  daily_revenue: number
  mtd_revenue: number
  // Events data
  events: EventData[]
  total_events: number
  open_events: number
  closed_events: number
  total_revenue_loss: number
}

export interface DailyPerformanceSummaryRequest {
  stats: DailyPerformanceStats
  model?: string
}

export interface DailyPerformanceSummaryResponse {
  summary: string
}
