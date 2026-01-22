import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface Data {
  x: string[]
  y: number[]
  name: string
}

interface EquipmentAnalysisBESS {
  bess_enclosure: Data[]
  bess_bank: Data[]
  bess_string: Data[]
}

const URL =
  '/v1/protected/web-application/projects/{project_id}/equipment-analysis/bess'

type get = types.paths[typeof URL]['get']
type pathParams = get['parameters']['path']
type getQueryParams = get['parameters']['query']

export const useGetEquipmentAnalysisBESS = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: pathParams
  queryParams: getQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = { url: URL }

  const defaultQueryOptions = {}

  return useCustomQuery<EquipmentAnalysisBESS>({
    axiosConfig,
    queryName: 'getEquipmentAnalysisBESS',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
