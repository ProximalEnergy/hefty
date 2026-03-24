import { NotificationTypeEnum } from '@/api/enumerations'
import type { NotificationPage } from '@/api/v1/admin/notifications'
import { formatNotification } from '@/utils/notificationFormatters'
import { formatRelativeTime } from '@/utils/relativeTime'
import {
  ActionIcon,
  Avatar,
  Group,
  Menu,
  Stack,
  Text,
  Tooltip,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import {
  IconBell,
  IconCalendar,
  IconCloudRain,
  IconDots,
  IconFlag,
  IconFlame,
  IconMail,
  IconMessage,
  IconTornado,
  IconTrash,
  IconWind,
} from '@tabler/icons-react'
import type { ElementType } from 'react'
import { useNavigate } from 'react-router'

import classes from './NotificationsPanel.module.css'

type Notification = NotificationPage['notifications'][number]
type NotificationTypeId =
  (typeof NotificationTypeEnum)[keyof typeof NotificationTypeEnum]
type NotificationData = Record<string, unknown>
type FormattedNotification = ReturnType<typeof formatNotification>
type ReadState = 'read' | 'unread'

type NavigationAction =
  | {
      method: 'navigate'
      link: string
    }
  | {
      method: 'redirect'
      link: string
    }

type NavigationResolver = (args: {
  data: NotificationData
  formatted: FormattedNotification
}) => NavigationAction | null

type TextDisplayResolver = (args: {
  data: NotificationData
  formatted: FormattedNotification
  severityLabel: string
  projectName: string
}) => {
  title: string
  body: string
}

interface NotificationsEntryProps {
  notification: Notification
  projectName: string
  onClose: () => void
  onMarkAsRead: (notificationId: number) => void
  onMarkAsUnread: (notificationId: number) => void
  onDelete: (notificationId: number) => void
}

const iconMap: Partial<Record<NotificationTypeId, ElementType>> = {
  [NotificationTypeEnum.FIRE]: IconFlame,
  [NotificationTypeEnum.HAIL]: IconCloudRain,
  [NotificationTypeEnum.TORNADO]: IconTornado,
  [NotificationTypeEnum.WIND]: IconWind,
  [NotificationTypeEnum.CALENDAR_REMINDER]: IconCalendar,
  [NotificationTypeEnum.EVENT_CHAT_MESSAGE]: IconMessage,
  [NotificationTypeEnum.PROJECT_CAPACITY_REDUCTION]: IconFlag,
}

const severityColorMap: Record<string, string> = {
  critical: '#fa5252',
  warning: '#fab005',
  info: '#339af0',
}

const navigationMap: Partial<Record<NotificationTypeId, NavigationResolver>> = {
  [NotificationTypeEnum.CALENDAR_REMINDER]: ({ data }) => {
    const calendarItemId =
      typeof data.calendar_item_id === 'string' ||
      typeof data.calendar_item_id === 'number'
        ? String(data.calendar_item_id)
        : null

    if (!calendarItemId) {
      return null
    }

    return {
      method: 'navigate',
      link: `/portfolio/calendar?calendarItemId=${calendarItemId}`,
    }
  },
  [NotificationTypeEnum.EVENT_CHAT_MESSAGE]: ({ formatted }) =>
    formatted.link ? { method: 'navigate', link: formatted.link } : null,
}

const defaultTextDisplay: TextDisplayResolver = ({
  formatted,
  severityLabel,
  projectName,
}) => ({
  title: `${severityLabel} ${formatted.title} - ${projectName}`,
  body: formatted.body,
})

const getNotificationData = (notification: Notification): NotificationData => {
  if (
    typeof notification.data === 'object' &&
    notification.data !== null &&
    !Array.isArray(notification.data)
  ) {
    return notification.data as NotificationData
  }

  return {}
}

const getSeverityLabel = (severity: string): string =>
  severity.charAt(0).toUpperCase() + severity.slice(1).toLowerCase()

const getSeverityColor = (severity: string): string =>
  severityColorMap[severity.toLowerCase()] ?? '#868e96'

const getNavigationAction = ({
  notificationTypeId,
  data,
  formatted,
}: {
  notificationTypeId: number
  data: NotificationData
  formatted: FormattedNotification
}): NavigationAction | null => {
  const resolver = navigationMap[notificationTypeId as NotificationTypeId]
  if (resolver) {
    const action = resolver({ data, formatted })
    if (action) {
      return action
    }
  }

  return formatted.link ? { method: 'redirect', link: formatted.link } : null
}

const NotificationsEntry = ({
  notification,
  projectName,
  onClose,
  onMarkAsRead,
  onMarkAsUnread,
  onDelete,
}: NotificationsEntryProps) => {
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme('light', {
    getInitialValueInEffect: true,
  })
  const navigate = useNavigate()

  const data = getNotificationData(notification)
  const formatted = formatNotification(
    notification.notification_type_id,
    data,
    notification.created_at,
    {
      severity: notification.severity,
      projectName,
      projectId: notification.project_id,
    },
  )
  const isUnread = (notification as { state?: string }).state === 'unread'
  const readState: ReadState = isUnread ? 'unread' : 'read'
  const relativeTime = formatRelativeTime(notification.created_at)
  const severityColor = getSeverityColor(notification.severity)
  const severityLabel = getSeverityLabel(notification.severity)
  const NotificationIcon =
    iconMap[notification.notification_type_id as NotificationTypeId] ?? IconBell

  const textDisplay = defaultTextDisplay({
    data,
    formatted,
    severityLabel,
    projectName,
  })

  const readActionMap: Record<
    ReadState,
    {
      label: string
      run: () => void
    }
  > = {
    unread: {
      label: 'Mark as read',
      run: () => onMarkAsRead(notification.notification_id),
    },
    read: {
      label: 'Mark as unread',
      run: () => onMarkAsUnread(notification.notification_id),
    },
  }

  const handleNotificationClick = () => {
    if (isUnread) {
      onMarkAsRead(notification.notification_id)
    }

    const navigationAction = getNavigationAction({
      notificationTypeId: notification.notification_type_id,
      data,
      formatted,
    })

    if (!navigationAction) {
      return
    }

    if (navigationAction.method === 'navigate') {
      navigate(navigationAction.link)
      onClose()
      return
    }

    window.location.href = navigationAction.link
  }

  const isDark = colorScheme === 'dark'
  const primaryText = 'var(--mantine-primary-color-light-color)'
  const avatarBg = isDark ? theme.colors.dark[5] : 'var(--mantine-color-gray-1)'
  const dotBorder = isDark
    ? `2px solid ${theme.colors.dark[7]}`
    : '2px solid white'

  return (
    <Group
      align="flex-start"
      gap="sm"
      p="md"
      className={`${classes.notificationItem} ${
        isUnread ? classes.notificationItemUnread : classes.notificationItemRead
      }`}
      onClick={handleNotificationClick}
    >
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

      <Stack gap={4} style={{ flex: 1, minWidth: 0, position: 'relative' }}>
        <Group gap="xs" align="flex-start" wrap="nowrap">
          <Text
            size="sm"
            fw={isUnread ? 700 : 400}
            style={{
              flex: 1,
              color: isUnread ? primaryText : undefined,
            }}
          >
            {textDisplay.title}
          </Text>
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

        <div className={classes.menuIconContainer}>
          <Menu position="bottom-end" withinPortal>
            <Menu.Target>
              <ActionIcon
                variant="subtle"
                size="xl"
                onClick={(event) => {
                  event.stopPropagation()
                }}
              >
                <IconDots size={22} />
              </ActionIcon>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Item
                leftSection={<IconMail size={16} />}
                onClick={(event) => {
                  event.stopPropagation()
                  readActionMap[readState].run()
                }}
              >
                {readActionMap[readState].label}
              </Menu.Item>
              <Menu.Item
                leftSection={<IconTrash size={16} />}
                color="red"
                onClick={(event) => {
                  event.stopPropagation()
                  onDelete(notification.notification_id)
                }}
              >
                Delete
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
        </div>

        <Text size="sm" c="dimmed" fw={isUnread ? 500 : 400}>
          {textDisplay.body}
        </Text>
        <Tooltip label={relativeTime.full}>
          <Text size="xs" c="dimmed" style={{ width: 'fit-content' }}>
            {relativeTime.relative}
          </Text>
        </Tooltip>
      </Stack>
    </Group>
  )
}

export default NotificationsEntry
