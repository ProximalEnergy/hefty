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

export interface PVRevenueData {
  kpiData: OperationalKPIData[] | undefined
  isLoading: boolean
  isError: boolean
}

interface PVRevenueSummary {
  energyMTD: number | null
  energyYTD: number | null
  ppaRate: number
  revenueMTD: number | null
  revenueYTD: number | null
}

/**
 * Single batched KPI fetch for all PV/PVS projects.
 *
 * Args:
 *   projectIds: IDs of projects to fetch energy data for.
 */
export function usePVRevenueData({
  projectIds,
}: {
  projectIds: string[]
}): PVRevenueData {
  const ytdStart = useMemo(
    () => dayjs().startOf('year').format('YYYY-MM-DD'),
    [],
  )
  const todayEnd = useMemo(() => dayjs().format('YYYY-MM-DD'), [])

  const {
    data: kpiData,
    isLoading,
    isError,
  } = useGetOperationalKPIData({
    queryParams: {
      project_ids: projectIds,
      kpi_type_ids: [KPITypeEnum.PROJECT_ENERGY_PRODUCTION],
      start: ytdStart,
      end: todayEnd,
      include_device_data: false,
      include_all_dates: true,
    },
    queryOptions: {
      enabled: projectIds.length > 0,
    },
  })

  return { kpiData, isLoading, isError }
}

/**
 * Compute PV revenue for a single project from shared KPI data.
 *
 * Args:
 *   projectId: The project to compute revenue for.
 *   ppaRate: PPA rate in $/MWh.
 *   tz: Project timezone string.
 *   kpiData: Shared KPI response from usePVRevenueData.
 */
export function computePVRevenue({
  projectId,
  ppaRate,
  tz,
  kpiData,
}: {
  projectId: string
  ppaRate: number
  tz: string | undefined
  kpiData: OperationalKPIData[] | undefined
}): PVRevenueSummary {
  const empty: PVRevenueSummary = {
    energyMTD: null,
    energyYTD: null,
    ppaRate,
    revenueMTD: null,
    revenueYTD: null,
  }
  if (!kpiData?.length || !tz) return empty

  const kpi = kpiData.find(
    (k) =>
      k.project_id === projectId &&
      k.kpi_type_id === KPITypeEnum.PROJECT_ENERGY_PRODUCTION,
  )
  if (!kpi?.data?.dates || !kpi.data.project_data) return empty

  const { dates, project_data } = kpi.data
  const monthStartKey = dayjs().tz(tz).startOf('month').format('YYYY-MM-DD')

  let mtd = 0
  let ytd = 0

  for (let i = 0; i < dates.length; i++) {
    const mwh = project_data[i] ?? 0
    const dateKey = dates[i]

    ytd += mwh
    if (dateKey >= monthStartKey) mtd += mwh
  }

  return {
    energyMTD: mtd,
    energyYTD: ytd,
    ppaRate,
    revenueMTD: mtd * ppaRate,
    revenueYTD: ytd * ppaRate,
  }
}
