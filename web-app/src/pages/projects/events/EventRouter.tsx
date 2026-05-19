import { DeviceTypeEnum } from '@/api/enumerations'
import { PageLoader } from '@/components/Loading'
import { useGetEvents } from '@/hooks/api'
import DcFieldEventPage from '@/pages/projects/events/DcFieldEventPage'
import EventPage from '@/pages/projects/events/EventPage'
import { useParams } from 'react-router'

const EventRouter = () => {
  const { projectId } = useParams<{ projectId: string }>()
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
  if (event?.device?.device_type_id === DeviceTypeEnum.DC_FIELD) {
    return <DcFieldEventPage />
  }

  // Default to regular event page for all other device types
  return <EventPage />
}

export default EventRouter
