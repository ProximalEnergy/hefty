import { KPITypeEnum } from '@/api/enumerations'
import {
  OperationalKPIData,
  useGetOperationalKPIData,
} from '@/api/v1/operational/kpi_data'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useMemo } from 'react'

dayjs.extend(utc)
dayjs.extend(timezone)

export interface BessPcsMtdData {
  kpiData: OperationalKPIData[] | undefined
  isLoading: boolean
  isError: boolean
}

export type BessPcsAvailabilityPeriod = 'mtd' | 'ytd' | '30d' | '7d'

function getRangeStartKey({
  period,
  tz,
}: {
  period: BessPcsAvailabilityPeriod
  tz: string
}) {
  const now = dayjs().tz(tz)
  switch (period) {
    case 'mtd':
      return now.startOf('month').format('YYYY-MM-DD')
    case 'ytd':
      return now.startOf('year').format('YYYY-MM-DD')
    case '30d':
      return now.startOf('day').subtract(29, 'day').format('YYYY-MM-DD')
    case '7d':
      return now.startOf('day').subtract(6, 'day').format('YYYY-MM-DD')
  }
}

/**
 * Batched KPI fetch for PCS / PCS-module availability on BESS and PVS
 * projects.
 *
 * Args:
 *   projectIds: BESS and PVS project IDs.
 */
export function useBessPcsMtdData({
  projectIds,
}: {
  projectIds: string[]
}): BessPcsMtdData {
  const queryStart = useMemo(() => {
    const ytdStart = dayjs().startOf('year')
    const rolling30Start = dayjs().startOf('day').subtract(29, 'day')
    return (
      ytdStart.isBefore(rolling30Start) ? ytdStart : rolling30Start
    ).format('YYYY-MM-DD')
  }, [])
  const todayEnd = useMemo(() => dayjs().format('YYYY-MM-DD'), [])

  const { data, isLoading, isError } = useGetOperationalKPIData({
    queryParams: {
      project_ids: projectIds,
      kpi_type_ids: [
        KPITypeEnum.BESS_PCS_AVAILABILITY,
        KPITypeEnum.BESS_PCS_MODULE_AVAILABILITY,
      ],
      start: queryStart,
      end: todayEnd,
      include_device_data: false,
      include_all_dates: true,
    },
    queryOptions: {
      enabled: projectIds.length > 0,
    },
  })

  return { kpiData: data, isLoading, isError }
}

/**
 * Mean daily PCS availability for one project over a selected period.
 * KPI series values are stored as fractions; this converts to percent.
 * Prefers the module-level KPI when the project has PCS modules and that
 * series has values; otherwise uses PCS-level availability.
 *
 * Args:
 *   projectId: Project to aggregate.
 *   tz: Project timezone (for month boundary).
 *   kpiData: Shared KPI response from useBessPcsMtdData.
 *   preferModule: When true, prefer BESS_PCS_MODULE_AVAILABILITY when it has
 *     data in the selected window.
 *   period: Time window to aggregate.
 */
export function computeBessPcsMtdAvailability({
  projectId,
  tz,
  kpiData,
  preferModule,
  period,
}: {
  projectId: string
  tz: string | undefined
  kpiData: OperationalKPIData[] | undefined
  preferModule: boolean
  period: BessPcsAvailabilityPeriod
}): number | null {
  if (!kpiData?.length || !tz) return null

  const moduleKpi = kpiData.find(
    (k) =>
      k.project_id === projectId &&
      k.kpi_type_id === KPITypeEnum.BESS_PCS_MODULE_AVAILABILITY,
  )
  const pcsKpi = kpiData.find(
    (k) =>
      k.project_id === projectId &&
      k.kpi_type_id === KPITypeEnum.BESS_PCS_AVAILABILITY,
  )

  const rangeStartKey = getRangeStartKey({ period, tz })

  const periodMean = (kpi: OperationalKPIData | undefined): number | null => {
    if (!kpi?.data?.dates || !kpi.data.project_data) return null
    const { dates, project_data } = kpi.data
    let sum = 0
    let n = 0
    for (let i = 0; i < dates.length; i++) {
      if (dates[i] < rangeStartKey) continue
      const v = project_data[i]
      if (v != null) {
        sum += v
        n += 1
      }
    }
    return n === 0 ? null : (sum / n) * 100
  }

  if (preferModule) {
    const moduleMean = periodMean(moduleKpi)
    if (moduleMean != null) return moduleMean
    const pcsAfterModule = periodMean(pcsKpi)
    if (pcsAfterModule != null) return pcsAfterModule
    return null
  }

  const pcsMean = periodMean(pcsKpi)
  if (pcsMean != null) return pcsMean
  return periodMean(moduleKpi)
}

/**
 * Resolve the KPI type backing the displayed PCS availability value.
 *
 * Args:
 *   projectId: Project to resolve.
 *   tz: Project timezone (for month boundary).
 *   kpiData: Shared KPI response from useBessPcsMtdData.
 *   preferModule: When true, prefer BESS_PCS_MODULE_AVAILABILITY when it has
 *     data in the selected window.
 *   period: Time window to inspect.
 */
export function getBessPcsMtdKpiType({
  projectId,
  tz,
  kpiData,
  preferModule,
  period,
}: {
  projectId: string
  tz: string | undefined
  kpiData: OperationalKPIData[] | undefined
  preferModule: boolean
  period: BessPcsAvailabilityPeriod
}): number | null {
  if (!kpiData?.length || !tz) return null

  const moduleKpi = kpiData.find(
    (k) =>
      k.project_id === projectId &&
      k.kpi_type_id === KPITypeEnum.BESS_PCS_MODULE_AVAILABILITY,
  )
  const pcsKpi = kpiData.find(
    (k) =>
      k.project_id === projectId &&
      k.kpi_type_id === KPITypeEnum.BESS_PCS_AVAILABILITY,
  )

  const rangeStartKey = getRangeStartKey({ period, tz })

  const hasPeriodData = (kpi: OperationalKPIData | undefined): boolean => {
    if (!kpi?.data?.dates || !kpi.data.project_data) return false
    const { dates, project_data } = kpi.data
    for (let i = 0; i < dates.length; i++) {
      if (dates[i] < rangeStartKey) continue
      if (project_data[i] != null) return true
    }
    return false
  }

  if (preferModule) {
    if (hasPeriodData(moduleKpi))
      return KPITypeEnum.BESS_PCS_MODULE_AVAILABILITY
    if (hasPeriodData(pcsKpi)) return KPITypeEnum.BESS_PCS_AVAILABILITY
    return null
  }

  if (hasPeriodData(pcsKpi)) return KPITypeEnum.BESS_PCS_AVAILABILITY
  if (hasPeriodData(moduleKpi)) return KPITypeEnum.BESS_PCS_MODULE_AVAILABILITY
  return null
}
