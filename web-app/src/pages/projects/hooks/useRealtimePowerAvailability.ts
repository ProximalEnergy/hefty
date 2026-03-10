import {
  DeviceTypeEnum,
  ProjectTypeEnum,
  SensorTypeEnum,
} from '@/api/enumerations'
import {
  DataTimeSeriesLast,
  useGetDataTimeseriesLast,
} from '@/api/v1/protected/web-application/projects/real_time'
import { useGetDevicesV2 } from '@/hooks/api'
import { useMemo } from 'react'

const getValue = (row: DataTimeSeriesLast) =>
  row.value_double ?? row.value_real ?? 0

/**
 * Returns near real-time power availability for
 * storage projects. Fetches the last PCS available
 * charge/discharge power values, sums across PCS
 * devices, and returns the max absolute value as a
 * percentage of the project's POI capacity.
 */
export function useRealtimePowerAvailability(
  projectId: string | undefined,
  projectTypeId: number | undefined,
  poiCapacityMw: number | null | undefined,
) {
  const hasStorage =
    projectTypeId === ProjectTypeEnum.BESS ||
    projectTypeId === ProjectTypeEnum.PVS
  const isEnabled =
    !!projectId && hasStorage && poiCapacityMw != null && poiCapacityMw > 0

  const pcsDevices = useGetDevicesV2({
    pathParams: {
      projectId: projectId || '-1',
    },
    filters: {
      device_type_ids: [DeviceTypeEnum.BESS_PCS],
      fields: ['device_id', 'capacity_ac'],
    },
    queryOptions: {
      enabled: isEnabled,
      staleTime: 5 * 60 * 1000,
    },
  })

  const chargeData = useGetDataTimeseriesLast({
    pathParams: {
      projectId: projectId || '-1',
    },
    queryParams: {
      device_type_ids: [DeviceTypeEnum.BESS_PCS],
      sensor_type_ids: [SensorTypeEnum.BESS_PCS_AVAILABLE_CHARGE_POWER],
    },
    queryOptions: {
      enabled: isEnabled,
      refetchInterval: 60 * 1000,
      staleTime: 30 * 1000,
    },
  })

  const dischargeData = useGetDataTimeseriesLast({
    pathParams: {
      projectId: projectId || '-1',
    },
    queryParams: {
      device_type_ids: [DeviceTypeEnum.BESS_PCS],
      sensor_type_ids: [SensorTypeEnum.BESS_PCS_AVAILABLE_DISCHARGE_POWER],
    },
    queryOptions: {
      enabled: isEnabled,
      refetchInterval: 60 * 1000,
      staleTime: 30 * 1000,
    },
  })

  return useMemo(() => {
    if (!chargeData.data || !dischargeData.data || !poiCapacityMw) {
      return {
        powerAvailabilityPct: null,
        availablePowerMw: null,
        ratedCapacityMw: poiCapacityMw ?? null,
        numPcsUnits: null,
        maxPcsCapacityMw: null,
        isLoading: chargeData.isLoading || dischargeData.isLoading,
      }
    }

    const chargeSum = Math.abs(
      chargeData.data.reduce((acc, r) => acc + getValue(r), 0),
    )

    const dischargeSum = Math.abs(
      dischargeData.data.reduce((acc, r) => acc + getValue(r), 0),
    )

    const maxAvailable = Math.max(chargeSum, dischargeSum)

    const devices = pcsDevices.data ?? []
    const numPcsUnits = devices.length
    const totalPcsCapacityKw = devices.reduce(
      (acc, d) => acc + (d.capacity_ac ?? 0),
      0,
    )
    const maxPcsCapacityMw = totalPcsCapacityKw / 1000

    const pct = (maxAvailable / poiCapacityMw) * 100

    return {
      powerAvailabilityPct: Math.min(pct, 100),
      availablePowerMw: maxAvailable,
      ratedCapacityMw: poiCapacityMw,
      numPcsUnits,
      maxPcsCapacityMw,
      isLoading: chargeData.isLoading || dischargeData.isLoading,
    }
  }, [
    chargeData.data,
    chargeData.isLoading,
    dischargeData.data,
    dischargeData.isLoading,
    pcsDevices.data,
    poiCapacityMw,
  ])
}
