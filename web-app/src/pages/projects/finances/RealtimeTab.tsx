import { SensorTypeEnum } from '@/api/enumerations'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetRealtimePrice } from '@/api/v1/protected/web-application/projects/financial/market_performance'
import {
  useGetActiveOutageTickets,
  useGetPTPData,
} from '@/api/v1/protected/web-application/projects/financial/ptp_data'
import { useGetDataTimeseriesLast } from '@/api/v1/protected/web-application/projects/real_time'
import { StatSparkline } from '@/components/stats/StatSparkline'
import { StatsGrid } from '@/components/stats/StatsGrid'
import { Statistic } from '@/hooks/types'
import { formatCurrency } from '@/utils/currency'
import { QUERY_TIME } from '@/utils/queryTiming'
import {
  Box,
  Group,
  Skeleton,
  Stack,
  Text,
  useMantineTheme,
} from '@mantine/core'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useMemo, useState } from 'react'

import { COPDataCard } from './components/COPDataCard'
import { MarketPricesPowerCard } from './components/MarketPricesPowerCard'
import { OutageTicketsValue } from './components/OutageTicketsValue'
import { TBSpreadsCard } from './components/TBSpreadsCard'
import { ThreePartOfferCard } from './components/ThreePartOfferCard'
import { useOutageTicketsDescription } from './hooks/useOutageTicketsDescription'

dayjs.extend(utc)
dayjs.extend(timezone)

interface RealtimeTabProps {
  projectId: string
}

export const FinancesRealtimeTab = ({ projectId }: RealtimeTabProps) => {
  const project = useSelectProject(projectId)
  const theme = useMantineTheme()
  const [isHoveringRevenue, setIsHoveringRevenue] = useState(false)
  const [isHoveringRTPrice, setIsHoveringRTPrice] = useState(false)
  const [isHoveringPower, setIsHoveringPower] = useState(false)
  const [tbHighlightRanges, setTbHighlightRanges] = useState<Array<{
    start: string
    end: string
  }> | null>(null)

  // Fetch real-time price
  const { data: priceData, isLoading: priceLoading } = useGetRealtimePrice({
    pathParams: { projectId },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  // Calculate date range for today and tomorrow in project timezone
  const { startDate, endDate } = useMemo(() => {
    if (!project.data?.time_zone) {
      return { startDate: null, endDate: null }
    }
    const tz = project.data.time_zone
    const now = dayjs().tz(tz)
    const todayStart = now.startOf('day')
    const tomorrowEnd = todayStart.add(2, 'day') // End of tomorrow
    return {
      startDate: todayStart.toDate(),
      endDate: tomorrowEnd.toDate(),
    }
  }, [project.data?.time_zone])

  // Fetch market prices to get DA price for current hour
  const { data: marketPricesData } = useGetPTPData({
    pathParams: { projectId },
    queryParams: {
      endpoint: 'Market-Prices',
      category: 'market',
      start: startDate ? dayjs(startDate).toISOString() : undefined,
      end: endDate ? dayjs(endDate).toISOString() : undefined,
    },
    queryOptions: {
      enabled: !!projectId && !!startDate && !!endDate,
    },
  })

  // Calculate date range for revenue chart and stats: today's calendar day
  const { revenueStartDate, revenueEndDate } = useMemo(() => {
    if (!project.data?.time_zone) {
      return { revenueStartDate: null, revenueEndDate: null }
    }
    const tz = project.data.time_zone
    const now = dayjs().tz(tz)
    // Start: beginning of today's local calendar day
    const startDate = now.startOf('day')
    // End: end of today's local calendar day
    const endDate = now.endOf('day')
    return {
      revenueStartDate: startDate.toDate(),
      revenueEndDate: endDate.toDate(),
    }
  }, [project.data?.time_zone])

  // Calculate date range for COP data (future operating days - COP is forward-looking)
  const { copStartDate, copEndDate } = useMemo(() => {
    if (!project.data?.time_zone) {
      return { copStartDate: null, copEndDate: null }
    }
    const tz = project.data.time_zone
    const now = dayjs().tz(tz)
    // Start from current operating day (6 AM CT)
    let copStart = now.startOf('day').hour(6).minute(0).second(0)
    if (now.hour() < 6) {
      copStart = copStart.subtract(1, 'day')
    }
    // Query next 2 operating days for COP data
    const copEnd = copStart.add(2, 'day')
    return {
      copStartDate: copStart.toDate(),
      copEndDate: copEnd.toDate(),
    }
  }, [project.data])

  // Fetch Battery-Settlement-Details for RT and DA Energy Revenue (used in stats)
  const { data: batterySettlementData, isLoading: batterySettlementLoading } =
    useGetPTPData({
      pathParams: { projectId },
      queryParams: {
        endpoint: 'Battery-Settlement-Details',
        category: 'settlement',
        start: revenueStartDate
          ? dayjs(revenueStartDate).toISOString()
          : undefined,
        end: revenueEndDate ? dayjs(revenueEndDate).toISOString() : undefined,
      },
      queryOptions: {
        enabled: !!projectId && !!revenueStartDate && !!revenueEndDate,
      },
    })

  // Fetch power data for stats (current net dispatch)
  const { data: powerData, isLoading: powerLoading } = useGetPTPData({
    pathParams: { projectId },
    queryParams: {
      endpoint: 'Real-Time-Unit-Position',
      category: 'analysis',
      start: startDate ? dayjs(startDate).toISOString() : undefined,
      end: endDate ? dayjs(endDate).toISOString() : undefined,
    },
    queryOptions: {
      enabled: !!projectId && !!startDate && !!endDate,
    },
  })

  // Fetch active outage tickets (for description only)
  const { data: outageTicketsData } = useGetActiveOutageTickets({
    pathParams: { projectId },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  // Fetch latest SOC value
  const { data: socData, isLoading: socLoading } = useGetDataTimeseriesLast({
    pathParams: { projectId },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.PROJECT_SOC_PERCENT],
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.THIRTY_SECONDS, // Refetch every 30 seconds
      staleTime: QUERY_TIME.FIFTEEN_SECONDS, // Consider data stale after 15 seconds
    },
  })

  // Format RT price value
  const rtPriceValue =
    priceData?.price !== null && priceData?.price !== undefined
      ? `$${priceData.price.toFixed(2)} /MWh`
      : 'N/A'

  const rtPriceTime = useMemo(() => {
    if (!priceData?.timestamp) {
      return 'N/A'
    }
    return dayjs(priceData.timestamp)
      .tz(project.data?.time_zone || 'UTC')
      .format('HH:mm')
  }, [priceData?.timestamp, project.data?.time_zone])

  // Get DA price for current hour and calculate difference
  const { daPrice, priceDiff } = useMemo(() => {
    if (
      !marketPricesData?.data ||
      marketPricesData.data.length === 0 ||
      !priceData?.price
    ) {
      return { daPrice: null, priceDiff: null }
    }

    const settlementPointElement = marketPricesData.data.find(
      (el) =>
        el.definition === 'Settlement Point' &&
        el.dataPoints?.some((dp) => dp.keyName === 'DASPP'),
    )

    const element =
      settlementPointElement ||
      marketPricesData.data.find((el) =>
        el.dataPoints?.some((dp) => dp.keyName === 'DASPP'),
      ) ||
      marketPricesData.data[0]

    if (!element) {
      return { daPrice: null, priceDiff: null }
    }

    // Find DASPP data point
    const dasppDP = element.dataPoints?.find((dp) => dp.keyName === 'DASPP')
    if (!dasppDP || !dasppDP.values) {
      return { daPrice: null, priceDiff: null }
    }

    // Get current hour in project timezone
    const tz = project.data?.time_zone || 'UTC'
    const now = dayjs().tz(tz)
    const currentHourStart = now.startOf('hour')

    // Find DA price for current hour
    // DASPP is hourly, so find the interval that starts at the current hour
    let daPriceValue: number | null = null
    let bestMatch: { value: number; intervalStart: dayjs.Dayjs } | null = null

    for (const val of dasppDP.values) {
      const intervalStart = dayjs.utc(val.intervalStartUtc).tz(tz)
      const intervalEnd = val.intervalEndUtc
        ? dayjs.utc(val.intervalEndUtc).tz(tz)
        : null

      const value = val.data?.[0]?.value
      if (value === null || value === undefined) {
        continue
      }

      const numValue = parseFloat(String(value))
      if (isNaN(numValue)) {
        continue
      }

      // Check if current hour exactly matches this interval start
      if (intervalStart.isSame(currentHourStart, 'hour')) {
        daPriceValue = numValue
        break
      }

      // Otherwise, track the most recent interval that starts before or at current hour
      if (
        intervalStart.isSameOrBefore(currentHourStart, 'hour') &&
        (!intervalEnd || intervalEnd.isAfter(currentHourStart))
      ) {
        if (
          !bestMatch ||
          intervalStart.isAfter(bestMatch.intervalStart, 'hour')
        ) {
          bestMatch = { value: numValue, intervalStart }
        }
      }
    }

    // Use exact match if found, otherwise use best match
    if (daPriceValue === null && bestMatch) {
      daPriceValue = bestMatch.value
    }

    if (daPriceValue === null) {
      return { daPrice: null, priceDiff: null }
    }

    // Calculate difference (RT - DA)
    const diff = priceData.price - daPriceValue

    return { daPrice: daPriceValue, priceDiff: diff }
  }, [marketPricesData, priceData, project.data?.time_zone])

  // Get outage tickets description
  const outageTicketsDescription = useOutageTicketsDescription(
    outageTicketsData,
    project.data?.time_zone,
  )

  // Extract latest POI power value and sparkline data from powerData
  const { currentNetDispatch, sparklineData, lastPowerTimestamp } =
    useMemo(() => {
      if (!powerData?.data || powerData.data.length === 0) {
        return {
          currentNetDispatch: null,
          sparklineData: [],
          lastPowerTimestamp: null,
        }
      }

      const element =
        powerData.data.find(
          (el) =>
            el.definition === 'Generator' &&
            el.dataPoints?.some((dp) => dp.keyName === 'GEN_Production'),
        ) || powerData.data[0]

      if (!element) {
        return {
          currentNetDispatch: null,
          sparklineData: [],
          lastPowerTimestamp: null,
        }
      }

      // Find GEN_Production data point
      const genProductionDP = element.dataPoints?.find(
        (dp) => dp.keyName === 'GEN_Production',
      )

      if (
        !genProductionDP ||
        !genProductionDP.values ||
        genProductionDP.values.length === 0
      ) {
        return {
          currentNetDispatch: null,
          sparklineData: [],
          lastPowerTimestamp: null,
        }
      }

      // Extract all valid power values for sparkline (last 15 points)
      const allValues: number[] = []
      let lastTimestamp: string | null = null
      genProductionDP.values.forEach((v) => {
        const valueStr = v.data?.[0]?.value
        if (valueStr !== null && valueStr !== undefined) {
          const value = parseFloat(String(valueStr))
          if (!isNaN(value)) {
            allValues.push(value)
            // Get the timestamp of the last valid value
            if (v.intervalStartUtc) {
              lastTimestamp = dayjs
                .utc(v.intervalStartUtc)
                .tz(project.data?.time_zone || 'UTC')
                .format()
            }
          }
        }
      })

      // Get the latest value (last in array)
      const latestValue =
        allValues.length > 0 ? allValues[allValues.length - 1] : null

      // Get last 15 values for sparkline
      const sparklineValues = allValues.slice(-15)

      return {
        currentNetDispatch: latestValue,
        sparklineData: sparklineValues,
        lastPowerTimestamp: lastTimestamp,
      }
    }, [powerData, project.data?.time_zone])

  // Format current net dispatch value
  const currentNetDispatchValue = useMemo(() => {
    if (powerLoading) {
      return null // Return null to indicate loading, will show skeleton
    }
    if (currentNetDispatch === null || currentNetDispatch === undefined) {
      return 'N/A'
    }
    const sign = currentNetDispatch >= 0 ? '+' : ''
    return `${sign}${currentNetDispatch.toFixed(2)} MW`
  }, [powerLoading, currentNetDispatch])

  // Determine dispatch state (charging/discharging/idle)
  const dispatchState = useMemo(() => {
    if (currentNetDispatch === null || currentNetDispatch === undefined) {
      return null
    }
    const absPower = Math.abs(currentNetDispatch)
    const poiPower = project.data?.poi ?? 0
    // Consider idle if power is less than 1% of POI power
    if (poiPower > 0 && absPower < poiPower * 0.01) {
      return 'Idling'
    }
    // Positive = discharging, negative = charging
    return currentNetDispatch > 0 ? 'Discharging' : 'Charging'
  }, [currentNetDispatch, project.data?.poi])

  // Extract latest SOC value
  // Note: SOC values are stored as decimals (0-1), need to multiply by 100 for percentage
  const latestSOC = useMemo(() => {
    if (!socData || socData.length === 0) {
      return null
    }

    // Since we're querying for PROJECT_SOC_PERCENT (project-level, single tag),
    // there should be only one result. Get the value from the first (and only) entry.
    const socEntry = socData[0]

    if (!socEntry) {
      return null
    }

    // Extract value from the appropriate field (could be real, double, integer, etc.)
    const value =
      socEntry.value_real ??
      socEntry.value_double ??
      socEntry.value_integer ??
      (socEntry.value_text ? parseFloat(socEntry.value_text) : null)

    if (value === null || value === undefined || isNaN(value)) {
      return null
    }

    // SOC is stored as decimal (0-1), convert to percentage (0-100)
    return value * 100
  }, [socData])

  // Calculate remaining MWh from SOC and battery capacity
  const remainingMWh = useMemo(() => {
    if (latestSOC === null || latestSOC === undefined) {
      return null
    }
    // capacity_bess_energy_bol_dc is in MWh DC
    const batteryCapacityMWh = project.data?.capacity_bess_energy_bol_dc ?? 0
    if (batteryCapacityMWh === 0) {
      return null
    }
    // latestSOC is now a percentage (0-100), convert to decimal and multiply by capacity
    const remaining = (latestSOC / 100) * batteryCapacityMWh
    return remaining
  }, [latestSOC, project.data?.capacity_bess_energy_bol_dc])

  // Format SOC value
  const socValue = useMemo(() => {
    if (socLoading) {
      return null // Return null to indicate loading, will show skeleton
    }
    if (latestSOC === null || latestSOC === undefined) {
      return 'N/A'
    }
    return `${latestSOC.toFixed(0)}%`
  }, [socLoading, latestSOC])

  // Calculate Revenue Today from RT and DA Energy Amounts (today only)
  // Separate realized (past) from unrealized (future) revenue
  const {
    rtRevenue,
    daRevenue,
    daASRevenue,
    realizedRevenue,
    unrealizedRevenue,
  } = useMemo(() => {
    if (
      !batterySettlementData?.data ||
      batterySettlementData.data.length === 0
    ) {
      return {
        revenueToday: null,
        rtRevenue: null,
        daRevenue: null,
        daASRevenue: null,
        realizedRevenue: null,
        unrealizedRevenue: null,
      }
    }

    const element = batterySettlementData.data[0]

    if (!element || !element.dataPoints) {
      return {
        revenueToday: null,
        rtRevenue: null,
        daRevenue: null,
        daASRevenue: null,
        realizedRevenue: null,
        unrealizedRevenue: null,
      }
    }

    // Find RT_Energy_Amt and DA_Energy_Amt data points
    const rtEnergyAmtDP = element.dataPoints.find(
      (dp) => dp.keyName === 'RT_Energy_Amt',
    )
    const daEnergyAmtDP = element.dataPoints.find(
      (dp) => dp.keyName === 'DA_Energy_Amt',
    )

    // Find DA ancillary service data points
    const daRegUpAmtDP = element.dataPoints.find(
      (dp) => dp.keyName === 'DA_Reg_Up_Amt',
    )
    const daRegDownAmtDP = element.dataPoints.find(
      (dp) => dp.keyName === 'DA_Reg_Down_Amt',
    )
    const daRRSAmtDP = element.dataPoints.find(
      (dp) => dp.keyName === 'DA_RRS_Amt',
    )
    const daNSAmtDP = element.dataPoints.find(
      (dp) => dp.keyName === 'DA_NS_Amt',
    )
    const daECRSAmtDP = element.dataPoints.find(
      (dp) => dp.keyName === 'DA_ECRS_Amt',
    )

    let rtTotal = 0
    let daRealized = 0
    let daUnrealized = 0
    let daASRealized = 0
    let daASUnrealized = 0

    const tz = project.data?.time_zone
    const nowTz = tz ? dayjs().tz(tz) : dayjs()
    const nowUtc = dayjs.utc()
    const dayStart = nowTz.startOf('day')
    const dayEnd = nowTz.endOf('day')

    // Sum RT Energy Amount values for today's calendar day
    // RT revenue is always realized (it's real-time, already happened)
    if (rtEnergyAmtDP?.values) {
      rtEnergyAmtDP.values.forEach((v) => {
        const intervalStart = tz
          ? dayjs(v.intervalStartUtc).tz(tz)
          : dayjs(v.intervalStartUtc)
        if (intervalStart.isBefore(dayStart) || intervalStart.isAfter(dayEnd)) {
          return
        }
        const valueStr = v.data?.[0]?.value
        if (valueStr !== null && valueStr !== undefined) {
          const value = parseFloat(String(valueStr))
          if (!isNaN(value)) {
            rtTotal += value
          }
        }
      })
    }

    // Sum DA Energy Amount values for today's calendar day
    // Separate into realized (past) and unrealized (future)
    if (daEnergyAmtDP?.values) {
      daEnergyAmtDP.values.forEach((v) => {
        const intervalStart = tz
          ? dayjs(v.intervalStartUtc).tz(tz)
          : dayjs(v.intervalStartUtc)
        if (intervalStart.isBefore(dayStart) || intervalStart.isAfter(dayEnd)) {
          return
        }
        const valueStr = v.data?.[0]?.value
        if (valueStr !== null && valueStr !== undefined) {
          const value = parseFloat(String(valueStr))
          if (!isNaN(value)) {
            // Check if this interval is in the past (realized) or future (unrealized)
            const intervalStartUtc = dayjs.utc(v.intervalStartUtc)
            if (intervalStartUtc.isBefore(nowUtc)) {
              daRealized += value
            } else {
              daUnrealized += value
            }
          }
        }
      })
    }

    // Sum DA Ancillary Services for today's calendar day
    // Separate into realized (past) and unrealized (future)
    const daASDataPoints = [
      daRegUpAmtDP,
      daRegDownAmtDP,
      daRRSAmtDP,
      daNSAmtDP,
      daECRSAmtDP,
    ]

    daASDataPoints.forEach((asDP) => {
      if (!asDP?.values) return

      asDP.values.forEach((v) => {
        const intervalStart = tz
          ? dayjs(v.intervalStartUtc).tz(tz)
          : dayjs(v.intervalStartUtc)
        if (intervalStart.isBefore(dayStart) || intervalStart.isAfter(dayEnd)) {
          return
        }
        const valueStr = v.data?.[0]?.value
        if (valueStr !== null && valueStr !== undefined) {
          const value = parseFloat(String(valueStr))
          if (!isNaN(value)) {
            // Check if this interval is in the past (realized) or future (unrealized)
            const intervalStartUtc = dayjs.utc(v.intervalStartUtc)
            if (intervalStartUtc.isBefore(nowUtc)) {
              daASRealized += value
            } else {
              daASUnrealized += value
            }
          }
        }
      })
    })

    // Total DA revenue (realized + unrealized) including ancillary services
    const daASTotal = daASRealized + daASUnrealized
    const daTotal = daRealized + daUnrealized + daASTotal
    // Realized revenue = RT (always realized) + DA realized + DA AS realized
    const realized = rtTotal + daRealized + daASRealized
    // Total revenue = RT + DA + DA AS for today's calendar day
    const total = rtTotal + daTotal

    return {
      revenueToday: total,
      rtRevenue: rtTotal,
      daRevenue: daTotal,
      daASRevenue: daASTotal,
      realizedRevenue: realized,
      unrealizedRevenue: daUnrealized + daASUnrealized,
    }
  }, [batterySettlementData, project.data])

  // Format revenue today value
  const revenueTodayValue = useMemo(() => {
    if (batterySettlementLoading) {
      return null // Return null to indicate loading, will show skeleton
    }
    if (
      realizedRevenue === null ||
      realizedRevenue === undefined ||
      unrealizedRevenue === null ||
      unrealizedRevenue === undefined
    ) {
      return 'N/A'
    }
    // Format realized revenue with unrealized in parentheses
    const realizedStr = formatCurrency(realizedRevenue)
    if (unrealizedRevenue > 0) {
      const unrealizedStr = `+${formatCurrency(unrealizedRevenue)}`
      return (
        <>
          {realizedStr}{' '}
          <Text component="span" size="sm" c="dimmed">
            ({unrealizedStr} unrealized)
          </Text>
        </>
      )
    }
    return realizedStr
  }, [batterySettlementLoading, realizedRevenue, unrealizedRevenue])

  // Format revenue breakdown (RT and DA)
  const revenueBreakdown = useMemo(() => {
    if (batterySettlementLoading) {
      return null
    }
    if (
      rtRevenue === null ||
      rtRevenue === undefined ||
      daRevenue === null ||
      daRevenue === undefined
    ) {
      return null
    }
    const daASValue =
      daASRevenue !== null && daASRevenue !== undefined ? daASRevenue : 0

    return (
      <Text size="xs" c="dimmed">
        <Text component="span" c={theme.colors.orange[6]} fw={500}>
          RT:
        </Text>{' '}
        <Text component="span">{formatCurrency(rtRevenue)}</Text>{' '}
        <Text component="span" c={theme.colors.blue[6]} fw={500}>
          DA:
        </Text>{' '}
        <Text component="span">{formatCurrency(daRevenue)}</Text>{' '}
        <Text component="span" c={theme.colors.yellow[6]} fw={500}>
          AS:
        </Text>{' '}
        <Text component="span">{formatCurrency(daASValue)}</Text>
      </Text>
    )
  }, [batterySettlementLoading, rtRevenue, daRevenue, daASRevenue, theme])

  // Format revenue date for title (current operating day date)
  const revenueDate = useMemo(() => {
    if (!project.data?.time_zone) {
      return ''
    }
    const tz = project.data.time_zone
    const now = dayjs().tz(tz)
    // ERCOT operating day starts at 6 AM CT
    let operatingDay = now.startOf('day')
    if (now.hour() < 6) {
      // If before 6 AM, use yesterday's operating day
      operatingDay = operatingDay.subtract(1, 'day')
    }
    return operatingDay.format('MMM D')
  }, [project.data])

  // Placeholder data for real-time stats
  // TODO: Replace remaining placeholders with actual PTP API data
  const realtimeStats: Statistic[] = useMemo(
    () => [
      {
        title: 'Settlement Point Price (Node)',
        description: '15-minute average price (SPP) used for settlement.',
        value: priceLoading ? null : (
          <Box
            onMouseEnter={() => setIsHoveringRTPrice(true)}
            onMouseLeave={() => setIsHoveringRTPrice(false)}
            style={{ cursor: 'pointer' }}
          >
            <Stack gap={2}>
              <Text>
                <Text component="span" fz={32} fw={700}>
                  {rtPriceValue}
                </Text>{' '}
                <Text component="span" size="sm" c="dimmed">
                  (Updated {rtPriceTime})
                </Text>
              </Text>
              {daPrice !== null && priceDiff !== null && (
                <Text size="xs" c="dimmed">
                  DA: ${daPrice.toFixed(2)} / MWh ({priceDiff >= 0 ? '+' : ''}$
                  {priceDiff.toFixed(2)} /MWh DART Spread)
                </Text>
              )}
            </Stack>
          </Box>
        ),
        icon: 'price',
      },
      {
        title: `Revenue Today${revenueDate ? ` (${revenueDate})` : ''}`,
        description: 'Total revenue generated so far today',
        value: (
          <Box
            onMouseEnter={() => setIsHoveringRevenue(true)}
            onMouseLeave={() => setIsHoveringRevenue(false)}
            style={{ cursor: 'pointer' }}
          >
            <Stack gap={2}>
              {revenueTodayValue === null ? (
                <Skeleton height={32} width={120} radius="xl" />
              ) : (
                <Text fz={32} fw={700}>
                  {revenueTodayValue}
                </Text>
              )}
              {revenueBreakdown}
            </Stack>
          </Box>
        ),
        icon: 'revenue',
      },
      {
        title: 'Active Outage Tickets',
        description: outageTicketsDescription,
        value: (
          <OutageTicketsValue
            projectId={projectId}
            projectTimeZone={project.data?.time_zone}
          />
        ),
        icon: 'events',
      },
      {
        title: 'Power',
        description:
          'Current net dispatch (positive = discharging, negative = charging)',
        value: (
          <Box
            onMouseEnter={() => setIsHoveringPower(true)}
            onMouseLeave={() => setIsHoveringPower(false)}
            style={{ cursor: 'pointer' }}
          >
            <Stack gap={2}>
              <Group gap="xs" align="center">
                {currentNetDispatchValue === null ? (
                  <Skeleton height={32} width={120} radius="xl" />
                ) : (
                  <Text fz={32} fw={700}>
                    {currentNetDispatchValue}
                  </Text>
                )}
                {sparklineData.length > 0 && (
                  <StatSparkline data={sparklineData} width={60} height={20} />
                )}
              </Group>
              {dispatchState && (
                <Text size="xs" c="dimmed">
                  {dispatchState}
                </Text>
              )}
            </Stack>
          </Box>
        ),
        icon: 'dispatch',
      },
      {
        title: 'State of Charge',
        description: 'Current battery state of charge',
        value: (
          <Stack gap={2}>
            {socValue === null ? (
              <Skeleton height={32} width={80} radius="xl" />
            ) : (
              <Text fz={32} fw={700}>
                {socValue}
              </Text>
            )}
            {remainingMWh !== null && (
              <Text size="xs" c="dimmed">
                ≈ {remainingMWh.toFixed(1)} MWh remaining
              </Text>
            )}
          </Stack>
        ),
        icon: 'soc',
      },
    ],
    [
      priceLoading,
      rtPriceValue,
      rtPriceTime,
      daPrice,
      priceDiff,
      revenueTodayValue,
      revenueBreakdown,
      revenueDate,
      outageTicketsDescription,
      projectId,
      project.data,
      currentNetDispatchValue,
      sparklineData,
      dispatchState,
      socValue,
      remainingMWh,
    ],
  )

  // Determine if any stats are loading
  const statsLoading =
    priceLoading || batterySettlementLoading || powerLoading || socLoading

  return (
    <Stack gap="md">
      {/* Real-time Stats Grid */}
      <StatsGrid data={realtimeStats} isLoading={statsLoading} />

      {/* Market Prices & Power Chart */}
      <Group align="stretch" wrap="nowrap">
        <Box style={{ flex: 4, minWidth: 0 }}>
          <MarketPricesPowerCard
            projectId={projectId}
            projectTimeZone={project.data?.time_zone}
            highlightTodayRevenue={isHoveringRevenue}
            highlightRTPrice={isHoveringRTPrice}
            currentRTPrice={priceData?.price ?? null}
            highlightPower={isHoveringPower}
            currentPower={currentNetDispatch}
            lastPowerTimestamp={lastPowerTimestamp}
            highlightTimeRanges={tbHighlightRanges ?? undefined}
          />
        </Box>
        <Box style={{ flex: 1, minWidth: 0 }}>
          <TBSpreadsCard
            projectId={projectId}
            projectTimeZone={project.data?.time_zone}
            onHighlightIntervalsChange={setTbHighlightRanges}
          />
        </Box>
      </Group>

      {/* COP Data Chart */}
      <COPDataCard
        projectId={projectId}
        projectTimeZone={project.data?.time_zone}
        startDate={copStartDate}
        endDate={copEndDate}
      />

      {/* Three-Part Offer Display */}
      <ThreePartOfferCard
        projectId={projectId}
        projectTimeZone={project.data?.time_zone}
        startDate={startDate}
        endDate={endDate}
      />
    </Stack>
  )
}
