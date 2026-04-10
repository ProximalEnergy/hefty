import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

interface Data {
  times: string[]
  positions: { [key: string]: number[] }
  setpoints: { [key: string]: number[] }
}

const URL =
  '/v1/protected/web-application/projects/{project_id}/equipment-analysis/tracker/{pv_block_id}'

type get = types.paths[typeof URL]['get']
type pathParams = get['parameters']['path']
type getQueryParams = get['parameters']['query']

export const useGetEquipmentAnalysisTrackerBlock = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: pathParams
  queryParams: getQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = { url: URL }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  return useCustomQuery<Data>({
    axiosConfig,
    queryName: 'getEquipmentAnalysisTrackerBlock',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
