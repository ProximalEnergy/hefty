import { useGetOperationalKPIData } from '@/api/v1/operational/kpi_data'
import { useGetProjectKPITypes } from '@/api/v1/operational/kpi_types'
import {
  DashboardComponent,
  useAddUserDashboard,
  useGetBarData,
  useGetDashboard,
  useGetGaugeData,
  useGetLineData,
  useGetScatterData,
  useUpdateUserDashboard,
} from '@/api/v1/operational/project/custom_dash'
import { useSelectProject } from '@/api/v1/operational/projects'
import {
  SensorType,
  useGetSensorTypes,
} from '@/api/v1/operational/sensor_types'
import { PageLoader } from '@/components/Loading'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
// import { GISContext } from '@/contexts/GISContext'
import { useGetKPIType } from '@/hooks/api'
import { useProjectDropdownToggle } from '@/hooks/custom'
// import * as gisUtils from '@/utils/GIS'
import {
  ActionIcon,
  Button,
  Drawer,
  Group,
  Paper,
  RingProgress,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
  Tooltip,
  useComputedColorScheme,
  useDrawersStack,
} from '@mantine/core'
import { Link, RichTextEditor } from '@mantine/tiptap'
import { IconTrash } from '@tabler/icons-react'
import { UseQueryResult } from '@tanstack/react-query'
import { useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { AxiosError } from 'axios'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import DOMPurify from 'dompurify'
// import { FeatureCollection } from 'geojson'
import { PlotType } from 'plotly.js'
import {
  startTransition,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react'
import { Responsive, WidthProvider } from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
// import { Layer, LngLatBoundsLike, Map, Source } from 'react-map-gl'
import {
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from 'react-router'

import BarConfigComp from './BarConfig'
import GaugeConfigComp from './GaugeConfig'
import KPIConfigComp from './KPIConfig'
import LineConfigComp from './LineConfig'
import RichTextConfigComp from './RichTextConfig'
import ScatterConfigComp from './ScatterConfig'

dayjs.extend(utc)
dayjs.extend(timezone)

const defaultTimeRanges = {
  Today: 3,
  Yesterday: 4,
  'Past 2 Days': 1,
  'Past 3 Days': 2,
}
const defaultKPITimeRanges = {
  '1 Month': 1,
  'Year to Date': 2,
  'Beginning of Life': 3,
  'Month to Date': 4,
}

// Helper function to calculate time ranges based on selected values
const calculateTimeRange = (timeRangeValue: number) => {
  switch (timeRangeValue) {
    case 1: // Past 2 Days
      return 'past-2-days'
    case 2: // Past 3 Days
      return 'past-3-days'
    case 3: // Today
      return 'today'
    case 4: // Yesterday
      return 'yesterday'
    default:
      return 'today'
  }
}

// Helper function to calculate KPI time ranges based on selected values
const calculateKPITimeRange = (timeRangeValue: number, timeZone: string) => {
  // Get current time in project timezone and floor to last 5-minute interval
  const now = dayjs()
    .tz(timeZone)
    .minute(Math.floor(dayjs().tz(timeZone).minute() / 5) * 5)
    .second(0)
    .millisecond(0)

  switch (timeRangeValue) {
    case 1: // 1 Month
      return {
        start: now.subtract(1, 'month').format('YYYY-MM-DD'),
        end: now.format('YYYY-MM-DD'),
      }
    case 2: // Year to Date
      return {
        start: now.startOf('year').format('YYYY-MM-DD'),
        end: now.format('YYYY-MM-DD'),
      }
    case 3: // Beginning of Life
      return {
        start: now.startOf('year').subtract(10, 'year').format('YYYY-MM-DD'), // Assuming 10 years for "beginning of life"
        end: now.format('YYYY-MM-DD'),
      }
    case 4: // Month to Date
      return {
        start: now.startOf('month').format('YYYY-MM-DD'),
        end: now.format('YYYY-MM-DD'),
      }
    default:
      return {
        start: now.subtract(1, 'month').format('YYYY-MM-DD'),
        end: now.format('YYYY-MM-DD'),
      }
  }
}

const ResponsiveGridLayout = WidthProvider(Responsive)

// Helper function to convert string to proper case
const toProperCase = (str: string): string => {
  return str
    .toLowerCase()
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

// Helper function to get minimum height based on component type
const getComponentMinHeight = (componentType: string): number => {
  switch (componentType) {
    case 'rich_text':
      return 1
    case 'gauge':
      return 3
    default:
      return 2
  }
}

// Helper function to apply aggregation method to KPI data
const applyAggregationMethod = (
  values: (number | null)[],
  aggregationMethod: string,
): number | null => {
  // Filter out null values
  const validValues = values.filter((value): value is number => value !== null)

  if (validValues.length === 0) {
    return null
  }

  switch (aggregationMethod.toLowerCase()) {
    case 'average':
    case 'mean':
      return (
        validValues.reduce((sum, value) => sum + value, 0) / validValues.length
      )

    case 'sum':
      return validValues.reduce((sum, value) => sum + value, 0)

    case 'min':
    case 'minimum':
      return Math.min(...validValues)

    case 'max':
    case 'maximum':
      return Math.max(...validValues)

    case 'median': {
      const sortedValues = [...validValues].sort((a, b) => a - b)
      const mid = Math.floor(sortedValues.length / 2)
      return sortedValues.length % 2 === 0
        ? (sortedValues[mid - 1] + sortedValues[mid]) / 2
        : sortedValues[mid]
    }

    case 'count':
      return validValues.length

    case 'std':
    case 'standard_deviation': {
      const mean =
        validValues.reduce((sum, value) => sum + value, 0) / validValues.length
      const variance =
        validValues.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) /
        validValues.length
      return Math.sqrt(variance)
    }

    default:
      // Default to average if method is not recognized
      return (
        validValues.reduce((sum, value) => sum + value, 0) / validValues.length
      )
  }
}

export interface GaugeConfig {
  measuredVariable: string
  maximumValue: string
}

export interface KPIConfig {
  kpiTypeId: string
}

export interface LineConfig {
  traces: Array<{
    id: string
    sensorTypeId: string | null
    aggregationMethod: string | null
  }>
}

export interface ScatterConfig {
  xAxisSensorTypeId: string | null
  yAxisSensorTypeId: string | null
}

export interface BarConfig {
  sensorTypeId: string | null
  aggregationMethod: string | null
}

export interface RichTextConfig {
  content: string
}

// // Placeholder Map Component
// const PlaceholderMap = ({ projectId }: { projectId: string }) => {
//   const devices = useGetDevicesV2({
//     pathParams: { projectId },
//     filters: {
//       device_type_ids: [2], // PCS devices
//     },
//   })
//   const computedColorScheme = useComputedColorScheme('dark')
//   const context = useContext(GISContext)
//   const blankMapStyle = gisUtils.useBlankMapStyle()

//   if (!context) {
//     throw new Error('GISContext is not provided')
//   }

//   if (devices.isLoading) {
//     return <PageLoader />
//   }

//   // Create a simple GeoJSON from devices data
//   let bounds: LngLatBoundsLike | undefined = undefined

//   const filteredData = {
//     type: 'FeatureCollection',
//     features: devices.data?.map((device) => {
//       return {
//         type: 'Feature',
//         geometry: device.polygon,
//         properties: {
//           name: device.name_long,
//           value: 1,
//         },
//       }
//     }),
//   } as FeatureCollection

//   if (filteredData.features.length > 0) {
//     bounds = gisUtils.findBoundingBox(filteredData)
//   }

//   return (
//     <div style={{ height: '100%', width: '100%' }}>
//       <Map
//         initialViewState={{
//           bounds: bounds || undefined,
//           fitBoundsOptions: {
//             padding: {
//               top: 25,
//               bottom: 25,
//               left: 65,
//               right: 65,
//             },
//           },
//         }}
//         style={{
//           borderBottomLeftRadius: 'inherit',
//           borderBottomRightRadius: 'inherit',
//         }}
//         mapStyle={
//           gisUtils.mapStyle({
//             satellite: true,
//             theme: computedColorScheme,
//           }) ?? blankMapStyle
//         }
//         mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
//         interactiveLayerIds={['data']}
//       >
//         <Source id="data" type="geojson" data={filteredData}>
//           <Layer
//             {...gisUtils.layerData({
//               featureKey: 'value',
//               colors: [
//                 { id: 0, value: '#1C7ED6' },
//                 { id: 1, value: '#FFD43B' },
//                 { id: 2, value: '#FF6B6B' },
//               ],
//               lowValue: 0,
//               highValue: 100,
//             })}
//           />
//         </Source>
//       </Map>
//     </div>
//   )
// }

// Individual component types - each calls hooks unconditionally
const GaugeComponent = ({
  component,
  projectId,
  startQuery,
  endQuery,
}: {
  component: DashboardComponent & { config: GaugeConfig }
  projectId: string | undefined
  defaultTimeRange: number
  timeZone: string
  startQuery: string
  endQuery: string
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 })

  const gauge = useGetGaugeData({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      measured_variable: component.config.measuredVariable,
      maximum_value: component.config.maximumValue,
      start: startQuery,
      end: endQuery,
    },
    queryOptions: {
      enabled:
        !!projectId &&
        !!component.config.measuredVariable &&
        !!component.config.maximumValue &&
        !!startQuery &&
        !!endQuery,
    },
  })

  // Update container size when component mounts, resizes, or grid layout changes
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect()
        setContainerSize({ width, height })
      }
    }

    // Initial size calculation with a small delay to ensure container is rendered
    const timeoutId = setTimeout(updateSize, 0)

    // Use ResizeObserver for more accurate container size detection
    let resizeObserver: ResizeObserver | null = null
    if (containerRef.current && window.ResizeObserver) {
      resizeObserver = new ResizeObserver(updateSize)
      resizeObserver.observe(containerRef.current)
    }

    // Fallback to window resize listener
    window.addEventListener('resize', updateSize)

    return () => {
      clearTimeout(timeoutId)
      if (resizeObserver) {
        resizeObserver.disconnect()
      }
      window.removeEventListener('resize', updateSize)
    }
  }, [component.h, component.w, gauge.data]) // Re-run when grid dimensions change

  if (gauge.isLoading) {
    return <PageLoader />
  }

  // Calculate ring size based on container dimensions
  const minDimension = Math.min(containerSize.width, containerSize.height)
  const ringSize = minDimension * 0.9 // 80% of smallest dimension, minimum 100px

  return (
    <Stack align="center" justify="center" h="100%" w="100%">
      <Text fw={600} size="lg">
        Metered Energy / Expected Energy
      </Text>
      <Stack
        ref={containerRef}
        align="center"
        justify="center"
        h="100%"
        w="100%"
      >
        <RingProgress
          thickness={12}
          size={Math.max(ringSize ?? 0, 12 * 2 + 1)}
          sections={[
            {
              value: gauge.data?.value || 0,
              color: 'green',
            },
          ]}
          label={
            <Stack gap={0} py={0}>
              <Text size="sm" fw={700} ta="center">
                {gauge.data?.value_raw.toFixed(0) || 0} /{' '}
                {gauge.data?.max.toFixed(0) || 0}
              </Text>
              <Text size="sm" fw={700} ta="center">
                MWh
              </Text>
            </Stack>
          }
          style={
            {
              '--rp-size': `${ringSize}px`,
            } as React.CSSProperties
          }
        />
      </Stack>
    </Stack>
  )
}

const KPIComponent = ({
  component,
  projectId,
  defaultKPITimeRange,
  timeZone,
}: {
  component: DashboardComponent & { config: KPIConfig }
  projectId: string | undefined
  defaultKPITimeRange: number
  timeZone: string
}) => {
  const { start, end } = calculateKPITimeRange(defaultKPITimeRange, timeZone)

  const parsedKpiTypeId = component.config.kpiTypeId
    ? Number(component.config.kpiTypeId)
    : -1

  const kpi = useGetOperationalKPIData({
    queryParams: {
      project_ids: [projectId || '-1'],
      kpi_type_ids: [parsedKpiTypeId],
      include_device_data: false,
      start,
      end,
    },
    queryOptions: {
      enabled: !!projectId && !!component.config.kpiTypeId,
    },
  })
  const kpiType = useGetKPIType({
    pathParams: {
      kpiTypeId: parsedKpiTypeId,
    },
    queryOptions: {
      enabled: !!component.config.kpiTypeId,
    },
  })

  // Calculate kpiValue using the aggregation method
  let kpiValue =
    kpi.data && kpiType.data
      ? applyAggregationMethod(
          kpi.data[0]?.data.project_data || [],
          kpiType.data.aggregation_method || 'average',
        )
      : null

  // If unit is "%", multiply by 100
  if (kpiValue !== null && kpiType.data?.unit === '%') {
    kpiValue = kpiValue * 100
  }

  const isLoading = kpi.isLoading || kpiType.isLoading
  if (isLoading) {
    return <PageLoader />
  }

  return (
    <Stack align="center" h="100%">
      <Text fw={600} size="lg">
        {kpiType.data?.name_long}
      </Text>
      <Text size="xs" c="dimmed">
        {toProperCase(kpiType.data?.aggregation_method || 'average')} from{' '}
        {start} to {end}
      </Text>
      <Stack align="center" justify="center" h="100%">
        <Text size="xl" fw={700} c="blue">
          {kpiValue !== null ? kpiValue.toFixed(2) : 'N/A'}
          {kpiType.data?.unit &&
            (kpiType.data.unit === '%'
              ? kpiType.data.unit
              : ` ${kpiType.data.unit}`)}
        </Text>
      </Stack>
    </Stack>
  )
}

const LineComponent = ({
  component,
  projectId,
  startQuery,
  endQuery,
  sensorTypes,
}: {
  component: DashboardComponent & { config: LineConfig }
  projectId: string | undefined
  startQuery: string
  endQuery: string
  sensorTypes: UseQueryResult<SensorType[], AxiosError<unknown>>
}) => {
  const uniqueSensorTypeIds = component.config.traces
    .map((trace: { sensorTypeId: string | null }) => trace.sensorTypeId)
    .filter((id: string | null) => id !== null)
  const uniqueSensorTypeIdsData = sensorTypes.data?.filter((sensorType) =>
    uniqueSensorTypeIds.includes(sensorType.sensor_type_id.toString()),
  )

  const lineData = useGetLineData({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      sensor_type_ids: component.config.traces
        .map((trace: { sensorTypeId: string | null }) =>
          Number(trace.sensorTypeId),
        )
        .filter((id: number) => !isNaN(id)),
      aggregation_types: component.config.traces
        .map(
          (trace: { aggregationMethod: string | null }) =>
            trace.aggregationMethod,
        )
        .filter((method: string | null) => method !== null) as string[],
      start: startQuery,
      end: endQuery,
    },
    queryOptions: {
      enabled:
        !!projectId &&
        component.config.traces.length > 0 &&
        !!startQuery &&
        !!endQuery &&
        component.config.traces.every(
          (trace: {
            sensorTypeId: string | null
            aggregationMethod: string | null
          }) => trace.sensorTypeId && trace.aggregationMethod,
        ),
    },
  })

  if (lineData.isLoading) {
    return <PageLoader />
  }

  if (!lineData.data || lineData.data.length === 0) {
    return (
      <Stack h="100%">
        <Text fw={600} size="sm" mb="xs">
          Line Chart
        </Text>
        <div
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Text c="dimmed">No data available</Text>
        </div>
      </Stack>
    )
  }

  // Group traces by unit
  const unitGroups = lineData.data.reduce(
    (groups: { [key: string]: typeof lineData.data }, traceData) => {
      const unit = traceData.unit || 'Unitless'
      const displayUnit = unit === 'C' ? 'Degrees (C)' : unit
      if (!groups[displayUnit]) {
        groups[displayUnit] = []
      }
      groups[displayUnit].push(traceData)
      return groups
    },
    {},
  )

  const unitKeys = Object.keys(unitGroups)

  // Transform the data for Plotly with y-axis assignments
  const plotData = lineData.data
    .map((traceData, index) => {
      const unit = traceData.unit || 'Unitless'
      const displayUnit = unit === 'C' ? 'Degrees (C)' : unit
      const unitIndex = unitKeys.indexOf(displayUnit)

      // Assign y-axis based on unit index
      let yAxis = 'y'
      if (unitIndex === 1) {
        yAxis = 'y2'
      } else if (unitIndex === 2) {
        yAxis = 'y3'
      } else if (unitIndex === 3) {
        yAxis = 'y4'
      }

      return {
        x: traceData.x,
        y: traceData.y,
        type: 'scatter' as PlotType,
        mode: 'lines' as const,
        name: `${traceData.name} (${displayUnit})`,
        yaxis: yAxis,
        hoverlabel: { namelength: -1 },
        line: {
          color: `hsl(${(index * 137.5) % 360}, 70%, 50%)`, // Generate distinct colors
        },
      }
    })
    .sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }))

  // Create layout with multiple y-axes
  const layout: Record<string, unknown> = {
    showlegend: lineData.data.length > 1,
    margin: { t: 20, b: 50, l: 80, r: 80 },
    xaxis: {
      title: 'Time',
      showgrid: true,
      zeroline: true,
      showline: true,
      mirror: true,
      ticks: 'outside',
      ticklen: 5,
      tickwidth: 1,
      tickcolor: '#666',
      tickfont: {
        size: 10,
      },
      titlefont: {
        size: 12,
      },
    },
    yaxis: {
      title: unitKeys[0] || 'Value',
      side: 'left',
      showgrid: true,
      zeroline: true,
      showline: true,
      mirror: true,
      ticks: 'outside',
      ticklen: 5,
      tickwidth: 1,
      tickcolor: '#666',
      tickfont: {
        size: 10,
      },
      titlefont: {
        size: 12,
      },
    },
  }

  // Add secondary y-axis if we have more than one unit
  if (unitKeys.length > 1) {
    layout.yaxis2 = {
      title: unitKeys[1],
      side: 'right',
      overlaying: 'y',
      showgrid: false,
      zeroline: false,
      showline: true,
      mirror: true,
      ticks: 'outside',
      ticklen: 5,
      tickwidth: 1,
      tickcolor: '#666',
      tickfont: {
        size: 10,
      },
      titlefont: {
        size: 12,
      },
    }
  }

  // Add third y-axis if we have more than two units
  if (unitKeys.length > 2) {
    layout.yaxis3 = {
      title: unitKeys[2],
      side: 'right',
      overlaying: 'y',
      position: -1, // Offset to the right to avoid overlap
      showgrid: false,
      zeroline: false,
      showline: true,
      mirror: true,
      ticks: 'outside',
      ticklen: 5,
      tickwidth: 1,
      tickcolor: '#666',
      tickfont: {
        size: 10,
      },
      titlefont: {
        size: 12,
      },
    }
  }

  // Add fourth y-axis if we have more than three units
  if (unitKeys.length > 3) {
    layout.yaxis4 = {
      title: unitKeys[3],
      side: 'left',
      overlaying: 'y',
      position: 0.05, // Offset to the left to avoid overlap
      showgrid: false,
      zeroline: false,
      showline: true,
      mirror: true,
      ticks: 'outside',
      ticklen: 5,
      tickwidth: 1,
      tickcolor: '#666',
      tickfont: {
        size: 10,
      },
      titlefont: {
        size: 12,
      },
    }
  }

  return (
    <Stack h="100%">
      <Group justify="space-between" align="center">
        <Tooltip
          position="bottom"
          label={
            <Stack p={0} gap={0}>
              {uniqueSensorTypeIdsData?.map((sensorType) => (
                <Text key={sensorType.sensor_type_id}>
                  {sensorType.name_long}
                </Text>
              ))}
            </Stack>
          }
        >
          <Text fw={600} size="sm" mb="xs">
            {uniqueSensorTypeIdsData?.length === 1
              ? uniqueSensorTypeIdsData[0].name_long
              : `Selected Metrics (${uniqueSensorTypeIdsData?.length} Types)`}
          </Text>
        </Tooltip>
      </Group>
      <PlotlyPlot
        data={plotData}
        layout={layout}
        config={{ displayModeBar: false }}
      />
    </Stack>
  )
}

const ScatterComponent = ({
  component,
  projectId,
  startQuery,
  endQuery,
}: {
  component: DashboardComponent & { config: ScatterConfig }
  projectId: string | undefined
  startQuery: string
  endQuery: string
}) => {
  const scatter = useGetScatterData({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      x_axis_sensor_type_id: component.config.xAxisSensorTypeId
        ? Number(component.config.xAxisSensorTypeId)
        : -1,
      y_axis_sensor_type_id: component.config.yAxisSensorTypeId
        ? Number(component.config.yAxisSensorTypeId)
        : -1,
      start: startQuery,
      end: endQuery,
    },
    queryOptions: {
      enabled:
        !!projectId &&
        !!component.config.xAxisSensorTypeId &&
        !!component.config.yAxisSensorTypeId &&
        !!startQuery &&
        !!endQuery,
    },
  })

  if (scatter.isLoading) {
    return <PageLoader />
  }

  return (
    <Stack h="100%">
      <Text fw={600} size="sm" mb="xs">
        {scatter.data?.y.name} vs {scatter.data?.x.name}
      </Text>
      <PlotlyPlot
        data={[
          {
            x: scatter.data?.x.values,
            y: scatter.data?.y.values,
            type: 'scatter' as PlotType,
            mode: 'markers' as const,
            name: `${scatter.data?.x.name} vs ${scatter.data?.y.name}`,
            hoverlabel: { namelength: -1 },
          },
        ]}
        layout={{
          showlegend: false,
          margin: { t: 10, b: 10, l: 10, r: 10 },
          xaxis: {
            title: {
              text: `${scatter.data?.x.name} (${scatter.data?.x.unit || 'Unitless'})`,
            },
          },
          yaxis: {
            title: {
              text: `${scatter.data?.y.name} (${scatter.data?.y.unit || 'Unitless'})`,
            },
          },
        }}
        config={{ displayModeBar: false }}
      />
    </Stack>
  )
}

const BarComponent = ({
  component,
  projectId,
  startQuery,
  endQuery,
}: {
  component: DashboardComponent & { config: BarConfig }
  projectId: string | undefined
  startQuery: string
  endQuery: string
}) => {
  const barData = useGetBarData({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      sensor_type_id: component.config.sensorTypeId
        ? Number(component.config.sensorTypeId)
        : -1,
      aggregation_type: component.config.aggregationMethod ?? '',
      start: startQuery,
      end: endQuery,
    },
    queryOptions: {
      enabled:
        !!projectId &&
        !!component.config.sensorTypeId &&
        !!component.config.aggregationMethod &&
        !!startQuery &&
        !!endQuery,
    },
  })

  if (barData.isLoading) {
    return <PageLoader />
  }

  if (!barData.data || !barData.data.x || !barData.data.y) {
    return (
      <Stack h="100%">
        <Text fw={600} size="sm" mb="xs">
          {barData.data?.name || 'Bar Chart'}
        </Text>
        <div
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Text c="dimmed">No data available</Text>
        </div>
      </Stack>
    )
  }

  return (
    <Stack h="100%">
      <Text fw={600} size="sm" mb="xs">
        {barData.data.name}
      </Text>
      <PlotlyPlot
        data={[
          {
            x: barData.data.x,
            y: barData.data.y,
            type: 'bar',
            name: barData.data.name,
            hoverlabel: { namelength: -1 },
          },
        ]}
        layout={{
          showlegend: false,
          margin: { t: 10, b: 10, l: 10, r: 10 },
          xaxis: {
            title: { text: 'Device' },
          },
          yaxis: {
            title: { text: barData.data.unit || 'Value' },
          },
        }}
        config={{ displayModeBar: false }}
      />
    </Stack>
  )
}

const RichTextComponent = ({
  component,
  setCanDrag,
  updateComponentConfig,
  isEditing,
}: {
  component: DashboardComponent & { config: RichTextConfig }
  setCanDrag: (canDrag: boolean) => void
  updateComponentConfig: (componentId: string, config: RichTextConfig) => void
  isEditing: boolean
}) => {
  const [isFocused, setIsFocused] = useState(false)

  const editor = useEditor({
    shouldRerenderOnTransaction: true,
    extensions: [StarterKit, Link],
    content: component.config.content,
    editable: isEditing,
    onUpdate: ({ editor }) => {
      const html = editor.getHTML()
      updateComponentConfig(component.component_id, {
        ...component.config,
        content: html,
      })
    },
    onFocus: () => {
      if (isEditing) {
        setIsFocused(true)
      }
    },
    onBlur: () => {
      setIsFocused(false)
    },
  })

  // Update editor content when component config changes
  useEffect(() => {
    if (editor && component.config.content !== editor.getHTML()) {
      editor.commands.setContent(component.config.content)
    }
  }, [component.config.content, editor])

  // Update editor editable state when editing mode changes
  useEffect(() => {
    if (editor) {
      editor.setEditable(isEditing)
    }
  }, [editor, isEditing])

  if (!isEditing) {
    // Read-only view when not editing
    const sanitizedContent = DOMPurify.sanitize(component.config.content, {
      ALLOWED_TAGS: [
        'p',
        'br',
        'strong',
        'em',
        'u',
        's',
        'code',
        'pre',
        'h1',
        'h2',
        'h3',
        'h4',
        'h5',
        'h6',
        'ul',
        'ol',
        'li',
        'blockquote',
        'hr',
        'a',
        'span',
        'div',
      ],
      ALLOWED_ATTR: ['href', 'target', 'rel', 'class', 'style'],
      ALLOW_DATA_ATTR: false,
    })

    return (
      <div
        dangerouslySetInnerHTML={{ __html: sanitizedContent }}
        style={{
          height: '100%',
          overflow: 'auto',
          fontSize: '14px',
          lineHeight: '1.5',
          margin: 0,
          padding: 0,
        }}
      />
    )
  }

  // Full editor when editing
  return (
    <div style={{ height: '100%', position: 'relative' }}>
      <RichTextEditor
        editor={editor}
        h="100%"
        onMouseEnter={() => setCanDrag(false)}
        onMouseLeave={() => setCanDrag(true)}
        onClick={() => {
          if (isEditing && editor) {
            editor.commands.focus()
          }
        }}
        styles={{
          toolbar: {
            position: 'absolute',
            top: '-50px',
            left: '0',
            right: '0',
            zIndex: 20,
            backgroundColor: 'var(--mantine-color-body)',
            border: '1px solid var(--mantine-color-gray-3)',
            borderRadius: 'var(--mantine-radius-md)',
            padding: '8px',
            boxShadow: 'var(--mantine-shadow-md)',
            opacity: isFocused ? 1 : 0,
            visibility: isFocused ? 'visible' : 'hidden',
            transition: 'opacity 0.2s ease, visibility 0.2s ease',
          },
          content: {
            marginTop: '0',
            padding: '8px',
            minHeight: '60px',
            cursor: 'text',
          },
        }}
      >
        <RichTextEditor.Toolbar>
          <RichTextEditor.ControlsGroup>
            <RichTextEditor.Bold />
            <RichTextEditor.Italic />
            <RichTextEditor.Strikethrough />
            <RichTextEditor.ClearFormatting />
            <RichTextEditor.Code />
          </RichTextEditor.ControlsGroup>

          <RichTextEditor.ControlsGroup>
            <RichTextEditor.H1 />
            <RichTextEditor.H2 />
            <RichTextEditor.H3 />
            <RichTextEditor.H4 />
          </RichTextEditor.ControlsGroup>

          <RichTextEditor.ControlsGroup>
            <RichTextEditor.Blockquote />
            <RichTextEditor.Hr />
            <RichTextEditor.BulletList />
            <RichTextEditor.OrderedList />
          </RichTextEditor.ControlsGroup>

          <RichTextEditor.ControlsGroup>
            <RichTextEditor.Link />
            <RichTextEditor.Unlink />
          </RichTextEditor.ControlsGroup>

          <RichTextEditor.ControlsGroup>
            <RichTextEditor.Undo />
            <RichTextEditor.Redo />
          </RichTextEditor.ControlsGroup>
        </RichTextEditor.Toolbar>

        <RichTextEditor.Content />
      </RichTextEditor>
    </div>
  )
}

// const GISComponent = ({
//   component,
//   projectId,
// }: {
//   component: DashboardComponent & { config: GISConfig }
//   projectId: string | undefined
// }) => {
//   return (
//     <Stack h="100%">
//       <Text fw={600} size="sm" mb="xs">
//         GIS Map
//       </Text>
//       <div style={{ flex: 1, position: 'relative' }}>
//         {projectId && <PlaceholderMap projectId={projectId} />}
//       </div>
//       <Text size="xs" c="dimmed">
//         Device: {component.config.deviceTypeId}
//       </Text>
//     </Stack>
//   )
// }

// Component renderer for different dashboard component types
const RenderComponent = ({
  component,
  projectId,
  defaultTimeRange,
  defaultKPITimeRange,
  timeZone,
  sensorTypes,
  setCanDrag,
  updateComponentConfig,
  isEditing,
  startQuery,
  endQuery,
}: {
  component: DashboardComponent
  projectId: string | undefined
  defaultTimeRange: number
  defaultKPITimeRange: number
  timeZone: string
  sensorTypes: UseQueryResult<SensorType[], AxiosError<unknown>>
  setCanDrag: (canDrag: boolean) => void
  updateComponentConfig: (componentId: string, config: RichTextConfig) => void
  isEditing: boolean
  startQuery: string
  endQuery: string
}) => {
  switch (component.component_type) {
    case 'gauge':
      return (
        <GaugeComponent
          component={component as DashboardComponent & { config: GaugeConfig }}
          projectId={projectId}
          defaultTimeRange={defaultTimeRange}
          timeZone={timeZone}
          startQuery={startQuery}
          endQuery={endQuery}
        />
      )
    case 'kpi':
      return (
        <KPIComponent
          component={component as DashboardComponent & { config: KPIConfig }}
          projectId={projectId}
          defaultKPITimeRange={defaultKPITimeRange}
          timeZone={timeZone}
        />
      )
    case 'line':
      return (
        <LineComponent
          component={component as DashboardComponent & { config: LineConfig }}
          projectId={projectId}
          startQuery={startQuery}
          endQuery={endQuery}
          sensorTypes={sensorTypes}
        />
      )
    case 'scatter':
      return (
        <ScatterComponent
          component={
            component as DashboardComponent & { config: ScatterConfig }
          }
          projectId={projectId}
          startQuery={startQuery}
          endQuery={endQuery}
        />
      )
    case 'bar':
      return (
        <BarComponent
          component={component as DashboardComponent & { config: BarConfig }}
          projectId={projectId}
          startQuery={startQuery}
          endQuery={endQuery}
        />
      )
    case 'rich_text':
      return (
        <RichTextComponent
          component={
            component as DashboardComponent & { config: RichTextConfig }
          }
          setCanDrag={setCanDrag}
          updateComponentConfig={updateComponentConfig}
          isEditing={isEditing}
        />
      )
    // case 'gis':
    //   return (
    //     <GISComponent
    //       component={component as DashboardComponent & { config: GISConfig }}
    //       projectId={projectId}
    //     />
    //   )
    default:
      return (
        <Stack align="center" justify="center" h="100%">
          <Text c="dimmed">Unknown component type</Text>
        </Stack>
      )
  }
}

const Page = () => {
  const { projectId, dashboardId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const colorScheme = useComputedColorScheme('dark')
  useProjectDropdownToggle()
  const project = useSelectProject(projectId!)

  // Get dashboard data when dashboardId is present
  const dashboard = useGetDashboard({
    pathParams: {
      projectId: projectId || '-1',
      dashboardId: dashboardId || '-1',
    },
    queryOptions: {
      enabled: !!dashboardId && !!projectId,
    },
  })

  const stack = useDrawersStack([
    'select-component',
    'gauge-config',
    'kpi-config',
    'gis-config',
    'bar-config',
    'line-config',
    'scatter-config',
    'rich-text-config',
  ])

  // Check if user navigated from "/new" route
  const isNewDashboard = location.pathname.endsWith('/new')

  // State for dashboard components
  const [dashboardComponents, setDashboardComponents] = useState<
    DashboardComponent[]
  >([])
  const [editing, setEditing] = useState(isNewDashboard)
  const [canDrag, setCanDrag] = useState(true)
  const [dashboardName, setDashboardName] = useState('')
  const [defaultTimeRange, setDefaultTimeRange] = useState(1)
  const [defaultKPITimeRange, setDefaultKPITimeRange] = useState(1)
  // Sample data for scatter plot preview (computed once on mount)
  const [scatterPreviewY] = useState(() =>
    Array.from({ length: 10 }, () => Math.random() * 10),
  )
  const [searchParams, setSearchParams] = useSearchParams()
  const prevDefaultTimeRangeRef = useRef(defaultTimeRange)
  const { start: startURL, end: endURL } = useValidateDateRange({
    timeZone: project.data?.time_zone || 'UTC',
  })
  const startQuery = startURL?.toISOString()
  const endQuery = endURL?.toISOString()

  // Calculate default range for AdvancedDatePicker
  const defaultRange = calculateTimeRange(defaultTimeRange)

  // Initialize the mutations
  const addUserDashboardMutation = useAddUserDashboard()
  const updateUserDashboardMutation = useUpdateUserDashboard()

  // Load dashboard data when available
  useEffect(() => {
    if (dashboard.data && !isNewDashboard) {
      const components = dashboard.data.components.map((component) => ({
        ...component,
        config:
          typeof component.config === 'string'
            ? JSON.parse(component.config)
            : component.config,
      }))

      startTransition(() => {
        setDashboardComponents(components)
        setDashboardName(dashboard.data.dashboard_name)

        if (dashboard.data.default_time_range) {
          setDefaultTimeRange(Number(dashboard.data.default_time_range))
        }

        if (dashboard.data.default_kpi_time_range) {
          setDefaultKPITimeRange(Number(dashboard.data.default_kpi_time_range))
        }
      })
    }
  }, [dashboard.data, isNewDashboard])

  // Clear URL parameters when defaultTimeRange changes to allow defaultRange to take effect
  useEffect(() => {
    if (prevDefaultTimeRangeRef.current !== defaultTimeRange) {
      prevDefaultTimeRangeRef.current = defaultTimeRange
      if (searchParams.has('start') || searchParams.has('end')) {
        const newSearchParams = new URLSearchParams(searchParams)
        newSearchParams.delete('start')
        newSearchParams.delete('end')
        setSearchParams(newSearchParams, { replace: true })
      }
    }
  }, [defaultTimeRange, searchParams, setSearchParams])

  // Helper function to get next grid position
  const getNextGridPosition = (componentType?: string) => {
    if (dashboardComponents.length === 0) {
      return {
        x: 0,
        y: 0,
        w: 3,
        h: componentType ? getComponentMinHeight(componentType) : 2,
      }
    }
    const lastComponent = dashboardComponents[dashboardComponents.length - 1]
    return {
      x: 0,
      y: lastComponent.y + lastComponent.h,
      w: 3,
      h: componentType ? getComponentMinHeight(componentType) : 2,
    }
  }
  // Hooks used inside of configs, these will not prevent page load but may prevent component load:
  // - useGetSensorTypes
  const sensorTypes = useGetSensorTypes({
    queryParams: {
      sensor_type_ids: project.data?.spec.used_sensor_type_ids,
    },
    queryOptions: {
      enabled: !!project.data?.project_id,
    },
  })
  // - useGetDeviceTypes
  // const deviceTypes = useGetDeviceTypes({
  //   queryParams: {
  //     device_type_ids: project.data?.spec.used_device_type_ids,
  //   },
  //   queryOptions: {
  //     enabled: !!project.data?.project_id,
  //   },
  // })
  // - useGetProjectKPITypes
  const kpiTypes = useGetProjectKPITypes({
    pathParams: {
      projectId: project.data?.project_id || '-1',
    },
    queryOptions: {
      enabled: !!project.data?.project_id,
    },
  })

  // Callback functions for each component type
  const addGaugeComponent = (config: GaugeConfig) => {
    const gridPos = getNextGridPosition('gauge')
    const newComponent: DashboardComponent = {
      component_id: Date.now().toString(),
      component_type: 'gauge',
      config,
      ...gridPos,
    }
    setDashboardComponents((prev) => [...prev, newComponent])
    stack.closeAll()
  }

  const addKPIComponent = (config: KPIConfig) => {
    const gridPos = getNextGridPosition()
    const newComponent: DashboardComponent = {
      component_id: Date.now().toString(),
      component_type: 'kpi',
      config,
      ...gridPos,
    }
    setDashboardComponents((prev) => [...prev, newComponent])
    stack.closeAll()
  }

  const addLineComponent = (config: LineConfig) => {
    const gridPos = getNextGridPosition()
    const newComponent: DashboardComponent = {
      component_id: Date.now().toString(),
      component_type: 'line',
      config,
      ...gridPos,
    }
    setDashboardComponents((prev) => [...prev, newComponent])
    stack.closeAll()
  }

  const addScatterComponent = (config: ScatterConfig) => {
    const gridPos = getNextGridPosition()
    const newComponent: DashboardComponent = {
      component_id: Date.now().toString(),
      component_type: 'scatter',
      config,
      ...gridPos,
    }
    setDashboardComponents((prev) => [...prev, newComponent])
    stack.closeAll()
  }

  const addBarComponent = (config: BarConfig) => {
    const gridPos = getNextGridPosition()
    const newComponent: DashboardComponent = {
      component_id: Date.now().toString(),
      component_type: 'bar',
      config,
      ...gridPos,
    }
    setDashboardComponents((prev) => [...prev, newComponent])
    stack.closeAll()
  }

  const addRichTextComponent = (config: RichTextConfig) => {
    const gridPos = getNextGridPosition('rich_text')
    const newComponent: DashboardComponent = {
      component_id: Date.now().toString(),
      component_type: 'rich_text',
      config,
      ...gridPos,
    }
    setDashboardComponents((prev) => [...prev, newComponent])
    stack.closeAll()
  }

  // const addGISComponent = (config: GISConfig) => {
  //   const gridPos = getNextGridPosition()
  //   const newComponent: DashboardComponent = {
  //     component_id: Date.now().toString(),
  //     component_type: 'gis',
  //     config,
  //     ...gridPos,
  //   }
  //   setDashboardComponents((prev) => [...prev, newComponent])
  //   stack.closeAll()
  // }

  // Grid layout change handler
  const onLayoutChange = useCallback(
    (
      layout: Array<{ i: string; x: number; y: number; w: number; h: number }>,
    ) => {
      setDashboardComponents((prevComponents) => {
        const updatedComponents = prevComponents.map((component) => {
          const layoutItem = layout.find(
            (l) => l.i === String(component.component_id),
          )
          if (layoutItem) {
            const updated = {
              ...component,
              x: layoutItem.x,
              y: layoutItem.y,
              w: layoutItem.w,
              h: layoutItem.h,
            }
            return updated
          }
          return component
        })
        return updatedComponents
      })
    },
    [],
  )

  // Remove component function
  const removeComponent = (id: string) => {
    setDashboardComponents((prev) =>
      prev.filter((component) => component.component_id !== id),
    )
  }

  // Update component config function
  const updateComponentConfig = (
    componentId: string,
    newConfig: RichTextConfig,
  ) => {
    setDashboardComponents((prev) =>
      prev.map((component) =>
        component.component_id === componentId
          ? { ...component, config: newConfig }
          : component,
      ),
    )
  }

  // Toggle editing state
  const toggleEditing = () => {
    setEditing(!editing)
  }

  // Handle save functionality
  const handleSave = async () => {
    if (isNewDashboard) {
      // If on "/new" route, create a new dashboard
      if (!dashboardName.trim()) {
        // You might want to show an error message here
        console.error('Dashboard name is required')
        return
      }

      try {
        const response = await addUserDashboardMutation.mutateAsync({
          project_id: projectId || '',
          dashboard_name: dashboardName,
          default_time_range: defaultTimeRange,
          default_kpi_time_range: defaultKPITimeRange,
          components: dashboardComponents,
        })

        // Extract dashboard_id from response
        const dashboardId = response.data.dashboard_id

        // Reset editing state after successful save
        setEditing(false)

        // Navigate to the new dashboard
        navigate(`/projects/${projectId}/custom-dash/${dashboardId}`, {
          replace: true,
        })
      } catch (error) {
        console.error('Failed to save dashboard:', error)
      }
    } else {
      // If on "/:dashboardId" route, update the existing dashboard
      if (!dashboardId) {
        console.error('Dashboard ID is required for update')
        return
      }

      try {
        const updateData = {
          project_id: projectId || '',
          dashboard_id: dashboardId,
          dashboard_name: dashboardName,
          default_time_range: defaultTimeRange,
          default_kpi_time_range: defaultKPITimeRange,
          components: dashboardComponents,
        }

        await updateUserDashboardMutation.mutateAsync(updateData)

        // Reset editing state after successful update
        setEditing(false)
      } catch (error: unknown) {
        console.error('Failed to update dashboard:', error)
        if (error && typeof error === 'object' && 'response' in error) {
          const axiosError = error as {
            response: { data: unknown; status: number; headers: unknown }
          }
          console.error('Response data:', axiosError.response.data)
          console.error('Response status:', axiosError.response.status)
          console.error('Response headers:', axiosError.response.headers)
        }
      }
    }
  }

  if (project.isLoading || (dashboardId && dashboard.isLoading)) {
    return <PageLoader />
  }
  const paperBGColor = colorScheme === 'dark' ? 'gray.8' : 'gray.1'

  return (
    <Stack h="100%" p="md">
      <Drawer.Stack>
        <Drawer
          {...stack.register('select-component')}
          position="left"
          title="Click a component to add to your dashboard."
        >
          <Stack p="sm">
            <Tooltip
              label={
                !project.data?.has_expected_energy_integration
                  ? 'Expected energy integration is required for gauge components'
                  : ''
              }
              disabled={!!project.data?.has_expected_energy_integration}
            >
              <Paper
                bg={paperBGColor}
                withBorder
                onClick={
                  project.data?.has_expected_energy_integration
                    ? () => stack.open('gauge-config')
                    : undefined
                }
                style={{
                  cursor: project.data?.has_expected_energy_integration
                    ? 'pointer'
                    : 'not-allowed',
                  opacity: project.data?.has_expected_energy_integration
                    ? 1
                    : 0.5,
                  borderColor: 'grey',
                }}
              >
                <Stack px="sm">
                  <Text size="lg" fw={700}>
                    Gauge
                  </Text>
                  <Group w="100%" align="center" justify="center">
                    <RingProgress
                      size={100}
                      thickness={4}
                      style={{ '--rp-size': '100px' } as React.CSSProperties}
                      sections={[
                        {
                          value: 99,
                          color: 'green',
                        },
                      ]}
                      label={
                        <Stack gap={0} align="center">
                          <Text size="lg" fw={700} ta="center" c={'inherit'}>
                            99%
                          </Text>
                        </Stack>
                      }
                    />
                  </Group>
                </Stack>
              </Paper>
            </Tooltip>
            <Paper
              withBorder
              bg={paperBGColor}
              onClick={() => stack.open('kpi-config')}
              style={{ cursor: 'pointer', borderColor: 'grey' }}
            >
              <Stack px="sm" py="md">
                <Text size="lg" fw={700}>
                  KPI Card
                </Text>
                <Stack align="center" gap="xs">
                  <Text size="xs" c="dimmed">
                    Average from 2024-01-01 to 2024-01-31
                  </Text>
                  <Text size="xl" fw={700} c="blue">
                    99.50%
                  </Text>
                </Stack>
              </Stack>
            </Paper>
            {/* <Paper withBorder onClick={() => stack.open('gis-config')}>
              <Stack px="sm">
                <Text size="lg" fw={700}>
                  GIS Map
                </Text>
                <Group w="100%" h="20vh" align="center" justify="center">
                  {projectId && <PlaceholderMap projectId={projectId} />}
                </Group>
              </Stack>
            </Paper> */}
            <Paper
              bg={paperBGColor}
              withBorder
              onClick={() => stack.open('bar-config')}
              style={{ cursor: 'pointer', borderColor: 'grey' }}
            >
              <Stack px="sm">
                <Text size="lg" fw={700}>
                  Bar Chart
                </Text>
                <Group w="100%" h="20vh" align="center" justify="center">
                  <PlotlyPlot
                    data={[
                      {
                        x: ['2021-01-01', '2021-01-02', '2021-01-03'],
                        y: [1, 3, 2],
                        type: 'bar',
                      },
                    ]}
                    layout={{}}
                    config={{ displayModeBar: false }}
                  />
                </Group>
              </Stack>
            </Paper>
            <Paper
              bg={paperBGColor}
              withBorder
              onClick={() => stack.open('line-config')}
              style={{ cursor: 'pointer', borderColor: 'grey' }}
            >
              <Stack px="sm">
                <Text size="lg" fw={700}>
                  Line Chart
                </Text>
                <Group w="100%" h="20vh" align="center" justify="center">
                  <PlotlyPlot
                    data={[
                      {
                        x: Array.from({ length: 314 }, (_, i) => i / 10),
                        y: Array.from({ length: 314 }, (_, i) =>
                          Math.sin(i / 10),
                        ),
                        type: 'line' as PlotType,
                      },
                      {
                        x: Array.from({ length: 314 }, (_, i) => i / 10),
                        y: Array.from(
                          { length: 314 },
                          (_, i) => i / 100 - 314 / 100 / 2,
                        ),
                        type: 'line' as PlotType,
                      },
                    ]}
                    layout={{ showlegend: false }}
                    config={{ displayModeBar: false }}
                  />
                </Group>
              </Stack>
            </Paper>
            <Paper
              bg={paperBGColor}
              withBorder
              onClick={() => stack.open('scatter-config')}
              style={{ cursor: 'pointer', borderColor: 'grey' }}
            >
              <Stack px="sm">
                <Text size="lg" fw={700}>
                  Scatter Plot
                </Text>
                <Group w="100%" h="20vh" align="center" justify="center">
                  <PlotlyPlot
                    data={[
                      {
                        x: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                        y: scatterPreviewY,
                        type: 'scatter' as PlotType,
                        mode: 'markers' as const,
                      },
                    ]}
                    layout={{ showlegend: false }}
                    config={{ displayModeBar: false }}
                  />
                </Group>
              </Stack>
            </Paper>
            <Paper
              bg={paperBGColor}
              withBorder
              onClick={() => stack.open('rich-text-config')}
              style={{ cursor: 'pointer', borderColor: 'grey' }}
            >
              <Stack px="sm" py="md">
                <Text size="lg" fw={700}>
                  Rich Text
                </Text>
                <Group w="100%" h="20vh" align="center" justify="center">
                  <Stack align="center" gap="xs">
                    <Text size="sm" c="dimmed">
                      Add formatted text, links, and other content
                    </Text>
                    <Text size="xs" c="dimmed">
                      Bold, italic, headings, lists, and more
                    </Text>
                  </Stack>
                </Group>
              </Stack>
            </Paper>
          </Stack>
        </Drawer>
        <Drawer {...stack.register('gauge-config')} position="left">
          <GaugeConfigComp stack={stack} onAdd={addGaugeComponent} />
        </Drawer>
        <Drawer {...stack.register('kpi-config')} position="left">
          <KPIConfigComp
            stack={stack}
            kpiTypes={kpiTypes}
            onAdd={addKPIComponent}
          />
        </Drawer>
        {/* <Drawer {...stack.register('gis-config')} position="left">
          <GISConfig stack={stack} onAdd={addGISComponent} />
        </Drawer> */}
        <Drawer {...stack.register('bar-config')} position="left">
          <BarConfigComp
            stack={stack}
            sensorTypes={sensorTypes}
            onAdd={addBarComponent}
          />
        </Drawer>
        <Drawer size="lg" {...stack.register('line-config')} position="left">
          <LineConfigComp
            stack={stack}
            sensorTypes={sensorTypes}
            onAdd={addLineComponent}
          />
        </Drawer>
        <Drawer {...stack.register('scatter-config')} position="left">
          <ScatterConfigComp
            stack={stack}
            sensorTypes={sensorTypes}
            onAdd={addScatterComponent}
          />
        </Drawer>
        <Drawer {...stack.register('rich-text-config')} position="left">
          <RichTextConfigComp stack={stack} onAdd={addRichTextComponent} />
        </Drawer>
      </Drawer.Stack>
      <Group justify="space-between" align="center">
        {editing ? (
          <Group>
            <TextInput
              placeholder="Enter dashboard name"
              label="Dashboard Name"
              value={dashboardName}
              onChange={(event) => setDashboardName(event.currentTarget.value)}
              size="lg"
              style={{ minWidth: 300 }}
            />
            <Select
              size="lg"
              placeholder="Select time range..."
              label="Default Time Range"
              data={Object.entries(defaultTimeRanges).map(([key, value]) => ({
                label: key,
                value: value.toString(),
              }))}
              onChange={(value) => setDefaultTimeRange(Number(value))}
              value={defaultTimeRange.toString()}
            />
            <Select
              size="lg"
              placeholder="Select KPI time range..."
              label="KPI Time Range"
              data={Object.entries(defaultKPITimeRanges).map(
                ([key, value]) => ({
                  label: key,
                  value: value.toString(),
                }),
              )}
              onChange={(value) => setDefaultKPITimeRange(Number(value))}
              value={defaultKPITimeRange.toString()}
            />
            {/* Invisible AdvancedDatePicker to handle default range updates in editing mode */}
            <div style={{ display: 'none' }}>
              <AdvancedDatePicker
                key={`date-picker-${defaultTimeRange}`}
                includeTodayInDateRange={true}
                defaultRange={defaultRange}
                maxDays={3}
              />
            </div>
          </Group>
        ) : (
          <Group>
            <Title>{dashboardName || 'Custom Dashboard'}</Title>
            <AdvancedDatePicker
              key={`date-picker-${defaultTimeRange}`}
              includeTodayInDateRange={true}
              defaultRange={defaultRange}
              maxDays={3}
              includeClearButton={false}
              disableQuickActions={true}
            />
          </Group>
        )}
        <Group justify="flex-end" align="center" gap="md">
          {editing && (
            <Button
              variant="outline"
              color="gray"
              onClick={() => {
                setEditing(false)
                // Reset to original dashboard data if available
                if (dashboard.data && !isNewDashboard) {
                  const components = dashboard.data.components.map(
                    (component) => ({
                      ...component,
                      config:
                        typeof component.config === 'string'
                          ? JSON.parse(component.config)
                          : component.config,
                    }),
                  )
                  setDashboardComponents(components)
                  setDashboardName(dashboard.data.dashboard_name)
                  if (dashboard.data.default_time_range) {
                    setDefaultTimeRange(
                      Number(dashboard.data.default_time_range),
                    )
                  }
                  if (dashboard.data.default_kpi_time_range) {
                    setDefaultKPITimeRange(
                      Number(dashboard.data.default_kpi_time_range),
                    )
                  }
                }
              }}
            >
              Exit Without Saving
            </Button>
          )}
          <Tooltip
            label={
              editing && !dashboardName.trim()
                ? 'Dashboard name is required'
                : ''
            }
            disabled={!editing || dashboardName.trim() !== ''}
          >
            <Button
              variant={editing ? 'filled' : 'outline'}
              onClick={editing ? handleSave : toggleEditing}
              disabled={editing && !dashboardName.trim()}
              loading={
                addUserDashboardMutation.isPending ||
                updateUserDashboardMutation.isPending
              }
            >
              {editing ? 'Save Layout' : 'Edit Layout'}
            </Button>
          </Tooltip>
          {editing && (
            <Button
              variant="default"
              onClick={() => stack.open('select-component')}
            >
              Add Component
            </Button>
          )}
        </Group>
      </Group>

      {/* Drag and Drop Grid Layout */}
      {dashboardComponents.length > 0 ? (
        <ResponsiveGridLayout
          className="layout"
          cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
          rowHeight={60}
          isDraggable={editing && canDrag}
          isResizable={editing}
          onLayoutChange={onLayoutChange}
          margin={[12.8, 12.8]}
          containerPadding={[0, 0]}
          snapToGrid={true}
          preventCollision={false}
          compactType="vertical"
        >
          {dashboardComponents.map((component) => (
            <div
              key={component.component_id}
              data-grid={{
                x: component.x,
                y: component.y,
                w: component.w,
                h: component.h,
                minW: 2,
                minH: getComponentMinHeight(component.component_type),
                maxW: 12,
                maxH: 8,
              }}
            >
              {component.component_type === 'rich_text' ? (
                <div
                  style={{
                    position: 'relative',
                    height: '100%',
                    width: '100%',
                    padding: editing ? '4px' : '4px',
                    margin: '0',
                    border: editing
                      ? '2px solid var(--mantine-color-blue-6)'
                      : 'none',
                    borderRadius: editing ? 'var(--mantine-radius-md)' : '0',
                    backgroundColor: 'transparent',
                    overflow: editing ? 'visible' : 'hidden',
                    minHeight: editing ? '60px' : 'auto',
                  }}
                >
                  {editing && (
                    <ActionIcon
                      size="sm"
                      variant="subtle"
                      color="red"
                      onClick={() => removeComponent(component.component_id)}
                      style={{
                        position: 'absolute',
                        top: 4,
                        right: 4,
                        zIndex: 10,
                      }}
                      onMouseEnter={() => setCanDrag(false)}
                      onMouseLeave={() => setCanDrag(true)}
                    >
                      <IconTrash size={14} />
                    </ActionIcon>
                  )}
                  <RenderComponent
                    component={component}
                    projectId={projectId}
                    defaultTimeRange={defaultTimeRange}
                    defaultKPITimeRange={defaultKPITimeRange}
                    timeZone={project.data?.time_zone || 'UTC'}
                    sensorTypes={sensorTypes}
                    setCanDrag={setCanDrag}
                    updateComponentConfig={updateComponentConfig}
                    isEditing={editing}
                    startQuery={startQuery || ''}
                    endQuery={endQuery || ''}
                  />
                </div>
              ) : (
                <Paper
                  p="xs"
                  withBorder
                  h="100%"
                  w="100%"
                  style={{
                    position: 'relative',
                    backgroundColor: 'var(--mantine-color-body)',
                    border: editing
                      ? '2px solid var(--mantine-color-blue-6)'
                      : undefined,
                    borderRadius: 'var(--mantine-radius-md)',
                  }}
                >
                  {editing && (
                    <ActionIcon
                      size="sm"
                      variant="subtle"
                      color="red"
                      onClick={() => removeComponent(component.component_id)}
                      style={{
                        position: 'absolute',
                        top: 8,
                        right: 8,
                        zIndex: 10,
                      }}
                      onMouseEnter={() => setCanDrag(false)}
                      onMouseLeave={() => setCanDrag(true)}
                    >
                      <IconTrash size={14} />
                    </ActionIcon>
                  )}
                  <RenderComponent
                    component={component}
                    projectId={projectId}
                    defaultTimeRange={defaultTimeRange}
                    defaultKPITimeRange={defaultKPITimeRange}
                    timeZone={project.data?.time_zone || 'UTC'}
                    sensorTypes={sensorTypes}
                    setCanDrag={setCanDrag}
                    updateComponentConfig={updateComponentConfig}
                    isEditing={editing}
                    startQuery={startQuery || ''}
                    endQuery={endQuery || ''}
                  />
                </Paper>
              )}
            </div>
          ))}
        </ResponsiveGridLayout>
      ) : (
        <Paper
          p="xl"
          withBorder
          style={{
            textAlign: 'center',
            border:
              colorScheme === 'dark'
                ? '2px dashed var(--mantine-color-gray-7)'
                : '2px dashed var(--mantine-color-gray-4)',
          }}
          bg={colorScheme === 'dark' ? 'gray.9' : 'gray.0'}
          c="dimmed"
          radius="md"
        >
          <Stack align="center" gap="md">
            <Text size="lg" c="dimmed">
              No dashboard components yet
            </Text>
            <Text size="sm" c="dimmed">
              Click &quot;Edit Layout&quot; and then &quot;Add Component&quot;
              to create your first dashboard component
            </Text>
          </Stack>
        </Paper>
      )}
    </Stack>
  )
}

export default Page
