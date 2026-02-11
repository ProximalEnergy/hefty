import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetBatterySettlementDetails } from '@/api/v1/protected/web-application/projects/financial/battery_settlement'
import { useGetPTPData } from '@/api/v1/protected/web-application/projects/financial/ptp_data'
import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import {
  Group,
  SegmentedControl,
  Skeleton,
  Text,
  Tooltip,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import dayjs from 'dayjs'
import advancedFormat from 'dayjs/plugin/advancedFormat'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import type { Layout, PlotData } from 'plotly.js'
import { useEffect, useMemo, useState } from 'react'

dayjs.extend(utc)
dayjs.extend(timezone)
dayjs.extend(advancedFormat)

type PlotTrace = Partial<PlotData> & {
  y?: Array<number | null>
  base?: Array<number | null>
}

interface MarketPricesPowerCardProps {
  projectId: string
  projectTimeZone?: string | null
  startDate?: Date | null
  endDate?: Date | null
  useCustomDateRange?: boolean // If true, use provided dates for data fetching
  highlightTodayRevenue?: boolean
  highlightRTPrice?: boolean
  currentRTPrice?: number | null
  highlightPower?: boolean
  currentPower?: number | null
  lastPowerTimestamp?: string | null
  highlightTimeRanges?: Array<{ start: string; end: string }>
}

export const MarketPricesPowerCard = ({
  projectId,
  projectTimeZone,
  startDate,
  endDate,
  useCustomDateRange = false,
  highlightTodayRevenue = false,
  highlightRTPrice = false,
  currentRTPrice = null,
  highlightPower = false,
  currentPower = null,
  lastPowerTimestamp = null,
  highlightTimeRanges,
}: MarketPricesPowerCardProps) => {
  const theme = useMantineTheme()
  const computedColorScheme = useComputedColorScheme('dark')
  const project = useSelectProject(projectId)
  const [pulseTick, setPulseTick] = useState(0)
  const [powerPulseTick, setPowerPulseTick] = useState(0)
  const [revenueViewMode, setRevenueViewMode] = useState<
    'cumulative' | 'grouped' | 'detailed' | 'rt-energy-x-rt-price'
  >('grouped')

  const pulseSize = useMemo(() => {
    if (!highlightRTPrice) {
      return 12
    }

    // Pulse between 12 and 18
    const min = 12
    const max = 18
    const range = max - min
    // Use sine wave for smooth pulsing
    const time = pulseTick / 32 // ~3.2s per full cycle at ~60fps
    const pulse = Math.sin(time) * (range / 2) + (min + max) / 2
    return pulse
  }, [highlightRTPrice, pulseTick])

  const powerPulseSize = useMemo(() => {
    if (!highlightPower) {
      return 12
    }

    // Pulse between 12 and 18
    const min = 12
    const max = 18
    const range = max - min
    // Use sine wave for smooth pulsing
    const time = powerPulseTick / 32 // ~3.2s per full cycle at ~60fps
    const pulse = Math.sin(time) * (range / 2) + (min + max) / 2
    return pulse
  }, [highlightPower, powerPulseTick])

  // Animate pulse when highlighting RT price
  useEffect(() => {
    if (!highlightRTPrice) return

    const interval = setInterval(() => {
      setPulseTick((t) => t + 1)
    }, 16) // ~60fps

    return () => clearInterval(interval)
  }, [highlightRTPrice])

  // Animate pulse when highlighting Power
  useEffect(() => {
    if (!highlightPower) return

    const interval = setInterval(() => {
      setPowerPulseTick((t) => t + 1)
    }, 16) // ~60fps

    return () => clearInterval(interval)
  }, [highlightPower])

  // Calculate data fetch date range: use provided dates if useCustomDateRange is true, otherwise use default
  const dataFetchRange = useMemo(() => {
    if (!projectTimeZone) {
      return { start: undefined, end: undefined }
    }

    // If useCustomDateRange is true and dates are provided, use them
    if (useCustomDateRange && startDate && endDate) {
      const tz = projectTimeZone
      // Convert Date objects to dayjs in UTC first, then to target timezone to avoid shifts
      const start = dayjs.utc(startDate).tz(tz).startOf('day')
      const end = dayjs.utc(endDate).tz(tz).endOf('day')
      // Expand range slightly to ensure we have data for the edges
      return {
        start: start.subtract(1, 'day').toISOString(),
        end: end.add(1, 'day').toISOString(),
      }
    }

    // Default: beginning of day before yesterday to end of tomorrow
    const tz = projectTimeZone
    const now = dayjs().tz(tz)
    const dayBeforeYesterdayStart = now.subtract(2, 'day').startOf('day')
    const tomorrowEnd = now.add(1, 'day').endOf('day')
    return {
      start: dayBeforeYesterdayStart.toISOString(),
      end: tomorrowEnd.toISOString(),
    }
  }, [projectTimeZone, startDate, endDate, useCustomDateRange])

  // Prepare date strings for battery settlement API (timezone-aware)
  const settlementStartRequest = useMemo(() => {
    if (!projectTimeZone || !dataFetchRange.start) return ''
    return dayjs(dataFetchRange.start).tz(projectTimeZone, true).toISOString()
  }, [dataFetchRange.start, projectTimeZone])

  const settlementEndRequest = useMemo(() => {
    if (!projectTimeZone || !dataFetchRange.end) return ''
    return dayjs(dataFetchRange.end).tz(projectTimeZone, true).toISOString()
  }, [dataFetchRange.end, projectTimeZone])

  const { data: marketPricesData, isLoading: marketPricesLoading } =
    useGetPTPData({
      pathParams: { projectId },
      queryParams: {
        endpoint: 'Market-Prices',
        category: 'market',
        start: dataFetchRange.start,
        end: dataFetchRange.end,
      },
      queryOptions: {
        enabled: !!projectId && !!dataFetchRange.start && !!dataFetchRange.end,
      },
    })

  const { data: powerData, isLoading: powerLoading } = useGetPTPData({
    pathParams: { projectId },
    queryParams: {
      endpoint: 'Real-Time-Unit-Position',
      category: 'analysis',
      start: dataFetchRange.start,
      end: dataFetchRange.end,
    },
    queryOptions: {
      enabled: !!projectId && !!dataFetchRange.start && !!dataFetchRange.end,
    },
  })

  const needsSettlementRevenue = revenueViewMode !== 'rt-energy-x-rt-price'

  // Fetch battery settlement details for revenue chart
  const { data: batterySettlementData, isLoading: settlementLoading } =
    useGetBatterySettlementDetails({
      pathParams: { projectId },
      queryParams: {
        start: settlementStartRequest,
        end: settlementEndRequest,
      },
      queryOptions: {
        enabled:
          !!projectId &&
          !!settlementStartRequest &&
          !!settlementEndRequest &&
          needsSettlementRevenue,
      },
    })

  // Transform power data for Plotly chart
  const powerPlotData: PlotTrace[] = useMemo(() => {
    if (!powerData?.data || powerData.data.length === 0) {
      return []
    }

    const element =
      powerData.data.find(
        (el) =>
          el.definition === 'Generator' &&
          el.dataPoints?.some((dp) => dp.keyName === 'GEN_Production'),
      ) || powerData.data[0]

    if (!element) {
      return []
    }

    const traces: PlotTrace[] = []

    element.dataPoints.forEach((dp) => {
      if (dp.keyName !== 'GEN_Production') return

      const x: string[] = []
      const y: (number | null)[] = []

      dp.values.forEach((v) => {
        const timestamp = dayjs
          .utc(v.intervalStartUtc)
          .tz(projectTimeZone || 'UTC')
          .format()
        x.push(timestamp)

        const valueStr = v.data[0]?.value
        const value =
          valueStr !== null && valueStr !== undefined
            ? parseFloat(String(valueStr))
            : null
        y.push(value)
      })

      traces.push({
        x,
        y,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Measured Power (MW)',
        fill: 'tozeroy',
        line: {
          width: 2,
          color: theme.colors.green[6],
        },
        marker: {
          size: 5,
          color: theme.colors.green[6],
        },
        yaxis: 'y2',
      } as PlotTrace)
    })

    return traces
  }, [powerData, projectTimeZone, theme])

  // Transform market prices data for Plotly chart
  const marketPricesPlotData: PlotTrace[] = useMemo(() => {
    if (!marketPricesData?.data || marketPricesData.data.length === 0) {
      return []
    }

    const settlementPointElement = marketPricesData.data.find(
      (el) =>
        el.definition === 'Settlement Point' &&
        el.dataPoints?.some(
          (dp) => dp.keyName === 'RTSPP' || dp.keyName === 'DASPP',
        ),
    )

    const element =
      settlementPointElement ||
      marketPricesData.data.find((el) =>
        el.dataPoints?.some(
          (dp) => dp.keyName === 'RTSPP' || dp.keyName === 'DASPP',
        ),
      ) ||
      marketPricesData.data[0]

    if (!element) {
      return []
    }

    const traces: PlotTrace[] = []

    element.dataPoints.forEach((dp) => {
      if (dp.keyName !== 'RTSPP' && dp.keyName !== 'DASPP') return

      const stepX: string[] = []
      const stepY: (number | null)[] = []

      dp.values.forEach((v) => {
        const value = v.data[0]?.value ?? null

        const startTimestamp = dayjs
          .utc(v.intervalStartUtc)
          .tz(projectTimeZone || 'UTC')
          .format()
        stepX.push(startTimestamp)
        stepY.push(value)

        if (v.intervalEndUtc) {
          const endTimestamp = dayjs
            .utc(v.intervalEndUtc)
            .tz(projectTimeZone || 'UTC')
            .format()
          stepX.push(endTimestamp)
          stepY.push(value)
        }
      })

      traces.push({
        x: stepX,
        y: stepY,
        type: 'scatter',
        mode: 'lines',
        name:
          dp.keyName === 'RTSPP'
            ? 'Real-Time Price (RTSPP) - 15min'
            : 'Day-Ahead Price (DASPP) - Hourly',
        line: {
          width: 2,
          shape: 'hv',
          color:
            dp.keyName === 'RTSPP'
              ? theme.colors.orange[6]
              : theme.colors.blue[6],
        },
      } as PlotTrace)
    })

    return traces
  }, [marketPricesData, projectTimeZone, theme])

  // Transform revenue data for stacked column chart (similar to RevenueBreakdownCard)
  const revenuePlotData: PlotTrace[] = useMemo(() => {
    if (revenueViewMode === 'rt-energy-x-rt-price') {
      if (!projectTimeZone) {
        return []
      }

      const priceElement =
        marketPricesData?.data?.find(
          (el) =>
            el.definition === 'Settlement Point' &&
            el.dataPoints?.some((dp) => dp.keyName === 'RTSPP'),
        ) ||
        marketPricesData?.data?.find((el) =>
          el.dataPoints?.some((dp) => dp.keyName === 'RTSPP'),
        ) ||
        marketPricesData?.data?.[0]

      const rtPriceDp = priceElement?.dataPoints?.find(
        (dp) => dp.keyName === 'RTSPP',
      )

      const rtPriceByStartUtc = new Map<string, number>()
      rtPriceDp?.values?.forEach((v) => {
        const ts = v.intervalStartUtc
        const raw = v.data?.[0]?.value
        const value =
          raw !== null && raw !== undefined ? parseFloat(String(raw)) : NaN
        if (ts && Number.isFinite(value)) {
          rtPriceByStartUtc.set(ts, value)
        }
      })

      const powerElement =
        powerData?.data?.find(
          (el) =>
            el.definition === 'Generator' &&
            el.dataPoints?.some((dp) => dp.keyName === 'GEN_Production'),
        ) || powerData?.data?.[0]
      const powerDp = powerElement?.dataPoints?.find(
        (dp) => dp.keyName === 'GEN_Production',
      )

      const hourlyRevenue = new Map<string, number>()
      powerDp?.values?.forEach((v) => {
        const ts = v.intervalStartUtc
        const rawMw = v.data?.[0]?.value
        const mw =
          rawMw !== null && rawMw !== undefined
            ? parseFloat(String(rawMw))
            : NaN
        if (!ts || !Number.isFinite(mw)) {
          return
        }

        const price = rtPriceByStartUtc.get(ts)
        if (price === undefined) {
          return
        }

        const intervalHours = (() => {
          if (!v.intervalEndUtc) {
            return 0.25
          }
          const start = dayjs.utc(v.intervalStartUtc)
          const end = dayjs.utc(v.intervalEndUtc)
          const hours = end.diff(start, 'minute') / 60
          return Number.isFinite(hours) && hours > 0 ? hours : 0.25
        })()

        const revenue = mw * intervalHours * price
        const hourKey = dayjs
          .utc(ts)
          .tz(projectTimeZone)
          .startOf('hour')
          .format()
        hourlyRevenue.set(hourKey, (hourlyRevenue.get(hourKey) ?? 0) + revenue)
      })

      let sortedHours = Array.from(hourlyRevenue.keys()).sort()
      if (useCustomDateRange && startDate && endDate && projectTimeZone) {
        const tz = projectTimeZone
        const rangeStart = dayjs.utc(startDate).tz(tz).startOf('day')
        const rangeEnd = dayjs.utc(endDate).tz(tz).endOf('day')
        sortedHours = sortedHours.filter((hour) => {
          const hourTime = dayjs(hour).tz(tz)
          const hourDate = hourTime.startOf('day')
          const startDateOnly = rangeStart.startOf('day')
          const endDateOnly = rangeEnd.startOf('day')
          return (
            (hourDate.isAfter(startDateOnly) ||
              hourDate.isSame(startDateOnly)) &&
            (hourDate.isBefore(endDateOnly) || hourDate.isSame(endDateOnly))
          )
        })
      }

      const todayStart = projectTimeZone
        ? dayjs().tz(projectTimeZone).startOf('day')
        : dayjs().startOf('day')
      const todayEnd = projectTimeZone
        ? dayjs().tz(projectTimeZone).endOf('day')
        : dayjs().endOf('day')

      const markerColors = sortedHours.map((hour) => {
        const hourTime = dayjs(hour).tz(projectTimeZone || 'UTC')
        const isToday =
          highlightTodayRevenue &&
          hourTime.isAfter(todayStart.subtract(1, 'second')) &&
          hourTime.isBefore(todayEnd.add(1, 'second'))
        if (highlightTodayRevenue && !isToday) {
          const hex = theme.colors.orange[6]
          const r = parseInt(hex.slice(1, 3), 16)
          const g = parseInt(hex.slice(3, 5), 16)
          const b = parseInt(hex.slice(5, 7), 16)
          return `rgba(${r}, ${g}, ${b}, 0.3)`
        }
        return theme.colors.orange[6]
      })

      const y = sortedHours.map((h) => hourlyRevenue.get(h) ?? 0)
      return [
        {
          x: sortedHours,
          y,
          base: sortedHours.map(() => 0),
          type: 'bar',
          name: 'RT Energy × RT Price (physical)',
          marker: { color: markerColors },
          hovertemplate:
            '<b>RT Energy × RT Price</b><br>%{x}: %{y:$,.2f}<extra></extra>',
          offset: 0,
          width: 3600000,
          yaxis: 'y3',
        } as PlotTrace,
      ]
    }

    if (
      !batterySettlementData?.qse_data?.data ||
      !batterySettlementData?.qse_data?.index
    ) {
      return []
    }

    const { data, index } = batterySettlementData.qse_data

    // Helper to find field by partial name match
    const findField = (partialName: string): (number | null)[] | undefined => {
      const key = Object.keys(data).find((k) =>
        k.toLowerCase().includes(partialName.toLowerCase()),
      )
      return key ? data[key] : undefined
    }

    // Find all revenue-related fields
    const daEnergyAmt =
      data['DA_Energy_Amt'] ||
      findField('DA_Energy_Amt') ||
      findField('Day-Ahead Energy Amount')
    const rtEnergyAmt =
      data['RT_Energy_Amt'] ||
      findField('RT_Energy_Amt') ||
      findField('Real-Time Energy Amount')
    const daRegUpAmt =
      data['DA_Reg_Up_Amt'] || findField('DA_Reg_Up') || findField('Reg_Up')
    const daRegDownAmt =
      data['DA_Reg_Down_Amt'] ||
      findField('DA_Reg_Down') ||
      findField('Reg_Down')
    const daRRSAmt =
      data['DA_RRS_Amt'] || findField('DA_RRS') || findField('RRS')
    const daNSAmt =
      data['DA_NS_Amt'] || findField('DA_NS') || findField('Non-Spin')
    const daECRSAmt =
      data['DA_ECRS_Amt'] || findField('DA_ECRS') || findField('ECRS')
    const rtAncillaryImb =
      data['RT_Ancillary_Imbalance_Amt'] ||
      findField('RT_Ancillary_Imbalance') ||
      findField('Ancillary Imbalance')
    const rtReliabilityImb =
      data['RT_Reliability_Deployment_Imbalance_Amt'] ||
      findField('RT_Reliability') ||
      findField('Reliability Deployment')
    const bpDevAmt =
      data['BP_Dev_Amt'] ||
      findField('BP_Dev') ||
      findField('Base Point Deviation')

    // Group data by hour
    const hourlyData = new Map<
      string,
      {
        daEnergy: number
        rtEnergy: number
        ancillaryServices: number
        penalties: number
        // Individual breakdown components
        regUp: number
        regDown: number
        rrs: number
        nonSpin: number
        ecrs: number
        rtAncillaryImb: number
        rtReliabilityImb: number
        bpDev: number
      }
    >()

    index.forEach((timestampStr, idx) => {
      const timestamp = dayjs(timestampStr).tz(projectTimeZone || 'UTC')
      const hourKey = timestamp.startOf('hour').format()

      if (!hourlyData.has(hourKey)) {
        hourlyData.set(hourKey, {
          daEnergy: 0,
          rtEnergy: 0,
          ancillaryServices: 0,
          penalties: 0,
          regUp: 0,
          regDown: 0,
          rrs: 0,
          nonSpin: 0,
          ecrs: 0,
          rtAncillaryImb: 0,
          rtReliabilityImb: 0,
          bpDev: 0,
        })
      }

      const hourData = hourlyData.get(hourKey)!

      if (
        daEnergyAmt &&
        daEnergyAmt[idx] !== null &&
        daEnergyAmt[idx] !== undefined
      ) {
        hourData.daEnergy += daEnergyAmt[idx] || 0
      }
      if (
        rtEnergyAmt &&
        rtEnergyAmt[idx] !== null &&
        rtEnergyAmt[idx] !== undefined
      ) {
        hourData.rtEnergy += rtEnergyAmt[idx] || 0
      }
      if (
        daRegUpAmt &&
        daRegUpAmt[idx] !== null &&
        daRegUpAmt[idx] !== undefined
      ) {
        const value = daRegUpAmt[idx] || 0
        hourData.regUp += value
        hourData.ancillaryServices += value
      }
      if (
        daRegDownAmt &&
        daRegDownAmt[idx] !== null &&
        daRegDownAmt[idx] !== undefined
      ) {
        const value = daRegDownAmt[idx] || 0
        hourData.regDown += value
        hourData.ancillaryServices += value
      }
      if (daRRSAmt && daRRSAmt[idx] !== null && daRRSAmt[idx] !== undefined) {
        const value = daRRSAmt[idx] || 0
        hourData.rrs += value
        hourData.ancillaryServices += value
      }
      if (daNSAmt && daNSAmt[idx] !== null && daNSAmt[idx] !== undefined) {
        const value = daNSAmt[idx] || 0
        hourData.nonSpin += value
        hourData.ancillaryServices += value
      }
      if (
        daECRSAmt &&
        daECRSAmt[idx] !== null &&
        daECRSAmt[idx] !== undefined
      ) {
        const value = daECRSAmt[idx] || 0
        hourData.ecrs += value
        hourData.ancillaryServices += value
      }
      if (
        rtAncillaryImb &&
        rtAncillaryImb[idx] !== null &&
        rtAncillaryImb[idx] !== undefined
      ) {
        const value = rtAncillaryImb[idx] || 0
        hourData.rtAncillaryImb += value
        hourData.ancillaryServices += value
      }
      if (
        rtReliabilityImb &&
        rtReliabilityImb[idx] !== null &&
        rtReliabilityImb[idx] !== undefined
      ) {
        const value = rtReliabilityImb[idx] || 0
        hourData.rtReliabilityImb += value
        hourData.penalties += value
      }
      if (bpDevAmt && bpDevAmt[idx] !== null && bpDevAmt[idx] !== undefined) {
        const value = bpDevAmt[idx] || 0
        hourData.bpDev += value
        hourData.penalties += value
      }
    })

    let sortedHours = Array.from(hourlyData.keys()).sort()

    // Filter hours to only include those within the selected date range if useCustomDateRange is true
    if (useCustomDateRange && startDate && endDate && projectTimeZone) {
      const tz = projectTimeZone
      // Convert Date objects to dayjs in UTC first, then to target timezone to avoid shifts
      const rangeStart = dayjs.utc(startDate).tz(tz).startOf('day')
      const rangeEnd = dayjs.utc(endDate).tz(tz).endOf('day')
      sortedHours = sortedHours.filter((hour) => {
        const hourTime = dayjs(hour).tz(tz)
        // Include hours that are on or after the start date and on or before the end date
        // Compare dates (ignoring time) to ensure the entire end date is included
        const hourDate = hourTime.startOf('day')
        const startDateOnly = rangeStart.startOf('day')
        const endDateOnly = rangeEnd.startOf('day')
        // Check if hour date is >= start date and <= end date
        return (
          (hourDate.isAfter(startDateOnly) || hourDate.isSame(startDateOnly)) &&
          (hourDate.isBefore(endDateOnly) || hourDate.isSame(endDateOnly))
        )
      })
    }

    const traces: PlotTrace[] = []

    // Calculate today's date range in project timezone for highlighting
    const todayStart = projectTimeZone
      ? dayjs().tz(projectTimeZone).startOf('day')
      : dayjs().startOf('day')
    const todayEnd = projectTimeZone
      ? dayjs().tz(projectTimeZone).endOf('day')
      : dayjs().endOf('day')

    // Handle cumulative mode - line chart showing cumulative revenue
    if (revenueViewMode === 'cumulative') {
      // Calculate cumulative totals for each hour up to now
      let cumulativeTotal = 0
      const cumulativeValues: number[] = []
      const cumulativeX: string[] = []
      const now = projectTimeZone ? dayjs().tz(projectTimeZone) : dayjs()

      sortedHours.forEach((hour) => {
        const hourTime = dayjs(hour).tz(projectTimeZone || 'UTC')
        // Only include hours up to now
        if (hourTime.isAfter(now)) {
          return
        }

        const hourData = hourlyData.get(hour)!
        const hourTotal =
          hourData.daEnergy +
          hourData.rtEnergy +
          hourData.ancillaryServices +
          hourData.penalties
        cumulativeTotal += hourTotal
        cumulativeValues.push(cumulativeTotal)
        cumulativeX.push(hour)
      })

      // Determine which hours are "today" for highlighting
      const markerColors = cumulativeX.map((hour) => {
        const hourTime = dayjs(hour).tz(projectTimeZone || 'UTC')
        const isToday =
          highlightTodayRevenue &&
          hourTime.isAfter(todayStart.subtract(1, 'second')) &&
          hourTime.isBefore(todayEnd.add(1, 'second'))
        return isToday ? theme.colors.blue[6] : theme.colors.blue[4]
      })

      return [
        {
          x: cumulativeX,
          y: cumulativeValues,
          type: 'scatter',
          mode: 'lines+markers',
          name: 'Cumulative Revenue',
          line: {
            width: 2,
            color: theme.colors.blue[6],
          },
          marker: {
            size: 4,
            color: markerColors,
          },
          hovertemplate: `<b>Cumulative Revenue</b><br>%{y:$,.2f}<extra></extra>`,
          yaxis: 'y3',
        } as PlotTrace,
      ]
    }

    type RevenueCategoryKey =
      | 'daEnergy'
      | 'rtEnergy'
      | 'ancillaryServices'
      | 'penalties'
      | 'regUp'
      | 'regDown'
      | 'rrs'
      | 'nonSpin'
      | 'ecrs'
      | 'rtAncillaryImb'
      | 'rtReliabilityImb'
      | 'bpDev'

    type RevenueCategory = {
      key: RevenueCategoryKey
      name: string
      color: string
    }

    const categories: RevenueCategory[] =
      revenueViewMode === 'detailed'
        ? [
            {
              key: 'daEnergy' as const,
              name: 'Day-Ahead Energy',
              color: theme.colors.blue[6],
            },
            {
              key: 'rtEnergy' as const,
              name: 'Real-Time Energy',
              color: theme.colors.orange[6],
            },
            {
              key: 'regUp' as const,
              name: 'Reg Up',
              color: theme.colors.green[6],
            },
            {
              key: 'regDown' as const,
              name: 'Reg Down',
              color: theme.colors.green[5],
            },
            {
              key: 'rrs' as const,
              name: 'RRS',
              color: theme.colors.yellow[6],
            },
            {
              key: 'nonSpin' as const,
              name: 'Non-Spin',
              color: theme.colors.yellow[5],
            },
            {
              key: 'ecrs' as const,
              name: 'ECRS',
              color: theme.colors.yellow[4],
            },
            {
              key: 'rtAncillaryImb' as const,
              name: 'RT Ancillary Imbalance',
              color: theme.colors.cyan[6],
            },
            {
              key: 'rtReliabilityImb' as const,
              name: 'RT Reliability Imbalance',
              color: theme.colors.red[7],
            },
            {
              key: 'bpDev' as const,
              name: 'Base Point Deviation',
              color: theme.colors.red[6],
            },
          ]
        : [
            {
              key: 'daEnergy' as const,
              name: 'Day-Ahead Energy',
              color: theme.colors.blue[6],
            },
            {
              key: 'rtEnergy' as const,
              name: 'Real-Time Energy',
              color: theme.colors.orange[6],
            },
            {
              key: 'ancillaryServices' as const,
              name: 'Ancillary Services',
              color: theme.colors.yellow[6],
            },
            {
              key: 'penalties' as const,
              name: 'Penalties/Imbalances',
              color: theme.colors.red[6],
            },
          ]

    // Build positive traces
    categories.forEach((category) => {
      const values = sortedHours.map((hour) => {
        const value = hourlyData.get(hour)![category.key]
        return value > 0 ? value : 0
      })
      const actualValues = sortedHours.map((hour) => {
        return hourlyData.get(hour)![category.key]
      })
      const bases = sortedHours.map((hour) => {
        let base = 0
        const categoryIdx = categories.indexOf(category)
        for (let i = 0; i < categoryIdx; i++) {
          const prevValue = hourlyData.get(hour)![categories[i].key]
          if (prevValue > 0) {
            base += prevValue
          }
        }
        return base
      })

      // Determine which hours are "today" for highlighting
      const markerColors = sortedHours.map((hour) => {
        const hourTime = dayjs(hour).tz(projectTimeZone || 'UTC')
        const isToday =
          highlightTodayRevenue &&
          hourTime.isAfter(todayStart.subtract(1, 'second')) &&
          hourTime.isBefore(todayEnd.add(1, 'second'))
        // Use brighter color for today, dimmed color for other days
        if (highlightTodayRevenue && !isToday) {
          // Convert hex to rgba with lower opacity for non-today bars
          const hex = category.color
          const r = parseInt(hex.slice(1, 3), 16)
          const g = parseInt(hex.slice(3, 5), 16)
          const b = parseInt(hex.slice(5, 7), 16)
          return `rgba(${r}, ${g}, ${b}, 0.3)`
        }
        return category.color
      })

      traces.push({
        x: sortedHours,
        y: values,
        base: bases,
        type: 'bar',
        name: category.name,
        marker: {
          color: markerColors,
        },
        hovertemplate: `<b>${category.name}</b><br>%{customdata:$,.2f}<extra></extra>`,
        customdata: actualValues,
        offset: 0, // Align bars to start of hour
        width: 3600000, // One hour in milliseconds
        yaxis: 'y3', // Use y3 for revenue subplot
      } as PlotTrace)
    })

    // Build negative traces
    categories
      .slice()
      .reverse()
      .forEach((category) => {
        const values = sortedHours.map((hour) => {
          const value = hourlyData.get(hour)![category.key]
          return value < 0 ? value : 0
        })
        const actualValues = sortedHours.map((hour) => {
          return hourlyData.get(hour)![category.key]
        })
        const bases = sortedHours.map((hour) => {
          let base = 0
          const categoryIdx = categories.indexOf(category)
          for (let i = categories.length - 1; i > categoryIdx; i--) {
            const prevValue = hourlyData.get(hour)![categories[i].key]
            if (prevValue < 0) {
              base += prevValue
            }
          }
          return base
        })

        // Determine which hours are "today" for highlighting (reuse same logic)
        const markerColors = sortedHours.map((hour) => {
          const hourTime = dayjs(hour).tz(projectTimeZone || 'UTC')
          const isToday =
            highlightTodayRevenue &&
            hourTime.isAfter(todayStart.subtract(1, 'second')) &&
            hourTime.isBefore(todayEnd.add(1, 'second'))
          // Use brighter color for today, dimmed color for other days
          if (highlightTodayRevenue && !isToday) {
            // Convert hex to rgba with lower opacity for non-today bars
            const hex = category.color
            const r = parseInt(hex.slice(1, 3), 16)
            const g = parseInt(hex.slice(3, 5), 16)
            const b = parseInt(hex.slice(5, 7), 16)
            return `rgba(${r}, ${g}, ${b}, 0.3)`
          }
          return category.color
        })

        traces.push({
          x: sortedHours,
          y: values,
          base: bases,
          type: 'bar',
          name: category.name,
          marker: {
            color: markerColors,
          },
          showlegend: false,
          hoverinfo: 'skip',
          customdata: actualValues,
          offset: 0, // Align bars to start of hour
          width: 3600000, // One hour in milliseconds
          yaxis: 'y3', // Use y3 for revenue subplot
        } as PlotTrace)
      })

    return traces
  }, [
    batterySettlementData,
    projectTimeZone,
    theme,
    highlightTodayRevenue,
    revenueViewMode,
    useCustomDateRange,
    startDate,
    endDate,
    marketPricesData,
    powerData,
  ])

  // Add RT price marker when hovering
  const rtPriceMarker: PlotTrace[] = useMemo(() => {
    if (
      !highlightRTPrice ||
      currentRTPrice === null ||
      currentRTPrice === undefined
    ) {
      return []
    }

    const currentTimestamp = projectTimeZone
      ? dayjs().tz(projectTimeZone).format()
      : dayjs().format()

    return [
      {
        x: [currentTimestamp],
        y: [currentRTPrice],
        type: 'scatter',
        mode: 'markers',
        name: 'Current RT Price',
        showlegend: false,
        marker: {
          size: pulseSize,
          color: theme.colors.orange[6],
          line: {
            color: theme.colors.orange[9],
            width: 2,
          },
          symbol: 'circle',
        },
        hovertemplate: `<b>Current RT Price</b><br>%{y:$.2f}/MWh<extra></extra>`,
      } as PlotTrace,
    ]
  }, [highlightRTPrice, currentRTPrice, projectTimeZone, theme, pulseSize])

  // Add Power marker when hovering
  const powerMarker: PlotTrace[] = useMemo(() => {
    if (
      !highlightPower ||
      currentPower === null ||
      currentPower === undefined ||
      !lastPowerTimestamp
    ) {
      return []
    }

    return [
      {
        x: [lastPowerTimestamp],
        y: [currentPower],
        type: 'scatter',
        mode: 'markers',
        name: 'Current Power',
        showlegend: false,
        marker: {
          size: powerPulseSize,
          color: theme.colors.green[6],
          line: {
            color: theme.colors.green[9],
            width: 2,
          },
          symbol: 'circle',
        },
        hovertemplate: `<b>Current Power</b><br>%{y:.2f} MW<extra></extra>`,
        yaxis: 'y2', // Use y2 axis (right side for power)
      } as PlotTrace,
    ]
  }, [highlightPower, currentPower, lastPowerTimestamp, theme, powerPulseSize])

  // Combine plot data
  const combinedPlotData: PlotTrace[] = useMemo(() => {
    return [
      ...marketPricesPlotData,
      ...powerPlotData,
      ...revenuePlotData,
      ...rtPriceMarker,
      ...powerMarker,
    ]
  }, [
    marketPricesPlotData,
    powerPlotData,
    revenuePlotData,
    rtPriceMarker,
    powerMarker,
  ])

  // Check if there are any negative values in market prices data and get min/max values
  const { hasNegativePrices, minPrice, maxPrice } = useMemo(() => {
    let hasNegative = false
    let min = Infinity
    let max = 0

    marketPricesPlotData.forEach((trace) => {
      if (Array.isArray(trace.y)) {
        trace.y.forEach((val) => {
          if (val !== null && typeof val === 'number') {
            if (val < 0) {
              hasNegative = true
            }
            if (val < min) {
              min = val
            }
            if (val > max) {
              max = val
            }
          }
        })
      }
    })

    return {
      hasNegativePrices: hasNegative,
      minPrice: min === Infinity ? 0 : min,
      maxPrice: max,
    }
  }, [marketPricesPlotData])

  // Get current timestamp for vertical line
  const currentTimestamp = projectTimeZone
    ? dayjs().tz(projectTimeZone).format()
    : null

  // Calculate x-axis range: use provided dates if useCustomDateRange is true, otherwise use default
  const xAxisRange = useMemo(() => {
    if (!projectTimeZone) {
      return undefined
    }

    // If useCustomDateRange is true and dates are provided, use them
    if (useCustomDateRange && startDate && endDate) {
      const tz = projectTimeZone
      // Convert Date objects to dayjs in UTC first, then to target timezone to avoid shifts
      const start = dayjs.utc(startDate).tz(tz).startOf('day')
      const end = dayjs.utc(endDate).tz(tz).endOf('day')
      // Use .format() to match the format used in plot data timestamps
      return [start.format(), end.format()]
    }

    // Default: start at beginning of day before yesterday, end at end of day tomorrow
    const tz = projectTimeZone
    const now = dayjs().tz(tz)
    const dayBeforeYesterdayStart = now.subtract(2, 'day').startOf('day')
    const tomorrowEnd = now.add(1, 'day').endOf('day')
    // Use .format() to match the format used in plot data timestamps
    return [dayBeforeYesterdayStart.format(), tomorrowEnd.format()]
  }, [projectTimeZone, startDate, endDate, useCustomDateRange])

  // Calculate 1:30pm CT timestamp for DA price publication annotation
  const daPricePublicationTime = useMemo(() => {
    if (!projectTimeZone) {
      return null
    }
    // Get today's date in Central Time, set to 1:30pm
    const todayCT = dayjs().tz('America/Chicago')
    const daTimeCT = todayCT.hour(13).minute(30).second(0).millisecond(0)
    // Convert to project timezone
    return daTimeCT.tz(projectTimeZone).format()
  }, [projectTimeZone])

  // Calculate next day text for DA clearing hover
  const nextDayText = useMemo(() => {
    if (!projectTimeZone) {
      return null
    }
    const tomorrow = dayjs().tz(projectTimeZone).add(1, 'day')
    const month = tomorrow.format('MMMM')
    const day = tomorrow.format('Do') // e.g., "15th"
    return `Expected DA Clearing for ${month} ${day}`
  }, [projectTimeZone])

  const layout: Partial<Layout> = useMemo(() => {
    const shapes: Partial<import('plotly.js').Shape>[] = []

    if (highlightTimeRanges && highlightTimeRanges.length > 0) {
      const hex =
        theme.colors[theme.primaryColor]?.[6] ??
        theme.colors.blue?.[6] ??
        '#228be6'
      const r = parseInt(hex.slice(1, 3), 16)
      const g = parseInt(hex.slice(3, 5), 16)
      const b = parseInt(hex.slice(5, 7), 16)
      const fill = `rgba(${r}, ${g}, ${b}, 0.15)`

      highlightTimeRanges.forEach((range) => {
        shapes.push({
          type: 'rect',
          x0: range.start,
          x1: range.end,
          y0: 0,
          y1: 1,
          xref: 'x',
          yref: 'paper',
          fillcolor: fill,
          line: { width: 0 },
          layer: 'below',
        })
      })
    }

    if (currentTimestamp) {
      shapes.push({
        type: 'line',
        x0: currentTimestamp,
        x1: currentTimestamp,
        y0: 0,
        y1: 1,
        xref: 'x',
        yref: 'paper',
        line: {
          color: theme.colors.red[6],
          width: 2,
          dash: 'dash',
        },
      })
    }

    // Calculate revenue range for y3 axis
    const revenueValues: number[] = []
    revenuePlotData.forEach((trace) => {
      if (revenueViewMode === 'cumulative') {
        // For cumulative mode, just use the y values (line chart)
        if (Array.isArray(trace.y)) {
          trace.y.forEach((val) => {
            if (typeof val === 'number') {
              revenueValues.push(val)
            }
          })
        }
      } else {
        // For bar charts, calculate top and bottom of bars
        const base = trace.base
        const y = trace.y
        if (Array.isArray(base) && Array.isArray(y)) {
          base.forEach((b: number | null, idx: number) => {
            const val = y[idx]
            if (typeof b === 'number' && typeof val === 'number') {
              revenueValues.push(b + val) // Top of bar
              revenueValues.push(b) // Bottom of bar
            }
          })
        }
      }
    })
    const minRevenue =
      revenueValues.length > 0 ? Math.min(...revenueValues) : -1000
    const maxRevenue =
      revenueValues.length > 0 ? Math.max(...revenueValues) : 1000
    const revenueRange =
      revenueValues.length > 0
        ? [
            minRevenue < 0 ? minRevenue * 1.1 : minRevenue * 0.9,
            maxRevenue > 0 ? maxRevenue * 1.1 : maxRevenue * 0.9,
          ]
        : [-1000, 1000]

    return {
      // Shared x-axis for both subplots
      xaxis: {
        title: { text: 'Time' },
        domain: [0, 1],
        range: xAxisRange,
      },
      // Main chart area (top 60%) - Prices and Power
      yaxis: {
        title: { text: 'Price ($/MWh)' },
        side: 'left',
        domain: [0.42, 1], // Top ~58% of chart (leaving gap)
        ...(() => {
          const max = maxPrice > 60 ? maxPrice * 1.1 : 60
          if (!hasNegativePrices) {
            return { range: [0, max] }
          } else if (maxPrice > 0) {
            const min = minPrice * 1.1
            return { range: [min, max] }
          }
          return { range: [0, 60] }
        })(),
      },
      yaxis2: {
        title: { text: 'Power (MW)' },
        side: 'right',
        overlaying: 'y',
        domain: [0.42, 1], // Same domain as yaxis
        showgrid: false,
        ...(project.data?.poi
          ? {
              range: [project.data.poi * 1.05 * -1, project.data.poi * 1.05],
              fixedrange: true,
            }
          : {}),
      },
      // Revenue subplot (bottom 35%)
      yaxis3: {
        title: { text: 'Revenue ($)' },
        side: 'left',
        domain: [0, 0.33], // Bottom ~33% of chart (leaving gap)
        range: revenueRange,
        zeroline: true,
        zerolinecolor: theme.colors.gray[6],
        zerolinewidth: 2,
        anchor: 'x', // Anchor to shared x-axis
      },
      hovermode: 'x unified',
      barmode: revenueViewMode === 'cumulative' ? undefined : 'stack', // Stack the revenue bars (not for cumulative)
      height: 600, // Increased height for subplot
      legend: {
        orientation: 'h',
        y: -0.15,
        xanchor: 'center',
        x: 0.5,
      },
      shapes,
      annotations: daPricePublicationTime
        ? [
            {
              x: daPricePublicationTime,
              y: 0.4,
              xref: 'x',
              yref: 'paper',
              text: 'DA Market Clearing',
              hovertext: nextDayText || undefined,
              showarrow: true,
              arrowhead: 2,
              arrowsize: 1,
              arrowwidth: 1,
              arrowcolor:
                computedColorScheme === 'dark'
                  ? 'rgba(255,255,255,0.3)'
                  : theme.colors.gray[6],
              ax: 0,
              ay: 30,
              font: {
                size: 10,
                color:
                  computedColorScheme === 'dark'
                    ? theme.colors.dark[0]
                    : theme.colors.gray[7],
              },
              bgcolor:
                computedColorScheme === 'dark'
                  ? 'rgba(37,38,43,0.9)'
                  : 'rgba(255,255,255,0.9)',
              bordercolor:
                computedColorScheme === 'dark'
                  ? 'rgba(255,255,255,0.2)'
                  : theme.colors.gray[6],
              borderwidth: 1,
              borderpad: 4,
            },
          ]
        : [],
    }
  }, [
    currentTimestamp,
    daPricePublicationTime,
    nextDayText,
    computedColorScheme,
    theme,
    project.data,
    hasNegativePrices,
    minPrice,
    maxPrice,
    revenuePlotData,
    xAxisRange,
    revenueViewMode,
    highlightTimeRanges,
  ])

  // Card title
  const cardTitle = 'Market Prices, Power & Revenue'

  return (
    <CustomCard
      title={cardTitle}
      headerChildren={
        <Group gap="xs" align="center">
          <Text size="sm" c="dimmed">
            Revenue:
          </Text>
          <SegmentedControl
            value={revenueViewMode}
            onChange={(value) =>
              setRevenueViewMode(
                value as
                  | 'cumulative'
                  | 'grouped'
                  | 'detailed'
                  | 'rt-energy-x-rt-price',
              )
            }
            data={[
              {
                label: (
                  <Tooltip label="Line chart showing cumulative revenue over the period up to now">
                    <span>Cumulative</span>
                  </Tooltip>
                ),
                value: 'cumulative',
              },
              {
                label: (
                  <Tooltip label="Stacked column charts grouped by category (Day-Ahead Energy, Real-Time Energy, Ancillary Services, Penalties/Imbalances)">
                    <span>Grouped</span>
                  </Tooltip>
                ),
                value: 'grouped',
              },
              {
                label: (
                  <Tooltip label="Stacked column charts with detailed breakdown of individual revenue components (Reg Up, Reg Down, RRS, Non-Spin, ECRS, etc.)">
                    <span>Detailed</span>
                  </Tooltip>
                ),
                value: 'detailed',
              },
              {
                label: (
                  <Tooltip label="Physical RT revenue only: GEN_Production × RTSPP (excludes virtuals)">
                    <span>RT Px × MW</span>
                  </Tooltip>
                ),
                value: 'rt-energy-x-rt-price',
              },
            ]}
            size="xs"
          />
        </Group>
      }
    >
      {marketPricesLoading ||
      powerLoading ||
      (needsSettlementRevenue && settlementLoading) ? (
        <Skeleton height={600} radius="md" />
      ) : combinedPlotData.length === 0 ? (
        <Text c="dimmed" ta="center" py="xl">
          No data available. Make sure RTSPP, DASPP, and GEN_Production data
          points exist.
        </Text>
      ) : (
        <PlotlyPlot
          data={combinedPlotData}
          layout={layout}
          isLoading={marketPricesLoading || powerLoading || settlementLoading}
          error={null}
        />
      )}
    </CustomCard>
  )
}
