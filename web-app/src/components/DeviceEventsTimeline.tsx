import { CMMSTicket } from '@/api/v1/operational/project/cmms_tickets'
import type { Event, FailureMode } from '@/hooks/types'
import CMMSTicketCard from '@/pages/projects/cmms/CMMSTicketCard'
import {
  Badge,
  Box,
  Group,
  HoverCard,
  ScrollArea,
  Skeleton,
  Stack,
  Text,
  Timeline,
} from '@mantine/core'
import { IconExternalLink } from '@tabler/icons-react'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { Link } from 'react-router'

interface EventOrTicket {
  type: string
  event?: Event
  ticket?: CMMSTicket
}

const DeviceEventsTimeline = ({
  isLoading,
  events,
  failureModes,
  projectId,
  selectedEvent,
  tickets,
}: {
  isLoading: boolean
  events: Event[]
  failureModes: FailureMode[]
  projectId: string
  selectedEvent: Event
  tickets: CMMSTicket[] | undefined
}) => {
  const [eventsAndTickets, setEventsAndTickets] = useState<EventOrTicket[]>([])

  useEffect(() => {
    queueMicrotask(() =>
      setEventsAndTickets(
        [
          ...events.map((event) => ({
            type: 'event',
            event: event,
            ticket: undefined,
          })),
          ...(tickets || []).map((ticket) => ({
            type: 'ticket',
            event: undefined,
            ticket: ticket,
          })),
        ].sort((a, b) => {
          const aTime =
            a.type === 'event'
              ? dayjs(a.event?.time_start).unix()
              : dayjs(a.ticket?.source_created_at).unix()
          const bTime =
            b.type === 'event'
              ? dayjs(b.event?.time_start).unix()
              : dayjs(b.ticket?.source_created_at).unix()
          return bTime - aTime // Sort in descending order (newest first)
        }),
      ),
    )
  }, [events, tickets])
  if (isLoading) {
    return <Skeleton height="100%" />
  }

  let timelineLength = 2
  if (events[0].time_end) {
    timelineLength = 1
  }

  return (
    <ScrollArea scrollbars="y" h="100%">
      <ScrollArea.Autosize h="100%">
        <Box>
          <Timeline
            active={eventsAndTickets.length - timelineLength}
            reverseActive
            align="left"
          >
            {eventsAndTickets.map((item, index) => {
              if (item.type === 'event') {
                return (
                  <Timeline.Item key={index}>
                    <Link
                      to={`/projects/${projectId}/impacts/event/?eventId=${item.event?.event_id}`}
                      style={{ color: 'inherit' }}
                    >
                      <Text
                        style={{
                          fontWeight:
                            selectedEvent.event_id === item.event?.event_id
                              ? 'bold'
                              : 'normal',
                        }}
                      >
                        {item.event?.time_end
                          ? `${dayjs(item.event?.time_start).format(
                              'MM/DD/YYYY',
                            )} - ${dayjs(item.event?.time_end).format(
                              'MM/DD/YYYY',
                            )}`
                          : dayjs(item.event?.time_start).format('MM/DD/YYYY')}
                      </Text>
                    </Link>
                    <Group>
                      <Text
                        size="sm"
                        style={{
                          fontWeight:
                            selectedEvent.event_id === item.event?.event_id
                              ? 'bold'
                              : 'normal',
                        }}
                      >
                        Failure mode:{' '}
                        {failureModes.find(
                          (fm) =>
                            fm.failure_mode_id === item.event?.failure_mode_id,
                        )?.name_long || 'Unknown'}
                      </Text>
                    </Group>
                  </Timeline.Item>
                )
              }

              return (
                <Timeline.Item key={index} color="orange" radius="xs">
                  <HoverCard>
                    <HoverCard.Target>
                      <Link
                        to={item.ticket?.link || ''}
                        style={{ color: 'inherit' }}
                      >
                        <Group gap={2}>
                          <Text>
                            {dayjs(item.ticket?.source_created_at).format(
                              'MM/DD/YYYY',
                            )}
                          </Text>
                          <IconExternalLink size={12} />
                        </Group>
                      </Link>
                    </HoverCard.Target>
                    <HoverCard.Dropdown>
                      <CMMSTicketCard
                        ticket={item.ticket!}
                        withBorder={false}
                      />
                    </HoverCard.Dropdown>
                  </HoverCard>
                  <Stack p={0} gap={0}>
                    <Text c="dimmed" size="sm">
                      {item.ticket?.summary}
                    </Text>
                    <Badge color="orange" size="sm">
                      {item.ticket?.status}
                    </Badge>
                  </Stack>
                </Timeline.Item>
              )
            })}
          </Timeline>
        </Box>
      </ScrollArea.Autosize>
    </ScrollArea>
  )
}

export default DeviceEventsTimeline
