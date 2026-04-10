import { ProjectTypeEnum, SensorTypeEnum } from '@/api/enumerations'
import { useGetSolarPosition } from '@/api/v1/operational/project/project_solar'
import { useGetMeterPowerAndExpectedPowerV3 } from '@/api/v1/protected/system'
import { roundTime } from '@/utils/interval'
import { QUERY_TIME } from '@/utils/queryTiming'
import dayjs from 'dayjs'
import { useMemo } from 'react'

const POINTS_PER_HOUR = 12

/**
 * Returns near real-time performance index.
 * Fetches 24h of data (same query as the Meter Power
 * chart). During daytime uses the last hour slice;
 * at nighttime uses the full 24h window.
 */
export function useRealtimePerformanceIndex(
  projectId: string | undefined,
  projectTypeId: number | undefined,
  hasExpectedIntegration: boolean | undefined,
  nameShort: string | undefined,
) {
  const now = dayjs()
  const end = now.minute(Math.floor(now.minute() / 5) * 5).second(0)
  const endTime = end.toISOString()
  const startTime = end.subtract(24, 'hour').toISOString()

  const isPV =
    projectTypeId === ProjectTypeEnum.PV ||
    projectTypeId === ProjectTypeEnum.PVS
  const isEnabled = !!projectId && isPV && hasExpectedIntegration === true

  const solarPosition = useGetSolarPosition({
    pathParams: {
      project_id: projectId || '-1',
    },
    queryOptions: {
      enabled: isEnabled,
      refetchInterval: QUERY_TIME.TEN_MINUTES,
      staleTime: QUERY_TIME.FIVE_MINUTES,
    },
  })

  const isNighttime = solarPosition.data
    ? !solarPosition.data.is_daytime
    : false

  const includeSoiling = !['sigurd'].includes(nameShort || '')
  const includeDegradation = ['sigurd'].includes(nameShort || '')

  const data = useGetMeterPowerAndExpectedPowerV3({
    pathParams: { project_id: projectId || '-1' },
    queryParams: {
      start: roundTime(startTime, '5min', 'down'),
      end: roundTime(endTime, '5min', 'up'),
      interval: '5min',
      include_storage: projectTypeId === ProjectTypeEnum.PVS,
      include_setpoint: true,
      include_soiling: includeSoiling,
      include_degradation: includeDegradation,
    },
    queryOptions: {
      enabled: isEnabled,
      refetchOnWindowFocus: false,
      refetchInterval: QUERY_TIME.ONE_MINUTE,
      staleTime: QUERY_TIME.THIRTY_SECONDS,
    },
  })

  return useMemo(() => {
    if (!data.data || !projectTypeId) {
      return {
        performanceIndexPct: null,
        isLoading: data.isLoading,
        isNighttime,
      }
    }

    const traces = data.data

    const meterSensorTypeId =
      projectTypeId === ProjectTypeEnum.PVS
        ? SensorTypeEnum.PV_MV_COLLECTOR_CIRCUIT_METER_ACTIVE_POWER
        : SensorTypeEnum.METER_ACTIVE_POWER
    const meterTrace = traces.find(
      (t) => t.sensor_type_id === meterSensorTypeId,
    )
    const expectedTrace = traces.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_EXPECTED_POWER,
    )

    if (!meterTrace || !expectedTrace) {
      return {
        performanceIndexPct: null,
        isLoading: data.isLoading,
        isNighttime,
      }
    }

    let meterY = meterTrace.y as (number | null)[]
    let expectedY = expectedTrace.y as (number | null)[]

    if (!isNighttime) {
      meterY = meterY.slice(-POINTS_PER_HOUR)
      expectedY = expectedY.slice(-POINTS_PER_HOUR)
    }

    const sumMeter = meterY
      .map((v) => (v != null ? Math.max(0, v) : 0))
      .reduce((a, b) => a + b, 0)
    const sumExpected = expectedY.map((v) => v ?? 0).reduce((a, b) => a + b, 0)

    const pct = sumExpected === 0 ? null : (sumMeter / sumExpected) * 100

    return {
      performanceIndexPct: pct,
      isLoading: data.isLoading,
      isNighttime,
    }
  }, [data.data, data.isLoading, projectTypeId, isNighttime])
}
