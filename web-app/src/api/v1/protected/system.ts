import type { Endpoint } from '@/api/utils'
import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

const URL_METER_POWER_AND_EXPECTED_POWER_V3 =
  '/v1/protected/system/{project_id}/meter-power-and-expected-power-v3'
type GetMeterPowerAndExpectedPowerV3 = Endpoint<
  typeof URL_METER_POWER_AND_EXPECTED_POWER_V3,
  'get'
>

export const useGetMeterPowerAndExpectedPowerV3 = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: GetMeterPowerAndExpectedPowerV3['PathParams']
  queryParams: GetMeterPowerAndExpectedPowerV3['QueryParams']
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL_METER_POWER_AND_EXPECTED_POWER_V3,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  return useCustomQuery<GetMeterPowerAndExpectedPowerV3['Response']>({
    axiosConfig,
    queryName: 'getMeterPowerAndExpectedPowerV3',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
