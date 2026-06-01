import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import type * as Plotly from 'plotly.js'

dayjs.extend(utc)
dayjs.extend(timezone)

type BudgetedPowerRow = {
  time: string
  poi_ac_power: number
}

type CumulativePerformanceSummary = {
  actual: number
  budgeted: number
  percent: number
  isExceeded: boolean
}

/** Hour-of-day (0–23) → average budgeted MW for overlay traces. */
export function buildHourlyBudgetedAverages(
  anchorDay: dayjs.Dayjs,
  comparisonMode: '15days' | 'dayof',
  budgetRows: BudgetedPowerRow[],
  timeZone: string,
  cod: string | null | undefined,
  degradationRate: number,
): Record<number, number> | null {
  if (!budgetRows.length) {
    return null
  }
  let filteredData = budgetRows
  if (comparisonMode === 'dayof') {
    const selectedMonthDay = anchorDay.format('MM-DD')
    filteredData = budgetRows.filter((dataPoint) => {
      const timestamp = dayjs.utc(dataPoint.time).tz(timeZone)
      return timestamp.format('MM-DD') === selectedMonthDay
    })
  }
  if (filteredData.length === 0) {
    return null
  }
  const hourlyAverages: Record<number, number[]> = {}
  filteredData.forEach((dataPoint) => {
    const timestamp = dayjs.utc(dataPoint.time).tz(timeZone)
    const hour = timestamp.hour()
    if (!hourlyAverages[hour]) {
      hourlyAverages[hour] = []
    }
    let degradedPower = dataPoint.poi_ac_power
    if (cod) {
      const codDate = dayjs(cod)
      const yearsSinceCOD = anchorDay.diff(codDate, 'year', true)
      const degradationFactor = 1 - (degradationRate / 100) * yearsSinceCOD
      degradedPower = dataPoint.poi_ac_power * Math.max(0, degradationFactor)
    }
    hourlyAverages[hour].push(degradedPower)
  })
  const result: Record<number, number> = {}
  Object.keys(hourlyAverages).forEach((hour) => {
    const hourNum = parseInt(hour, 10)
    const values = hourlyAverages[hourNum]
    result[hourNum] = values.reduce((sum, val) => sum + val, 0) / values.length
  })
  return result
}

/** Actual vs budgeted from cumulative energy chart traces. */
export function computeCumulativePerformanceSummary(
  energyChartData: Partial<Plotly.Data>[],
  energyView: string,
): CumulativePerformanceSummary | null {
  if (!energyChartData.length || energyView !== 'cumulative') {
    return null
  }

  const actualTrace = energyChartData.find(
    (trace: Partial<Plotly.Data>) => trace.name === 'Actual',
  )
  const budgetedTrace = energyChartData.find(
    (trace: Partial<Plotly.Data>) => trace.name === 'Budgeted',
  )

  if (!actualTrace || !budgetedTrace) {
    return null
  }

  const actualY = (actualTrace as { y?: unknown[] }).y
  const budgetedY = (budgetedTrace as { y?: unknown[] }).y

  if (
    !Array.isArray(actualY) ||
    !Array.isArray(budgetedY) ||
    actualY.length === 0 ||
    budgetedY.length === 0
  ) {
    return null
  }

  const actualFinal = actualY[actualY.length - 1] as number
  const budgetedFinal = budgetedY[budgetedY.length - 1] as number

  if (!actualFinal || !budgetedFinal || budgetedFinal === 0) {
    return null
  }

  const performancePercent =
    ((actualFinal - budgetedFinal) / budgetedFinal) * 100
  const isExceeded = performancePercent > 0

  return {
    actual: actualFinal,
    budgeted: budgetedFinal,
    percent: Math.abs(performancePercent),
    isExceeded,
  }
}
