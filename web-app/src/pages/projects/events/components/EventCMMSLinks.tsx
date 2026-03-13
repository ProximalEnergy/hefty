import { useGetCMMSPermissions } from '@/api/v1/operational/project/cmms_permissions'
import { useGetEventCMMSTickets } from '@/api/v1/protected/web-application/projects/event-cmms-tickets/event_cmms_tickets'
import { Event } from '@/hooks/types'
import { Badge, Button, Group, Skeleton, Stack, Tooltip } from '@mantine/core'
import { useState } from 'react'
import { useParams } from 'react-router'

import EventFirstModal from './EventFirstModal'

const EventCMMSLinks = ({ event }: { event: Event }) => {
  const { projectId } = useParams()
  const [opened, setOpened] = useState(false)
  const cmmsPermissions = useGetCMMSPermissions({
    pathParams: { project_id: projectId! },
    queryOptions: { enabled: !!projectId },
  })
  const hasIntegration = cmmsPermissions.data?.some(
    (permission) => permission.can_view,
  )
  const existingLinks = useGetEventCMMSTickets({
    pathParams: { project_id: projectId! },
    queryParams: { event_ids: [event.event_id] },
    queryOptions: { enabled: !!projectId && !!event.event_id },
  })
  const eventCMMSTickets = existingLinks.data ?? []
  const badgeText = `Linked to ${eventCMMSTickets.length} ticket${eventCMMSTickets.length !== 1 ? 's' : ''}`
  return (
    <Stack>
      {existingLinks.isLoading || cmmsPermissions.isLoading ? (
        <Skeleton radius="md" w="100%">
          <Group>
            <Badge size="md">{badgeText}</Badge>
            <Button size="xs">Open Event Linkage Suite</Button>
          </Group>
        </Skeleton>
      ) : (
        <Group>
          <Badge
            color={eventCMMSTickets.length > 0 ? 'green' : 'grey'}
            size="md"
          >
            {badgeText}
          </Badge>
          {hasIntegration ? (
            <Button
              size="xs"
              variant="light"
              color="gray"
              onClick={() => setOpened(true)}
            >
              Open Ticket Linkage Suite
            </Button>
          ) : (
            <Tooltip label="CMMS integration not configured for this project.">
              <Button size="xs" variant="light" color="gray" disabled>
                Open Ticket Linkage Suite
              </Button>
            </Tooltip>
          )}
        </Group>
      )}
      <EventFirstModal
        opened={opened}
        onClose={() => setOpened(false)}
        event={event}
        linkedTicketIds={eventCMMSTickets.map(
          (ticket) => ticket.cmms_ticket_id,
        )}
        projectId={projectId!}
      />
    </Stack>
  )
}

export default EventCMMSLinks
