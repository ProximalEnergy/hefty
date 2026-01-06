import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

import type { NotificationType } from './notification_types'

export type NotificationPreference =
  types.components['schemas']['NotificationPreference']
type NotificationPreferenceUpdate =
  types.components['schemas']['NotificationPreferenceUpdate'] & {
    project_id: string
    notification_type_id: number
  }

export const useGetNotificationPreferences = ({
  projectIds,
  queryOptions = {},
}: {
  projectIds?: string[]
  queryOptions?: Partial<UseQueryOptions<NotificationPreference[]>>
} = {}) => {
  const axiosConfig = {
    url: '/v1/admin/notification-preferences',
    method: 'GET' as const,
  }

  const queryParams = projectIds ? { project_ids: projectIds } : {}

  return useCustomQuery<NotificationPreference[]>({
    axiosConfig,
    queryName: 'getNotificationPreferences',
    queryParams,
    queryOptions,
  })
}

export const useUpdateNotificationPreference = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation<
    NotificationPreference,
    Error,
    NotificationPreferenceUpdate,
    {
      previousQueries: Map<string, NotificationPreference[] | undefined>
    }
  >({
    mutationFn: async (data) => {
      const token = await getToken({ template: 'default' })
      const response = await axios.put<NotificationPreference>(
        `${baseURL}/v1/admin/notification-preferences`,
        data,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        },
      )
      return response.data
    },
    onMutate: async (data) => {
      const projectId = data.project_id
      const notificationTypeId = data.notification_type_id
      // Cancel any outgoing refetches for all notification preference queries
      await queryClient.cancelQueries({
        predicate: (query) =>
          query.queryKey[0] === 'getNotificationPreferences',
      })

      // Snapshot all previous values (since query keys may vary by projectIds)
      const previousQueries = new Map<
        string,
        NotificationPreference[] | undefined
      >()
      queryClient
        .getQueryCache()
        .getAll()
        .forEach((query) => {
          if (query.queryKey[0] === 'getNotificationPreferences') {
            const keyStr = JSON.stringify(query.queryKey)
            previousQueries.set(
              keyStr,
              query.state.data as NotificationPreference[] | undefined,
            )
          }
        })

      // Optimistically update all matching query caches
      queryClient
        .getQueryCache()
        .getAll()
        .forEach((query) => {
          if (query.queryKey[0] === 'getNotificationPreferences') {
            queryClient.setQueryData<NotificationPreference[]>(
              query.queryKey,
              (old) => {
                if (!old) return old

                const existingIndex = old.findIndex(
                  (pref) =>
                    pref.project_id === projectId &&
                    pref.notification_type_id === notificationTypeId,
                )

                if (existingIndex >= 0) {
                  // Update existing preference
                  const updated = [...old]
                  const existing = updated[existingIndex]
                  updated[existingIndex] = {
                    ...existing,
                    ...(data.in_app_enabled !== undefined &&
                      data.in_app_enabled !== null && {
                        in_app_enabled: data.in_app_enabled,
                      }),
                    ...(data.email_enabled !== undefined &&
                      data.email_enabled !== null && {
                        email_enabled: data.email_enabled,
                      }),
                    ...(data.in_app_min_severity !== undefined &&
                      data.in_app_min_severity !== null && {
                        in_app_min_severity: data.in_app_min_severity,
                      }),
                    ...(data.email_min_severity !== undefined &&
                      data.email_min_severity !== null && {
                        email_min_severity: data.email_min_severity,
                      }),
                  }
                  return updated
                }

                // Preference doesn't exist yet in this query's data.
                // Get notification type defaults from cache to preserve current UI state
                const notificationTypes = queryClient.getQueryData<
                  NotificationType[]
                >(['getNotificationTypes'])
                const notificationType = notificationTypes?.find(
                  (type) => type.notification_type_id === notificationTypeId,
                )

                // Use defaults from notification type for fields we're not updating
                // This preserves what the UI is currently displaying
                const optimisticPreference: NotificationPreference = {
                  notification_preference_id: -1,
                  user_id: '',
                  project_id: projectId,
                  notification_type_id: notificationTypeId,
                  in_app_enabled:
                    data.in_app_enabled !== undefined &&
                    data.in_app_enabled !== null
                      ? data.in_app_enabled
                      : data.in_app_min_severity !== undefined
                        ? true
                        : (notificationType?.in_app_enabled_default ?? false),
                  email_enabled:
                    data.email_enabled !== undefined &&
                    data.email_enabled !== null
                      ? data.email_enabled
                      : data.email_min_severity !== undefined
                        ? true
                        : (notificationType?.email_enabled_default ?? false),
                  in_app_min_severity:
                    data.in_app_min_severity ??
                    notificationType?.in_app_severity_default ??
                    'info',
                  email_min_severity:
                    data.email_min_severity ??
                    notificationType?.email_severity_default ??
                    'info',
                }

                return [...old, optimisticPreference]
              },
            )
          }
        })

      // Return context with the previous values
      return { previousQueries }
    },
    onError: (_err, _variables, context) => {
      // Rollback to the previous values on error
      if (context?.previousQueries) {
        context.previousQueries.forEach(
          (
            previousData: NotificationPreference[] | undefined,
            queryKeyStr: string,
          ) => {
            const queryKey = JSON.parse(queryKeyStr)
            queryClient.setQueryData(queryKey, previousData)
          },
        )
      }
    },
    onSettled: () => {
      // Always refetch after error or success to ensure we have the latest data
      queryClient.invalidateQueries({
        predicate: (query) =>
          query.queryKey[0] === 'getNotificationPreferences',
      })
    },
  })
}
