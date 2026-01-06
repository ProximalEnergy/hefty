import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

export type NotificationType = types.components['schemas']['NotificationType']

export const useGetNotificationTypes = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions<NotificationType[]>>
} = {}) => {
  const axiosConfig = {
    url: '/v1/admin/notification-types',
    method: 'GET' as const,
  }

  return useCustomQuery<NotificationType[]>({
    axiosConfig,
    queryName: 'getNotificationTypes',
    queryOptions,
  })
}
