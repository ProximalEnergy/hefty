import { useGetUserType } from '@/api/admin'
import { DeviceTypeEnum, UserTypeEnum } from '@/api/enumerations'
import { useSelectProject } from '@/api/v1/operational/projects'
import type { MetStationContext } from '@/features/performance/met-station/types/met-station'
import { useGetDevicesV2 } from '@/hooks/api'

type UseMetStationContextProps = {
  projectId: string | undefined
}

export function useMetStationContext({
  projectId,
}: UseMetStationContextProps): MetStationContext {
  const userType = useGetUserType({})
  const isSuperadmin = userType.data?.user_type_id === UserTypeEnum.SUPERADMIN
  const projectQuery = useSelectProject(projectId)
  const devicesQuery = useGetDevicesV2({
    pathParams: { projectId: projectId ?? '' },
    filters: {
      device_type_ids: [DeviceTypeEnum.MET_STATION],
    },
    queryOptions: { enabled: projectId != null },
  })

  return {
    projectId: projectId ?? '',
    project: projectQuery.data,
    devices: devicesQuery.data,
    isSuperadmin,
    isLoading:
      projectQuery.isLoading || devicesQuery.isLoading || userType.isLoading,
    error: projectQuery.error ?? devicesQuery.error ?? userType.error ?? null,
  }
}
