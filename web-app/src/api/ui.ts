import type { components } from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
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

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<components['schemas']['BlockDropdownItem'][]>({
    axiosConfig,
    queryName: 'getBlockDropdown',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
