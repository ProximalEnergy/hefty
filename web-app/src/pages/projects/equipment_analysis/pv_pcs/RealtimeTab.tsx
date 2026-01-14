import { DeviceTypeEnum, SensorTypeEnum } from '@/api/enumerations'
import { useGetCMMSTickets } from '@/api/v1/operational/project/cmms_tickets'
import { useGetEventsSummary } from '@/api/v1/operational/project/events'
import { useGetSolarPosition } from '@/api/v1/operational/project/project_solar'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetMeterPowerAndExpectedPower } from '@/api/v1/protected/pv-expected-energy/plot/plot'
import {
  useGetExpectedPowerByDeviceTypeID,
  useGetRealTimeByDeviceTypeID,
} from '@/api/v1/protected/web-application/projects/real_time'
import { PageLoader } from '@/components/Loading'
import { ACVoltageChart } from '@/components/pv-pcs/ACVoltageChart'
import { ActivePowerChart } from '@/components/pv-pcs/ActivePowerChart'
import { DCVoltageChart } from '@/components/pv-pcs/DCVoltageChart'
import { EfficiencyChart } from '@/components/pv-pcs/EfficiencyChart'
import { EfficiencyLevelCard } from '@/components/pv-pcs/EfficiencyLevelCard'
import { ReactivePowerChart } from '@/components/pv-pcs/ReactivePowerChart'
import { StatsCards } from '@/components/pv-pcs/StatsCards'
import { StatusAndErrorCodes } from '@/components/pv-pcs/StatusAndErrorCodes'
import { useGetDevicesV2 } from '@/hooks/api'
import { DataTimeSeries } from '@/hooks/types'
import { Stack } from '@mantine/core'
import dayjs from 'dayjs'
import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router'

const PV_PCS_DEVICE_TYPE_ID = DeviceTypeEnum.PV_PCS

const findLatestExpectedPower = (series?: DataTimeSeries[]) => {
  let value: number | null = null
  let timestamp: string | null = null

  const expectedTrace = series?.find((trace) => trace.name === 'Expected Power')
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

const RealtimeTab = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const project = useSelectProject(projectId!)

  // Only include expected power values if the project has expected energy integration
  const hasExpectedIntegration = project.data?.has_expected_energy_integration

  // Get all PV PCS devices for CMMS tickets
  const devices = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: [PV_PCS_DEVICE_TYPE_ID],
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  // Get realtime data for active power, reactive power, power factor, voltages, status
  const realtimeData = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: PV_PCS_DEVICE_TYPE_ID,
    },
    queryParams: {
      sensor_type_ids: [
        SensorTypeEnum.PV_PCS_AC_POWER,
        SensorTypeEnum.PV_PCS_AC_POWER_SETPOINT,
        SensorTypeEnum.PV_PCS_REACTIVE_POWER,
        SensorTypeEnum.PV_PCS_REACTIVE_POWER_SETPOINT,
        SensorTypeEnum.PV_PCS_VOLTAGE_LL_AB,
        SensorTypeEnum.PV_PCS_VOLTAGE_LL_BC,
        SensorTypeEnum.PV_PCS_VOLTAGE_LL_CA,
        SensorTypeEnum.PV_PCS_DC_VOLTAGE,
        SensorTypeEnum.PV_PCS_STATUS,
        SensorTypeEnum.PV_PCS_MODULE_EFFICIENCY,
      ],
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 30000, // Refetch every 30 seconds
      staleTime: 15000,
    },
  })

  // Get active events for PV PCS devices
  const activeEvents = useGetEventsSummary({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_type_ids: [PV_PCS_DEVICE_TYPE_ID],
      open: true,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 60000, // Refetch every minute
    },
  })

  // Get active events for all PV Circuit devices
  const pvCircuitEvents = useGetEventsSummary({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_type_ids: [DeviceTypeEnum.PV_CIRCUIT],
      open: true,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 60000, // Refetch every minute
    },
  })

  // Get active events for PV Block devices
  const pvBlockEvents = useGetEventsSummary({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_type_ids: [DeviceTypeEnum.BLOCK],
      open: true,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 60000, // Refetch every minute
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
  const expectedPowerData = useGetMeterPowerAndExpectedPower({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: expectedPowerTimeRange.start,
      end: expectedPowerTimeRange.end,
      include_soiling: true,
      interval: '5min',
    },
    queryOptions: {
      enabled: !!projectId && hasExpectedIntegration === true,
      refetchInterval: 30000, // Refetch every 30 seconds
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 25000, // Consider data stale after 25 seconds
    },
  })

  // Get CMMS tickets for PV PCS devices
  const cmmsTickets = useGetCMMSTickets({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_type_ids: [PV_PCS_DEVICE_TYPE_ID],
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 60000, // Refetch every minute
    },
  })

  // Get expected power for all PCS devices using the new endpoint
  const pcsExpectedPower = useGetExpectedPowerByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: PV_PCS_DEVICE_TYPE_ID,
    },
    queryOptions: {
      enabled: !!projectId && hasExpectedIntegration === true,
      refetchInterval: 30000, // Refetch every 30 seconds
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 25000, // Consider data stale after 25 seconds
    },
  })

  // Get solar position to determine if it's nighttime
  const solarPosition = useGetSolarPosition({
    pathParams: { project_id: projectId || '-1' },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 30000, // Refetch every 30 seconds
      staleTime: 15000,
    },
  })

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
      refetchInterval: 30000, // Refetch every 30 seconds
      staleTime: 15000,
    },
  })

  // Calculate stats from realtime data
  const stats = useMemo(() => {
    const powerTrace = realtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_PCS_AC_POWER,
    )
    const reactivePowerTrace = realtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_PCS_REACTIVE_POWER,
    )
    const efficiencyTrace = realtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_PCS_MODULE_EFFICIENCY,
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

    // Get expected power at POI (still from expectedPowerData for comparison)
    const { value: expectedPowerMW, timestamp: expectedPowerTimestamp } =
      findLatestExpectedPower(expectedPowerData.data?.data)

    // Preserve previous value during refetches - use previous value if current data is null/loading
    const finalExpectedPowerMW = expectedPowerMW
    const finalExpectedPowerTimestamp = expectedPowerTimestamp

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
        ? finalExpectedPowerTimestamp
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
    expectedPowerData.data,
    pcsExpectedPower.data,
    devices.data,
    solarPosition.data,
    meterRealtimeData.data,
    hasExpectedIntegration,
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
      <StatsCards stats={stats} />

      <ActivePowerChart
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

      <ACVoltageChart realtimeData={realtimeData} />

      <DCVoltageChart realtimeData={realtimeData} />

      <StatusAndErrorCodes
        realtimeData={realtimeData}
        projectId={projectId || '-1'}
      />

      <EfficiencyLevelCard avgEfficiency={stats.avgEfficiency} />
    </Stack>
  )
}

export default RealtimeTab
