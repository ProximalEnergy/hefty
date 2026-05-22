import { DeviceTypeEnum } from '@/api/enumerations'
import { useGetEventMessages } from '@/api/v1/operational/event_messages'
import { useSelectProject } from '@/api/v1/operational/projects'
import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { useGetEvents } from '@/hooks/api'
import { useProjectDropdownToggle } from '@/hooks/custom'
import { useParams, useSearchParams } from 'react-router'
import { EventDCFieldView } from '@/features/project-impacts/views/EventDCFieldView'
import { EventGeneralView } from '@/features/project-impacts/views/EventGeneralView'

export function EventRoute() {
  const { projectId } = useParams<{ projectId: string }>()
  const [searchParams] = useSearchParams()
  const eventId = parseInt(searchParams.get('eventId') || '-1')
  const project = useSelectProject(projectId)

  useProjectDropdownToggle()

  const eventData = useGetEvents({
    pathParams: {
      projectId: projectId || '-1',
    },
    queryParams: {
      event_ids: [eventId],
      open: false,
    },
    queryOptions: {
      enabled: eventId > 0 && !!projectId,
    },
  })
  const eventMessages = useGetEventMessages({
    queryParams: {
      event_id: eventId,
      project_id: projectId || '-1',
    },
    queryOptions: {
      enabled: eventId > 0 && !!projectId,
    },
  })
  const eventMessageCount = eventMessages.data?.length ?? 0

  if (eventData.isLoading || project.isLoading) {
    return <PageLoader />
  }

  const event = eventData.data?.[0]

  if (!event) {
    return <PageError text="Event not found" />
  }

  if (!project.data || !projectId) {
    return <PageError text="Project not found" />
  }

  if (event.device.device_type_id === DeviceTypeEnum.DC_FIELD) {
    return (
      <EventDCFieldView
        event={event}
        eventId={eventId}
        eventMessageCount={eventMessageCount}
        project={project.data}
        projectId={projectId}
      />
    )
  }

  return (
    <EventGeneralView
      event={event}
      eventId={eventId}
      eventMessageCount={eventMessageCount}
      project={project.data}
      projectId={projectId}
    />
  )
}
