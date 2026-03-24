import type { EventFirstModalEvent } from '@/hooks/types'
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Group,
  Stack,
  Text,
} from '@mantine/core'
import { IconExternalLink } from '@tabler/icons-react'
import dayjs from 'dayjs'

const EventCard = ({
  event,
  projectId,
  isLinked = false,
  onLink,
  onUnlink,
  isLinking = false,
  isUnlinking = false,
  canLink = true,
}: {
  event: EventFirstModalEvent
  projectId: string
  isLinked?: boolean
  onLink?: () => void
  onUnlink?: () => void
  isLinking?: boolean
  isUnlinking?: boolean
  canLink?: boolean
}) => {
  const isLoading = isLinked ? isUnlinking : isLinking
  const isDisabled = isLinked ? !onUnlink || isUnlinking : !onLink || isLinking

  return (
    <Card withBorder>
      <Group w="100%" justify="space-between" align="flex-start">
        <Stack h="100%">
          <Text>{event.device_name_full}</Text>
          <Text>
            {dayjs(event.time_start).format('MM/DD/YYYY HH:mm')} -{' '}
            {event.time_end
              ? dayjs(event.time_end).format('MM/DD/YYYY HH:mm')
              : 'Ongoing'}
          </Text>
          <Text>{event.failure_mode?.name_long}</Text>
          <Text>
            {event.loss_total_financial
              ? event.loss_total_financial.toLocaleString('en-US', {
                  style: 'currency',
                  currency: 'USD',
                })
              : ''}
          </Text>
        </Stack>
        <Stack h="100%" justify="flex-start" align="flex-end">
          <Group align="flex-end">
            <Badge size="lg" color={event.time_end === null ? 'red' : 'green'}>
              {event.time_end === null ? 'Open' : 'Closed'}
            </Badge>
            {canLink && (
              <ActionIcon
                variant="transparent"
                onClick={() => {
                  window.open(
                    `/projects/${projectId}/events/event/?eventId=${event.event_id}`,
                    '_blank',
                  )
                }}
              >
                <IconExternalLink size={16} />
              </ActionIcon>
            )}
          </Group>
          {canLink && (
            <Button
              size="xs"
              variant="light"
              color="gray"
              onClick={isLinked ? onUnlink : onLink}
              loading={isLoading}
              disabled={isDisabled}
            >
              {isLinked ? 'Unlink Event' : 'Link Event'}
            </Button>
          )}
        </Stack>
      </Group>
    </Card>
  )
}

export default EventCard
