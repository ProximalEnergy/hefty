import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface EquipmentAnalysisCombiner {
  x: string[]
  y: number[]
  y_norm: number[]
}

const URL =
  '/v1/protected/web-application/projects/{project_id}/equipment-analysis/combiner'

type get = types.paths[typeof URL]['get']
type pathParams = get['parameters']['path']
type getQueryParams = get['parameters']['query']

export const useGetEquipmentAnalysisCombiner = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: pathParams
  queryParams?: getQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = { url: URL }

  const defaultQueryOptions = {}

  return useCustomQuery<EquipmentAnalysisCombiner>({
    axiosConfig,
    queryName: 'getEquipmentAnalysisCombiner',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
