import { DeviceTypeEnum } from '@/api/enumerations'
import type { Project } from '@/api/v1/operational/projects'
import { Event } from '@/hooks/types'
import { Badge, Group, Stack, Text, Title } from '@mantine/core'
import { IconClock } from '@tabler/icons-react'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { Link } from 'react-router'
import EventCMMSLinks from '@/features/project-impacts/components/EventCMMSLinks'

dayjs.extend(timezone)
dayjs.extend(utc)

type EventSummaryDetailsProps = {
  event: Event
  project: Project
  projectId: string
}

export function EventSummaryDetails({
  event,
  project,
  projectId,
}: EventSummaryDetailsProps) {
  const eventStartTime = dayjs(event.time_start).tz(project.time_zone)
  const eventEndTime = dayjs(event.time_end).tz(project.time_zone)
  const eventStatus = event.time_end ? 'Closed' : 'Open'

  return (
    <Stack>
      <Group>
        <Title order={2}>
          {event.device.device_type_id === DeviceTypeEnum.TRACKER_ROW ? (
            <>
              <Link
                to={`/projects/${projectId}/device-details/tracker-row/${event.device_id}`}
                style={{ color: 'inherit' }}
              >
                {event.device_name_full}
              </Link>{' '}
              Event
            </>
          ) : (
            <>{event.device_name_full} Event</>
          )}
        </Title>
        <Badge color={event.time_end ? 'green' : 'red'}>{eventStatus}</Badge>
      </Group>
      <Badge color="gray" size="lg" variant="outline">
        <Group gap={2}>
          <IconClock size={16} /> {eventStartTime.format('MM/DD/YYYY HH:mm')} -{' '}
          {event.time_end ? eventEndTime.format('MM/DD/YYYY HH:mm') : 'ONGOING'}
        </Group>
      </Badge>
      <EventCMMSLinks event={event} projectId={projectId} />
      <Text>
        {'Failure Mode: '}
        {event.failure_mode?.name_long}
      </Text>
    </Stack>
  )
}
