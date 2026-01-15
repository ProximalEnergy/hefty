import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

const _COMPONENT_NAME = 'UserSubscription'
const URL = '/v1/admin/subscriptions'

type UserSubscription = types.components['schemas'][typeof _COMPONENT_NAME]

export const useGetSubscriptions = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL,
  }

  const defaultQueryOptions = {}

  return useCustomQuery<UserSubscription[]>({
    axiosConfig,
    queryName: 'getSubscriptions',
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
