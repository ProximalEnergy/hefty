import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

const _COMPONENT_NAME = 'FailureMode'
const URL = '/v1/operational/failure-modes'

type FailureMode = types.components['schemas'][typeof _COMPONENT_NAME]
type get = types.paths[typeof URL]['get']
type getQueryParams = get['parameters']['query']

export const useGetFailureModes = ({
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

  return useCustomQuery<FailureMode[]>({
    axiosConfig,
    queryName: 'getFailureModes',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
