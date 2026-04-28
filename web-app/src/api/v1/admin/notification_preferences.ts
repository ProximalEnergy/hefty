import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { QUERY_TIME } from '@/utils/queryTiming'
import { useAuth } from '@clerk/react'
import { notifications } from '@mantine/notifications'
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
type NotificationPreferenceBulkUpdate =
  types.components['schemas']['NotificationPreferenceBulkUpdate']
type NotificationPreferenceFieldsUpdate = Pick<
  NotificationPreferenceBulkUpdate,
  | 'in_app_enabled'
  | 'email_enabled'
  | 'in_app_min_severity'
  | 'email_min_severity'
>

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

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    refetchOnMount: false, // Only refetch if explicitly requested
    refetchOnReconnect: false, // Don't refetch on reconnect
    staleTime: QUERY_TIME.NEVER, // User settings don't change unless user changes them
    gcTime: Infinity, // Keep in cache forever (formerly cacheTime)
  }

  return useCustomQuery<NotificationPreference[]>({
    axiosConfig,
    queryName: 'getNotificationPreferences',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

// Track mutation order per preference to ensure we only apply the latest mutation
// Use WeakMap keyed by QueryClient instance to ensure state is tied to user session
const mutationTimestampsByClient = new WeakMap<
  ReturnType<typeof useQueryClient>,
  Map<string, number>
>()

const getPreferenceKey = (
  projectId: string,
  notificationTypeId: number,
): string => {
  return `${projectId}-${notificationTypeId}`
}

const getMutationTimestamps = (
  queryClient: ReturnType<typeof useQueryClient>,
): Map<string, number> => {
  let timestamps = mutationTimestampsByClient.get(queryClient)
  if (!timestamps) {
    timestamps = new Map<string, number>()
    mutationTimestampsByClient.set(queryClient, timestamps)
  }
  return timestamps
}

const getPreferenceFieldUpdates = ({
  data,
  serverPreference,
}: {
  data: NotificationPreferenceFieldsUpdate
  serverPreference?: NotificationPreference
}): Partial<NotificationPreference> => ({
  ...(data.in_app_enabled !== undefined &&
    data.in_app_enabled !== null && {
      in_app_enabled: serverPreference?.in_app_enabled ?? data.in_app_enabled,
    }),
  ...(data.email_enabled !== undefined &&
    data.email_enabled !== null && {
      email_enabled: serverPreference?.email_enabled ?? data.email_enabled,
    }),
  ...(data.in_app_min_severity !== undefined &&
    data.in_app_min_severity !== null && {
      in_app_min_severity:
        serverPreference?.in_app_min_severity ?? data.in_app_min_severity,
    }),
  ...(data.email_min_severity !== undefined &&
    data.email_min_severity !== null && {
      email_min_severity:
        serverPreference?.email_min_severity ?? data.email_min_severity,
    }),
})

const createOptimisticNotificationPreference = ({
  data,
  notificationType,
  notificationTypeId,
  projectId,
}: {
  data: NotificationPreferenceFieldsUpdate
  notificationType?: NotificationType
  notificationTypeId: number
  projectId: string
}): NotificationPreference => ({
  notification_preference_id: -1,
  user_id: '',
  project_id: projectId,
  notification_type_id: notificationTypeId,
  in_app_enabled:
    data.in_app_enabled ??
    (data.in_app_min_severity !== undefined && data.in_app_min_severity !== null
      ? true
      : (notificationType?.in_app_enabled_default ?? false)),
  email_enabled:
    data.email_enabled ??
    (data.email_min_severity !== undefined && data.email_min_severity !== null
      ? true
      : (notificationType?.email_enabled_default ?? false)),
  in_app_min_severity:
    data.in_app_min_severity ??
    notificationType?.in_app_severity_default ??
    'info',
  email_min_severity:
    data.email_min_severity ??
    notificationType?.email_severity_default ??
    'info',
})

const mergeNotificationPreferences = ({
  existingPreferences,
  updatedPreferences,
}: {
  existingPreferences: NotificationPreference[]
  updatedPreferences: NotificationPreference[]
}): NotificationPreference[] => {
  const mergedPreferences = [...existingPreferences]

  updatedPreferences.forEach((updatedPreference) => {
    const existingIndex = mergedPreferences.findIndex(
      (preference) =>
        preference.project_id === updatedPreference.project_id &&
        preference.notification_type_id ===
          updatedPreference.notification_type_id,
    )

    if (existingIndex >= 0) {
      mergedPreferences[existingIndex] = updatedPreference
      return
    }

    mergedPreferences.push(updatedPreference)
  })

  return mergedPreferences
}

const showNotificationPreferenceSaveSuccess = () => {
  notifications.show({
    title: 'Saved',
    message: 'Notification settings updated.',
    color: 'green',
  })
}

const showNotificationPreferenceSaveError = () => {
  notifications.show({
    title: 'Save failed',
    message: 'Unable to update notification settings.',
    color: 'red',
  })
}

export const useUpdateNotificationPreference = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  const mutationTimestamps = getMutationTimestamps(queryClient)

  return useMutation<
    NotificationPreference,
    Error,
    NotificationPreferenceUpdate,
    {
      previousQueries: Map<string, NotificationPreference[] | undefined>
      mutationTimestamp: number
      preferenceKey: string
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
      const preferenceKey = getPreferenceKey(projectId, notificationTypeId)

      // Record this mutation's timestamp - this ensures we only apply the latest mutation
      const mutationTimestamp = Date.now()
      mutationTimestamps.set(preferenceKey, mutationTimestamp)

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
        .findAll({ queryKey: ['getNotificationPreferences'] })
        .forEach((query) => {
          const keyStr = JSON.stringify(query.queryKey)
          previousQueries.set(
            keyStr,
            query.state.data as NotificationPreference[] | undefined,
          )
        })

      // Optimistically update all matching query caches
      queryClient
        .getQueryCache()
        .findAll({ queryKey: ['getNotificationPreferences'] })
        .forEach((query) => {
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
                // Note: null values mean "don't change" per backend logic, so we only update non-null fields
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
        })

      // Return context with the previous values and mutation tracking info
      return { previousQueries, mutationTimestamp, preferenceKey }
    },
    onSuccess: (data, variables, context) => {
      const preferenceKey =
        context?.preferenceKey ??
        getPreferenceKey(variables.project_id, variables.notification_type_id)
      const mutationTimestamp = context?.mutationTimestamp ?? 0

      // Only apply this mutation if it's still the latest one for this preference
      // This prevents older mutations from overwriting newer optimistic updates
      const latestTimestamp = mutationTimestamps.get(preferenceKey) ?? 0
      if (mutationTimestamp < latestTimestamp) {
        // A newer mutation has already started, ignore this older result
        return
      }

      // Update query cache directly with server response, merging intelligently
      // to prevent race conditions when multiple mutations happen rapidly or GET
      // requests complete concurrently
      queryClient
        .getQueryCache()
        .findAll({ queryKey: ['getNotificationPreferences'] })
        .forEach((query) => {
          queryClient.setQueryData<NotificationPreference[]>(
            query.queryKey,
            (old) => {
              if (!old) return old

              const existingIndex = old.findIndex(
                (pref) =>
                  pref.project_id === variables.project_id &&
                  pref.notification_type_id === variables.notification_type_id,
              )

              if (existingIndex >= 0) {
                // Always merge intelligently: only update fields that this mutation was updating.
                // This preserves concurrent optimistic updates from other mutations or GET requests
                // that may have completed while this mutation was in flight.
                const updated = [...old]
                const current = updated[existingIndex]

                // Merge server response, but only update fields that were explicitly changed
                // in this mutation (from variables), preserving other fields from current cache
                updated[existingIndex] = {
                  ...current,
                  ...(variables.in_app_enabled !== undefined && {
                    in_app_enabled: data.in_app_enabled,
                  }),
                  ...(variables.email_enabled !== undefined && {
                    email_enabled: data.email_enabled,
                  }),
                  ...(variables.in_app_min_severity !== undefined && {
                    in_app_min_severity: data.in_app_min_severity,
                  }),
                  ...(variables.email_min_severity !== undefined && {
                    email_min_severity: data.email_min_severity,
                  }),
                  // Always update the ID and other server fields
                  notification_preference_id: data.notification_preference_id,
                  user_id: data.user_id,
                }
                return updated
              }

              // Add new preference if it doesn't exist
              return [...old, data]
            },
          )
        })

      // Clean up: remove timestamp once mutation completes successfully
      // Only remove if this was the latest mutation (to avoid race conditions)
      if (mutationTimestamp >= latestTimestamp) {
        mutationTimestamps.delete(preferenceKey)
      }

      showNotificationPreferenceSaveSuccess()
    },
    onError: (_err, variables, context) => {
      const preferenceKey =
        context?.preferenceKey ??
        getPreferenceKey(variables.project_id, variables.notification_type_id)
      const mutationTimestamp = context?.mutationTimestamp ?? 0

      // Only rollback if this was the latest mutation (or if we don't have tracking info)
      // This prevents rolling back when a newer mutation has already updated the cache
      const latestTimestamp = mutationTimestamps.get(preferenceKey) ?? 0
      const shouldRollback =
        !context?.mutationTimestamp || mutationTimestamp >= latestTimestamp

      if (shouldRollback && context?.previousQueries) {
        // Rollback to the previous values on error
        // We don't invalidate queries here because:
        // 1. We've already rolled back to the previous state
        // 2. Invalidating would trigger refetches that can interfere with other mutations
        // 3. The data is already correct after rollback
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

      // Clean up timestamp if this was the latest mutation
      if (shouldRollback) {
        mutationTimestamps.delete(preferenceKey)
        showNotificationPreferenceSaveError()
      }
    },
  })
}

export const useBulkUpdateNotificationPreferences = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  const mutationTimestamps = getMutationTimestamps(queryClient)

  return useMutation<
    NotificationPreference[],
    Error,
    NotificationPreferenceBulkUpdate,
    {
      previousQueries: Map<string, NotificationPreference[] | undefined>
      mutationTimestamp: number
      preferenceKeys: string[]
    }
  >({
    mutationFn: async (data) => {
      const token = await getToken({ template: 'default' })
      const response = await axios.put<NotificationPreference[]>(
        `${baseURL}/v1/admin/notification-preferences/bulk`,
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
      const mutationTimestamp = Date.now()
      const preferenceKeys = data.project_ids.flatMap((projectId) =>
        data.notification_type_ids.map((notificationTypeId) =>
          getPreferenceKey(projectId, notificationTypeId),
        ),
      )

      preferenceKeys.forEach((preferenceKey) => {
        mutationTimestamps.set(preferenceKey, mutationTimestamp)
      })

      await queryClient.cancelQueries({
        predicate: (query) =>
          query.queryKey[0] === 'getNotificationPreferences',
      })

      const previousQueries = new Map<
        string,
        NotificationPreference[] | undefined
      >()
      queryClient
        .getQueryCache()
        .findAll({ queryKey: ['getNotificationPreferences'] })
        .forEach((query) => {
          const keyStr = JSON.stringify(query.queryKey)
          previousQueries.set(
            keyStr,
            query.state.data as NotificationPreference[] | undefined,
          )
        })

      const notificationTypes = queryClient.getQueryData<NotificationType[]>([
        'getNotificationTypes',
      ])

      queryClient
        .getQueryCache()
        .findAll({ queryKey: ['getNotificationPreferences'] })
        .forEach((query) => {
          queryClient.setQueryData<NotificationPreference[]>(
            query.queryKey,
            (old) => {
              if (!old) return old

              const updatedPreferences = [...old]
              data.project_ids.forEach((projectId) => {
                data.notification_type_ids.forEach((notificationTypeId) => {
                  const existingIndex = updatedPreferences.findIndex(
                    (preference) =>
                      preference.project_id === projectId &&
                      preference.notification_type_id === notificationTypeId,
                  )

                  if (existingIndex >= 0) {
                    updatedPreferences[existingIndex] = {
                      ...updatedPreferences[existingIndex],
                      ...getPreferenceFieldUpdates({ data }),
                    }
                    return
                  }

                  const notificationType = notificationTypes?.find(
                    (type) => type.notification_type_id === notificationTypeId,
                  )
                  updatedPreferences.push(
                    createOptimisticNotificationPreference({
                      data,
                      notificationType,
                      notificationTypeId,
                      projectId,
                    }),
                  )
                })
              })

              return updatedPreferences
            },
          )
        })

      return { previousQueries, mutationTimestamp, preferenceKeys }
    },
    onSuccess: (data, _variables, context) => {
      const mutationTimestamp = context?.mutationTimestamp ?? 0
      const latestPreferences = data.filter((preference) => {
        const preferenceKey = getPreferenceKey(
          preference.project_id,
          preference.notification_type_id,
        )
        const latestTimestamp = mutationTimestamps.get(preferenceKey) ?? 0
        return mutationTimestamp >= latestTimestamp
      })

      if (latestPreferences.length > 0) {
        queryClient
          .getQueryCache()
          .findAll({ queryKey: ['getNotificationPreferences'] })
          .forEach((query) => {
            queryClient.setQueryData<NotificationPreference[]>(
              query.queryKey,
              (old) => {
                if (!old) return old
                return mergeNotificationPreferences({
                  existingPreferences: old,
                  updatedPreferences: latestPreferences,
                })
              },
            )
          })
      }

      latestPreferences.forEach((preference) => {
        const preferenceKey = getPreferenceKey(
          preference.project_id,
          preference.notification_type_id,
        )
        const latestTimestamp = mutationTimestamps.get(preferenceKey) ?? 0
        if (mutationTimestamp >= latestTimestamp) {
          mutationTimestamps.delete(preferenceKey)
        }
      })

      if (latestPreferences.length > 0) {
        showNotificationPreferenceSaveSuccess()
      }
    },
    onError: (_err, _variables, context) => {
      const mutationTimestamp = context?.mutationTimestamp ?? 0
      const shouldRollback =
        !context ||
        context.preferenceKeys.every((preferenceKey) => {
          const latestTimestamp = mutationTimestamps.get(preferenceKey) ?? 0
          return mutationTimestamp >= latestTimestamp
        })

      if (shouldRollback && context?.previousQueries) {
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

      context?.preferenceKeys.forEach((preferenceKey) => {
        const latestTimestamp = mutationTimestamps.get(preferenceKey) ?? 0
        if (mutationTimestamp >= latestTimestamp) {
          mutationTimestamps.delete(preferenceKey)
        }
      })

      if (shouldRollback) {
        showNotificationPreferenceSaveError()
      }
    },
  })
}
