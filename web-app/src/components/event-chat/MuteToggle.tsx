import { useGetNotificationPreferences } from '@/api/v1/admin/notification_preferences'
import { useGetNotificationTypes } from '@/api/v1/admin/notification_types'
import {
  useGetEventChatMuteStatus,
  useToggleEventChatMute,
} from '@/api/v1/operational/event_messages'
import { ActionIcon, Tooltip } from '@mantine/core'
import { IconBell, IconBellOff } from '@tabler/icons-react'
import { useMemo } from 'react'

interface MuteToggleProps {
  eventId: number
  projectId?: string
}

export function MuteToggle({ eventId, projectId }: MuteToggleProps) {
  const { data: muteStatus } = useGetEventChatMuteStatus(
    eventId,
    projectId || 'placeholder',
  )
  const notificationTypes = useGetNotificationTypes({})
  const preferences = useGetNotificationPreferences({
    projectIds: projectId ? [projectId] : [],
  })
  const toggleMute = useToggleEventChatMute()

  const eventChatType = useMemo(
    () =>
      notificationTypes.data?.find((t) => t.name_long === 'event_chat_message'),
    [notificationTypes.data],
  )
  const pref = useMemo(() => {
    if (!projectId || !eventChatType || !preferences.data) return null
    return preferences.data.find(
      (p) =>
        p.project_id === projectId &&
        p.notification_type_id === eventChatType.notification_type_id,
    )
  }, [projectId, eventChatType, preferences.data])
  const firstMessageNotificationsEnabled = pref
    ? pref.in_app_enabled && pref.email_enabled
    : true

  const isMuted = muteStatus?.muted ?? false

  // Build tooltip text
  let tooltipText = isMuted
    ? 'Unmute notifications for this conversation'
    : 'Mute notifications for this conversation'

  if (projectId && eventChatType && preferences.data !== undefined) {
    const firstMessageStatus = firstMessageNotificationsEnabled
      ? 'enabled'
      : 'disabled'
    tooltipText += `. First message notifications: ${firstMessageStatus}`
  }

  return (
    <Tooltip label={tooltipText} multiline w={250}>
      <ActionIcon
        variant={isMuted ? 'filled' : 'subtle'}
        color={isMuted ? 'gray' : 'orange'}
        size="lg"
        onClick={() => {
          if (projectId) {
            toggleMute.mutate({ eventId, projectId })
          }
        }}
        loading={toggleMute.isPending}
        title={tooltipText}
      >
        {isMuted ? <IconBellOff size={18} /> : <IconBell size={18} />}
      </ActionIcon>
    </Tooltip>
  )
}
