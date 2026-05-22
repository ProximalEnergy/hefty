import { useGetEventDevices } from '@/api/v1/operational/project/events'

export function useProjectImpactsEventViewStableContext({
  projectId,
}: {
  projectId: string
}) {
  const eventDevices = useGetEventDevices({
    pathParams: { projectId: projectId as string },
  })
  return {
    eventDevices,
  }
}
