import { NotificationStateEnum } from '@/api/enumerations'
import type * as types from '@/api/schema'
import { useGetUnreadNotificationCount } from '@/api/v1/admin/notifications'
import { baseURL } from '@/urlConfig'
import { formatNotification } from '@/utils/notificationFormatters'
import { useAuth } from '@clerk/react'
import { ActionIcon, Group, Indicator } from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { notifications } from '@mantine/notifications'
import { IconBell } from '@tabler/icons-react'
import { useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import cx from 'clsx'
import { useEffect, useRef } from 'react'

import NotificationsPanel from './NotificationsPanel'
import classes from './ThemeToggle.module.css'

const UserAlerts = () => {
  const { data: unreadCountData } = useGetUnreadNotificationCount({})
  const queryClient = useQueryClient()
  const { getToken } = useAuth()
  const [
    notificationsOpened,
    { open: openNotifications, close: closeNotifications },
  ] = useDisclosure(false)
  const unreadCount = unreadCountData?.count || 0
  const previousUnreadCountRef = useRef<number>(unreadCount)
  const isFetchingRef = useRef(false)

  useEffect(() => {
    // Check if unread count has increased (skip initial mount)
    if (
      unreadCount > previousUnreadCountRef.current &&
      !isFetchingRef.current
    ) {
      isFetchingRef.current = true

      // Fetch the latest notification to show in toast
      const fetchLatestNotification = async () => {
        try {
          const token = await getToken({ template: 'default' })
          const response = await axios.get(
            `${baseURL}/v1/admin/notifications`,
            {
              headers: { Authorization: `Bearer ${token}` },
              params: { limit: 1, offset: 0 }, // Get just the latest one
            },
          )
          const notificationList =
            response.data as types.components['schemas']['NotificationInterface'][]

          if (notificationList.length > 0) {
            const latestNotification = notificationList[0]

            // Check if notification was created recently (within last 90 seconds)
            // This prevents toasts when marking old notifications as unread
            const now = new Date()
            const notificationAge =
              now.getTime() - new Date(latestNotification.created_at).getTime()
            const recentThreshold = 90 * 1000 // 90 seconds

            // Only show toast if notification is unread and was created recently
            const isUnread =
              (latestNotification as { state?: string }).state ===
              NotificationStateEnum.UNREAD

            if (isUnread && notificationAge <= recentThreshold) {
              const formatted = formatNotification(
                latestNotification.notification_type_id,
                latestNotification.data as Record<string, unknown>,
                latestNotification.created_at,
                {
                  severity: latestNotification.severity,
                  projectId: latestNotification.project_id,
                  projectName: String(
                    (latestNotification.data as Record<string, unknown>)
                      ?.project_name_long ?? '',
                  ),
                },
              )

              // Get severity color
              const getSeverityColor = (severity: string) => {
                switch (severity.toLowerCase()) {
                  case 'critical':
                    return '#fa5252'
                  case 'warning':
                    return '#fab005'
                  case 'info':
                    return '#339af0'
                  default:
                    return '#868e96'
                }
              }

              notifications.show({
                title: formatted.title,
                message: formatted.body,
                color: getSeverityColor(latestNotification.severity),
                autoClose: 5000,
                position: 'top-right',
                onClick: () => {
                  openNotifications()
                },
              })
            }
          }

          // Invalidate notifications query to fetch fresh data
          queryClient.invalidateQueries({
            predicate: (query) =>
              query.queryKey[0] === 'getNotificationsInfinite',
          })
        } catch (error) {
          console.error('Failed to fetch latest notification:', error)
        } finally {
          isFetchingRef.current = false
        }
      }

      fetchLatestNotification()
    }

    // Update previous count
    previousUnreadCountRef.current = unreadCount
  }, [unreadCount, queryClient, openNotifications, getToken])

  return (
    <>
      <Group justify="center">
        <Indicator
          disabled={unreadCount === 0}
          label={unreadCount > 0 ? unreadCount : undefined}
          size={16}
          color="red"
        >
          <ActionIcon
            variant="default"
            size="lg"
            aria-label="Open notifications"
            onClick={openNotifications}
          >
            <IconBell className={cx(classes.icon)} stroke={1.5} />
          </ActionIcon>
        </Indicator>
      </Group>
      <NotificationsPanel
        opened={notificationsOpened}
        onClose={closeNotifications}
      />
    </>
  )
}

export default UserAlerts
