import { SensorTypeEnum } from '@/api/enumerations'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetDataTimeseriesLast } from '@/api/v1/protected/web-application/projects/real_time'
import { useMemo } from 'react'

export function useBatterySOC(projectId: string) {
  const project = useSelectProject(projectId)

  const { data: socData, isLoading: socLoading } = useGetDataTimeseriesLast({
    pathParams: { projectId },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.PROJECT_SOC_PERCENT],
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 30 * 1000,
      staleTime: 15 * 1000,
    },
  })

  const latestSOC = useMemo(() => {
    if (!socData?.length) return null
    const entry = socData[0]
    if (!entry) return null
    const v =
      entry.value_real ??
      entry.value_double ??
      entry.value_integer ??
      (entry.value_text ? parseFloat(entry.value_text) : null)
    if (v === null || v === undefined || isNaN(v)) return null
    return v * 100
  }, [socData])

  const remainingMWh = useMemo(() => {
    if (latestSOC === null) return null
    const cap = project.data?.capacity_bess_energy_bol_dc ?? 0
    if (cap === 0) return null
    return (latestSOC / 100) * cap
  }, [latestSOC, project.data?.capacity_bess_energy_bol_dc])

  const socValue = useMemo(() => {
    if (socLoading) return null
    if (latestSOC === null) return 'N/A'
    return `${latestSOC.toFixed(0)}%`
  }, [socLoading, latestSOC])

  return {
    socValue,
    remainingMWh,
    isLoading: socLoading,
  }
}
