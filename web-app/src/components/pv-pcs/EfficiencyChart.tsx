import { DeviceTypeEnum, SensorTypeEnum } from '@/api/enumerations'
import { useGetDataTimeSeriesV3 } from '@/api/v1/operational/project/project_data'
import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useGetDevicesV2 } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import dayjs from 'dayjs'
import type { Data, PlotRelayoutEvent } from 'plotly.js'
import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router'

interface EfficiencyChartProps {
  devices: ReturnType<typeof useGetDevicesV2>
}

export const EfficiencyChart = ({ devices }: EfficiencyChartProps) => {
  const { projectId } = useParams<{ projectId: string }>()

  // Get efficiency time range (last 10 minutes) - update every 15 minutes
  const [efficiencyTimeRange, setEfficiencyTimeRange] = useState(() => {
    const now = dayjs()
    return {
      start: now.subtract(10, 'minutes').toISOString(),
      end: now.toISOString(),
    }
  })

  useEffect(() => {
    const interval = setInterval(
      () => {
        const now = dayjs()
        setEfficiencyTimeRange({
          start: now.subtract(10, 'minutes').toISOString(),
          end: now.toISOString(),
        })
      },
      15 * 60 * 1000,
    ) // Update every 15 minutes

    return () => clearInterval(interval)
  }, [])

  const acPowerTimeSeries = useGetDataTimeSeriesV3({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.PV_INVERTER_AC_POWER],
      start: efficiencyTimeRange.start,
      end: efficiencyTimeRange.end,
      interval: '1min',
      cutoff_now: true,
    },
    queryOptions: {
      enabled: !!projectId && devices.data && devices.data.length > 0,
      refetchInterval: QUERY_TIME.FIFTEEN_MINUTES, // Refetch every 15 minutes
      staleTime: QUERY_TIME.FOURTEEN_MINUTES, // Consider data stale after 14 minutes
    },
  })

  const dcPowerTimeSeries = useGetDataTimeSeriesV3({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.PV_INVERTER_DC_POWER],
      start: efficiencyTimeRange.start,
      end: efficiencyTimeRange.end,
      interval: '1min',
      cutoff_now: true,
    },
    queryOptions: {
      enabled: !!projectId && devices.data && devices.data.length > 0,
      refetchInterval: QUERY_TIME.FIFTEEN_MINUTES, // Refetch every 15 minutes
      staleTime: QUERY_TIME.FOURTEEN_MINUTES, // Consider data stale after 14 minutes
    },
  })

  // Fetch PCS Module devices to use as fallback
  const pcsModuleDevices = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: [DeviceTypeEnum.PV_INVERTER_MODULE],
    },
    queryOptions: {
      enabled: !!projectId,
      staleTime: QUERY_TIME.NEVER,
    },
  })

  // Fetch module-level sensor data as fallback
  const moduleAcPowerTimeSeries = useGetDataTimeSeriesV3({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.PV_INVERTER_MODULE_AC_POWER],
      start: efficiencyTimeRange.start,
      end: efficiencyTimeRange.end,
      interval: '1min',
      cutoff_now: true,
    },
    queryOptions: {
      enabled:
        !!projectId &&
        devices.data &&
        devices.data.length > 0 &&
        pcsModuleDevices.data &&
        pcsModuleDevices.data.length > 0,
      refetchInterval: QUERY_TIME.FIFTEEN_MINUTES,
      staleTime: QUERY_TIME.FOURTEEN_MINUTES,
    },
  })

  const moduleDcPowerTimeSeries = useGetDataTimeSeriesV3({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.PV_INVERTER_MODULE_DC_POWER],
      start: efficiencyTimeRange.start,
      end: efficiencyTimeRange.end,
      interval: '1min',
      cutoff_now: true,
    },
    queryOptions: {
      enabled:
        !!projectId &&
        devices.data &&
        devices.data.length > 0 &&
        pcsModuleDevices.data &&
        pcsModuleDevices.data.length > 0,
      refetchInterval: QUERY_TIME.FIFTEEN_MINUTES,
      staleTime: QUERY_TIME.FOURTEEN_MINUTES,
    },
  })

  const [userZoomed, setUserZoomed] = useState(false)
  const [yAxisRange, setYAxisRange] = useState<[number, number] | null>(null)
  const [xAxisRange, setXAxisRange] = useState<[number, number] | null>(null)

  const efficiencyChartData = useMemo(() => {
    if (!devices.data) {
      return []
    }

    const pcsDeviceIds = new Set(devices.data.map((d) => d.device_id))

    // Build map of PCS device ID to its child module device IDs
    const pcsToModulesMap = new Map<number, number[]>()
    if (pcsModuleDevices.data) {
      pcsModuleDevices.data.forEach((module) => {
        if (
          module.parent_device_id &&
          pcsDeviceIds.has(module.parent_device_id)
        ) {
          const pcsId = module.parent_device_id
          if (!pcsToModulesMap.has(pcsId)) {
            pcsToModulesMap.set(pcsId, [])
          }
          pcsToModulesMap.get(pcsId)!.push(module.device_id)
        }
      })
    }

    const acPowerByDevice = new Map<number, Map<string, number>>()
    if (acPowerTimeSeries.data) {
      acPowerTimeSeries.data.forEach((trace) => {
        const deviceId = trace.device_id
        if (!deviceId || !pcsDeviceIds.has(deviceId)) {
          return
        }

        if (!acPowerByDevice.has(deviceId)) {
          acPowerByDevice.set(deviceId, new Map())
        }
        const timeMap = acPowerByDevice.get(deviceId)!

        if (trace.x && trace.y) {
          trace.x.forEach((time, idx) => {
            const value = trace.y?.[idx]
            if (value !== null && value !== undefined && time) {
              timeMap.set(time, value)
            }
          })
        }
      })
    }

    const dcPowerByDevice = new Map<number, Map<string, number>>()
    if (dcPowerTimeSeries.data) {
      dcPowerTimeSeries.data.forEach((trace) => {
        const deviceId = trace.device_id
        if (!deviceId || !pcsDeviceIds.has(deviceId)) {
          return
        }

        if (!dcPowerByDevice.has(deviceId)) {
          dcPowerByDevice.set(deviceId, new Map())
        }
        const timeMap = dcPowerByDevice.get(deviceId)!

        if (trace.x && trace.y) {
          trace.x.forEach((time, idx) => {
            const value = trace.y?.[idx]
            if (value !== null && value !== undefined && time) {
              timeMap.set(time, value)
            }
          })
        }
      })
    }

    // Build module-level data maps (by module device ID)
    const moduleAcPowerByModule = new Map<number, Map<string, number>>()
    if (moduleAcPowerTimeSeries.data) {
      moduleAcPowerTimeSeries.data.forEach((trace) => {
        const deviceId = trace.device_id
        if (!deviceId) {
          return
        }

        if (!moduleAcPowerByModule.has(deviceId)) {
          moduleAcPowerByModule.set(deviceId, new Map())
        }
        const timeMap = moduleAcPowerByModule.get(deviceId)!

        if (trace.x && trace.y) {
          trace.x.forEach((time, idx) => {
            const value = trace.y?.[idx]
            if (value !== null && value !== undefined && time) {
              timeMap.set(time, value)
            }
          })
        }
      })
    }

    const moduleDcPowerByModule = new Map<number, Map<string, number>>()
    if (moduleDcPowerTimeSeries.data) {
      moduleDcPowerTimeSeries.data.forEach((trace) => {
        const deviceId = trace.device_id
        if (!deviceId) {
          return
        }

        if (!moduleDcPowerByModule.has(deviceId)) {
          moduleDcPowerByModule.set(deviceId, new Map())
        }
        const timeMap = moduleDcPowerByModule.get(deviceId)!

        if (trace.x && trace.y) {
          trace.x.forEach((time, idx) => {
            const value = trace.y?.[idx]
            if (value !== null && value !== undefined && time) {
              timeMap.set(time, value)
            }
          })
        }
      })
    }

    // For PCS devices without direct sensor data, sum module-level data
    pcsDeviceIds.forEach((pcsId) => {
      if (!acPowerByDevice.has(pcsId) || !dcPowerByDevice.has(pcsId)) {
        const moduleIds = pcsToModulesMap.get(pcsId) || []
        if (moduleIds.length > 0) {
          // Get all time points from all modules
          const allTimePoints = new Set<string>()
          moduleIds.forEach((moduleId) => {
            const acMap = moduleAcPowerByModule.get(moduleId)
            const dcMap = moduleDcPowerByModule.get(moduleId)
            if (acMap) acMap.forEach((_, time) => allTimePoints.add(time))
            if (dcMap) dcMap.forEach((_, time) => allTimePoints.add(time))
          })

          // Sum module values per time point
          const summedAcMap = new Map<string, number>()
          const summedDcMap = new Map<string, number>()

          allTimePoints.forEach((time) => {
            let acSum = 0
            let dcSum = 0
            let hasAcData = false
            let hasDcData = false

            moduleIds.forEach((moduleId) => {
              const acValue = moduleAcPowerByModule.get(moduleId)?.get(time)
              const dcValue = moduleDcPowerByModule.get(moduleId)?.get(time)

              if (acValue !== null && acValue !== undefined) {
                acSum += acValue
                hasAcData = true
              }
              if (dcValue !== null && dcValue !== undefined) {
                dcSum += dcValue
                hasDcData = true
              }
            })

            if (hasAcData) {
              summedAcMap.set(time, acSum)
            }
            if (hasDcData) {
              summedDcMap.set(time, dcSum)
            }
          })

          // Use summed module data if we have it and don't have direct PCS data
          if (!acPowerByDevice.has(pcsId) && summedAcMap.size > 0) {
            acPowerByDevice.set(pcsId, summedAcMap)
          }
          if (!dcPowerByDevice.has(pcsId) && summedDcMap.size > 0) {
            dcPowerByDevice.set(pcsId, summedDcMap)
          }
        }
      }
    })

    const deviceNames: string[] = []
    const efficiencyAverages: (number | null)[] = []

    // Show all PCS devices, even if they don't have data
    devices.data.forEach((device) => {
      const deviceId = device.device_id
      const deviceName =
        device.name_long || device.name_short || `PCS ${device.device_id}`

      const acPowerMap = acPowerByDevice.get(deviceId)
      const dcPowerMap = dcPowerByDevice.get(deviceId)

      // If no data maps exist, show device with null efficiency
      if (!acPowerMap || !dcPowerMap) {
        deviceNames.push(deviceName)
        efficiencyAverages.push(null)
        return
      }

      const allTimePoints = new Set<string>()
      acPowerMap.forEach((_, time) => allTimePoints.add(time))
      dcPowerMap.forEach((_, time) => allTimePoints.add(time))
      const sortedTimePoints = Array.from(allTimePoints).sort()

      const efficiencyValues: number[] = []
      sortedTimePoints.forEach((time) => {
        const acPower = acPowerMap.get(time)
        const dcPower = dcPowerMap.get(time)

        if (
          acPower !== undefined &&
          dcPower !== undefined &&
          dcPower !== 0 &&
          acPower !== null &&
          dcPower !== null
        ) {
          const efficiency = (acPower / dcPower) * 100
          efficiencyValues.push(efficiency)
        }
      })

      // Calculate average efficiency, or use null if no valid data
      if (efficiencyValues.length > 0) {
        const averageEfficiency =
          efficiencyValues.reduce((sum, val) => sum + val, 0) /
          efficiencyValues.length
        deviceNames.push(deviceName)
        efficiencyAverages.push(averageEfficiency)
      } else {
        // Device exists but has no valid efficiency data
        deviceNames.push(deviceName)
        efficiencyAverages.push(null)
      }
    })

    const traces: Data[] = []
    if (deviceNames.length > 0) {
      traces.push({
        x: deviceNames,
        y: efficiencyAverages,
        type: 'bar' as const,
        name: '10-Minute Average Efficiency',
        marker: {
          color: efficiencyAverages.map((val) =>
            val === null ? '#95a5a6' : '#2ecc71',
          ),
        },
      })
    }

    return traces
  }, [
    acPowerTimeSeries.data,
    dcPowerTimeSeries.data,
    moduleAcPowerTimeSeries.data,
    moduleDcPowerTimeSeries.data,
    pcsModuleDevices.data,
    devices.data,
  ])

  const yAxisRangeComputed = useMemo(() => {
    // Always use 0-100% range for efficiency
    return [0, 100] as [number, number]
  }, [])

  const handlePvEfficiencyRelayout = (event: Readonly<PlotRelayoutEvent>) => {
    let userZoomedLocal = false

    if (
      event['yaxis.range[0]'] !== undefined &&
      event['yaxis.range[1]'] !== undefined
    ) {
      const newRange: [number, number] = [
        event['yaxis.range[0]'] as number,
        event['yaxis.range[1]'] as number,
      ]
      setYAxisRange(newRange)
      userZoomedLocal = true
    } else if (event['yaxis.autorange'] === true) {
      setYAxisRange(null)
    }

    if (
      event['xaxis.range[0]'] !== undefined &&
      event['xaxis.range[1]'] !== undefined
    ) {
      const newRange: [number, number] = [
        event['xaxis.range[0]'] as number,
        event['xaxis.range[1]'] as number,
      ]
      setXAxisRange(newRange)
      userZoomedLocal = true
    } else if (event['xaxis.autorange'] === true) {
      setXAxisRange(null)
    }

    if (
      event['yaxis.autorange'] === true &&
      event['xaxis.autorange'] === true
    ) {
      setUserZoomed(false)
    } else if (userZoomedLocal) {
      setUserZoomed(true)
    }
  }

  if (!devices.data || devices.data.length === 0) {
    return null
  }

  return (
    <CustomCard
      title="Efficiency (10-Minute Average: AC Power / DC Power)"
      style={{ height: '400px' }}
      allowMinimize={true}
      storageKey={`pv-pcs-realtime-efficiency-${projectId}`}
    >
      <PlotlyPlot
        data={efficiencyChartData}
        layout={{
          uirevision: `efficiency-${projectId}`,
          yaxis: {
            title: { text: 'Efficiency (%)' },
            range: userZoomed && yAxisRange ? yAxisRange : yAxisRangeComputed,
          },
          xaxis: {
            title: { text: 'PCS Device' },
            range:
              userZoomed && xAxisRange
                ? xAxisRange
                : efficiencyChartData.length > 0 &&
                    efficiencyChartData[0] &&
                    'x' in efficiencyChartData[0] &&
                    Array.isArray(efficiencyChartData[0].x)
                  ? [-0.5, (efficiencyChartData[0].x as string[]).length - 0.5]
                  : undefined,
          },
        }}
        onRelayout={handlePvEfficiencyRelayout}
        isLoading={
          acPowerTimeSeries.isLoading ||
          dcPowerTimeSeries.isLoading ||
          moduleAcPowerTimeSeries.isLoading ||
          moduleDcPowerTimeSeries.isLoading ||
          pcsModuleDevices.isLoading
        }
        error={
          acPowerTimeSeries.error ||
          dcPowerTimeSeries.error ||
          moduleAcPowerTimeSeries.error ||
          moduleDcPowerTimeSeries.error ||
          pcsModuleDevices.error
        }
        noDataMessage="No data available. Required sensor types: PV Inverter AC Power, PV Inverter DC Power (or PV Inverter Module AC Power, PV Inverter Module DC Power as fallback)"
      />
    </CustomCard>
  )
}
