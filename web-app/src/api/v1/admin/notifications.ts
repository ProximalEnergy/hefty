import { NotificationStateEnum } from '@/api/enumerations'
import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { PERSONAL_PORTFOLIO_EXCLUDED_PROJECT_IDS_KEY } from '@/utils/personalPortfolio'
import { QUERY_TIME } from '@/utils/queryTiming'
import { useAuth } from '@clerk/react'
import { useLocalStorage } from '@mantine/hooks'
import {
  type InfiniteData,
  UseInfiniteQueryOptions,
  UseQueryOptions,
  useInfiniteQuery,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'
import qs from 'qs'

const _COMPONENT_NAME = 'NotificationInterface'

type Notification = types.components['schemas'][typeof _COMPONENT_NAME]
export type NotificationPage = {
  notifications: Notification[]
  nextOffset: number | undefined
}

type InfiniteNotificationsQueryKey = readonly [
  'getNotificationsInfinite',
  {
    pageSize: number
    projectIdsExcluded: string[]
  },
]

const areProjectIdSetsEqual = (
  firstProjectIds: readonly string[],
  secondProjectIds: readonly string[],
) => {
  if (firstProjectIds.length !== secondProjectIds.length) {
    return false
  }

  const secondProjectIdSet = new Set(secondProjectIds)
  return firstProjectIds.every((projectId) => secondProjectIdSet.has(projectId))
}

const getInfiniteNotificationsProjectIdsExcluded = (
  queryKey: readonly unknown[],
) => {
  const queryParams = queryKey[1]
  if (queryParams == null || typeof queryParams !== 'object') {
    return undefined
  }

  const { projectIdsExcluded } = queryParams as {
    projectIdsExcluded?: unknown
  }
  if (!Array.isArray(projectIdsExcluded)) {
    return undefined
  }

  if (
    projectIdsExcluded.every(
      (projectId): projectId is string => typeof projectId === 'string',
    )
  ) {
    return projectIdsExcluded
  }

  return undefined
}

const isCurrentPortfolioNotificationsQuery = (
  queryKey: readonly unknown[],
  projectIdsExcluded: readonly string[],
) => {
  if (queryKey[0] !== 'getNotificationsInfinite') {
    return false
  }

  const queryProjectIdsExcluded =
    getInfiniteNotificationsProjectIdsExcluded(queryKey)

  if (queryProjectIdsExcluded == null) {
    return projectIdsExcluded.length === 0
  }

  return areProjectIdSetsEqual(queryProjectIdsExcluded, projectIdsExcluded)
}

export const usePersonalPortfolioExcludedProjectIds = () => {
  const [excludedProjectIds] = useLocalStorage<string[]>({
    key: PERSONAL_PORTFOLIO_EXCLUDED_PROJECT_IDS_KEY,
    defaultValue: [],
    getInitialValueInEffect: false,
  })

  return excludedProjectIds
}

export const serializeNotificationQueryParams = (
  params: Record<string, unknown>,
) => qs.stringify(params, { arrayFormat: 'repeat' })

export const useInfiniteNotifications = ({
  pageSize = 50,
  queryOptions = {},
}: {
  pageSize?: number
  queryOptions?: Partial<
    UseInfiniteQueryOptions<
      NotificationPage,
      unknown,
      InfiniteData<NotificationPage>,
      InfiniteNotificationsQueryKey,
      number
    >
  >
}) => {
  const { getToken } = useAuth()
  const projectIdsExcluded = usePersonalPortfolioExcludedProjectIds()

  return useInfiniteQuery<
    NotificationPage,
    unknown,
    InfiniteData<NotificationPage>,
    InfiniteNotificationsQueryKey,
    number
  >({
    queryKey: ['getNotificationsInfinite', { pageSize, projectIdsExcluded }],
    queryFn: async ({ pageParam = 0 }) => {
      const token = await getToken({ template: 'default' })
      const response = await axios.get(`${baseURL}/v1/admin/notifications`, {
        headers: { Authorization: `Bearer ${token}` },
        params: {
          limit: pageSize,
          offset: pageParam,
          project_ids_excluded: projectIdsExcluded,
        },
        paramsSerializer: serializeNotificationQueryParams,
      })
      const data = response.data as Notification[]
      return {
        notifications: data,
        nextOffset: data.length === pageSize ? pageParam + pageSize : undefined,
      }
    },
    getNextPageParam: (lastPage) => lastPage.nextOffset,
    initialPageParam: 0,
    // 5 minutes - prevent frequent background refetches
    staleTime: QUERY_TIME.FIVE_MINUTES,
    refetchOnWindowFocus: false,
    ...queryOptions,
  })
}

export const useGetUnreadNotificationCount = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const projectIdsExcluded = usePersonalPortfolioExcludedProjectIds()
  const axiosConfig = {
    url: `/v1/admin/notifications/unread-count`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    // 30 seconds - count doesn't need to be super fresh
    staleTime: QUERY_TIME.THIRTY_SECONDS,
    refetchInterval: QUERY_TIME.THIRTY_SECONDS,
  }

  return useCustomQuery<{ count: number }>({
    axiosConfig,
    queryName: 'getUnreadNotificationCount',
    queryParams: { project_ids_excluded: projectIdsExcluded },
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useMarkNotificationAsRead = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (notificationId: number) => {
      const token = await getToken({ template: 'default' })
      const response = await axios.put(
        `${baseURL}/v1/admin/notifications/${notificationId}/read`,
        {},
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      )
      return response.data
    },
    onMutate: async (notificationId: number) => {
      // Cancel outgoing refetches for all page sizes.
      await queryClient.cancelQueries({
        predicate: (query) => query.queryKey[0] === 'getNotificationsInfinite',
      })

      // Get all infinite notification queries.
      const allInfiniteQueries = queryClient.getQueriesData<
        InfiniteData<NotificationPage>
      >({
        predicate: (query) => query.queryKey[0] === 'getNotificationsInfinite',
      })

      // Store previous values for rollback
      const previousQueries = new Map(allInfiniteQueries)

      // Optimistically update all infinite queries
      allInfiniteQueries.forEach(([queryKey, data]) => {
        if (data) {
          const nextPages = data.pages.map((page) => ({
            ...page,
            notifications: page.notifications.map((notification) =>
              notification.notification_id === notificationId
                ? { ...notification, state: NotificationStateEnum.READ }
                : notification,
            ),
          }))
          queryClient.setQueryData<InfiniteData<NotificationPage>>(queryKey, {
            ...data,
            pages: nextPages,
          })
        }
      })

      // Return context with the snapshotted values
      return { previousQueries }
    },
    onError: (_err, _notificationId, context) => {
      // Rollback to the previous values if mutation fails
      if (context?.previousQueries) {
        context.previousQueries.forEach((data, queryKey) => {
          queryClient.setQueryData(queryKey, data)
        })
      }
      // Invalidate on error to refetch and ensure consistency
      queryClient.invalidateQueries({
        predicate: (query) => query.queryKey[0] === 'getNotificationsInfinite',
      })
      queryClient.invalidateQueries({
        queryKey: ['getUnreadNotificationCount'],
      })
    },
    onSuccess: () => {
      // Only invalidate unread count on success, keep optimistic update
      queryClient.invalidateQueries({
        queryKey: ['getUnreadNotificationCount'],
      })
    },
  })
}

export const useMarkNotificationAsUnread = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (notificationId: number) => {
      const token = await getToken({ template: 'default' })
      const response = await axios.put(
        `${baseURL}/v1/admin/notifications/${notificationId}/unread`,
        {},
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      )
      return response.data
    },
    onMutate: async (notificationId: number) => {
      // Cancel outgoing refetches for all page sizes.
      await queryClient.cancelQueries({
        predicate: (query) => query.queryKey[0] === 'getNotificationsInfinite',
      })

      // Get all infinite notification queries.
      const allInfiniteQueries = queryClient.getQueriesData<
        InfiniteData<NotificationPage>
      >({
        predicate: (query) => query.queryKey[0] === 'getNotificationsInfinite',
      })

      // Store previous values for rollback
      const previousQueries = new Map(allInfiniteQueries)

      // Optimistically update all infinite queries
      allInfiniteQueries.forEach(([queryKey, data]) => {
        if (data) {
          const nextPages = data.pages.map((page) => ({
            ...page,
            notifications: page.notifications.map((notification) =>
              notification.notification_id === notificationId
                ? { ...notification, state: NotificationStateEnum.UNREAD }
                : notification,
            ),
          }))
          queryClient.setQueryData<InfiniteData<NotificationPage>>(queryKey, {
            ...data,
            pages: nextPages,
          })
        }
      })

      // Return context with the snapshotted values
      return { previousQueries }
    },
    onError: (_err, _notificationId, context) => {
      // Rollback to the previous values if mutation fails
      if (context?.previousQueries) {
        context.previousQueries.forEach((data, queryKey) => {
          queryClient.setQueryData(queryKey, data)
        })
      }
      // Invalidate on error to refetch and ensure consistency
      queryClient.invalidateQueries({
        predicate: (query) => query.queryKey[0] === 'getNotificationsInfinite',
      })
      queryClient.invalidateQueries({
        queryKey: ['getUnreadNotificationCount'],
      })
    },
    onSuccess: () => {
      // Only invalidate unread count on success, keep optimistic update
      queryClient.invalidateQueries({
        queryKey: ['getUnreadNotificationCount'],
      })
    },
  })
}

export const useDeleteNotification = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (notificationId: number) => {
      const token = await getToken({ template: 'default' })
      await axios.delete(
        `${baseURL}/v1/admin/notifications/${notificationId}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      )
    },
    onMutate: async (notificationId: number) => {
      // Cancel outgoing refetches for all page sizes.
      await queryClient.cancelQueries({
        predicate: (query) => query.queryKey[0] === 'getNotificationsInfinite',
      })

      // Get all infinite notification queries.
      const allInfiniteQueries = queryClient.getQueriesData<
        InfiniteData<NotificationPage>
      >({
        predicate: (query) => query.queryKey[0] === 'getNotificationsInfinite',
      })

      // Store previous values for rollback
      const previousQueries = new Map(allInfiniteQueries)

      // Optimistically update all infinite queries
      allInfiniteQueries.forEach(([queryKey, data]) => {
        if (data) {
          const nextPages = data.pages.map((page) => ({
            ...page,
            notifications: page.notifications.filter(
              (notification) => notification.notification_id !== notificationId,
            ),
          }))
          queryClient.setQueryData<InfiniteData<NotificationPage>>(queryKey, {
            ...data,
            pages: nextPages,
          })
        }
      })

      // Return context with the snapshotted values
      return { previousQueries }
    },
    onError: (_err, _notificationId, context) => {
      // Rollback to the previous values if mutation fails
      if (context?.previousQueries) {
        context.previousQueries.forEach((data, queryKey) => {
          queryClient.setQueryData(queryKey, data)
        })
      }
      // Invalidate on error to refetch and ensure consistency
      queryClient.invalidateQueries({
        predicate: (query) => query.queryKey[0] === 'getNotificationsInfinite',
      })
      queryClient.invalidateQueries({
        queryKey: ['getUnreadNotificationCount'],
      })
    },
    onSuccess: () => {
      // Only invalidate unread count on success, keep optimistic update
      queryClient.invalidateQueries({
        queryKey: ['getUnreadNotificationCount'],
      })
    },
  })
}

export const useDeleteAllNotifications = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  const projectIdsExcluded = usePersonalPortfolioExcludedProjectIds()

  return useMutation({
    mutationFn: async () => {
      const token = await getToken({ template: 'default' })
      await axios.delete(`${baseURL}/v1/admin/notifications/delete-all`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        params: { project_ids_excluded: projectIdsExcluded },
        paramsSerializer: serializeNotificationQueryParams,
      })
    },
    onMutate: async () => {
      // Cancel outgoing refetches for current portfolio page sizes.
      await queryClient.cancelQueries({
        predicate: (query) =>
          isCurrentPortfolioNotificationsQuery(
            query.queryKey,
            projectIdsExcluded,
          ),
      })

      // Get current portfolio infinite notification queries.
      const allInfiniteQueries = queryClient.getQueriesData<
        InfiniteData<NotificationPage>
      >({
        predicate: (query) =>
          isCurrentPortfolioNotificationsQuery(
            query.queryKey,
            projectIdsExcluded,
          ),
      })

      // Store previous values for rollback
      const previousQueries = new Map(allInfiniteQueries)

      // Optimistically clear notifications from current portfolio queries
      allInfiniteQueries.forEach(([queryKey]) => {
        queryClient.setQueryData<InfiniteData<NotificationPage>>(queryKey, {
          pages: [{ notifications: [], nextOffset: undefined }],
          pageParams: [0],
        })
      })

      // Return context with the snapshotted values
      return { previousQueries }
    },
    onError: (_err, _variables, context) => {
      // Rollback to the previous values if mutation fails
      if (context?.previousQueries) {
        context.previousQueries.forEach((data, queryKey) => {
          queryClient.setQueryData(queryKey, data)
        })
      }
      // Invalidate on error to refetch and ensure consistency
      queryClient.invalidateQueries({
        predicate: (query) =>
          isCurrentPortfolioNotificationsQuery(
            query.queryKey,
            projectIdsExcluded,
          ),
      })
      queryClient.invalidateQueries({
        queryKey: ['getUnreadNotificationCount'],
      })
    },
    onSuccess: () => {
      // Invalidate queries to ensure consistency
      queryClient.invalidateQueries({
        predicate: (query) =>
          isCurrentPortfolioNotificationsQuery(
            query.queryKey,
            projectIdsExcluded,
          ),
      })
      queryClient.invalidateQueries({
        queryKey: ['getUnreadNotificationCount'],
      })
    },
  })
}

export const useMarkAllNotificationsAsRead = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  const projectIdsExcluded = usePersonalPortfolioExcludedProjectIds()

  return useMutation({
    mutationFn: async () => {
      const token = await getToken({ template: 'default' })
      const response = await axios.put(
        `${baseURL}/v1/admin/notifications/read-all`,
        {},
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
          params: { project_ids_excluded: projectIdsExcluded },
          paramsSerializer: serializeNotificationQueryParams,
        },
      )
      return response.data
    },
    onMutate: async () => {
      // Cancel outgoing refetches for current portfolio page sizes.
      await queryClient.cancelQueries({
        predicate: (query) =>
          isCurrentPortfolioNotificationsQuery(
            query.queryKey,
            projectIdsExcluded,
          ),
      })

      // Get current portfolio infinite notification queries.
      const allInfiniteQueries = queryClient.getQueriesData<
        InfiniteData<NotificationPage>
      >({
        predicate: (query) =>
          isCurrentPortfolioNotificationsQuery(
            query.queryKey,
            projectIdsExcluded,
          ),
      })

      // Store previous values for rollback
      const previousQueries = new Map(allInfiniteQueries)

      // Optimistically update current portfolio queries
      allInfiniteQueries.forEach(([queryKey, data]) => {
        if (data) {
          const nextPages = data.pages.map((page) => ({
            ...page,
            notifications: page.notifications.map((notification) =>
              (notification as { state?: string }).state ===
              NotificationStateEnum.UNREAD
                ? { ...notification, state: NotificationStateEnum.READ }
                : notification,
            ),
          }))
          queryClient.setQueryData<InfiniteData<NotificationPage>>(queryKey, {
            ...data,
            pages: nextPages,
          })
        }
      })

      // Return context with the snapshotted values
      return { previousQueries }
    },
    onError: (_err, _variables, context) => {
      // Rollback to the previous values if mutation fails
      if (context?.previousQueries) {
        context.previousQueries.forEach((data, queryKey) => {
          queryClient.setQueryData(queryKey, data)
        })
      }
      // Invalidate on error to refetch and ensure consistency
      queryClient.invalidateQueries({
        predicate: (query) =>
          isCurrentPortfolioNotificationsQuery(
            query.queryKey,
            projectIdsExcluded,
          ),
      })
      queryClient.invalidateQueries({
        queryKey: ['getUnreadNotificationCount'],
      })
    },
    onSuccess: () => {
      // Only invalidate unread count on success, keep optimistic update
      queryClient.invalidateQueries({
        queryKey: ['getUnreadNotificationCount'],
      })
    },
  })
}
