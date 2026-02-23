import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetRealtimePrice } from '@/api/v1/protected/web-application/projects/financial/market_performance'
import { useGetPTPData } from '@/api/v1/protected/web-application/projects/financial/ptp_data'
import dayjs from 'dayjs'
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useMemo } from 'react'

dayjs.extend(utc)
dayjs.extend(timezone)
dayjs.extend(isSameOrBefore)

export function useMarketPrices(projectId: string) {
  const project = useSelectProject(projectId)

  const { data: priceData, isLoading: priceLoading } = useGetRealtimePrice({
    pathParams: { projectId },
    queryOptions: { enabled: !!projectId },
  })

  const { startDate, endDate } = useMemo(() => {
    if (!project.data?.time_zone) {
      return { startDate: null, endDate: null }
    }
    const tz = project.data.time_zone
    const now = dayjs().tz(tz)
    const todayStart = now.startOf('day')
    const tomorrowEnd = todayStart.add(2, 'day')
    return {
      startDate: todayStart.toDate(),
      endDate: tomorrowEnd.toDate(),
    }
  }, [project.data?.time_zone])

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

  const rtPriceValue =
    priceData?.price !== null && priceData?.price !== undefined
      ? `$${priceData.price.toFixed(2)} /MWh`
      : 'N/A'

  const { daPrice, priceDiff } = useMemo(() => {
    if (
      !marketPricesData?.data ||
      marketPricesData.data.length === 0 ||
      priceData?.price === null ||
      priceData?.price === undefined
    ) {
      return { daPrice: null, priceDiff: null }
    }
    const spEl = marketPricesData.data.find(
      (el) =>
        el.definition === 'Settlement Point' &&
        el.dataPoints?.some((dp) => dp.keyName === 'DASPP'),
    )
    const element =
      spEl ||
      marketPricesData.data.find((el) =>
        el.dataPoints?.some((dp) => dp.keyName === 'DASPP'),
      ) ||
      marketPricesData.data[0]
    if (!element) {
      return { daPrice: null, priceDiff: null }
    }
    const dasppDP = element.dataPoints?.find((dp) => dp.keyName === 'DASPP')
    if (!dasppDP?.values) {
      return { daPrice: null, priceDiff: null }
    }
    const tz = project.data?.time_zone || 'UTC'
    const currentHourStart = dayjs().tz(tz).startOf('hour')
    let daPriceVal: number | null = null
    let bestMatch: {
      value: number
      intervalStart: dayjs.Dayjs
    } | null = null
    for (const val of dasppDP.values) {
      const intStart = dayjs.utc(val.intervalStartUtc).tz(tz)
      const intEnd = val.intervalEndUtc
        ? dayjs.utc(val.intervalEndUtc).tz(tz)
        : null
      const v = val.data?.[0]?.value
      if (v === null || v === undefined) continue
      const num = parseFloat(String(v))
      if (isNaN(num)) continue
      if (intStart.isSame(currentHourStart, 'hour')) {
        daPriceVal = num
        break
      }
      if (
        intStart.isSameOrBefore(currentHourStart, 'hour') &&
        (!intEnd || intEnd.isAfter(currentHourStart))
      ) {
        if (!bestMatch || intStart.isAfter(bestMatch.intervalStart, 'hour')) {
          bestMatch = {
            value: num,
            intervalStart: intStart,
          }
        }
      }
    }
    if (daPriceVal === null && bestMatch) {
      daPriceVal = bestMatch.value
    }
    if (daPriceVal === null) {
      return { daPrice: null, priceDiff: null }
    }
    return {
      daPrice: daPriceVal,
      priceDiff: priceData.price - daPriceVal,
    }
  }, [marketPricesData, priceData, project.data?.time_zone])

  return {
    rtPriceValue,
    daPrice,
    priceDiff,
    isLoading: priceLoading,
  }
}
