import {
  DeviceTypeEnum,
  ProjectTypeEnum,
  SensorTypeEnum,
} from '@/api/enumerations'
import { useGetDeviceTypes } from '@/api/v1/operational/device_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetSensorTypes } from '@/api/v1/operational/sensor_types'
import { useGetRealTimeByDeviceTypeID } from '@/api/v1/protected/web-application/projects/real_time'
import CustomCard from '@/components/CustomCard'
import { PageLoader } from '@/components/Loading'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useProjectFilter } from '@/hooks/custom'
import { formatRelativeTime } from '@/utils/relativeTime'
import {
  Button,
  Group,
  List,
  SegmentedControl,
  Select,
  Stack,
  Switch,
  Text,
} from '@mantine/core'
import {
  IconChevronLeft,
  IconChevronRight,
  IconChevronsLeft,
  IconChevronsRight,
  IconDatabaseX,
} from '@tabler/icons-react'
import { Data, Layout, PlotMouseEvent } from 'plotly.js'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router'

// Constants
const IS_LARGE_THRESHOLD = 200
const GROUP_BUTTON_PX = 0
const GROUP_BUTTON_VARIANT = 'default'

// Helper function to convert staleness limit to milliseconds
const getStalenessLimitMs = (limit: string): number => {
  switch (limit) {
    case '5 minutes':
      return 5 * 60 * 1000
    case '30 minutes':
      return 30 * 60 * 1000
    case '1 hour':
      return 60 * 60 * 1000
    case '1 day':
      return 24 * 60 * 60 * 1000
    default:
      return 60 * 60 * 1000 // default to 1 hour
  }
}

// Helper function to check if data is stale based on time
const isDataStale = (timeString: string, stalenessLimitMs: number): boolean => {
  const dataTime = new Date(timeString).getTime()
  const currentTime = Date.now()
  return currentTime - dataTime > stalenessLimitMs
}

interface RealTimeProps {
  initialDeviceTypeId?: number
  restrictToDeviceTypeId?: number
}

const Page = ({
  initialDeviceTypeId,
  restrictToDeviceTypeId,
}: RealTimeProps) => {
  useProjectFilter({
    hasRealTimeData: true,
  })

  const navigate = useNavigate()
  const possibleDeviceTypes: {
    label: string
    deviceId: string
    sensorTypeIds: string[]
  }[] = [
    {
      label: 'PV PCS',
      deviceId: '2',
      sensorTypeIds: [
        String(SensorTypeEnum.PV_PCS_AC_POWER),
        String(SensorTypeEnum.PV_PCS_AC_POWER_SETPOINT),
      ],
    },
    {
      label: 'PV PCS Module',
      deviceId: '3',
      sensorTypeIds: [String(SensorTypeEnum.PV_PCS_MODULE_AC_POWER)],
    },
    {
      label: 'PV DC Combiner',
      deviceId: '9',
      sensorTypeIds: [String(SensorTypeEnum.PV_DC_COMBINER_CURRENT)],
    },
    {
      label: 'Tracker',
      deviceId: '29',
      sensorTypeIds: [
        String(SensorTypeEnum.TRACKER_POSITION),
        String(SensorTypeEnum.TRACKER_SETPOINT),
      ],
    },
    {
      label: 'BESS PCS',
      deviceId: '13',
      sensorTypeIds: [String(SensorTypeEnum.BESS_PCS_AC_POWER)],
    },
    {
      label: 'BESS PCS Module Group',
      deviceId: '32',
      sensorTypeIds: [String(SensorTypeEnum.BESS_PCS_MODULE_GROUP_AC_POWER)],
    },
    {
      label: 'BESS PCS Module',
      deviceId: '33',
      sensorTypeIds: [String(SensorTypeEnum.BESS_PCS_MODULE_AC_POWER)],
    },
    {
      label: 'BESS String',
      deviceId: '27',
      sensorTypeIds: [String(SensorTypeEnum.BESS_STRING_SOC_PERCENT)],
    },
  ]

  // deviceTypeId will keep track of which device type is selected
  const [deviceTypeId, setDeviceTypeId] = useState<number>()

  // traceName will keep track of which trace is selected
  // In the future this will include 'Setpoint' and 'Expected'
  // NOTE: This will need to be dynamically updated based on the device type
  // (some device types may not have all 3 options)
  const [traceName, setTraceName] = useState<string>('Actual')

  // groupBy will keep track of which group to display
  // An example of a group is a PV Block's worth of trackers
  const [groupBy, setGroupBy] = useState<string | null>(null)

  // stalenessLimit will keep track of how old data can be before being marked as stale
  const [stalenessLimit, setStalenessLimit] = useState<string>('1 hour')

  // showStaleWarnings will control whether to display warning symbols
  const [showStaleWarnings, setShowStaleWarnings] = useState<boolean>(true)

  const { projectId } = useParams<{ projectId: string }>()

  const projectData = useSelectProject(projectId!)

  useEffect(() => {
    if (projectData.data) {
      const defaultDeviceTypeId =
        projectData.data?.project_type_id === ProjectTypeEnum.PV
          ? DeviceTypeEnum.PV_PCS
          : DeviceTypeEnum.BESS_PCS
      queueMicrotask(() =>
        setDeviceTypeId(initialDeviceTypeId ?? defaultDeviceTypeId),
      )
    }
  }, [initialDeviceTypeId, projectData.data])

  const usedDeviceIds = (
    projectData.data?.spec?.used_device_type_ids ?? []
  ).map(String)

  const usedSensorIds = (
    projectData.data?.spec?.used_sensor_type_ids ?? []
  ).map(String)

  const projectDeviceTypes = possibleDeviceTypes
    .filter((dt) => usedDeviceIds.includes(dt.deviceId))
    .filter((dt) =>
      restrictToDeviceTypeId
        ? dt.deviceId === String(restrictToDeviceTypeId)
        : true,
    )
    .map((dt) => ({
      ...dt,
      sensorTypeIds: dt.sensorTypeIds.filter((id) =>
        usedSensorIds.includes(id),
      ),
    }))
    .filter((dt) => dt.sensorTypeIds.length > 0)

  const sensorTypeIds = projectDeviceTypes
    .filter((dt) => dt.deviceId === deviceTypeId?.toString())[0]
    ?.sensorTypeIds.map((id) => Number(id))

  // Query latest data
  const data = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: deviceTypeId || -1,
    },
    queryParams: {
      sensor_type_ids: sensorTypeIds,
    },
    queryOptions: { enabled: !!projectId && !!sensorTypeIds && !!deviceTypeId },
  })

  // Query device types
  const deviceTypes = useGetDeviceTypes({
    queryOptions: { enabled: !!projectId },
  })

  const sensorTypes = useGetSensorTypes({
    queryParams: {
      sensor_type_ids: usedSensorIds.map((id) => Number(id)),
    },
    queryOptions: { enabled: !!projectId && usedSensorIds.length > 0 },
  })

  // Get the device type name_long for the selected device type
  const deviceTypeName = deviceTypes.data?.find(
    (deviceType) => deviceType.device_type_id === deviceTypeId,
  )?.name_long

  const latestData = data.data
  const realTimeData = groupBy
    ? {
        ...latestData,
        device_names: latestData?.device_names?.filter(
          (_, idx) => latestData?.device_names_y?.[idx] === groupBy,
        ),
        device_names_y: latestData?.device_names_y?.filter(
          (name) => name === groupBy,
        ),
        device_ids: latestData?.device_ids?.filter(
          (_, idx) => latestData?.device_names_y?.[idx] === groupBy,
        ),
        traces: latestData?.traces?.map((trace) => ({
          ...trace,
          values: trace.values?.filter(
            (_, idx) => latestData?.device_names_y?.[idx] === groupBy,
          ),
        })),
      }
    : latestData

  const availableGroups = new Set(latestData?.device_names_y)
  const canGroup = availableGroups.size > 1

  const handleClick = (event: Readonly<PlotMouseEvent>) => {
    if (!event.points?.[0]) {
      return
    }
    const point = event.points[0]
    const customPointData = point.customdata as unknown as Plotly.Datum[]

    navigate(
      `/projects/${projectId}/device-details/single/${customPointData[0]}`,
    )
  }

  // Get the unit for the currently selected trace
  // For heatmaps, we need to find the sensor type that matches the current trace name
  const unit = (() => {
    if (!sensorTypes?.data || !traceName) return undefined

    // First, try to find by sensor type name matching the trace name
    let sensorType = sensorTypes.data.find(
      (st) =>
        st.name_long === traceName ||
        st.name_metric === traceName ||
        st.name_short === traceName,
    )

    // If not found by name, fall back to the first sensor type for this device type
    if (!sensorType) {
      sensorType = sensorTypes.data.find((st) =>
        projectDeviceTypes
          .find((dt) => dt.deviceId === deviceTypeId?.toString())
          ?.sensorTypeIds.includes(st.sensor_type_id.toString()),
      )
    }

    if (!sensorType?.unit) return undefined

    // For percentage units, combine name_metric with unit, removing "Percent" from name_metric
    if (sensorType.unit === '%') {
      const cleanNameMetric = sensorType.name_metric
        ?.replace(/\bPercent\b/gi, '')
        .trim()
      return cleanNameMetric
        ? `${cleanNameMetric} ${sensorType.unit}`
        : sensorType.unit
    }

    return sensorType.unit
  })()

  useEffect(() => {
    if (realTimeData?.traces?.length) {
      queueMicrotask(() => setTraceName(realTimeData?.traces?.[0]?.name ?? ''))
    }
  }, [realTimeData?.traces])

  let trace: Partial<Data>[]

  // If there are more than IS_LARGE_THRESHOLD devices, we use a heatmap
  // Else, we use a bar chart
  const isLarge = (realTimeData?.device_ids?.length || 0) > IS_LARGE_THRESHOLD
  let xvals: string[] = []
  let yvals: string[] = []
  if (isLarge) {
    const selectedTrace = realTimeData?.traces?.find(
      (t) => t.name === traceName,
    )

    const indexByLabel: Record<string, number[]> = {}
    ;(realTimeData?.device_names_y ?? []).forEach((label, idx) => {
      if (!indexByLabel[label]) indexByLabel[label] = []
      indexByLabel[label].push(idx)
    })

    xvals = realTimeData?.device_names_x ?? []
    yvals = realTimeData?.device_names_y ?? []
    const zvals = selectedTrace?.values ?? []
    const times = selectedTrace?.times ?? []
    const stalenessLimitMs = getStalenessLimitMs(stalenessLimit)

    // Determine which data points are stale
    const staleIndices = times.map((time) =>
      isDataStale(time, stalenessLimitMs),
    )

    const zmin = deviceTypeId === DeviceTypeEnum.TRACKER_ROW ? -60 : 0
    const zmax =
      deviceTypeId === DeviceTypeEnum.TRACKER_ROW
        ? 60
        : Math.max(
            ...(latestData?.traces
              .find((t) => t.name === traceName)
              ?.values.filter((v): v is number => v !== null) ?? []),
          )
    trace = [
      {
        x: xvals,
        y: yvals,
        z: zvals,
        zmin: zmin,
        zmax: zmax,
        type: 'heatmap',
        showlegend: false,
        customdata: (realTimeData?.device_ids ?? []).map((id, idx) => [
          id as Plotly.Datum,
          deviceTypeName as Plotly.Datum,
          (times[idx]
            ? formatRelativeTime(times[idx]).relative
            : 'N/A') as Plotly.Datum,
          staleIndices[idx] ? 'Stale' : ('Fresh' as Plotly.Datum),
        ]),
        xgap: xvals.length < 20_000 ? 1 : 0.2,
        ygap: yvals.length < 20_000 ? 1 : 0.2,
        hovertemplate: unit?.includes('%')
          ? '%{customdata[1]} %{y}.%{x}<br>%{z:.1%}<br>Received: %{customdata[2]}<extra></extra>'
          : '%{customdata[1]} %{y}.%{x}<br>%{z:.2f}<br>Received: %{customdata[2]}<extra></extra>',
        hoverongaps: false,
        colorbar: {
          title: {
            text:
              deviceTypeId === DeviceTypeEnum.PV_DC_COMBINER
                ? 'Current (A)'
                : deviceTypeId === DeviceTypeEnum.TRACKER_ROW
                  ? 'Angle (degrees)'
                  : unit || '',
          },
          tickformat: unit?.includes('%') ? ',.0%' : undefined,
        },
        // Add text annotations for stale data points (only if enabled)
        text: showStaleWarnings
          ? staleIndices.map((isStale) => (isStale ? '⚠️' : ''))
          : [],
        texttemplate: '%{text}',
        textfont: { size: 12 },
      },
    ]
  } else {
    const xvals = realTimeData?.device_names ?? []
    const stalenessLimitMs = getStalenessLimitMs(stalenessLimit)

    trace =
      realTimeData?.traces?.map((t, index) => {
        const values = t.values ?? []
        const times = t.times ?? []

        // Determine which data points are stale
        const staleIndices = times.map((time) =>
          isDataStale(time, stalenessLimitMs),
        )

        return {
          x: xvals,
          y: values,
          type: 'bar' as const,
          name: t.name,
          showlegend: true,
          width: 0.8 - index * 0.1,
          opacity: 0.7,
          customdata: (realTimeData?.device_ids ?? []).map((id, idx) => [
            id as Plotly.Datum,
            deviceTypeName as Plotly.Datum,
            (times[idx]
              ? formatRelativeTime(times[idx]).relative
              : 'N/A') as Plotly.Datum,
            staleIndices[idx] ? 'Stale' : ('Fresh' as Plotly.Datum),
          ]),
          hoverlabel: { namelength: -1 },
          hovertemplate:
            '%{customdata[1]} %{x}<br>%{y:.2f}<br>Received: %{customdata[2]}<extra></extra>',
          // Add text annotations for stale data points (only if enabled)
          text: showStaleWarnings
            ? staleIndices.map((isStale) => (isStale ? '⚠️' : ''))
            : [],
          textposition: 'inside',
          textfont: { size: 12 },
        }
      }) ?? []
  }

  const largeYAxisTitle = (() => {
    switch (deviceTypeId) {
      case DeviceTypeEnum.PV_PCS_MODULE:
        return 'PV PCS'
      case DeviceTypeEnum.PV_DC_COMBINER:
        return 'PV PCS'
      case DeviceTypeEnum.BESS_STRING:
        return 'BESS PCS'
      case DeviceTypeEnum.TRACKER_ROW:
        return 'Tracker Zone'
      case DeviceTypeEnum.BESS_CELL:
        return 'BESS Module'
      case DeviceTypeEnum.BESS_PCS_MODULE_GROUP:
        return 'BESS PCS'
      case DeviceTypeEnum.BESS_PCS_MODULE:
        return 'BESS PCS'
      default:
        return undefined
    }
  })()

  const getChartDescription = () => {
    switch (deviceTypeId) {
      case DeviceTypeEnum.PV_PCS:
        return (
          <Stack gap="xs">
            <Text fw={600}>Understanding PV PCS Power Output</Text>
            <Text size="sm">
              This chart displays the real-time power output of each PV
              Inverter.
            </Text>
            <Text size="sm">
              <Text component="span" fw={500} c="red">
                Red bars:
              </Text>{' '}
              Actual power output of the inverter. Useful for comparing
              inverters to identify outliers.
            </Text>
            <Text size="sm">
              <Text component="span" fw={500} c="blue">
                Blue bars:
              </Text>{' '}
              Set-point of the inverter. Typically set to nameplate when there
              are no curtailment events. Shows if power is being constrained by
              the plant controller.
            </Text>
            <List size="sm" spacing="xs">
              <List.Item>
                <Text component="span" fw={500} c="red">
                  Uniform red bars:
                </Text>{' '}
                Normal operation
              </List.Item>
              <List.Item>
                <Text component="span" fw={500} c="blue">
                  Full blue bars:
                </Text>{' '}
                Normal operation (near nameplate power)
              </List.Item>
              <List.Item>
                <Text component="span" fw={500} c="red">
                  Low red bars:
                </Text>{' '}
                Potential inverter issues or low sunlight conditions
              </List.Item>
            </List>
            <Text size="sm">
              <Text component="span" fw={500}>
                Note:
              </Text>{' '}
              Click any bar to explore detailed information about that device.
            </Text>
          </Stack>
        )
      case DeviceTypeEnum.PV_PCS_MODULE:
        return (
          <Stack gap="xs">
            <Text fw={600}>Understanding PV PCS Module Performance</Text>
            <Text size="sm">
              This chart shows the power output of individual PV PCS modules.
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Lower values:
              </Text>{' '}
              Modules are performing below expected levels
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Higher values:
              </Text>{' '}
              Modules are performing at or above expected levels
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Note:
              </Text>{' '}
              Click any bar to explore detailed information about that module.
            </Text>
          </Stack>
        )
      case DeviceTypeEnum.PV_DC_COMBINER:
        return (
          <Stack gap="xs">
            <Text fw={600}>Understanding PV DC Combiner Current</Text>
            <Text size="sm">
              This chart shows the DC current from each combiner box at each
              inverter.
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Y-axis:
              </Text>{' '}
              Indicates which inverter the combiner box is attached to
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                X-axis:
              </Text>{' '}
              Indicates which combiner is reporting current data
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Colors:
              </Text>{' '}
              <Text component="span" c="green">
                Green
              </Text>{' '}
              indicates more current,{' '}
              <Text component="span" c="red">
                red
              </Text>{' '}
              indicates less current
            </Text>
            <List size="sm" spacing="xs">
              <List.Item>
                <Text component="span" fw={500}>
                  Similar colors:
                </Text>{' '}
                Normal operation across combiners
              </List.Item>
              <List.Item>
                <Text component="span" fw={500} c="red">
                  Redder colors:
                </Text>{' '}
                Potential combiner performance issues
              </List.Item>
              <List.Item>
                <Text component="span" fw={500}>
                  Blank colors:
                </Text>{' '}
                Data loss or missing combiners
              </List.Item>
            </List>
            <Text size="sm">
              <Text component="span" fw={500}>
                Note:
              </Text>{' '}
              Click any box to navigate to device details for that combiner.
            </Text>
          </Stack>
        )
      case DeviceTypeEnum.TRACKER_ROW:
        return (
          <Stack gap="xs">
            <Text fw={600}>Understanding Tracker Angle Visualization</Text>
            <Text size="sm">
              This heatmap visualizes the real-time tracking angle or set-point
              of each tracker row.
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Y-axis:
              </Text>{' '}
              Tracker zone
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                X-axis:
              </Text>{' '}
              Tracker row
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Colors:
              </Text>{' '}
              Each cell represents the tracker&apos;s angle with a legend
              provided. Colors range from{' '}
              <Text component="span" c="#b5d6e0">
                blue
              </Text>{' '}
              (sunrise) to{' '}
              <Text component="span" c="#ffef7a">
                yellow
              </Text>{' '}
              (mid-morning) to{' '}
              <Text component="span" c="#f7c16a">
                orange
              </Text>{' '}
              (noon) to{' '}
              <Text component="span" c="#ff6b3e">
                red
              </Text>{' '}
              (mid-afternoon) to{' '}
              <Text component="span" c="#27214e">
                purple
              </Text>{' '}
              (sunset).
            </Text>
            <List size="sm" spacing="xs">
              <List.Item>
                <Text component="span" fw={500}>
                  Uniform color:
                </Text>{' '}
                All trackers are aligned (normal operation)
              </List.Item>
              <List.Item>
                <Text component="span" fw={500}>
                  Different colors:
                </Text>{' '}
                Individual trackers or controllers may have issues
              </List.Item>
            </List>
            <Text size="sm">
              <Text component="span" fw={500}>
                Note:
              </Text>{' '}
              Use the toggle button to switch between tracker angle and setpoint
              views.
            </Text>
          </Stack>
        )
      case DeviceTypeEnum.BESS_PCS:
        return (
          <Stack gap="xs">
            <Text fw={600}>Understanding BESS PCS Power Output</Text>
            <Text size="sm">
              This chart displays the real-time power output of each BESS PCS
              (Power Conversion System).
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Lower values:
              </Text>{' '}
              PCS units are operating at lower power levels
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Higher values:
              </Text>{' '}
              PCS units are operating at higher power levels
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Note:
              </Text>{' '}
              Click any bar to explore detailed information about that PCS.
            </Text>
          </Stack>
        )
      case DeviceTypeEnum.BESS_PCS_MODULE_GROUP:
        return (
          <Stack gap="xs">
            <Text fw={600}>
              Understanding BESS PCS Module Group Performance
            </Text>
            <Text size="sm">
              This chart shows the performance of BESS PCS module groups.
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Lower values:
              </Text>{' '}
              Module groups are performing below expected levels
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Higher values:
              </Text>{' '}
              Module groups are performing at or above expected levels
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Note:
              </Text>{' '}
              Click any bar to explore detailed information about that module
              group.
            </Text>
          </Stack>
        )
      case DeviceTypeEnum.BESS_PCS_MODULE:
        return (
          <Stack gap="xs">
            <Text fw={600}>Understanding BESS PCS Module Performance</Text>
            <Text size="sm">
              This chart shows the performance of individual BESS PCS modules.
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Lower values:
              </Text>{' '}
              Modules are performing below expected levels
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Higher values:
              </Text>{' '}
              Modules are performing at or above expected levels
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Note:
              </Text>{' '}
              Click any bar to explore detailed information about that module.
            </Text>
          </Stack>
        )
      case DeviceTypeEnum.BESS_STRING:
        return (
          <Stack gap="xs">
            <Text fw={600}>Understanding BESS String Performance</Text>
            <Text size="sm">
              This chart shows the performance of BESS strings.
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Lower values:
              </Text>{' '}
              Strings are performing below expected levels
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Higher values:
              </Text>{' '}
              Strings are performing at or above expected levels
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Note:
              </Text>{' '}
              Click any bar to explore detailed information about that string.
            </Text>
          </Stack>
        )
      case DeviceTypeEnum.BESS_CELL:
        return (
          <Stack gap="xs">
            <Text fw={600}>Understanding BESS Cell Performance</Text>
            <Text size="sm">
              This chart shows the performance of individual BESS cells.
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Lower values:
              </Text>{' '}
              Cells are performing below expected levels
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Higher values:
              </Text>{' '}
              Cells are performing at or above expected levels
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Note:
              </Text>{' '}
              Click any bar to explore detailed information about that cell.
            </Text>
          </Stack>
        )
      default:
        return null
    }
  }

  const bessYRange = (() => {
    if (deviceTypeId !== 13) return undefined

    const allValues =
      realTimeData?.traces?.flatMap(
        (t) => t.values?.filter((v): v is number => v !== null) ?? [],
      ) ?? []
    const maxAbs = allValues.reduce((max, v) => Math.max(max, Math.abs(v)), 0)
    const yAxisMax = Math.max(1.0, maxAbs)
    return [-yAxisMax, yAxisMax]
  })()

  const layout: Partial<Layout> = {
    barmode: 'overlay',
    plot_bgcolor: 'transparent',
    xaxis: {
      showgrid: false,
      type: isLarge ? 'category' : undefined,
      categoryorder: 'array',
      categoryarray: naturalSort(xvals),
      title: {
        text: deviceTypeName ? `${deviceTypeName} Device Name` : 'Device Name',
      },
    },
    yaxis: {
      type: isLarge ? 'category' : undefined,
      categoryorder: 'array',
      categoryarray: naturalSort(yvals),
      showgrid: isLarge ? false : true,
      range: isLarge ? undefined : (bessYRange ?? ['data', 'data']),
      title: { text: isLarge ? largeYAxisTitle : (unit ?? '') },
      tickformat: unit?.includes('%') ? ',.0%' : undefined,
    },
  }

  useEffect(() => {
    if (!canGroup) {
      queueMicrotask(() => setGroupBy(null))
    }
  }, [canGroup])

  useEffect(() => {
    queueMicrotask(() => setGroupBy(null))
  }, [deviceTypeId])

  if (projectData.isLoading) {
    return <PageLoader />
  }

  if (!projectData.data?.has_real_time_data) {
    return (
      <Stack h="100%" p="md">
        <Text>
          Real time data is not available for this project yet. Check back soon!
        </Text>
      </Stack>
    )
  }

  return (
    <Stack h="100%" w="100%">
      <Group>
        {canGroup && (isLarge || !!groupBy) && (
          <GroupNavigation
            availableGroups={availableGroups}
            groupBy={groupBy}
            setGroupBy={setGroupBy}
          />
        )}
        {isLarge && (
          <>
            <SegmentedControl
              value={traceName}
              onChange={setTraceName}
              data={
                realTimeData?.traces?.map((trace) => ({
                  label: trace.name,
                  value: trace.name,
                })) || []
              }
            />
          </>
        )}
        <Select
          value={stalenessLimit}
          onChange={(value) => setStalenessLimit(value || '1 hour')}
          data={[
            { value: '5 minutes', label: '5 minutes' },
            { value: '30 minutes', label: '30 minutes' },
            { value: '1 hour', label: '1 hour' },
            { value: '1 day', label: '1 day' },
          ]}
          size="sm"
          w={150}
          disabled={!showStaleWarnings}
        />
        <Switch
          label="Show Stale Data Warnings"
          checked={showStaleWarnings}
          onChange={(event) =>
            setShowStaleWarnings(event.currentTarget.checked)
          }
        />
      </Group>
      <CustomCard
        style={{ flex: 1, height: '100%', width: '100%' }}
        info={getChartDescription()}
      >
        {!data.isLoading && realTimeData?.traces?.length === 0 ? (
          <Stack align="center" justify="center" h="100%">
            <IconDatabaseX size={48} strokeWidth={2} />
            <Text>Data not available for this request.</Text>
          </Stack>
        ) : (
          <PlotlyPlot
            data={trace}
            layout={layout}
            onClick={handleClick}
            isLoading={data.isLoading}
            error={data.error}
            colorscale={
              deviceTypeId === DeviceTypeEnum.TRACKER_ROW
                ? 'tracker'
                : 'good-bad'
            }
          />
        )}
      </CustomCard>
    </Stack>
  )
}

interface GroupNavigationProps {
  availableGroups: Set<string>
  groupBy: string | null
  setGroupBy: (value: string | null) => void
}

const GroupNavigation = ({
  availableGroups,
  groupBy,
  setGroupBy,
}: GroupNavigationProps) => {
  const handleFirst = () => {
    const groups = Array.from(availableGroups)
    if (groups.length > 0) {
      setGroupBy(groups[0])
    }
  }

  const handleLast = () => {
    const groups = Array.from(availableGroups)
    if (groups.length > 0) {
      setGroupBy(groups[groups.length - 1])
    }
  }

  const handlePrevious = () => {
    const groups = Array.from(availableGroups)
    const currentIndex = groups.indexOf(groupBy || '')
    if (currentIndex > 0) {
      setGroupBy(groups[currentIndex - 1])
    }
  }

  const handleNext = () => {
    const groups = Array.from(availableGroups)
    const currentIndex = groups.indexOf(groupBy || '')
    if (currentIndex < groups.length - 1) {
      setGroupBy(groups[currentIndex + 1])
    }
  }

  return (
    <Button.Group>
      <Button
        variant={GROUP_BUTTON_VARIANT}
        px={GROUP_BUTTON_PX}
        onClick={handleFirst}
        disabled={
          !groupBy || Array.from(availableGroups).indexOf(groupBy) === 0
        }
      >
        <IconChevronsLeft />
      </Button>
      <Button
        variant={GROUP_BUTTON_VARIANT}
        px={GROUP_BUTTON_PX}
        onClick={handlePrevious}
        disabled={
          !groupBy || Array.from(availableGroups).indexOf(groupBy) === 0
        }
      >
        <IconChevronLeft />
      </Button>
      <Select
        data={Array.from(availableGroups).map((group) => ({
          label: group,
          value: group,
        }))}
        placeholder="Group data by..."
        clearable
        onChange={setGroupBy}
        value={groupBy}
        radius={0}
      />
      <Button
        variant={GROUP_BUTTON_VARIANT}
        px={GROUP_BUTTON_PX}
        onClick={handleNext}
        disabled={
          !groupBy ||
          Array.from(availableGroups).indexOf(groupBy) ===
            Array.from(availableGroups).length - 1
        }
      >
        <IconChevronRight />
      </Button>
      <Button
        variant={GROUP_BUTTON_VARIANT}
        px={GROUP_BUTTON_PX}
        onClick={handleLast}
        disabled={
          !groupBy ||
          Array.from(availableGroups).indexOf(groupBy) ===
            Array.from(availableGroups).length - 1
        }
      >
        <IconChevronsRight />
      </Button>
    </Button.Group>
  )
}

const naturalSort = (array: string[]) => {
  return Array.from(new Set(array)).sort(
    new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' })
      .compare,
  )
}

export default Page
