import { PageLoader } from '@/components/Loading'
import { useGetEvents } from '@/hooks/api'
import { useParams } from 'react-router'

import DcFieldEventPage from './DcFieldEventPage'
import EventPage from './EventPage'

const EventRouter = () => {
  const { projectId } = useParams()
  const eventId = parseInt(
    new URLSearchParams(location.search).get('eventId') || '-1',
  )

  const eventData = useGetEvents({
    pathParams: {
      projectId: projectId || '-1',
    },
    queryParams: {
      event_ids: [eventId],
      open: false,
    },
    queryOptions: {
      enabled: !!eventId && !!projectId,
    },
  })

  if (eventData.isLoading) {
    return <PageLoader />
  }

  const event = eventData.data?.[0]

  // Route to DC Field event page if device type is 30 (DC Field)
  if (event?.device?.device_type_id === 30) {
    return <DcFieldEventPage />
  }

  // Default to regular event page for all other device types
  return <EventPage />
}

export default EventRouter
