import { DeviceTypeEnum, SensorTypeEnum } from '@/api/enumerations'
import { useGetDataTimeseriesLast } from '@/api/v1/protected/web-application/projects/real_time'
import { useMemo } from 'react'

const STOW_THRESHOLD_PCT = 20

/**
 * Returns true if >20% of tracker zones are in stow mode.
 * Uses TRACKER_ZONE_STATUS from tracker zone devices.
 */
function isStowValue(value: string | number | null | undefined): boolean {
  if (value == null) return false
  const s = String(value).toLowerCase()
  return s.includes('stow')
}

export function useTrackerStowStatus(
  projectId: string | undefined,
  hasTrackers: boolean | undefined,
) {
  const data = useGetDataTimeseriesLast({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_type_ids: [DeviceTypeEnum.TRACKER_ZONE],
      sensor_type_ids: [SensorTypeEnum.TRACKER_ZONE_STATUS],
    },
    queryOptions: {
      enabled: !!projectId && hasTrackers === true,
      refetchInterval: 60 * 1000,
      staleTime: 30 * 1000,
    },
  })

  return useMemo(() => {
    const records = data.data || []
    if (records.length === 0) {
      return { isHighStow: null, isLoading: data.isLoading }
    }

    let stowCount = 0
    for (const r of records) {
      const val =
        r.value_text ?? r.value_integer ?? r.value_real ?? r.value_double
      if (isStowValue(val)) stowCount += 1
    }

    const total = records.length
    const stowPct = total > 0 ? (stowCount / total) * 100 : 0
    const isHighStow = stowPct > STOW_THRESHOLD_PCT

    return { isHighStow, isLoading: data.isLoading }
  }, [data.data, data.isLoading])
}
