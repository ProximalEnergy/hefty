import { useCustomQuery } from '@/hooks/api'
import * as types from '@/hooks/types'
import { UseQueryOptions } from '@tanstack/react-query'

export const useGetBlockDropdown = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/ui/${pathParams.projectId}/block-dropdown`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<types.BlockDropdownItem[]>({
    axiosConfig,
    queryName: 'getBlockDropdown',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
