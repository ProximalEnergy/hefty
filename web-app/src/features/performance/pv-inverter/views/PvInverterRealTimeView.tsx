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
import { PvPcsReactivePowerChart } from '@/components/pv-pcs/ReactivePowerChart'
import { PVPCSStatsCards } from '@/components/pv-pcs/StatsCards'
import { StatusAndErrorCodes } from '@/components/pv-pcs/StatusAndErrorCodes'
import { useGetDevicesV2 } from '@/hooks/api'
import type { DataTimeSeries } from '@/hooks/types'
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
    for (let index = expectedTrace.y.length - 1; index >= 0; index -= 1) {
      if (
        expectedTrace.y[index] !== null &&
        expectedTrace.y[index] !== undefined
      ) {
        value = expectedTrace.y[index] as number
        timestamp = expectedTrace.x[index] || null
        break
      }
    }
  }

  return { value, timestamp }
}

export function PvInverterRealTimeView() {
  const { projectId } = useParams<{ projectId: string }>()
  const project = useSelectProject(projectId!)
  const hasExpectedIntegration = project.data?.has_expected_energy_integration

  const devices = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: { device_type_ids: [PV_INVERTER_DEVICE_TYPE_ID] },
    queryOptions: { enabled: !!projectId },
  })

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
      refetchInterval: QUERY_TIME.THIRTY_SECONDS,
      staleTime: QUERY_TIME.FIFTEEN_SECONDS,
    },
  })

  const activeEvents = useGetEventsSummary({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_type_ids: [PV_INVERTER_DEVICE_TYPE_ID],
      open: true,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.ONE_MINUTE,
    },
  })

  const pvCircuitEvents = useGetEventsSummary({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_type_ids: [DeviceTypeEnum.PV_FEEDER],
      open: true,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.ONE_MINUTE,
    },
  })

  const pvBlockEvents = useGetEventsSummary({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_type_ids: [DeviceTypeEnum.PV_BLOCK],
      open: true,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.ONE_MINUTE,
    },
  })

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
    }, 30000)

    return () => clearInterval(interval)
  }, [])

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
      refetchInterval: QUERY_TIME.THIRTY_SECONDS,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: QUERY_TIME.TWENTY_FIVE_SECONDS,
    },
  })

  const cmmsTickets = useGetCMMSTickets({
    pathParams: { project_id: projectId || '-1' },
    queryParams: { device_type_ids: [PV_INVERTER_DEVICE_TYPE_ID] },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.ONE_MINUTE,
    },
  })

  const pcsExpectedPower = useGetExpectedPowerByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: PV_INVERTER_DEVICE_TYPE_ID,
    },
    queryOptions: {
      enabled: !!projectId && hasExpectedIntegration === true,
      refetchInterval: QUERY_TIME.THIRTY_SECONDS,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: QUERY_TIME.TWENTY_FIVE_SECONDS,
    },
  })

  const solarPosition = useGetSolarPosition({
    pathParams: { project_id: projectId || '-1' },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.THIRTY_SECONDS,
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

  useEffect(() => {
    if (latestExpectedPower.value !== null) {
      setPreservedExpectedPower({
        mw: latestExpectedPower.value,
        timestamp: latestExpectedPower.timestamp,
      })
    }
  }, [latestExpectedPower.value, latestExpectedPower.timestamp])

  useEffect(() => {
    if (solarPosition.data && !solarPosition.data.is_daytime) {
      setPreservedExpectedPower({ mw: null, timestamp: null })
    }
  }, [solarPosition.data])

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
      refetchInterval: QUERY_TIME.THIRTY_SECONDS,
      staleTime: QUERY_TIME.FIFTEEN_SECONDS,
    },
  })

  const stats = useMemo(() => {
    const powerTrace = realtimeData.data?.traces?.find(
      (trace) => trace.sensor_type_id === SensorTypeEnum.PV_INVERTER_AC_POWER,
    )
    const reactivePowerTrace = realtimeData.data?.traces?.find(
      (trace) =>
        trace.sensor_type_id === SensorTypeEnum.PV_INVERTER_REACTIVE_POWER,
    )
    const efficiencyTrace = realtimeData.data?.traces?.find(
      (trace) =>
        trace.sensor_type_id === SensorTypeEnum.PV_INVERTER_MODULE_EFFICIENCY,
    )

    const powerValues =
      powerTrace?.values?.filter((value): value is number => value !== null) ||
      []
    const reactivePowerValues =
      reactivePowerTrace?.values?.filter(
        (value): value is number => value !== null,
      ) || []
    const efficiencyValues =
      efficiencyTrace?.values?.filter(
        (value): value is number => value !== null,
      ) || []

    const totalPowerMW = powerValues.reduce((sum, value) => sum + value, 0)
    const totalReactivePowerMVar = reactivePowerValues.reduce(
      (sum, value) => sum + value,
      0,
    )

    let cumulativePCSPowerTimestamp: string | null = null
    if (powerTrace?.times && powerTrace.times.length > 0) {
      cumulativePCSPowerTimestamp =
        powerTrace.times[powerTrace.times.length - 1] || null
    }

    const avgEfficiency =
      efficiencyValues.length > 0
        ? efficiencyValues.reduce((sum, value) => sum + value, 0) /
          efficiencyValues.length
        : null

    const oneHourAgo = dayjs().subtract(1, 'hour').valueOf()
    const staleDeviceIds: number[] = []
    if (
      powerTrace?.times &&
      realtimeData.data?.device_ids &&
      powerTrace.times.length === realtimeData.data.device_ids.length
    ) {
      powerTrace.times.forEach((time, index) => {
        const deviceId = realtimeData.data?.device_ids[index]
        if (deviceId === undefined || deviceId === null) {
          return
        }
        if (!time) {
          staleDeviceIds.push(deviceId)
          return
        }
        const timestamp = new Date(time).getTime()
        if (timestamp < oneHourAgo || Number.isNaN(timestamp)) {
          staleDeviceIds.push(deviceId)
        }
      })
    }

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

    let poiPowerMW: number | null = null
    let poiPowerTimestamp: string | null = null
    if (meterRealtimeData.data?.traces) {
      const meterPowerTrace = meterRealtimeData.data.traces.find(
        (trace) => trace.sensor_type_id === SensorTypeEnum.METER_ACTIVE_POWER,
      )
      if (
        meterPowerTrace &&
        meterPowerTrace.values &&
        meterPowerTrace.values.length > 0 &&
        meterPowerTrace.times &&
        meterPowerTrace.times.length > 0
      ) {
        const validValues = meterPowerTrace.values.filter(
          (value): value is number => value !== null && value !== undefined,
        )
        if (validValues.length > 0) {
          poiPowerMW = validValues.reduce((sum, value) => sum + value, 0)
          const validTimes = meterPowerTrace.times.filter(
            (time): time is string => time !== null && time !== undefined,
          )
          if (validTimes.length > 0) {
            poiPowerTimestamp = validTimes[validTimes.length - 1]
          }
        }
      }
    }

    let cumulativeExpectedPCSPowerMW: number | null = null
    if (pcsExpectedPower.data?.expected_power) {
      const expectedPowerValues = Object.values(
        pcsExpectedPower.data.expected_power,
      ).filter(
        (value): value is number => value !== null && value !== undefined,
      )
      if (expectedPowerValues.length > 0) {
        cumulativeExpectedPCSPowerMW = expectedPowerValues.reduce(
          (sum, value) => sum + value,
          0,
        )
      }
    }

    const staleDeviceNames: string[] = []
    if (devices.data && staleDeviceIds.length > 0) {
      staleDeviceIds.forEach((deviceId) => {
        const device = devices.data.find((d) => d.device_id === deviceId)
        if (device) {
          staleDeviceNames.push(device.name_long || `Device ${deviceId}`)
        }
      })
    }

    const finalExpectedPowerMW = preservedExpectedPower.mw
    const finalExpectedPowerTimestamp = preservedExpectedPower.timestamp

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
        ? finalExpectedPowerTimestamp
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
      staleDevicesCount: staleDeviceIds.length,
      isNighttime: solarPosition.data ? !solarPosition.data.is_daytime : false,
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

  const maxCapacityMWac = useMemo(() => {
    if (!devices.data || devices.data.length === 0) {
      return null
    }
    const maxKWac = Math.max(
      ...devices.data.map((device) => device.capacity_ac || 0),
    )
    return maxKWac / 1000
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
      <PvPcsReactivePowerChart
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
