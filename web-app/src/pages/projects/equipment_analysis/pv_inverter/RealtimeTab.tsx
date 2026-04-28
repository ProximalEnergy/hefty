import { DeviceTypeEnum, SensorTypeEnum } from '@/api/enumerations'
import { useGetCMMSTickets } from '@/api/v1/operational/project/cmms_tickets'
import { useGetEventsSummary } from '@/api/v1/operational/project/events'
import { useGetSolarPosition } from '@/api/v1/operational/project/project_solar'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetMeterPowerAndExpectedPowerV3 } from '@/api/v1/protected/system'
import {
  useGetExpectedPowerByDeviceTypeID,
  useGetRealTimeByDeviceTypeID,
} from '@/api/v1/protected/web-application/projects/real_time'
import { PageLoader } from '@/components/Loading'
import { ACVoltageChartPvPcs } from '@/components/pv-pcs/ACVoltageChart'
import { ActivePowerChartPvPcs } from '@/components/pv-pcs/ActivePowerChart'
import { DCVoltageChartPvPcs } from '@/components/pv-pcs/DCVoltageChart'
import { EfficiencyChart } from '@/components/pv-pcs/EfficiencyChart'
import { EfficiencyLevelCard } from '@/components/pv-pcs/EfficiencyLevelCard'
import { ReactivePowerChart } from '@/components/pv-pcs/ReactivePowerChart'
import { PVPCSStatsCards } from '@/components/pv-pcs/StatsCards'
import { StatusAndErrorCodes } from '@/components/pv-pcs/StatusAndErrorCodes'
import { useGetDevicesV2 } from '@/hooks/api'
import { DataTimeSeries } from '@/hooks/types'
import { QUERY_TIME } from '@/utils/queryTiming'
import { Stack } from '@mantine/core'
import dayjs from 'dayjs'
import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router'

const PV_INVERTER_DEVICE_TYPE_ID = DeviceTypeEnum.PV_INVERTER

const findLatestExpectedPower = (series?: DataTimeSeries[]) => {
  let value: number | null = null
  let timestamp: string | null = null

  const expectedTrace = series?.find(
    (trace) => trace.sensor_type_id === SensorTypeEnum.PV_EXPECTED_POWER,
  )
  if (
    expectedTrace &&
    expectedTrace.y &&
    expectedTrace.y.length > 0 &&
    expectedTrace.x &&
    expectedTrace.x.length > 0
  ) {
    for (let i = expectedTrace.y.length - 1; i >= 0; i--) {
      if (expectedTrace.y[i] !== null && expectedTrace.y[i] !== undefined) {
        value = expectedTrace.y[i] as number
        timestamp = expectedTrace.x[i] || null
        break
      }
    }
  }

  return { value, timestamp }
}

const PVInverterRealtimeTab = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const project = useSelectProject(projectId!)

  // Only include expected power values if the project has expected energy integration
  const hasExpectedIntegration = project.data?.has_expected_energy_integration

  // Get all PV Inverter devices for CMMS tickets
  const devices = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: [PV_INVERTER_DEVICE_TYPE_ID],
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  // Get realtime data for active power, reactive power, power factor, voltages, status
  const realtimeData = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: PV_INVERTER_DEVICE_TYPE_ID,
    },
    queryParams: {
      sensor_type_ids: [
        SensorTypeEnum.PV_INVERTER_AC_POWER,
        SensorTypeEnum.PV_INVERTER_AC_POWER_SETPOINT,
        SensorTypeEnum.PV_INVERTER_REACTIVE_POWER,
        SensorTypeEnum.PV_INVERTER_REACTIVE_POWER_SETPOINT,
        SensorTypeEnum.PV_INVERTER_VOLTAGE_LL_AB,
        SensorTypeEnum.PV_INVERTER_VOLTAGE_LL_BC,
        SensorTypeEnum.PV_INVERTER_VOLTAGE_LL_CA,
        SensorTypeEnum.PV_INVERTER_DC_VOLTAGE,
        SensorTypeEnum.PV_INVERTER_STATUS,
        SensorTypeEnum.PV_INVERTER_MODULE_EFFICIENCY,
      ],
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.THIRTY_SECONDS, // Refetch every 30 seconds
      staleTime: QUERY_TIME.FIFTEEN_SECONDS,
    },
  })

  // Get active events for PV Inverter devices
  const activeEvents = useGetEventsSummary({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_type_ids: [PV_INVERTER_DEVICE_TYPE_ID],
      open: true,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.ONE_MINUTE, // Refetch every minute
    },
  })

  // Get active events for all PV Circuit devices
  const pvCircuitEvents = useGetEventsSummary({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_type_ids: [DeviceTypeEnum.PV_FEEDER],
      open: true,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.ONE_MINUTE, // Refetch every minute
    },
  })

  // Get active events for PV Block devices
  const pvBlockEvents = useGetEventsSummary({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_type_ids: [DeviceTypeEnum.PV_BLOCK],
      open: true,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.ONE_MINUTE, // Refetch every minute
    },
  })

  // Get expected power at POI - update time range every 30 seconds to match refetch interval
  const [expectedPowerTimeRange, setExpectedPowerTimeRange] = useState(() => {
    const now = dayjs()
    return {
      start: now.subtract(1, 'hour').toISOString(),
      end: now.toISOString(),
    }
  })

  useEffect(() => {
    const interval = setInterval(() => {
      const now = dayjs()
      setExpectedPowerTimeRange({
        start: now.subtract(1, 'hour').toISOString(),
        end: now.toISOString(),
      })
    }, 30000) // Update every 30 seconds

    return () => clearInterval(interval)
  }, [])

  // Preserve previous expected power value during refetches
  const expectedPowerData = useGetMeterPowerAndExpectedPowerV3({
    pathParams: { project_id: projectId || '-1' },
    queryParams: {
      start: expectedPowerTimeRange.start,
      end: expectedPowerTimeRange.end,
      include_soiling: true,
      interval: '5min',
    },
    queryOptions: {
      enabled: !!projectId && hasExpectedIntegration === true,
      refetchInterval: QUERY_TIME.THIRTY_SECONDS, // Refetch every 30 seconds
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: QUERY_TIME.TWENTY_FIVE_SECONDS, // Consider data stale after 25 seconds
    },
  })

  // Get CMMS tickets for PV Inverter devices
  const cmmsTickets = useGetCMMSTickets({
    pathParams: { project_id: projectId || '-1' },
    queryParams: {
      device_type_ids: [PV_INVERTER_DEVICE_TYPE_ID],
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.ONE_MINUTE, // Refetch every minute
    },
  })

  // Get expected power for all PCS devices using the new endpoint
  const pcsExpectedPower = useGetExpectedPowerByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: PV_INVERTER_DEVICE_TYPE_ID,
    },
    queryOptions: {
      enabled: !!projectId && hasExpectedIntegration === true,
      refetchInterval: QUERY_TIME.THIRTY_SECONDS, // Refetch every 30 seconds
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: QUERY_TIME.TWENTY_FIVE_SECONDS, // Consider data stale after 25 seconds
    },
  })

  // Get solar position to determine if it's nighttime
  const solarPosition = useGetSolarPosition({
    pathParams: { project_id: projectId || '-1' },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.THIRTY_SECONDS, // Refetch every 30 seconds
      staleTime: QUERY_TIME.FIFTEEN_SECONDS,
    },
  })

  const [preservedExpectedPower, setPreservedExpectedPower] = useState<{
    mw: number | null
    timestamp: string | null
  }>({ mw: null, timestamp: null })

  const latestExpectedPower = useMemo(() => {
    return findLatestExpectedPower(expectedPowerData.data as DataTimeSeries[])
  }, [expectedPowerData.data])

  // Preserve last known expected power while the time-window query refetches.
  // Without this, `expectedPowerMW` can flicker to null between refetches.
  useEffect(() => {
    if (latestExpectedPower.value !== null) {
      setPreservedExpectedPower({
        mw: latestExpectedPower.value,
        timestamp: latestExpectedPower.timestamp,
      })
    }
  }, [latestExpectedPower.value, latestExpectedPower.timestamp])

  // Clear expected power at night so we don't show a stale daytime value.
  useEffect(() => {
    if (solarPosition.data && !solarPosition.data.is_daytime) {
      setPreservedExpectedPower({ mw: null, timestamp: null })
    }
  }, [solarPosition.data])

  // Get realtime meter data for POI Power (same endpoint as PCS Power for up-to-date readings)
  const meterRealtimeData = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DeviceTypeEnum.METER,
    },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.METER_ACTIVE_POWER],
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.THIRTY_SECONDS, // Refetch every 30 seconds
      staleTime: QUERY_TIME.FIFTEEN_SECONDS,
    },
  })

  // Calculate stats from realtime data
  const stats = useMemo(() => {
    const powerTrace = realtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_INVERTER_AC_POWER,
    )
    const reactivePowerTrace = realtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_INVERTER_REACTIVE_POWER,
    )
    const efficiencyTrace = realtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_INVERTER_MODULE_EFFICIENCY,
    )

    const powerValues =
      powerTrace?.values?.filter((v): v is number => v !== null) || []
    const reactivePowerValues =
      reactivePowerTrace?.values?.filter((v): v is number => v !== null) || []
    const efficiencyValues =
      efficiencyTrace?.values?.filter((v): v is number => v !== null) || []

    const totalPowerMW = powerValues.reduce((sum, val) => sum + val, 0)
    const totalReactivePowerMVar = reactivePowerValues.reduce(
      (sum, val) => sum + val,
      0,
    )

    // Get the latest timestamp for cumulative PCS power
    let cumulativePCSPowerTimestamp: string | null = null
    if (powerTrace?.times && powerTrace.times.length > 0) {
      // Get the last timestamp (corresponds to the latest values)
      cumulativePCSPowerTimestamp =
        powerTrace.times[powerTrace.times.length - 1] || null
    }

    // Calculate average efficiency
    const avgEfficiency =
      efficiencyValues.length > 0
        ? efficiencyValues.reduce((sum, val) => sum + val, 0) /
          efficiencyValues.length
        : null

    // Find devices with stale data (no data in last hour)
    const oneHourAgo = dayjs().subtract(1, 'hour').valueOf()
    const staleDeviceIds: number[] = []
    if (
      powerTrace?.times &&
      realtimeData.data?.device_ids &&
      powerTrace.times.length === realtimeData.data.device_ids.length
    ) {
      powerTrace.times.forEach((time, idx) => {
        if (time) {
          const timestamp = new Date(time).getTime()
          if (timestamp < oneHourAgo || isNaN(timestamp)) {
            const deviceId = realtimeData.data.device_ids[idx]
            if (deviceId !== undefined && deviceId !== null) {
              staleDeviceIds.push(deviceId)
            }
          }
        } else {
          // No timestamp means no data - consider it stale
          const deviceId = realtimeData.data.device_ids[idx]
          if (deviceId !== undefined && deviceId !== null) {
            staleDeviceIds.push(deviceId)
          }
        }
      })
    }
    const staleDevicesCount = staleDeviceIds.length

    // Calculate daily revenue loss from all active events (PCS, PV Circuit, PV Block)
    const dailyRevenueLoss =
      (activeEvents.data?.reduce(
        (sum, event) => sum + (event.loss_daily_financial || 0),
        0,
      ) || 0) +
      (pvCircuitEvents.data?.reduce(
        (sum, event) => sum + (event.loss_daily_financial || 0),
        0,
      ) || 0) +
      (pvBlockEvents.data?.reduce(
        (sum, event) => sum + (event.loss_daily_financial || 0),
        0,
      ) || 0)

    const pcsEventsCount = activeEvents.data?.length || 0
    const pvCircuitEventsCount = pvCircuitEvents.data?.length || 0
    const pvBlockEventsCount = pvBlockEvents.data?.length || 0
    const totalEventsCount =
      pcsEventsCount + pvCircuitEventsCount + pvBlockEventsCount

    // Get latest meter power from realtime endpoint (same as PCS Power for up-to-date readings)
    let poiPowerMW: number | null = null
    let poiPowerTimestamp: string | null = null
    if (meterRealtimeData.data?.traces) {
      const meterPowerTrace = meterRealtimeData.data.traces.find(
        (t) => t.sensor_type_id === SensorTypeEnum.METER_ACTIVE_POWER,
      )
      if (
        meterPowerTrace &&
        meterPowerTrace.values &&
        meterPowerTrace.values.length > 0 &&
        meterPowerTrace.times &&
        meterPowerTrace.times.length > 0
      ) {
        // Sum all meter values (in case there are multiple meters)
        // Values are already in MW due to unit_scale applied in the endpoint
        const validValues = meterPowerTrace.values.filter(
          (v): v is number => v !== null && v !== undefined,
        )
        if (validValues.length > 0) {
          // Sum all meter readings (already in MW, same as PCS power)
          poiPowerMW = validValues.reduce((sum, val) => sum + val, 0)
          // Get the latest timestamp
          const validTimes = meterPowerTrace.times.filter(
            (t): t is string => t !== null && t !== undefined,
          )
          if (validTimes.length > 0) {
            poiPowerTimestamp = validTimes[validTimes.length - 1]
          }
        }
      }
    }

    const finalExpectedPowerMW = preservedExpectedPower.mw
    const finalExpectedPowerTimestamp = preservedExpectedPower.timestamp

    // Calculate cumulative expected PCS power (sum of all PCS devices' expected power)
    // Use the same timestamp as POI Power Expected since they come from the same data source
    let cumulativeExpectedPCSPowerMW: number | null = null
    if (pcsExpectedPower.data?.expected_power) {
      const expectedPowerValues = Object.values(
        pcsExpectedPower.data.expected_power,
      ).filter((v): v is number => v !== null && v !== undefined)
      if (expectedPowerValues.length > 0) {
        cumulativeExpectedPCSPowerMW = expectedPowerValues.reduce(
          (sum, val) => sum + val,
          0,
        )
      }
    }
    // Use the same timestamp as finalExpectedPowerTimestamp since they're from the same data source
    const cumulativeExpectedPCSPowerTimestamp = finalExpectedPowerTimestamp

    // Map stale device IDs to device names
    const staleDeviceNames: string[] = []
    if (devices.data && staleDeviceIds.length > 0) {
      staleDeviceIds.forEach((deviceId) => {
        const device = devices.data.find((d) => d.device_id === deviceId)
        if (device) {
          staleDeviceNames.push(device.name_long || `Device ${deviceId}`)
        }
      })
    }

    // Check if it's nighttime using solar position endpoint
    const isNighttime = solarPosition.data
      ? !solarPosition.data.is_daytime
      : false

    return {
      poiPowerMW: poiPowerMW !== null ? poiPowerMW.toFixed(2) : null,
      poiPowerTimestamp,
      expectedPowerMW:
        hasExpectedIntegration && finalExpectedPowerMW !== null
          ? finalExpectedPowerMW.toFixed(2)
          : null,
      expectedPowerTimestamp: hasExpectedIntegration
        ? finalExpectedPowerMW !== null
          ? finalExpectedPowerTimestamp
          : null
        : null,
      cumulativePCSPowerMW: totalPowerMW.toFixed(2),
      cumulativePCSPowerTimestamp,
      cumulativeExpectedPCSPowerMW:
        hasExpectedIntegration && cumulativeExpectedPCSPowerMW !== null
          ? cumulativeExpectedPCSPowerMW.toFixed(2)
          : null,
      cumulativeExpectedPCSPowerTimestamp: hasExpectedIntegration
        ? cumulativeExpectedPCSPowerTimestamp
        : null,
      cumulativePCSReactivePowerMVar: totalReactivePowerMVar.toFixed(2),
      totalEventsCount,
      pcsEventsCount,
      pvCircuitEventsCount,
      pvBlockEventsCount,
      dailyRevenueLoss: dailyRevenueLoss.toFixed(2),
      openCMMSTickets: cmmsTickets.data?.data?.length || 0,
      staleDeviceIds,
      staleDeviceNames,
      staleDevicesCount,
      isNighttime,
      avgEfficiency: avgEfficiency ? `${avgEfficiency.toFixed(1)}%` : 'N/A',
    }
  }, [
    realtimeData.data,
    activeEvents.data,
    pvCircuitEvents.data,
    pvBlockEvents.data,
    cmmsTickets.data,
    pcsExpectedPower.data,
    devices.data,
    solarPosition.data,
    meterRealtimeData.data,
    hasExpectedIntegration,
    preservedExpectedPower.mw,
    preservedExpectedPower.timestamp,
  ])

  // Calculate max capacity_ac from devices (convert from kWac to MWac)
  const maxCapacityMWac = useMemo(() => {
    if (!devices.data || devices.data.length === 0) {
      return null
    }
    const maxKWac = Math.max(...devices.data.map((d) => d.capacity_ac || 0))
    return maxKWac / 1000 // Convert kWac to MWac
  }, [devices.data])

  if (project.isLoading) {
    return <PageLoader />
  }

  return (
    <Stack gap="md" pb="md">
      <PVPCSStatsCards stats={stats} />

      <ActivePowerChartPvPcs
        realtimeData={realtimeData}
        maxCapacityMWac={maxCapacityMWac}
        hasExpectedEnergyIntegration={
          project.data?.has_expected_energy_integration
        }
      />

      <ReactivePowerChart
        realtimeData={realtimeData}
        maxCapacityMWac={maxCapacityMWac}
      />

      <EfficiencyChart devices={devices} />

      <ACVoltageChartPvPcs realtimeData={realtimeData} />

      <DCVoltageChartPvPcs realtimeData={realtimeData} />

      <StatusAndErrorCodes
        realtimeData={realtimeData}
        projectId={projectId || '-1'}
      />

      <EfficiencyLevelCard avgEfficiency={stats.avgEfficiency} />
    </Stack>
  )
}

export default PVInverterRealtimeTab
