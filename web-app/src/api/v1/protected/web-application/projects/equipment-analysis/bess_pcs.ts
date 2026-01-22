import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface EquipmentAnalysisBESSPCS {
  x: string[]
  y: number[]
  name: string
}

const URL =
  '/v1/protected/web-application/projects/{project_id}/equipment-analysis/bess-pcs'

type get = types.paths[typeof URL]['get']
type pathParams = get['parameters']['path']
type getQueryParams = get['parameters']['query']

export const useGetEquipmentAnalysisBESSPCS = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: pathParams
  queryParams: getQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL,
  }

  const defaultQueryOptions = {}

  return useCustomQuery<EquipmentAnalysisBESSPCS[]>({
    axiosConfig,
    queryName: 'getEquipmentAnalysisBESSPCS',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
