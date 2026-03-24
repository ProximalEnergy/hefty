import { NotificationTypeEnum } from '@/api/enumerations'
import {
  type NotificationPage,
  useDeleteAllNotifications,
  useDeleteNotification,
  useInfiniteNotifications,
  useMarkAllNotificationsAsRead,
  useMarkNotificationAsRead,
  useMarkNotificationAsUnread,
} from '@/api/v1/admin/notifications'
import { useGetProjects } from '@/api/v1/operational/projects'
import {
  ActionIcon,
  Drawer,
  Group,
  Loader,
  Menu,
  ScrollArea,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { useIntersection } from '@mantine/hooks'
import {
  IconBell,
  IconDots,
  IconSettings,
  IconTrash,
} from '@tabler/icons-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router'

import NotificationsEntry from './NotificationsEntry'

interface NotificationsPanelProps {
  opened: boolean
  onClose: () => void
}

type Notification = NotificationPage['notifications'][number]

const WEATHER_NOTIFICATION_TYPE_IDS = new Set<number>([
  NotificationTypeEnum.HAIL,
  NotificationTypeEnum.FIRE,
  NotificationTypeEnum.TORNADO,
  NotificationTypeEnum.WIND,
])

const getWeatherAlertDate = (
  data: Record<string, unknown> | null,
  createdAt: string,
): Date | null => {
  if (!data || typeof data.day !== 'string') {
    return null
  }

  const dayMatch = data.day.match(/day(\d+)/)
  const dayOffset = dayMatch ? parseInt(dayMatch[1], 10) : 0
  const createdDate = new Date(createdAt)
  if (Number.isNaN(createdDate.getTime())) {
    return null
  }

  const targetDate = new Date(createdDate)
  targetDate.setUTCDate(targetDate.getUTCDate() + dayOffset)
  targetDate.setUTCHours(23, 59, 59, 999)
  return targetDate
}

const isPastWeatherNotification = (
  notification: NotificationPage['notifications'][number],
): boolean => {
  if (!WEATHER_NOTIFICATION_TYPE_IDS.has(notification.notification_type_id)) {
    return false
  }
  const data =
    typeof notification.data === 'object' && notification.data !== null
      ? (notification.data as Record<string, unknown>)
      : null

  const weatherDate = getWeatherAlertDate(data, notification.created_at)
  if (!weatherDate) {
    return false
  }

  return weatherDate.getTime() < Date.now()
}

const NotificationsPanel = ({ opened, onClose }: NotificationsPanelProps) => {
  const { mutate: markNotificationAsRead } = useMarkNotificationAsRead()
  const autoReadIdsRef = useRef(new Set<number>())
  const {
    data: notificationsPages,
    isLoading,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteNotifications({
    pageSize: 20,
  })
  const { data: projects, isLoading: projectsLoading } = useGetProjects({
    queryParams: { deep: true },
    personalPortfolio: false,
  })
  const markAsUnreadMutation = useMarkNotificationAsUnread()
  const markAllAsReadMutation = useMarkAllNotificationsAsRead()
  const deleteNotificationMutation = useDeleteNotification()
  const deleteAllNotificationsMutation = useDeleteAllNotifications()

  const projectMap = useMemo(() => {
    if (!projects || projects.length === 0) {
      return new Map<string, string>()
    }

    const map = new Map<string, string>()
    projects.forEach((project) => {
      const normalizedId = String(project.project_id).toLowerCase().trim()
      map.set(normalizedId, project.name_long)
    })
    return map
  }, [projects])

  const handleMarkAllAsRead = () => {
    markAllAsReadMutation.mutate()
  }

  const handleDeleteAll = () => {
    if (
      window.confirm(
        'Are you sure you want to delete all notifications? ' +
          'This action cannot be undone.',
      )
    ) {
      deleteAllNotificationsMutation.mutate()
    }
  }

  const viewportRef = useRef<HTMLDivElement | null>(null)
  const [intersectionRoot, setIntersectionRoot] = useState<Element | null>(null)
  const lastIntersectingRef = useRef(false)
  const { ref: loadMoreRef, entry } = useIntersection({
    root: intersectionRoot,
    threshold: 0,
    rootMargin: '200px',
  })

  useEffect(() => {
    notificationsPages?.pages.forEach((page) => {
      page.notifications.forEach((notification) => {
        const isUnread = (notification as { state?: string }).state === 'unread'
        const shouldAutoMarkRead =
          isUnread && isPastWeatherNotification(notification)
        if (!shouldAutoMarkRead) {
          return
        }

        if (autoReadIdsRef.current.has(notification.notification_id)) {
          return
        }

        autoReadIdsRef.current.add(notification.notification_id)
        markNotificationAsRead(notification.notification_id)
      })
    })
  }, [markNotificationAsRead, notificationsPages])

  useEffect(() => {
    setIntersectionRoot(viewportRef.current)
  }, [])

  useEffect(() => {
    const isIntersecting = entry?.isIntersecting ?? false

    if (
      isIntersecting &&
      !lastIntersectingRef.current &&
      hasNextPage &&
      !isFetchingNextPage
    ) {
      fetchNextPage()
    }

    lastIntersectingRef.current = isIntersecting
  }, [entry?.isIntersecting, hasNextPage, isFetchingNextPage, fetchNextPage])

  const notifications = useMemo(() => {
    const pages = (notificationsPages?.pages ?? []) as NotificationPage[]
    return pages.flatMap((page) => page.notifications)
  }, [notificationsPages])

  const getProjectName = (notification: Notification): string => {
    const normalizedProjectId = String(notification.project_id)
      .toLowerCase()
      .trim()
    const projectName = projectMap.get(normalizedProjectId)

    if (projectName) {
      return projectName
    }

    if (projectsLoading) {
      return 'Loading...'
    }

    return 'Unknown Project'
  }

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      position="right"
      size="30%"
      styles={{
        content: {
          minWidth: '400px',
        },
        body: {
          padding: 0,
          display: 'flex',
          flexDirection: 'column',
          flex: 1,
          minHeight: 0,
        },
      }}
      overlayProps={{ opacity: 0 }}
      title={
        <Group justify="space-between" style={{ width: '100%' }}>
          <Group gap="xs">
            <IconBell size={20} />
            <Title order={4}>Notifications</Title>
          </Group>
          <Menu position="bottom-end">
            <Menu.Target>
              <ActionIcon variant="subtle" size="lg">
                <IconDots size={18} />
              </ActionIcon>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Item
                leftSection={<IconBell size={16} />}
                onClick={handleMarkAllAsRead}
              >
                Mark all as read
              </Menu.Item>
              <Menu.Item
                leftSection={<IconTrash size={16} />}
                color="red"
                onClick={handleDeleteAll}
              >
                Delete all notifications
              </Menu.Item>
              <Menu.Divider />
              <Menu.Item
                leftSection={<IconSettings size={16} />}
                component={Link}
                to="/application-settings"
                onClick={(e) => {
                  e.preventDefault()
                  onClose()
                  window.location.href = '/application-settings#notifications'
                }}
              >
                Notification settings
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
        </Group>
      }
    >
      <ScrollArea
        style={{ flex: 1, minHeight: 0 }}
        type="auto"
        viewportRef={viewportRef}
      >
        <Stack
          gap={0}
          p={0}
          style={{
            position: 'relative',
          }}
        >
          {isLoading ? (
            <Text size="sm" c="dimmed" p="md">
              Loading notifications...
            </Text>
          ) : !notifications || notifications.length === 0 ? (
            <Text size="sm" c="dimmed" p="md">
              No notifications at this time.
            </Text>
          ) : (
            notifications.map((notification) => {
              return (
                <NotificationsEntry
                  key={notification.notification_id}
                  notification={notification}
                  projectName={getProjectName(notification)}
                  onClose={onClose}
                  onMarkAsRead={markNotificationAsRead}
                  onMarkAsUnread={markAsUnreadMutation.mutate}
                  onDelete={deleteNotificationMutation.mutate}
                />
              )
            })
          )}
          {hasNextPage && (
            <Stack
              ref={loadMoreRef}
              gap="sm"
              align="center"
              p="md"
              style={{
                pointerEvents: 'none',
                minHeight: 80,
              }}
            >
              {(isFetchingNextPage ||
                (entry?.isIntersecting && hasNextPage)) && (
                <>
                  <Loader type="hex" size="md" />
                  <Text size="sm" c="dimmed" fw={500}>
                    Loading more notifications...
                  </Text>
                </>
              )}
            </Stack>
          )}
        </Stack>
      </ScrollArea>
    </Drawer>
  )
}

export default NotificationsPanel
