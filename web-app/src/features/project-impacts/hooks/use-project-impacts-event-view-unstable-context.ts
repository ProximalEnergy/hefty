import { useGetEventsSummary } from '@/api/v1/operational/project/events'

type ProjectImpactsEventViewUnstableContextProps = {
  projectId: string
  startQuery: string
  endQuery: string
  selectedDeviceTypes: string[]
  selectedDevices: string[]
  showClosedEvents: boolean
}

export function useProjectImpactsEventViewUnstableContext({
  projectId,
  startQuery,
  endQuery,
  selectedDeviceTypes,
  selectedDevices,
  showClosedEvents,
}: ProjectImpactsEventViewUnstableContextProps) {
  const eventsSummary = useGetEventsSummary({
    pathParams: { projectId: projectId as string },
    queryParams: {
      start: startQuery,
      end: endQuery,
      device_type_ids: selectedDeviceTypes.map((type) => parseInt(type)),
      device_ids: selectedDevices.map((device) => parseInt(device)),
      open: !showClosedEvents,
    },
  })
  return {
    eventsSummary,
  }
}
