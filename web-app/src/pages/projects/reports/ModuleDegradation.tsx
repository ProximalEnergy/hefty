import { useGetOperationalKPIData } from '@/api/v1/operational/kpi_data'
import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useGetProject } from '@/api/v1/operational/projects'
import CustomCard from '@/components/CustomCard'
import DocsButton from '@/components/DocsButton'
import { ColorBar, MapSettings } from '@/components/GIS'
import { PageLoader } from '@/components/Loading'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import Attribution from '@/components/gis/Attribution'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { GISContext } from '@/contexts/GISContext'
import {
  useGetDegradationPOA,
  useGetDevicesV2,
  useGetPvModules,
} from '@/hooks/api'
import { useProjectFilter } from '@/hooks/custom'
import { DegradationPOA, Device, PvModule } from '@/hooks/types'
import * as gisUtils from '@/utils/GIS'
import { findBoundingBox } from '@/utils/GIS'
import {
  ActionIcon,
  Box,
  Button,
  Group,
  HoverCard,
  Paper,
  ScrollArea,
  SegmentedControl,
  Select,
  Stack,
  Tabs,
  Text,
  Title,
  useComputedColorScheme,
} from '@mantine/core'
import { shallowEqual } from '@mantine/hooks'
import {
  IconDatabasePlus,
  IconFileTypeCsv,
  IconInfoCircle,
} from '@tabler/icons-react'
import dayjs from 'dayjs'
import { FeatureCollection } from 'geojson'
import { groupBy } from 'lodash'
import { Data, Layout, PlotData, Shape } from 'plotly.js'
import React, { memo, useCallback, useContext, useMemo, useState } from 'react'
import {
  Layer,
  MapMouseEvent,
  Map as ReactMap,
  Source,
} from 'react-map-gl/mapbox'
import { useParams } from 'react-router-dom'

import { HoverInfo } from '../gis/utils'

interface filteredData {
  x: string[]
  y: { [deviceId: string]: (number | null)[] }
  project_data: number[]
}
type FamilyAverage = { x: string[]; y: (number | null)[] } | null

function getFamilyAverageTimeseries(
  input: filteredData,
  ids: string[],
): { x: string[]; y: (number | null)[] } {
  // Build the new `y` array by iterating over each index of x
  const averagedY = input.x.map((_, i) => {
    let sum = 0
    let count = 0

    // Sum up the device values (ignoring null)
    for (const deviceId of ids) {
      const value = input.y[deviceId][i]
      if (value !== null) {
        sum += value
        count++
      }
    }

    // Return null if there were no valid (non-null) values
    return count === 0 ? null : sum / count
  })

  return { x: input.x, y: averagedY }
}

function exportToCsv(
  filteredData: filteredData,
  devices: Device[],
  pvModules: PvModule[],
): void {
  if (!filteredData || !filteredData.x?.length) return

  // 1) Get all device IDs from the y object
  const deviceIds = Object.keys(filteredData?.y || {}) // e.g., ["782", "783", ...]

  // 2) Build primary header row
  const headers = [
    'Module BIN',
    ...deviceIds.map((deviceId) => {
      const matchingDevice = devices.find(
        (device) => device.device_id === Number(deviceId),
      )
      const matchingModule = pvModules.find(
        (module) => module.pv_module_id === matchingDevice?.pv_module_id,
      )
      return matchingModule ? matchingModule.model : 'Unknown'
    }),
  ]

  // 3) Build second header row
  const secondHeader = [
    'Date',
    ...deviceIds.map((deviceId) => {
      const matchingDevice = devices.find(
        (device) => device.device_id === Number(deviceId),
      )
      return matchingDevice ? matchingDevice.name_long : `Device ${deviceId}`
    }),
  ]

  // 4) Build data rows: one row per date in filteredData.x
  const rows = filteredData.x.map((dateStr, i) => {
    const rowValues = deviceIds.map((deviceId) => {
      const val = filteredData?.y?.[Number(deviceId)]?.[i] ?? null
      return val != null ? val.toFixed(4) : ''
    })

    return [dateStr, ...rowValues]
  })

  // 5) Combine all into CSV array
  const csvArray = [headers, secondHeader, ...rows]
  const csvContent = csvArray.map((row) => row.join(',')).join('\n')

  // 6) Download as CSV
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'module_degradation.csv'
  link.click()
}

const GisTab: React.FC<{
  averagePerCombiner: { [deviceId: string]: number | null }
  devices?: Device[]
}> = ({ averagePerCombiner, devices }) => {
  const blankMapStyle = gisUtils.useBlankMapStyle()
  const context = useContext(GISContext)
  const { showLabels, showSatellite, colorsGoodBad } = context || {}
  const [hoverInfo, setHoverInfo] = useState<HoverInfo>({
    feature: null,
    x: 0,
    y: 0,
  })
  const computedColorScheme = useComputedColorScheme('dark')

  function CustomHoverCard({ hoverInfo }: { hoverInfo: HoverInfo }) {
    if (hoverInfo.feature === null) {
      return null
    }

    return (
      <Paper
        p="xs"
        withBorder
        style={{
          left: hoverInfo.x,
          top: hoverInfo.y,
          position: 'absolute',
          zIndex: 9,
          pointerEvents: 'none',
        }}
        radius="xs"
      >
        <Text fw={700}>Combiner {hoverInfo.feature.properties?.name}</Text>
        {hoverInfo.feature.properties?.performance && (
          <Text>
            Performance:{' '}
            {(hoverInfo.feature.properties?.performance * 100).toFixed(1) + '%'}
          </Text>
        )}
      </Paper>
    )
  }

  const features = {
    type: 'FeatureCollection',
    features: devices
      ?.filter((device) => device.device_type_id === 9)
      .map((device) => {
        return {
          type: 'Feature',
          geometry: device.polygon,
          properties: {
            name: device.name_long,
            performance: averagePerCombiner[device.device_id] || null,
          },
        }
      }),
  } as FeatureCollection

  const onHover = useCallback((event: MapMouseEvent) => {
    const {
      features,
      point: { x, y },
    } = event

    const hoveredFeature = features && features[0]

    if (hoveredFeature) {
      setHoverInfo({
        feature: hoveredFeature,
        x,
        y,
      })
    } else {
      setHoverInfo({
        feature: null,
        x: 0,
        y: 0,
      })
    }
  }, [])
  const lowValue = 0.8
  return (
    <Paper h="100%" w="100%" radius="md" pos="relative">
      <ReactMap
        initialViewState={{
          bounds: findBoundingBox(features),
          fitBoundsOptions: {
            padding: 35,
          },
        }}
        style={{
          borderRadius: 'inherit',
          height: '100%',
          width: '100%',
        }}
        mapStyle={
          gisUtils.mapStyle({
            satellite: showSatellite,
            theme: computedColorScheme,
          }) ?? blankMapStyle
        }
        interactiveLayerIds={['data']}
        onMouseMove={onHover}
        mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
      >
        <Source id="data" type="geojson" data={features}>
          <Layer
            {...gisUtils.layerData({
              featureKey: 'performance',
              colors: colorsGoodBad || [],
              lowValue: lowValue || 0,
              highValue: 1,
            })}
          />
          {showLabels && (
            <Layer {...gisUtils.layerLabel({ textField: 'name' })} />
          )}
        </Source>
        {hoverInfo.feature && <CustomHoverCard hoverInfo={hoverInfo} />}
      </ReactMap>
      <Box
        style={{
          position: 'absolute',
          bottom: 0,
          right: 0,
          zIndex: 1,
          height: '100%',
        }}
        px="md"
        py={75}
      >
        <ColorBar
          gradient={gisUtils.colorBar({
            colors: colorsGoodBad || [],
          })}
          lowLabel={'80% -'}
          highLabel={' + 100%'}
        />
      </Box>
      <Box
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          zIndex: 1,
        }}
        p="md"
      >
        <MapSettings />
      </Box>
      <Attribution />
    </Paper>
  )
}

const GraphsTab: React.FC<{
  filteredData: filteredData
  devices?: Device[]
  averagePerCombiner: { [deviceId: string]: number | null }
  pvModules: PvModule[]
}> = ({ filteredData, devices, averagePerCombiner, pvModules }) => {
  const deviceTypes = [
    { value: '9', label: 'Combiner' },
    { value: '2', label: 'Inverter' },
    { value: '14', label: 'Circuit' },
  ]
  const familyAverages: Record<string, FamilyAverage> = {}
  const [selectedDeviceType, setSelectedDeviceType] = useState<string | null>(
    '9',
  )
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [selectedSort, setSelectedSort] = useState<string | undefined>('family')

  // Calculated arrays
  const averagePerDay = filteredData.project_data

  // Compute maxPerCombiner from filtered data
  const maxPerCombiner = useMemo(() => {
    const result: { [deviceId: number]: number } = {}

    // Iterate through each key in `y`
    for (const deviceIdStr in filteredData.y) {
      const deviceId = Number(deviceIdStr)
      // Grab the array for this device ID
      const values = filteredData.y[deviceId]

      // Filter out any null values
      const validValues = values.filter((v) => v !== null) as number[]

      if (validValues.length === 0) {
        // Decide how to handle a situation with no valid numbers
        continue
      } else {
        result[deviceId] = Math.max(...validValues)
      }
    }

    return result
  }, [filteredData])

  const deviceMap = useMemo(() => {
    const map = new Map<number, Device>()
    devices?.forEach((device) => {
      map.set(device.device_id, device)
    })
    return map
  }, [devices])

  const findParentByType = (
    currentDevice: Device | undefined,
    targetTypeId: number,
  ): number | null => {
    let parentId =
      currentDevice?.parent_device_id || currentDevice?.parent_device_id || null
    let parentDevice = parentId ? deviceMap.get(parentId) : null

    while (parentDevice) {
      if (parentDevice.device_type_id === targetTypeId) {
        return parentDevice.device_id
      }
      parentId =
        parentDevice.parent_device_id || parentDevice.parent_device_id || null
      parentDevice = parentId ? deviceMap.get(parentId) : null
    }

    return null
  }

  // Build lists for parent relationships
  const combinerKeys = Object.keys(averagePerCombiner).filter((key) =>
    devices?.some((device) => device.device_id === Number(key)),
  )

  const combinerParents = combinerKeys.map((key) => {
    const device = deviceMap.get(Number(key))

    return {
      combinerId: device?.device_id,
      inverterId: findParentByType(device, 2),
      circuitId: findParentByType(device, 14),
    }
  })

  const inverterIds = Array.from(
    new Set(
      combinerParents
        .map((parent) => parent.inverterId)
        .filter((id): id is number => id !== null && id !== undefined),
    ),
  )
  const circuitIds = Array.from(
    new Set(
      combinerParents
        .map((parent) => parent.circuitId)
        .filter((id): id is number => id !== null && id !== undefined),
    ),
  )

  // Create uniqueModuleFamilies by iterating over combinerKeys and getting the pvModule.family from deviceMap
  const uniqueModuleFamilies = Array.from(
    new Set(
      combinerKeys.map((key) =>
        deviceMap.get(Number(key))?.pv_module_id
          ? pvModules.find(
              (pv) =>
                pv.pv_module_id === deviceMap.get(Number(key))?.pv_module_id,
            )?.family
          : null,
      ),
    ),
  )
  uniqueModuleFamilies.forEach((family: string | null | undefined) => {
    // Collect all pv_module_ids that match this family.
    // Adapt this filter to match how you're identifying families in pvModules.
    // e.g. if your "family" is stored in pvModule.family or something similar:
    const familyIds = pvModules
      .filter((pvModule) => pvModule.family === family)
      .map((pvModule) => pvModule.pv_module_id)

    // Extract device keys from deviceMap that match these ids.
    const deviceKeys = [...deviceMap.entries()]
      .filter(([, device]) => familyIds.includes(device.pv_module_id ?? 0))
      .map(([key]) => key.toString())

    // Get the average timeseries for these device keys
    const average = getFamilyAverageTimeseries(filteredData, deviceKeys)

    // Store the result in our record, keyed by the family name
    familyAverages[family || ''] = average
  })

  // -------------------------------------------
  // 2) Average per inverter
  // -------------------------------------------
  const averagePerInverter: { [inverterId: string]: number | null } =
    useMemo(() => {
      const output: { [inverterId: string]: number | null } = {}

      inverterIds.forEach((inverterId) => {
        // Find all combiners that map to this inverter
        const relevantCombiners = combinerParents
          .filter((cp) => cp.inverterId === inverterId)
          .map((cp) => String(cp.combinerId))

        let sumVal = 0
        let countVal = 0

        // Average these combiners' already-computed averages
        relevantCombiners.forEach((combinerId) => {
          const combinerAvg = averagePerCombiner[combinerId]
          if (combinerAvg != null) {
            sumVal += combinerAvg
            countVal++
          }
        })

        output[inverterId] = countVal > 0 ? sumVal / countVal : null
      })

      return output
    }, [combinerParents, averagePerCombiner, inverterIds])

  // -------------------------------------------
  // 3) Max per inverter (based on daily means)
  // -------------------------------------------
  // We compute, for each day, the average across that inverter's combiners,
  // then track the maximum of those daily means.
  const maxPerInverter: { [inverterId: string]: number | null } =
    useMemo(() => {
      // Initialize all to null
      const output: { [inverterId: string]: number | null } = {}
      inverterIds.forEach((id) => {
        output[id] = null
      })

      // If we have days (filteredData.x), iterate over each day index i
      const numDays = filteredData.x?.length || 0
      for (let i = 0; i < numDays; i++) {
        inverterIds.forEach((inverterId) => {
          // Find combiners for this inverter
          const relevantCombiners = combinerParents
            .filter((cp) => cp.inverterId === inverterId)
            .map((cp) => String(cp.combinerId))

          // Collect the day‐i value from each combiner
          const dailyValues = relevantCombiners
            .map(
              (combinerIdStr) =>
                filteredData?.y?.[Number(combinerIdStr)]?.[i] ?? null,
            )
            .filter((val): val is number => val != null)

          if (dailyValues.length > 0) {
            const sumVal = dailyValues.reduce((acc, val) => acc + val, 0)
            const mean = sumVal / dailyValues.length

            // Compare to the current max
            if (output[inverterId] == null || mean > output[inverterId]) {
              output[inverterId] = mean
            }
          }
        })
      }

      return output
    }, [filteredData, inverterIds, combinerParents])

  // -------------------------------------------
  // 4) Average per circuit
  // -------------------------------------------
  const averagePerCircuit: { [circuitId: string]: number | null } =
    useMemo(() => {
      const output: { [circuitId: string]: number | null } = {}

      circuitIds.forEach((circuitId) => {
        // Find combiners for this circuit
        const relevantCombiners = combinerParents
          .filter((cp) => cp.circuitId === circuitId)
          .map((cp) => String(cp.combinerId))

        let sumVal = 0
        let countVal = 0

        // Add up each combiner's average
        relevantCombiners.forEach((combinerIdStr) => {
          const combinerAvg = averagePerCombiner[combinerIdStr]
          if (combinerAvg != null) {
            sumVal += combinerAvg
            countVal++
          }
        })

        output[circuitId] = countVal > 0 ? sumVal / countVal : null
      })

      return output
    }, [combinerParents, averagePerCombiner, circuitIds])

  // -------------------------------------------
  // 5) Max per circuit (based on daily means)
  // -------------------------------------------
  const maxPerCircuit: { [circuitId: string]: number | null } = useMemo(() => {
    // Initialize all to null
    const output: { [circuitId: string]: number | null } = {}
    circuitIds.forEach((id) => {
      output[id] = null
    })

    // For each day i, compute the mean across that circuit's combiners,
    // then track if it's larger than the current max for that circuit.
    const numDays = filteredData.x?.length || 0
    for (let i = 0; i < numDays; i++) {
      circuitIds.forEach((circuitId) => {
        const relevantCombiners = combinerParents
          .filter((cp) => cp.circuitId === circuitId)
          .map((cp) => String(cp.combinerId))

        const dailyValues = relevantCombiners
          .map(
            (combinerIdStr) =>
              filteredData?.y?.[Number(combinerIdStr)]?.[i] ?? null,
          )
          .filter((val): val is number => val != null)

        if (dailyValues.length > 0) {
          const sumVal = dailyValues.reduce((acc, val) => acc + val, 0)
          const mean = sumVal / dailyValues.length

          if (output[circuitId] == null || mean > output[circuitId]) {
            output[circuitId] = mean
          }
        }
      })
    }

    return output
  }, [filteredData, circuitIds, combinerParents])

  // For device selection in "Device Performance"
  const selectData = useMemo(() => {
    return Object.keys(averagePerCombiner)
      .concat(Object.keys(averagePerInverter))
      .concat(Object.keys(averagePerCircuit))
      .filter((key) =>
        devices?.some((device) => device.device_id === Number(key)),
      )
      .map((key) => {
        const device = devices?.find(
          (device) => device.device_id === Number(key),
        )
        return {
          value: key,
          label: device?.name_full || `Device ${key}`,
        }
      })
  }, [averagePerCombiner, averagePerInverter, averagePerCircuit, devices])

  // For "Avg. DC Performance by combiner" hovers
  const countsPerKey = useMemo(() => {
    const counts: { [key: string]: number } = {}

    Object.entries(filteredData?.y || {}).forEach(([key, values]) => {
      // `values` is an array of (number | null)
      // Filter out null entries
      const nonNullCount = values.filter((v) => v !== null).length
      counts[key] = nonNullCount
    })

    return counts
  }, [filteredData.y])

  // For "Max DC Performance by combiner" hovers
  const maxDatePerKey = useMemo(() => {
    const maxDates: { [deviceId: string]: string } = {}
    const maxValues: { [deviceId: string]: number } = {}

    if (!filteredData.x || !filteredData.y) return maxDates

    Object.entries(filteredData?.y || {}).forEach(([deviceId, values]) => {
      // Iterate over each value, and see if it's the largest so far for this device
      values.forEach((value, i) => {
        if (value != null) {
          if (
            maxValues[deviceId] === undefined ||
            value > maxValues[deviceId]
          ) {
            maxValues[deviceId] = value
            // Use the corresponding date from x
            const currentDate = filteredData.x[i]
            maxDates[deviceId] = dayjs(currentDate).format('MM/DD/YYYY')
          }
        }
      })
    })

    return maxDates
  }, [filteredData.x, filteredData.y])

  // Build histogram
  const allValues: number[] = useMemo(() => {
    return Object.values(filteredData?.y || {}).flatMap((item) =>
      Object.values(item).filter(
        (value): value is number => typeof value === 'number',
      ),
    )
  }, [filteredData?.y])

  // Use .reduce for min/max to avoid stack overflow for large arrays
  const minValue: number =
    allValues.length > 0
      ? Math.round(allValues.reduce((a, b) => Math.min(a, b)) * 100) / 100
      : 0
  const maxValue: number =
    allValues.length > 0
      ? Math.round(allValues.reduce((a, b) => Math.max(a, b)) * 100) / 100
      : 0
  const binSize: number = 0.01
  const binNum: number = Math.round((maxValue - minValue) / binSize)

  const binValues: { [key: number]: number } = {}
  for (let i = 0; i < binNum; i++) {
    const binStart = minValue + binSize * i
    binValues[binStart] = 0
  }
  allValues.forEach((value) => {
    let binIndex = Math.floor((value - minValue) / binSize)
    if (binIndex === binNum) {
      binIndex = binNum - 1
    }
    const binStart = minValue + binSize * binIndex
    binValues[binStart] += 1
  })

  // Map module_id -> color
  const uniqueModuleIds = useMemo(() => {
    const moduleIds = devices?.map((d) => d.pv_module_id) || []
    return Array.from(new Set(moduleIds)).sort((a, b) => (a ?? 0) - (b ?? 0))
  }, [devices])

  const moduleIdToColorMap = useMemo(() => {
    // Plotly color set
    const plotlyColors = [
      '#1f77b4',
      '#ff7f0e',
      '#2ca02c',
      '#d62728',
      '#9467bd',
      '#8c564b',
      '#e377c2',
      '#7f7f7f',
      '#bcbd22',
      '#17becf',
    ]
    const map: { [moduleId: number]: string } = {}
    uniqueModuleIds.forEach((mId, index) => {
      map[mId ?? 0] = plotlyColors[index % plotlyColors.length]
    })
    return map
  }, [uniqueModuleIds])

  // --- BUILD PLOT DATA FOR COMBINER (AVERAGE) ---
  // We now split into multiple traces, one per module, removing "Module" from hover:
  const combinerDataForAvg = useMemo(() => {
    // Gather all combiner devices
    const combinerData = Object.keys(averagePerCombiner).map((key) => {
      const label =
        selectData.find((sd) => sd.value === key)?.label || `Device ${key}`
      const count = countsPerKey[key] || 0
      const device = deviceMap.get(Number(key))
      const moduleId = device?.pv_module_id
      const moduleName =
        pvModules.find((pv) => pv.pv_module_id === moduleId)?.model ||
        'Unknown Module'
      const performance = averagePerCombiner[key] ?? null

      return {
        deviceId: key,
        performance,
        count,
        label,
        moduleName,
        moduleId: moduleId ?? 0,
      }
    })

    // Group by module name
    const groupedByModule = groupBy(combinerData, (item) => item.moduleName)

    // Build traces: each module is a separate trace (legend entry)
    return Object.entries(groupedByModule).map(([moduleName, items]) => ({
      x: items.map((i) => i.deviceId), // device keys
      y: items.map((i) => i.performance),
      type: 'scatter' as const,
      mode: 'markers' as const,
      name: moduleName, // legend entry
      marker: {
        color: items.map((i) => moduleIdToColorMap[i.moduleId]),
      },
      hovertemplate:
        '%{customdata[1]}<br>' +
        'Average Value: %{y:,.1%}<br>' +
        'Count: %{customdata[0]}<extra></extra>',
      customdata: items.map((i) => [i.count, i.label]),
    }))
  }, [
    averagePerCombiner,
    selectData,
    countsPerKey,
    deviceMap,
    pvModules,
    moduleIdToColorMap,
  ])

  // --- BUILD PLOT DATA FOR COMBINER (MAX) ---
  const combinerDataForMax = useMemo(() => {
    // Gather all combiner devices
    const maxCombinerData = Object.keys(maxPerCombiner).map((key) => {
      const label =
        selectData.find((sd) => sd.value === key)?.label || `Device ${key}`
      const device = deviceMap.get(Number(key))
      const moduleId = device?.pv_module_id
      const moduleName =
        pvModules.find((pv) => pv.pv_module_id === moduleId)?.model ||
        'Unknown Module'
      const performance = maxPerCombiner[Number(key)] ?? null
      const maxDate = maxDatePerKey[Number(key)] || ''

      return {
        deviceId: key,
        performance,
        maxDate,
        label,
        moduleName,
        moduleId: moduleId ?? 0,
      }
    })

    // Group by module name
    const groupedByModule = groupBy(maxCombinerData, (item) => item.moduleName)

    // Build traces: each module is a separate trace (legend entry)
    return Object.entries(groupedByModule).map(([moduleName, items]) => ({
      x: items.map((i) => i.deviceId),
      y: items.map((i) => i.performance),
      type: 'scatter' as const,
      mode: 'markers' as const,
      name: moduleName, // legend entry
      marker: {
        color: items.map((i) => moduleIdToColorMap[i.moduleId]),
      },
      hovertemplate:
        '%{customdata[1]}<br>' +
        'Max Value: %{y:,.1%}<br>' +
        'Max Date: %{customdata[0]}<extra></extra>',
      customdata: items.map((i) => [i.maxDate, i.label]),
    }))
  }, [
    maxPerCombiner,
    selectData,
    deviceMap,
    maxDatePerKey,
    pvModules,
    moduleIdToColorMap,
  ])

  return (
    <Stack>
      <CustomCard
        title="Project Mean per Day"
        style={{ height: '35vh' }}
        info={
          'This plot shows the average DC performance across all combiners per day. '
        }
        headerChildren={
          uniqueModuleFamilies.length > 1 && (
            <Group>
              <SegmentedControl
                data={[
                  { value: 'all', label: 'All' },
                  { value: 'family', label: 'Family' },
                ]}
                onChange={(item) => setSelectedSort(item)}
                value={selectedSort}
                size="xs"
              />
            </Group>
          )
        }
      >
        <Stack h="100%">
          <PlotlyPlot
            data={[
              // Show this only if selectedSort is "all"
              ...(selectedSort === 'all'
                ? [
                    {
                      x: filteredData.x,
                      y: averagePerDay,
                      type: 'scatter' as const,
                      mode: 'lines+markers' as const,
                      name: 'Average DC Performance',
                    },
                  ]
                : ([] as Data[])),
              // Show this only if selectedSort is "family"
              ...(selectedSort === 'family'
                ? Object.entries(familyAverages).map(
                    ([family, familyValue]) => ({
                      x: familyValue?.x || [],
                      y: familyValue?.y || [],
                      type: 'scatter' as const,
                      mode: 'lines+markers' as const,
                      name: family,
                    }),
                  )
                : ([] as Data[])),
            ]}
            layout={{
              xaxis: {
                title: { text: 'Date' },
              },
              yaxis: {
                title: { text: 'DC Performance' },
                tickformat: ',.1%',
              },
              legend: {
                x: 0,
                y: 1,
                bgcolor: 'rgba(255, 255, 255, 0)',
                bordercolor: 'rgba(0,0,0,0)',
              },
            }}
          />
        </Stack>
      </CustomCard>
      <Group h="70vh" grow>
        <Stack h="100%" justify="flex-start">
          <CustomCard
            title={`Avg. DC Performance by ${
              deviceTypes.find(
                (deviceType) => deviceType.value === selectedDeviceType,
              )?.label
            }`}
            style={{ height: '50%' }}
            headerChildren={
              <Select
                data={deviceTypes.map((deviceType) => ({
                  value: deviceType.value,
                  label: deviceType.label,
                }))}
                onChange={(item) => setSelectedDeviceType(item)}
                value={selectedDeviceType}
                size="xs"
              />
            }
            info={`This plot shows the average DC performance across all days by ${
              deviceTypes.find((d) => d.value === selectedDeviceType)?.label
            }. The combiner device type is split by module (each is a separate legend entry).`}
          >
            {selectedDeviceType === '9' && (
              <PlotlyPlot
                data={combinerDataForAvg}
                layout={{
                  hovermode: 'closest',
                  xaxis: {
                    showticklabels: false,
                    showgrid: false,
                    title: { text: 'Combiner' },
                  },
                  yaxis: {
                    title: { text: 'DC Performance' },
                    tickformat: ',.0%',
                  },
                }}
              />
            )}
            {selectedDeviceType === '2' && (
              <PlotlyPlot
                data={[
                  {
                    x: Object.keys(averagePerInverter),
                    y: Object.values(averagePerInverter),
                    type: 'scatter',
                    mode: 'markers',
                    name: '',
                    hovertemplate:
                      '%{customdata}<br>' + 'Average Value: %{y:,.1%}<br>',
                    customdata: Object.keys(averagePerInverter).map((key) => {
                      const label =
                        selectData.find((sd) => sd.value === key)?.label || key
                      return label
                    }),
                  },
                ]}
                layout={{
                  hovermode: 'closest',
                  xaxis: {
                    showticklabels: false,
                    showgrid: false,
                    title: { text: 'Inverter' },
                  },
                  yaxis: {
                    title: { text: 'DC Performance' },
                    tickformat: ',.0%',
                  },
                }}
              />
            )}
            {selectedDeviceType === '14' && (
              <PlotlyPlot
                data={[
                  {
                    x: Object.keys(averagePerCircuit),
                    y: Object.values(averagePerCircuit),
                    type: 'scatter',
                    mode: 'markers',
                    name: '',
                    hovertemplate:
                      '%{customdata}<br>' + 'Average Value: %{y:,.1%}<br>',
                    customdata: Object.keys(averagePerCircuit).map((key) => {
                      const label =
                        selectData.find((sd) => sd.value === key)?.label || key
                      return label
                    }),
                  },
                ]}
                layout={{
                  hovermode: 'closest',
                  xaxis: {
                    showticklabels: false,
                    showgrid: false,
                    title: { text: 'Circuit' },
                  },
                  yaxis: {
                    title: { text: 'DC Performance' },
                    tickformat: ',.0%',
                  },
                }}
              />
            )}
          </CustomCard>

          <CustomCard
            title={`Maximum DC Performance by ${
              deviceTypes.find(
                (deviceType) => deviceType.value === selectedDeviceType,
              )?.label
            }`}
            style={{ height: '50%' }}
            info={`This plot shows the maximum DC performance across all days by ${
              deviceTypes.find((d) => d.value === selectedDeviceType)?.label
            }. For inverters/circuits, we take the daily mean of their combiners, then plot the maximum value of those daily means.`}
          >
            {selectedDeviceType === '9' && (
              <PlotlyPlot
                data={combinerDataForMax}
                layout={{
                  hovermode: 'closest',
                  xaxis: {
                    showticklabels: false,
                    showgrid: false,
                    title: { text: 'Combiner' },
                  },
                  yaxis: {
                    title: { text: 'DC Performance' },
                    tickformat: ',.0%',
                  },
                }}
              />
            )}
            {selectedDeviceType === '2' && (
              <PlotlyPlot
                data={[
                  {
                    x: Object.keys(maxPerInverter),
                    y: Object.values(maxPerInverter),
                    type: 'scatter',
                    mode: 'markers',
                    name: '',
                    hovertemplate:
                      '%{customdata}<br>' + 'Max Value: %{y:,.1%}<br>',
                    customdata: Object.keys(maxPerInverter).map((key) => {
                      const label =
                        selectData.find((sd) => sd.value === key)?.label || key
                      return label
                    }),
                  },
                ]}
                layout={{
                  hovermode: 'closest',
                  xaxis: {
                    showticklabels: false,
                    showgrid: false,
                    title: { text: 'Inverter' },
                  },
                  yaxis: {
                    title: { text: 'DC Performance' },
                    tickformat: ',.0%',
                  },
                }}
              />
            )}
            {selectedDeviceType === '14' && (
              <PlotlyPlot
                data={[
                  {
                    x: Object.keys(maxPerCircuit),
                    y: Object.values(maxPerCircuit),
                    type: 'scatter',
                    mode: 'markers',
                    name: '',
                    hovertemplate:
                      '%{customdata}<br>' + 'Max Value: %{y:,.1%}<br>',
                    customdata: Object.keys(maxPerCircuit).map((key) => {
                      const label =
                        selectData.find((sd) => sd.value === key)?.label || key
                      return label
                    }),
                  },
                ]}
                layout={{
                  hovermode: 'closest',
                  xaxis: {
                    showticklabels: false,
                    showgrid: false,
                    title: { text: 'Circuit' },
                  },
                  yaxis: {
                    title: { text: 'DC Performance' },
                    tickformat: ',.0%',
                  },
                }}
              />
            )}
          </CustomCard>
        </Stack>
        <Stack h="100%" justify="flex-start">
          <CustomCard
            title="Histogram: DC Performance Bins"
            style={{ height: '50%' }}
            info={`This plot shows the distribution of DC performance across all days. The bins are defined by 1% increments
              (e.g. a value of 1,000 for the 98% bin means that 1,000 combiners had a DC performance between 98% and 98.9% when averaged across all days).`}
          >
            <PlotlyPlot
              data={[
                {
                  x: Object.keys(binValues).map(Number),
                  y: Object.values(binValues).map(Number),
                  type: 'bar',
                },
              ]}
              layout={{
                bargap: 0,
                xaxis: {
                  tickformat: ',.0%',
                  tickangle: -45,
                  title: { text: 'DC Performance' },
                  type: 'linear',
                },
                yaxis: {
                  title: { text: 'Combiner Count' },
                },
              }}
            />
          </CustomCard>

          <CustomCard
            title="Device Performance"
            style={{ height: '50%' }}
            headerChildren={
              <Select
                data={selectData}
                onChange={(item) => setSelectedKey(item)}
                searchable
                value={selectedKey}
                placeholder="Select Device"
                size="xs"
                clearable={false}
              />
            }
            info={`This plot shows the DC performance of the selected device over time. Select a device on the right to view its performance.`}
          >
            {selectedKey ? (
              <PlotlyPlot
                data={[
                  {
                    x: filteredData?.x || [],
                    y: filteredData?.y?.[Number(selectedKey)] || [],
                    type: 'scatter',
                    mode: 'markers',
                  },
                ]}
                layout={{
                  xaxis: {
                    title: { text: 'Date' },
                  },
                  yaxis: {
                    title: { text: 'DC Performance' },
                    tickformat: ',.1%',
                  },
                }}
              />
            ) : (
              <Stack justify="center" align="center" h="100%">
                <Text>Select a device to view its performance over time.</Text>
                <IconDatabasePlus size={48} />
              </Stack>
            )}
          </CustomCard>
        </Stack>
      </Group>
    </Stack>
  )
}

const MemoizedGraphsTab = memo(GraphsTab, (prevProps, nextProps) => {
  return (
    shallowEqual(prevProps.filteredData, nextProps.filteredData) &&
    shallowEqual(prevProps.devices, nextProps.devices) &&
    shallowEqual(prevProps.averagePerCombiner, nextProps.averagePerCombiner)
  )
})

const ModuleDegradation: React.FC = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeId.PV, ProjectTypeId.PV_BESS],
  })

  // Variables and states
  const { projectId } = useParams()
  const [viewDate, setViewDate] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<string>('graphs')
  const [excludedDates, setExcludedDates] = useState<string[]>([])
  const { start, end } = useValidateDateRange({})
  const computedColorScheme = useComputedColorScheme('dark')

  // API calls
  const { data: project } = useGetProject({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: {
      enabled: !!projectId,
    },
  })
  const timezone = project?.time_zone || 'America/Chicago'

  let startQuery: string | undefined = undefined
  let endQuery: string | undefined = undefined

  if (project) {
    if (start) {
      // Convert to YYYY-MM-DD format
      startQuery = start.tz(timezone, true).format('YYYY-MM-DD')
    }
    if (end) {
      // Convert to YYYY-MM-DD format
      endQuery = end.tz(timezone, true).format('YYYY-MM-DD')
    }
  }

  const {
    data: moduleDegradationResponse,
    isLoading: isModuleDegradationLoading,
  } = useGetOperationalKPIData({
    queryParams: {
      project_ids: projectId ? [projectId] : undefined,
      kpi_type_ids: [17],
      start: startQuery,
      end: endQuery,
      include_device_data: true,
      include_all_dates: false,
    },
    queryOptions: {
      enabled: !!projectId && !!startQuery && !!endQuery,
    },
  })
  const moduleDegradation = moduleDegradationResponse?.[0]

  const { data: degradationPOA, isLoading: isViewDatePOALoading } =
    useGetDegradationPOA({
      pathParams: { projectId: projectId || '' },
      queryParams: {
        start: viewDate ? dayjs(viewDate).toISOString() : '',
        end: viewDate ? dayjs(viewDate).add(1, 'day').toISOString() : '',
      },
      queryOptions: {
        enabled: !!viewDate,
      },
    })

  const { data: devices, isLoading: isDevicesLoading } = useGetDevicesV2({
    pathParams: { projectId: projectId || '' },
    filters: {
      device_type_ids: [2, 6, 9, 14],
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  const { data: pvModules, isLoading: isPvModulesLoading } = useGetPvModules({
    pathParams: { projectId: projectId || '' },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  const { data: plotData, layout } = useMemo(() => {
    if (!degradationPOA) return { data: [], layout: {} }
    return processPoaData(degradationPOA, timezone, computedColorScheme)
  }, [degradationPOA, timezone, computedColorScheme])

  // Filtered degradation data
  const dates = moduleDegradation?.data?.dates

  const filteredData = useMemo(() => {
    // If chartData doesn't exist, return a default structure
    if (!moduleDegradation) {
      return { x: [], project_data: [], y: {} }
    }

    const excludeSet = new Set(excludedDates)

    // Prepare new arrays for the filtered data
    const filteredX: string[] = []
    const filteredProjectData: number[] = []

    // Update filteredY to accept number | null
    const filteredY: { [deviceId: number]: (number | null)[] } = {}
    for (const deviceId in moduleDegradation?.data?.device_data_obj
      ?.device_values) {
      filteredY[+deviceId] = []
    }

    // Loop through each x value, and if it's not in excludedDates, keep it
    moduleDegradation?.data?.dates.forEach((dateStr, i) => {
      if (!excludeSet.has(dateStr)) {
        filteredX.push(dateStr)
        filteredProjectData.push(moduleDegradation?.data?.project_data[i] || 0)

        // Push number | null without type issues
        for (const deviceId in moduleDegradation?.data?.device_data_obj
          ?.device_values) {
          filteredY[+deviceId].push(
            moduleDegradation?.data?.device_data_obj?.device_values[+deviceId][
              i
            ],
          )
        }
      }
    })

    // Return the newly filtered data
    return {
      x: filteredX,
      project_data: filteredProjectData,
      y: filteredY,
    }
  }, [moduleDegradation, excludedDates])

  const filteredIndex: number =
    moduleDegradation?.data?.dates.indexOf(
      moduleDegradation?.data?.dates.find((date) => date === viewDate) ?? '',
    ) ?? -1

  // Compute averagePerCombiner from filtered data
  const averagePerCombiner = useMemo(() => {
    const result: { [deviceId: number]: number } = {}

    // Iterate through each key in `y`
    for (const deviceIdStr in filteredData.y) {
      const deviceId = Number(deviceIdStr)
      // Grab the array for this device ID
      const values = filteredData.y[deviceId]

      // Filter out any null values
      const validValues = values.filter((v) => v !== null) as number[]

      if (validValues.length === 0) {
        // Decide how to handle a situation with no valid numbers
        continue
      } else {
        // Sum and compute the average
        const sum = validValues.reduce((acc, val) => acc + val, 0)
        result[deviceId] = sum / validValues.length
      }
    }

    return result
  }, [filteredData])

  // For Clearsky "Combiner Performance" chart
  const selectDataClearsky = useMemo(() => {
    const xValues: string[] = []
    const yValues: (number | null)[] = []
    Object.entries(
      moduleDegradation?.data?.device_data_obj?.device_values || {},
    ).forEach(([key, value]) => {
      xValues.push(key)
      yValues.push(value[filteredIndex])
    })
    return { x: xValues, y: yValues }
  }, [moduleDegradation, filteredIndex])

  if (isModuleDegradationLoading || isDevicesLoading || isPvModulesLoading) {
    return <PageLoader />
  }

  return (
    <Stack w="100%" h="100%" p="md" gap="sm">
      <Group justify="space-between" align="flex-start">
        <Group>
          <Title>Module Degradation</Title>
          <DocsButton
            href="https://docs.proximal.energy/reports/module_state_of_health.html"
            dropdownText="Read more about the filters and analysis process in Proximal's documentation."
          />
          <AdvancedDatePicker
            defaultRange={'past-year'}
            includeClearButton={false}
          />
        </Group>
        <ActionIcon size="xl">
          <IconFileTypeCsv
            onClick={() =>
              exportToCsv(filteredData, devices || [], pvModules || [])
            }
          />
        </ActionIcon>
      </Group>
      <Group>
        <Text size="sm" w="75%" style={{ textAlign: 'justify' }}>
          This report is designed to characterize the performance of the modules
          at the most granular level possible. The analysis is generated by
          heavily filtering data for clearsky, high-performance timestamps which
          guarantee that shortfalls can be attributed to module degradation or
          other DC performance issues. Note that this report assumes Proximal
          has the most updated knowledge of SCADA tag association with combiners
          and correct BIN classes. Combiner mismatch or incorrect BIN class
          issues can lead to severe inaccuracies in the DC Performance report.
        </Text>
      </Group>
      <Tabs
        value={activeTab}
        onChange={(value: string | null) => setActiveTab(value ?? 'graphs')}
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <Tabs.List>
          <Tabs.Tab value="graphs">Graphs</Tabs.Tab>
          <Tabs.Tab value="gis">GIS</Tabs.Tab>
          <Tabs.Tab value="clearsky">
            <Group align="center" gap={2}>
              Clearsky
              <HoverCard>
                <HoverCard.Target>
                  <IconInfoCircle size={16} />
                </HoverCard.Target>
                <HoverCard.Dropdown>
                  <Text size="sm">
                    Use this tab to view individual days' clearsky and combiner
                    performance data. Entire days can be excluded from the
                    analysis as applicable.{' '}
                  </Text>
                </HoverCard.Dropdown>
              </HoverCard>
            </Group>
          </Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel
          value="clearsky"
          pt="md"
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <Group h="100%" w="100%" justify="center">
            <Stack h="100%" flex={1}>
              <Paper withBorder h="100%" p="xs">
                <ScrollArea h="100%">
                  <Stack h="100%" align="center">
                    <Text>Included Dates</Text>
                    {dates
                      ?.filter((date) => !excludedDates.includes(date))
                      .map((date) => (
                        <Button
                          key={date}
                          size="xs"
                          onClick={() => {
                            setViewDate(date)
                          }}
                          variant={viewDate === date ? 'filled' : 'outline'}
                          fullWidth
                        >
                          {dayjs(date).format('MM/DD/YYYY')}
                        </Button>
                      ))}
                  </Stack>
                </ScrollArea>
              </Paper>
            </Stack>
            <Stack h="100%" flex={8}>
              <CustomCard
                title={`Combiner Performance${
                  viewDate ? ': ' + dayjs(viewDate).format('MM/DD/YYYY') : ''
                }`}
                style={{ width: '100%', height: '50%' }}
              >
                {selectDataClearsky ? (
                  <PlotlyPlot
                    data={[
                      {
                        x: selectDataClearsky.x,
                        y: selectDataClearsky.y,
                        type: 'scatter',
                        mode: 'markers',
                        hovertemplate:
                          '%{customdata}<br>' + 'DC Performance: %{y:,.1%}<br>',
                        customdata: selectDataClearsky.x.map((x) => {
                          const device = devices?.find(
                            (device) => device.device_id === Number(x),
                          )
                          return device?.name_full || x
                        }),
                        name: '',
                      },
                    ]}
                    layout={{
                      hovermode: 'closest',
                      xaxis: {
                        showticklabels: false,
                        showgrid: false,
                        title: { text: 'Combiner' },
                      },
                      yaxis: {
                        title: { text: 'DC Performance' },
                        tickformat: ',.0%',
                      },
                    }}
                  />
                ) : (
                  <Stack justify="center" align="center" h="100%">
                    <Text>
                      Select a date to view combiner performance & clearsky
                      data.
                    </Text>
                    <IconDatabasePlus size={48} />
                  </Stack>
                )}
              </CustomCard>
              <CustomCard
                style={{ width: '100%', height: '50%' }}
                title="Clearsky POA"
                info={
                  'This chart shows the POA data for the selected date. ' +
                  'A dashed line indicates that a POA trace has been excluded from clearsky analysis, ' +
                  'and the green rectangles highlight valid analysis periods after filtering.'
                }
              >
                {plotData ? (
                  <PlotlyPlot
                    data={plotData}
                    layout={layout}
                    isLoading={isViewDatePOALoading}
                  />
                ) : (
                  <Stack justify="center" align="center" h="100%">
                    <IconDatabasePlus size={48} />
                  </Stack>
                )}
              </CustomCard>

              <Button
                onClick={() =>
                  setExcludedDates([...excludedDates, viewDate || ''])
                }
              >
                Exclude
              </Button>
            </Stack>
            <Paper withBorder h="100%" p="xs" flex={1}>
              <ScrollArea h="100%">
                <Stack h="100%" align="center">
                  <Text>Excluded Dates</Text>
                  {excludedDates.map((date) => (
                    <Button
                      key={date}
                      size="xs"
                      onClick={() =>
                        setExcludedDates(
                          excludedDates.filter((d) => d !== date),
                        )
                      }
                      fullWidth
                    >
                      {dayjs(date).format('MM/DD/YYYY')}
                    </Button>
                  ))}
                </Stack>
              </ScrollArea>
            </Paper>
          </Group>
        </Tabs.Panel>
        <Tabs.Panel
          value="graphs"
          pt="md"
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <ScrollArea>
            {activeTab === 'graphs' && startQuery && (
              <MemoizedGraphsTab
                filteredData={filteredData}
                devices={devices}
                averagePerCombiner={averagePerCombiner}
                pvModules={pvModules || []}
              />
            )}
          </ScrollArea>
        </Tabs.Panel>
        <Tabs.Panel value="gis" h="100%" w="100%" pt="md">
          {activeTab === 'gis' && (
            <GisTab averagePerCombiner={averagePerCombiner} devices={devices} />
          )}
        </Tabs.Panel>
      </Tabs>
    </Stack>
  )
}

export default ModuleDegradation

// Helper function for Clearsky POA
function processPoaData(
  degradationPOA: DegradationPOA,
  timezone: string,
  computedColorScheme: string,
): {
  data: Partial<PlotData>[]
  layout: Partial<Layout>
} {
  const poaData = degradationPOA?.data
  const poaIndexes = poaData[0].x
  const validIndexes = degradationPOA?.valid_indexes
  const validColumns = degradationPOA?.valid_columns

  const shapes: Partial<Shape>[] = []
  let currentShape: Partial<Shape> | null = null

  // Add green rectangles to highlight validIndexes
  poaIndexes.forEach((x) => {
    const isValid = validIndexes.includes(x)
    if (isValid) {
      if (!currentShape) {
        currentShape = {
          type: 'rect',
          xref: 'x',
          yref: 'paper',
          x0: x,
          y0: 0,
          x1: x,
          y1: 1,
          fillcolor: 'rgba(0, 255, 0, 0.2)',
          line: {
            width: 0,
          },
        }
      } else {
        currentShape.x1 = x
      }
    } else if (currentShape) {
      shapes.push(currentShape)
      currentShape = null
    }
  })
  shapes.forEach((shape) => {
    if (shape.x0 === shape.x1) {
      const hourOffset = dayjs(shape.x0).tz(timezone).utcOffset() / 60
      const x0 = dayjs(shape.x0)
        .tz(timezone)
        .subtract(2, 'minute')
        .add(hourOffset, 'hour')
        .toISOString()
      const x1 = dayjs(shape.x1)
        .tz(timezone)
        .add(2, 'minute')
        .add(hourOffset, 'hour')
        .toISOString()
      shape.x0 = x0
      shape.x1 = x1
    }
  })

  const traces: Partial<Plotly.PlotData>[] = poaData.map((series, idx) => ({
    x: series.x, // Assuming each DataTimeSeries has an 'x' array
    y: series.y, // and a 'y' array
    type: 'scatter',
    mode: 'lines',
    name: series.name || `POA ${idx + 1}`, // Provide a name for the legend
    line: {
      color: validColumns.includes(series.name)
        ? `hsl(${(idx * 60) % 360}, 70%, 50%)`
        : computedColorScheme === 'dark'
          ? 'white'
          : 'black', // if series.name is in validColumns, use hsl, else use black or white depending on theme
      dash: validColumns.includes(series.name) ? 'solid' : 'dash',
    },
  }))

  const layout: Partial<Layout> = {
    shapes,
    showlegend: true,
    yaxis: {
      title: { text: 'POA' },
    },
    xaxis: {
      title: { text: 'Date' },
      type: 'date',
    },
    yaxis2: {
      title: { text: 'Filters' },
      showgrid: false,
      zeroline: false,
      side: 'right',
      overlaying: 'y',
    },
    // Optional: Improve layout aesthetics
    margin: { l: 50, r: 50, t: 50, b: 50 },
    legend: {
      orientation: 'h',
      x: 0.5,
      y: -0.2,
      xanchor: 'center',
      yanchor: 'top',
    },
  }

  return { data: traces, layout }
}
