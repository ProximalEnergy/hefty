import { CMMSTicket } from '@/api/v1/operational/project/cmms_tickets'
import * as types from '@/hooks/types'
import {
  Badge,
  Box,
  Group,
  HoverCard,
  ScrollArea,
  Skeleton,
  Text,
  Timeline,
} from '@mantine/core'
import { IconExternalLink } from '@tabler/icons-react'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { Link } from 'react-router'

import CMMSTicketCard from '../cmms/CMMSTicketCard'

interface EventOrTicket {
  type: string
  event?: types.Event
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
  events: types.Event[]
  failureModes: types.FailureMode[]
  projectId: string
  selectedEvent: types.Event
  tickets: CMMSTicket[] | undefined
}) => {
  const [eventsAndTickets, setEventsAndTickets] = useState<EventOrTicket[]>([])

  useEffect(() => {
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
            : dayjs(a.ticket?.created_at).unix()
        const bTime =
          b.type === 'event'
            ? dayjs(b.event?.time_start).unix()
            : dayjs(b.ticket?.created_at).unix()
        return bTime - aTime // Sort in descending order (newest first)
      }),
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
    <ScrollArea scrollbars="y" p="xs" h="100%">
      <ScrollArea.Autosize h="100%">
        <Box>
          <Timeline
            active={eventsAndTickets.length - timelineLength}
            reverseActive
            align="left"
          >
            {eventsAndTickets.map((item, index) =>
              item.type === 'event' ? (
                <Timeline.Item key={index}>
                  <Link
                    to={`/projects/${projectId}/events/event/?eventId=${item.event?.event_id}`}
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
                          )} - ${dayjs(item.event?.time_end).format('MM/DD/YYYY')}`
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
              ) : (
                <Timeline.Item key={index} color="orange" radius="xs">
                  <HoverCard>
                    <HoverCard.Target>
                      <Link
                        to={item.ticket?.link || ''}
                        style={{ color: 'inherit' }}
                      >
                        <Group gap={2}>
                          <Text>
                            {dayjs(item.ticket?.created_at).format(
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
                  <Text c="dimmed" size="sm">
                    {item.ticket?.summary}
                  </Text>
                  <Badge color="orange" size="sm">
                    {item.ticket?.status}
                  </Badge>
                </Timeline.Item>
              ),
            )}
          </Timeline>
        </Box>
      </ScrollArea.Autosize>
    </ScrollArea>
  )
}

export default DeviceEventsTimeline
