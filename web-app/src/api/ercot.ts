import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

const SETTLEMENT_POINTS_URL = '/v1/development/ercot/settlement-points'
const PRICES_URL = '/v1/development/ercot/prices'

type SettlementPointsGet = types.paths[typeof SETTLEMENT_POINTS_URL]['get']
type SettlementPointQueryParams = SettlementPointsGet['parameters']['query']
type SettlementPointResponse =
  SettlementPointsGet['responses'][200]['content']['application/json']

export const useGetERCOTSettlementPoints = ({
  queryParams,
  queryOptions = {},
}: {
  queryParams?: SettlementPointQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: SETTLEMENT_POINTS_URL,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<SettlementPointResponse>({
    axiosConfig,
    queryName: 'getERCOTSettlementPoints',
    pathParams: {},
    queryParams: {},
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

type PricesGet = types.paths[typeof PRICES_URL]['get']
type PricesQueryParams = PricesGet['parameters']['query']
type ERCOTPrices = Pick<
  types.components['schemas']['DataTimeSeries'],
  'x' | 'y' | 'name'
>
type ERCOTPricesResponse = ERCOTPrices[]

export const useGetERCOTPrices = ({
  queryParams,
  queryOptions = {},
}: {
  queryParams: PricesQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: PRICES_URL,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<ERCOTPricesResponse>({
    axiosConfig,
    queryName: 'getERCOTPrices',
    pathParams: {},
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
