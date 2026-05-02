import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

const _COMPONENT_NAME = 'RootCauseInterface'
const URL = '/v1/operational/root-causes'

type RootCause = types.components['schemas'][typeof _COMPONENT_NAME]
type get = types.paths[typeof URL]['get']
type getQueryParams = get['parameters']['query']

export const useGetRootCauses = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: getQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL,
  }

  const defaultQueryOptions = {}

  return useCustomQuery<RootCause[]>({
    axiosConfig,
    queryName: 'getRootCauses',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
