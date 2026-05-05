import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'
import { FeatureCollection } from 'geojson'

const URL =
  '/v1/operational/projects/{project_id}/gis/combiner/{block_device_id}'

type get = types.paths[typeof URL]['get']
type getPathParams = get['parameters']['path']

export const useGetGISCombinerBlock = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: getPathParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = { url: URL }

  const defaultQueryOptions = { staleTime: QUERY_TIME.ONE_MINUTE }

  return useCustomQuery<FeatureCollection>({
    axiosConfig,
    queryName: 'getGISCombinerBlock',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
