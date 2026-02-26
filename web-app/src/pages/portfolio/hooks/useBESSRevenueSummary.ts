import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetProjectIdentifiers } from '@/api/v1/protected/web-application/projects/financial/market_performance'
import { useGetPTPData } from '@/api/v1/protected/web-application/projects/financial/ptp_data'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useMemo } from 'react'

dayjs.extend(utc)
dayjs.extend(timezone)

interface RevenueSummary {
  revenueToday: number | null
  revenueMTD: number | null
  revenueYTD: number | null
  isLoading: boolean
}

function parseNumber(value: unknown): number {
  if (value === null || value === undefined) return 0
  const n = typeof value === 'number' ? value : parseFloat(String(value))
  return Number.isFinite(n) ? n : 0
}

function shouldNegate(keyName: string): boolean {
  const k = keyName.toUpperCase()
  return (
    k === 'DAEPAMT' ||
    k === 'DAESAMT' ||
    k === 'RTEIAMT' ||
    k.includes('SPD') ||
    k.includes('BPD')
  )
}

export function useBESSRevenueSummary({
  projectId,
  enabled,
}: {
  projectId: string
  enabled: boolean
}): RevenueSummary {
  const project = useSelectProject(projectId)
  const tz = project.data?.time_zone

  const {
    data: identifiersData,
    isLoading: identifiersLoading,
    isError: identifiersError,
  } = useGetProjectIdentifiers({
    pathParams: { projectId },
    queryOptions: { enabled },
  })
  const parentId = identifiersData?.parent_identifier

  const { ytdStart, todayEnd } = useMemo(() => {
    if (!tz) return { ytdStart: null, todayEnd: null }
    const now = dayjs().tz(tz)
    return {
      ytdStart: now.startOf('year').toDate(),
      todayEnd: now.endOf('day').toDate(),
    }
  }, [tz])

  const {
    data,
    isLoading: ptpLoading,
    isError: ptpError,
  } = useGetPTPData({
    pathParams: { projectId },
    queryParams: {
      endpoint: 'Settlement-Charges',
      category: 'settlement',
      start: ytdStart ? dayjs(ytdStart).toISOString() : undefined,
      end: todayEnd ? dayjs(todayEnd).toISOString() : undefined,
      element_id: parentId,
    },
    queryOptions: {
      enabled: enabled && !!ytdStart && !!todayEnd && !!parentId,
      staleTime: 1000 * 60 * 30,
      refetchOnWindowFocus: false,
    },
  })

  const hasError = identifiersError || ptpError
  const isLoading =
    enabled && !hasError && (identifiersLoading || !tz || ptpLoading || !data)

  return useMemo(() => {
    const empty: RevenueSummary = {
      revenueToday: null,
      revenueMTD: null,
      revenueYTD: null,
      isLoading,
    }
    if (!data?.data?.length || !tz) return empty

    const allElements = data.data
    const el = parentId
      ? allElements.find((e) => e.identifier === parentId) || allElements[0]
      : allElements[0]
    if (!el?.dataPoints) return empty

    const now = dayjs().tz(tz)
    const todayKey = now.format('YYYY-MM-DD')
    const monthStartKey = now.startOf('month').format('YYYY-MM-DD')

    // Native Intl formatter — orders of magnitude
    // faster than dayjs .utc().tz().format() per call
    const dateFmt = new Intl.DateTimeFormat('en-CA', {
      timeZone: tz,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    })

    type DataEntry = {
      value: unknown
      sequence?: unknown
    }

    let today = 0
    let mtd = 0
    let ytd = 0

    for (const dp of el.dataPoints) {
      if (!dp.values) continue
      const sign = shouldNegate(dp.keyName) ? -1 : 1

      for (const val of dp.values) {
        if (!val.intervalStartUtc) continue

        const bestData = (val.data as DataEntry[] | undefined) ?? []
        if (bestData.length === 0) continue

        let best = bestData[0]
        for (let i = 1; i < bestData.length; i++) {
          const s =
            typeof bestData[i].sequence === 'number'
              ? (bestData[i].sequence as number)
              : 0
          const bs =
            typeof best.sequence === 'number' ? (best.sequence as number) : 0
          if (s > bs) best = bestData[i]
        }

        const n = parseNumber(best?.value) * sign
        const dateKey = dateFmt.format(new Date(val.intervalStartUtc))

        ytd += n
        if (dateKey >= monthStartKey) mtd += n
        if (dateKey === todayKey) today += n
      }
    }

    return {
      revenueToday: today,
      revenueMTD: mtd,
      revenueYTD: ytd,
      isLoading,
    }
  }, [data, tz, isLoading, parentId])
}
