import type { CMMSTicket } from '@/api/v1/operational/project/cmms_tickets'
import DeviceEventsTimeline from '@/components/DeviceEventsTimeline'
import type { Event, FailureMode } from '@/hooks/types'

type EventTimelineProps = {
  events: Event[]
  failureModes: FailureMode[]
  isLoading: boolean
  projectId: string
  selectedEvent: Event
  tickets: CMMSTicket[] | undefined
}

export function EventTimeline({
  events,
  failureModes,
  isLoading,
  projectId,
  selectedEvent,
  tickets,
}: EventTimelineProps) {
  return (
    <DeviceEventsTimeline
      isLoading={isLoading}
      events={events}
      failureModes={failureModes}
      projectId={projectId}
      selectedEvent={selectedEvent}
      tickets={tickets}
    />
  )
}
