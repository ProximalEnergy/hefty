import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

type SettlementPointType = {
  settlement_point_type_id: number
  name_short: string
  name_long: string
}

type SettlementPointCore = {
  settlement_point_id: number
  name: string
  settlement_point_type_id: number
  load_zone_id: number | null
  trading_hub_id: number | null
}

type SettlementPoint = SettlementPointCore & {
  settlement_point_type: SettlementPointType
  load_zone: SettlementPointCore | null
  trading_hub: SettlementPointCore | null
}

export const useGetERCOTSettlementPoints = ({
  queryParams,
  queryOptions = {},
}: {
  queryParams?: { deep: boolean }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/development/ercot/settlement-points`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<SettlementPoint[]>({
    axiosConfig,
    queryName: 'getERCOTSettlementPoints',
    pathParams: {},
    queryParams: {},
    queryOptions,
  })
}

type ERCOTPrices = {
  x: string[]
  y: number[]
  name: string
}

export const useGetERCOTPrices = ({
  queryParams,
  queryOptions = {},
}: {
  queryParams: { settlement_point_id: number; start: string; end: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/development/ercot/prices`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<ERCOTPrices[]>({
    axiosConfig,
    queryName: 'getERCOTPrices',
    pathParams: {},
    queryParams,
    queryOptions,
  })
}
