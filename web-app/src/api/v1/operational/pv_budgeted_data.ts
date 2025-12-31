import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface PVBudgetedSeries {
  pv_budgeted_series_id: number
  company_id: string
  project_id: string
  p_value: string
  frequency: string
  soiling_mode: string | null
  soiling_fixed_percentage: number | null
  tmy_source: string | null
  model_version: string | null
  filename: string | null
}

interface PVBudgetedData {
  pv_budgeted_series_id: number
  time: string
  poi_ac_power: number
  ghi: number | null
  poa: number
  temperature: number | null
  soiling_percentage: number | null
}

interface PVBudgetedDailyData {
  date: string
  daily_energy_mwh: number
  avg_ghi: number | null
  avg_poa: number
  avg_temperature: number | null
  avg_soiling_percentage: number | null
  degradation_factor: number
  years_since_cod: number
}

export const useGetPVBudgetedSeries = ({
  queryParams,
  queryOptions = {},
}: {
  queryParams: {
    project_id: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: '/v1/operational/pv-budgeted-data/series',
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<PVBudgetedSeries[]>({
    axiosConfig,
    queryName: 'getPVBudgetedSeries',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetPVBudgetedData = ({
  queryParams,
  queryOptions = {},
}: {
  queryParams: {
    project_id: string
    start: string
    end: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: '/v1/operational/pv-budgeted-data',
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
    gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days
  }

  return useCustomQuery<PVBudgetedData[]>({
    axiosConfig,
    queryName: 'getPVBudgetedData',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetPVBudgetedDataBySeries = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: {
    pv_budgeted_series_id: number
  }
  queryParams: {
    project_id: string
    start: string
    end: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/pv-budgeted-data/series/${pathParams.pv_budgeted_series_id}`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
    gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days
  }

  return useCustomQuery<PVBudgetedData[]>({
    axiosConfig,
    queryName: 'getPVBudgetedDataBySeries',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetPVBudgetedSeriesDailyData = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: {
    pv_budgeted_series_id: number
  }
  queryParams: {
    project_id: string
    start_date: string
    end_date: string
    degradation_rate?: number
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/pv-budgeted-data/series/${pathParams.pv_budgeted_series_id}/daily-data`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
    gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days
  }

  return useCustomQuery<PVBudgetedDailyData[]>({
    axiosConfig,
    queryName: 'getPVBudgetedSeriesDailyData',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
