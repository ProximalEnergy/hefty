import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/react'
import {
  type InfiniteData,
  UseInfiniteQueryOptions,
  UseQueryOptions,
  useInfiniteQuery,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

const _COMPONENT_NAME = 'Notification'

type Notification = types.components['schemas'][typeof _COMPONENT_NAME]
export type NotificationPage = {
  notifications: Notification[]
  nextOffset: number | undefined
}

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
      readonly ['getNotificationsInfinite', { pageSize: number }],
      number
    >
  >
}) => {
  const { getToken } = useAuth()

  return useInfiniteQuery<
    NotificationPage,
    unknown,
    InfiniteData<NotificationPage>,
    readonly ['getNotificationsInfinite', { pageSize: number }],
    number
  >({
    queryKey: ['getNotificationsInfinite', { pageSize }],
    queryFn: async ({ pageParam = 0 }) => {
      const token = await getToken({ template: 'default' })
      const response = await axios.get(`${baseURL}/v1/admin/notifications`, {
        headers: { Authorization: `Bearer ${token}` },
        params: { limit: pageSize, offset: pageParam },
      })
      const data = response.data as Notification[]
      return {
        notifications: data,
        nextOffset: data.length === pageSize ? pageParam + pageSize : undefined,
      }
    },
    getNextPageParam: (lastPage) => lastPage.nextOffset,
    initialPageParam: 0,
    staleTime: 5 * 60 * 1000, // 5 minutes - prevent frequent background refetches
    refetchOnWindowFocus: false, // Don't refetch when window regains focus
    ...queryOptions,
  })
}

export const useGetUnreadNotificationCount = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/admin/notifications/unread-count`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 30 * 1000, // 30 seconds - count doesn't need to be super fresh
    refetchInterval: 30 * 1000, // Refetch every 30 seconds to check for new notifications
  }

  return useCustomQuery<{ count: number }>({
    axiosConfig,
    queryName: 'getUnreadNotificationCount',
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
      // Cancel any outgoing refetches (match all infinite queries regardless of pageSize)
      await queryClient.cancelQueries({
        predicate: (query) => query.queryKey[0] === 'getNotificationsInfinite',
      })

      // Get all infinite notification queries (there might be multiple with different pageSize)
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
                ? { ...notification, state: 'read' }
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
      // Cancel any outgoing refetches (match all infinite queries regardless of pageSize)
      await queryClient.cancelQueries({
        predicate: (query) => query.queryKey[0] === 'getNotificationsInfinite',
      })

      // Get all infinite notification queries (there might be multiple with different pageSize)
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
                ? { ...notification, state: 'unread' }
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
      // Cancel any outgoing refetches (match all infinite queries regardless of pageSize)
      await queryClient.cancelQueries({
        predicate: (query) => query.queryKey[0] === 'getNotificationsInfinite',
      })

      // Get all infinite notification queries (there might be multiple with different pageSize)
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

  return useMutation({
    mutationFn: async () => {
      const token = await getToken({ template: 'default' })
      await axios.delete(`${baseURL}/v1/admin/notifications/delete-all`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
    },
    onMutate: async () => {
      // Cancel any outgoing refetches (match all infinite queries regardless of pageSize)
      await queryClient.cancelQueries({
        predicate: (query) => query.queryKey[0] === 'getNotificationsInfinite',
      })

      // Get all infinite notification queries (there might be multiple with different pageSize)
      const allInfiniteQueries = queryClient.getQueriesData<
        InfiniteData<NotificationPage>
      >({
        predicate: (query) => query.queryKey[0] === 'getNotificationsInfinite',
      })

      // Store previous values for rollback
      const previousQueries = new Map(allInfiniteQueries)

      // Optimistically clear all notifications from all infinite queries
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
        predicate: (query) => query.queryKey[0] === 'getNotificationsInfinite',
      })
      queryClient.invalidateQueries({
        queryKey: ['getUnreadNotificationCount'],
      })
    },
    onSuccess: () => {
      // Invalidate queries to ensure consistency
      queryClient.invalidateQueries({
        predicate: (query) => query.queryKey[0] === 'getNotificationsInfinite',
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
        },
      )
      return response.data
    },
    onMutate: async () => {
      // Cancel any outgoing refetches (match all infinite queries regardless of pageSize)
      await queryClient.cancelQueries({
        predicate: (query) => query.queryKey[0] === 'getNotificationsInfinite',
      })

      // Get all infinite notification queries (there might be multiple with different pageSize)
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
              (notification as { state?: string }).state === 'unread'
                ? { ...notification, state: 'read' }
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
