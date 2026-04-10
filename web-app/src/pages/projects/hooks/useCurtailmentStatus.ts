import { DeviceTypeEnum, SensorTypeEnum } from '@/api/enumerations'
import {
  useGetDataTimeseriesLast,
  useGetRealTimeByDeviceTypeID,
} from '@/api/v1/protected/web-application/projects/real_time'
import { useGetTags } from '@/hooks/api'
import type { Tag } from '@/hooks/projectTags'
import { QUERY_TIME } from '@/utils/queryTiming'
import { useMemo } from 'react'

/**
 * Returns curtailment status for a PV project.
 * Curtailed = POI active power < POI capacity AND PPC active power setpoint < POI
 * capacity.
 */
export function useCurtailmentStatus(
  projectId: string | undefined,
  poiCapacityMW: number | null | undefined,
  isPV: boolean = true,
) {
  const enabled =
    !!projectId && isPV && poiCapacityMW != null && poiCapacityMW > 0

  const meterRealtime = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DeviceTypeEnum.METER,
    },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.METER_ACTIVE_POWER],
    },
    queryOptions: {
      enabled,
      refetchInterval: QUERY_TIME.THIRTY_SECONDS,
      staleTime: QUERY_TIME.FIFTEEN_SECONDS,
    },
  })

  const ppcSetpointTags = useGetTags({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.PPC_ACTIVE_POWER_SETPOINT],
    },
    queryOptions: {
      enabled,
      staleTime: QUERY_TIME.FIVE_MINUTES,
    },
  })

  const ppcSetpointTagIds: number[] = useMemo(() => {
    if (!Array.isArray(ppcSetpointTags.data)) return []
    return (ppcSetpointTags.data as Tag[])
      .filter(
        (t) =>
          t.tag_id &&
          t.sensor_type_id === SensorTypeEnum.PPC_ACTIVE_POWER_SETPOINT,
      )
      .map((t) => Number(t.tag_id))
  }, [ppcSetpointTags.data])

  const substationData = useGetDataTimeseriesLast({
    pathParams: { projectId: projectId || '-1' },
    queryParams: { tag_ids: ppcSetpointTagIds },
    queryOptions: {
      enabled: !!projectId && ppcSetpointTagIds.length > 0,
      staleTime: QUERY_TIME.THIRTY_SECONDS,
    },
  })

  return useMemo(() => {
    if (poiCapacityMW == null || poiCapacityMW <= 0) {
      return { isCurtailed: null, isLoading: false }
    }

    let poiPowerMW: number | null = null
    if (meterRealtime.data?.traces) {
      const trace = meterRealtime.data.traces.find(
        (t) => t.sensor_type_id === SensorTypeEnum.METER_ACTIVE_POWER,
      )
      const validValues = (trace?.values || []).filter(
        (v): v is number => v !== null && v !== undefined,
      )
      if (validValues.length > 0) {
        poiPowerMW = validValues.reduce((sum, val) => sum + val, 0)
      }
    }

    let ppcSetpointMW: number | null = null
    const data = substationData.data || []
    if (data.length > 0) {
      const values = data
        .map((r) => r.value_real ?? r.value_double ?? r.value_integer)
        .filter((v): v is number => v != null && !Number.isNaN(v))
      if (values.length > 0) {
        ppcSetpointMW = Math.max(...values)
      }
    }

    const isLoading =
      meterRealtime.isLoading ||
      ppcSetpointTags.isLoading ||
      (ppcSetpointTagIds.length > 0 && substationData.isLoading)

    if (poiPowerMW == null || ppcSetpointMW == null) {
      return { isCurtailed: null, isLoading }
    }

    const isCurtailed =
      poiPowerMW < poiCapacityMW && ppcSetpointMW < poiCapacityMW

    return { isCurtailed, isLoading }
  }, [
    poiCapacityMW,
    meterRealtime.data,
    meterRealtime.isLoading,
    ppcSetpointTags.isLoading,
    substationData.data,
    substationData.isLoading,
    ppcSetpointTagIds.length,
  ])
}
