import { useGetEventChatMuteStatus } from '@/api/v1/operational/event_messages'
import { useGetEventChatNotificationStatus } from '@/api/v1/operational/event_messages'
import { useToggleEventChatMute } from '@/api/v1/operational/event_messages'
import { ActionIcon, Tooltip } from '@mantine/core'
import { IconBell, IconBellOff } from '@tabler/icons-react'

interface MuteToggleProps {
  eventId: number
  projectId?: string
}

export function MuteToggle({ eventId, projectId }: MuteToggleProps) {
  const { data: muteStatus } = useGetEventChatMuteStatus(
    eventId,
    projectId || 'placeholder',
  )
  const { data: notificationStatus } = useGetEventChatNotificationStatus(
    projectId || 'placeholder', // Use placeholder to avoid empty string, but hook will disable if falsy
  )
  const toggleMute = useToggleEventChatMute()

  const isMuted = muteStatus?.muted ?? false
  // Default to enabled if no projectId or no status available
  const firstMessageNotificationsEnabled =
    projectId && notificationStatus ? notificationStatus.enabled : true

  // Build tooltip text
  let tooltipText = isMuted
    ? 'Unmute notifications for this conversation'
    : 'Mute notifications for this conversation'

  if (projectId && notificationStatus !== undefined) {
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
