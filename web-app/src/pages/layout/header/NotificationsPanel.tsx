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
import { formatNotification } from '@/utils/notificationFormatters'
import { formatRelativeTime } from '@/utils/relativeTime'
import {
  ActionIcon,
  Avatar,
  Drawer,
  Group,
  Loader,
  Menu,
  ScrollArea,
  Stack,
  Text,
  Title,
  Tooltip,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { useIntersection } from '@mantine/hooks'
import {
  IconBell,
  IconCalendar,
  IconCloudRain,
  IconDots,
  IconFlame,
  IconMail,
  IconMessage,
  IconSettings,
  IconTornado,
  IconTrash,
  IconWind,
} from '@tabler/icons-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router'

import classes from './NotificationsPanel.module.css'

interface NotificationsPanelProps {
  opened: boolean
  onClose: () => void
}

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
    personalPortfolio: false, // Get all projects user has access to, not just personal portfolio
  })
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme('light', {
    getInitialValueInEffect: true,
  })
  const isDark = colorScheme === 'dark'
  const navigate = useNavigate()
  const markAsUnreadMutation = useMarkNotificationAsUnread()
  const markAllAsReadMutation = useMarkAllNotificationsAsRead()
  const deleteNotificationMutation = useDeleteNotification()
  const deleteAllNotificationsMutation = useDeleteAllNotifications()

  // Create a map of project_id to project name
  // Normalize UUIDs to lowercase for consistent matching
  const projectMap = useMemo(() => {
    if (!projects || projects.length === 0) return new Map<string, string>()
    const map = new Map<string, string>()
    projects.forEach((project) => {
      // Normalize project_id to lowercase string for consistent comparison
      const normalizedId = String(project.project_id).toLowerCase().trim()
      map.set(normalizedId, project.name_long)
    })
    return map
  }, [projects])

  // Get severity color
  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return '#fa5252' // red
      case 'warning':
        return '#fab005' // yellow/orange
      case 'info':
        return '#339af0' // blue
      default:
        return '#868e96' // gray
    }
  }

  // Capitalize first letter of severity
  const capitalizeSeverity = (severity: string) => {
    return severity.charAt(0).toUpperCase() + severity.slice(1).toLowerCase()
  }

  const handleMarkAllAsRead = () => {
    markAllAsReadMutation.mutate()
  }

  const handleDeleteAll = () => {
    if (
      window.confirm(
        'Are you sure you want to delete all notifications? This action cannot be undone.',
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

    // Only trigger if we've transitioned from not intersecting to intersecting
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
              const formatted = formatNotification(
                notification.notification_type_id,
                notification.data as Record<string, unknown>,
                notification.created_at,
              )
              // Normalize project_id to lowercase string for consistent comparison
              const normalizedProjectId = String(notification.project_id)
                .toLowerCase()
                .trim()
              // Try map first, then fallback to direct find (in case map hasn't populated yet)
              let projectName = projectMap.get(normalizedProjectId)
              if (!projectName && projects && projects.length > 0) {
                const project = projects.find(
                  (p) =>
                    String(p.project_id).toLowerCase().trim() ===
                    normalizedProjectId,
                )
                projectName = project?.name_long
              }
              // If still not found and projects are loading, show loading state
              if (!projectName && projectsLoading) {
                projectName = 'Loading...'
              } else if (!projectName) {
                projectName = 'Unknown Project'
              }
              const isUnread =
                (notification as { state?: string }).state === 'unread'
              const severityColor = getSeverityColor(notification.severity)
              const severityLabel = capitalizeSeverity(notification.severity)

              const tid = notification.notification_type_id
              const isHailAlert = tid === NotificationTypeEnum.HAIL
              const isFireAlert = tid === NotificationTypeEnum.FIRE
              const isTornadoAlert = tid === NotificationTypeEnum.TORNADO
              const isWindAlert = tid === NotificationTypeEnum.WIND
              const isCalendarReminder =
                tid === NotificationTypeEnum.CALENDAR_REMINDER
              const isEventChatMessage =
                tid === NotificationTypeEnum.EVENT_CHAT_MESSAGE

              const NotificationIcon = isFireAlert
                ? IconFlame
                : isHailAlert
                  ? IconCloudRain
                  : isTornadoAlert
                    ? IconTornado
                    : isWindAlert
                      ? IconWind
                      : isCalendarReminder
                        ? IconCalendar
                        : isEventChatMessage
                          ? IconMessage
                          : IconBell

              const primaryText = 'var(--mantine-primary-color-light-color)'
              const avatarBg = isDark
                ? theme.colors.dark[5]
                : 'var(--mantine-color-gray-1)'
              const dotBorder = isDark
                ? `2px solid ${theme.colors.dark[7]}`
                : '2px solid white'

              return (
                <Group
                  key={notification.notification_id}
                  align="flex-start"
                  gap="sm"
                  p="md"
                  className={`${classes.notificationItem} ${
                    isUnread
                      ? classes.notificationItemUnread
                      : classes.notificationItemRead
                  }`}
                  onClick={async () => {
                    // Mark notification as read when clicked
                    if (isUnread) {
                      markNotificationAsRead(notification.notification_id)
                    }

                    // Handle calendar reminder notifications - navigate to calendar with item ID
                    if (isCalendarReminder) {
                      const calendarItemId =
                        notification.data &&
                        typeof notification.data === 'object' &&
                        'calendar_item_id' in notification.data
                          ? String(notification.data.calendar_item_id)
                          : null

                      if (calendarItemId) {
                        // Navigate to portfolio calendar with calendar item ID as query parameter
                        navigate(
                          `/portfolio/calendar?calendarItemId=${calendarItemId}`,
                        )
                        onClose() // Close the notifications panel
                      } else {
                        // Fall back to navigation if we don't have the required data
                        if (formatted.link) {
                          window.location.href = formatted.link
                        }
                      }
                    } else if (isEventChatMessage && formatted.link) {
                      // Event chat: in-app navigation to event page
                      navigate(formatted.link)
                      onClose()
                    } else if (formatted.link) {
                      // Other notifications: full navigation
                      window.location.href = formatted.link
                    }
                  }}
                >
                  {/* Icon with severity color overlay */}
                  <div style={{ position: 'relative', flexShrink: 0 }}>
                    <Avatar
                      size={58}
                      radius="xl"
                      color="gray"
                      style={{
                        backgroundColor: avatarBg,
                      }}
                    >
                      <NotificationIcon size={24} />
                    </Avatar>
                    {/* Severity color overlay on bottom right */}
                    <div
                      style={{
                        position: 'absolute',
                        bottom: -2,
                        right: -2,
                        width: 16,
                        height: 16,
                        borderRadius: '50%',
                        backgroundColor: severityColor,
                        border: dotBorder,
                      }}
                    />
                  </div>

                  {/* Notification content */}
                  <Stack
                    gap={4}
                    style={{ flex: 1, minWidth: 0, position: 'relative' }}
                  >
                    <Group gap="xs" align="flex-start" wrap="nowrap">
                      <Text
                        size="sm"
                        fw={isUnread ? 700 : 400}
                        style={{
                          flex: 1,
                          color: isUnread ? primaryText : undefined,
                        }}
                      >
                        {severityLabel} {formatted.title} - {projectName}
                      </Text>
                      {/* Unread dot indicator */}
                      {isUnread && (
                        <div
                          style={{
                            width: 8,
                            height: 8,
                            borderRadius: '50%',
                            backgroundColor: theme.primaryColor,
                            flexShrink: 0,
                            marginTop: 4,
                          }}
                        />
                      )}
                    </Group>
                    {/* Menu icon on hover - positioned absolutely to not affect layout */}
                    <div className={classes.menuIconContainer}>
                      <Menu position="bottom-end" withinPortal>
                        <Menu.Target>
                          <ActionIcon
                            variant="subtle"
                            size="xl"
                            onClick={(e) => {
                              e.stopPropagation()
                            }}
                          >
                            <IconDots size={22} />
                          </ActionIcon>
                        </Menu.Target>
                        <Menu.Dropdown>
                          {isUnread ? (
                            // Options for unread notifications
                            <>
                              <Menu.Item
                                leftSection={<IconMail size={16} />}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  markNotificationAsRead(
                                    notification.notification_id,
                                  )
                                }}
                              >
                                Mark as read
                              </Menu.Item>
                              <Menu.Item
                                leftSection={<IconTrash size={16} />}
                                color="red"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  deleteNotificationMutation.mutate(
                                    notification.notification_id,
                                  )
                                }}
                              >
                                Delete
                              </Menu.Item>
                            </>
                          ) : (
                            // Options for read notifications
                            <>
                              <Menu.Item
                                leftSection={<IconMail size={16} />}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  markAsUnreadMutation.mutate(
                                    notification.notification_id,
                                  )
                                }}
                              >
                                Mark as unread
                              </Menu.Item>
                              <Menu.Item
                                leftSection={<IconTrash size={16} />}
                                color="red"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  deleteNotificationMutation.mutate(
                                    notification.notification_id,
                                  )
                                }}
                              >
                                Delete
                              </Menu.Item>
                            </>
                          )}
                        </Menu.Dropdown>
                      </Menu>
                    </div>
                    <Text size="sm" c="dimmed" fw={isUnread ? 500 : 400}>
                      {formatted.body}
                    </Text>
                    <Tooltip
                      label={formatRelativeTime(notification.created_at).full}
                    >
                      <Text
                        size="xs"
                        c="dimmed"
                        style={{ width: 'fit-content' }}
                      >
                        {formatRelativeTime(notification.created_at).relative}
                      </Text>
                    </Tooltip>
                  </Stack>
                </Group>
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
