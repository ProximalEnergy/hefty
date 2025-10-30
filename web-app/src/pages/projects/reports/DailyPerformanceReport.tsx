import type { DailyPerformanceStats } from '@/api/v1/ai/daily_performance_summary'
import type { OperationalKPIData } from '@/api/v1/operational/kpi_data'
import { useGetOperationalKPIData } from '@/api/v1/operational/kpi_data'
import { useGetEventsSummary } from '@/api/v1/operational/project/events'
import { useGetTimeSeries } from '@/api/v1/operational/project/project_data'
import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import {
  useGetPVBudgetedData,
  useGetPVBudgetedDataBySeries,
  useGetPVBudgetedSeries,
  useGetPVBudgetedSeriesDailyData,
} from '@/api/v1/operational/pv_budgeted_data'
import { useGetMeterPowerAndExpectedPower } from '@/api/v1/protected/pv-expected-energy/plot/plot'
import AICard from '@/components/AICard'
import CustomCard from '@/components/CustomCard'
import { ColorBar, MapSettings } from '@/components/GIS'
import { PageLoader } from '@/components/Loading'
import Attribution from '@/components/gis/Attribution'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { GISContext } from '@/contexts/GISContext'
import { useGetDevicesV2 } from '@/hooks/api'
import { useProjectFilter } from '@/hooks/custom'
import type { Device, EventSummary } from '@/hooks/types'
import * as gisUtils from '@/utils/GIS'
import {
  ActionIcon,
  Box,
  Button,
  Card,
  Group,
  Modal,
  NumberInput,
  Paper,
  SegmentedControl,
  Select,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  Title,
  Tooltip,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { DatePickerInput } from '@mantine/dates'
import {
  IconBolt,
  IconCash,
  IconChartBar,
  IconCurrencyDollar,
  IconExclamationCircle,
  IconFileTypePdf,
  IconSun,
} from '@tabler/icons-react'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { FeatureCollection } from 'geojson'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import React, {
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from 'react'
import type { MapMouseEvent } from 'react-map-gl/mapbox'
import Map, { Layer, Source } from 'react-map-gl/mapbox'
import { Link, useParams } from 'react-router'

import { HoverInfo } from '../gis/utils'

dayjs.extend(utc)
dayjs.extend(timezone)

// Daily Energy Comparison Component - Power Plot Style
const DailyEnergyComparison = ({
  selectedDate,
  projectId,
  degradationRate,
  budgetedDataQuery,
}: {
  selectedDate: Date | null
  projectId: string | undefined
  degradationRate: number
  budgetedDataQuery: ReturnType<typeof useGetPVBudgetedData>
}) => {
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme('light')

  // Get project data
  const project = useSelectProject(projectId!)
  if (!project.data) return null

  // Calculate start and end times for the selected date in project timezone
  const startTime =
    selectedDate && project.data?.time_zone
      ? dayjs(selectedDate)
          .tz(project.data.time_zone)
          .startOf('day')
          .toISOString()
      : null
  const endTime =
    selectedDate && project.data?.time_zone
      ? dayjs(selectedDate)
          .tz(project.data.time_zone)
          .endOf('day')
          .toISOString()
      : null

  // TODO: Remove this in favor of a new database table.
  const includeSoiling = !['sigurd'].includes(project.data?.name_short || '')
  const includeDegradation = ['sigurd'].includes(project.data?.name_short || '')

  // Use the same hook as PowerPlotPVZoom for power data
  const powerData = useGetMeterPowerAndExpectedPower({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: startTime || '',
      end: endTime || '',
      interval: '15min', // 15-minute intervals for daily view
      include_storage: project.data?.project_type_id === ProjectTypeId.PV_BESS,
      include_setpoint: true,
      include_soiling: includeSoiling,
      include_degradation: includeDegradation,
    },
    queryOptions: {
      enabled: !!projectId && !!startTime && !!endTime,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 60 * 1000, // 1 minute
      gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days
    },
  })

  // Color map similar to PowerPlotPVZoom
  const colorMap: Record<string, string> = {
    'Meter Active Power': theme.colors.green[7],
    'Power Expected at Full Health': theme.colors.orange[7],
    'PPC Active Power Setpoint': theme.colors.blue[7],
    'PV Active Power': theme.colors.cyan[7],
    'BESS Active Power': theme.colors.yellow[7],
    'Interconnection Limit': theme.colors.gray[7],
    'Budgeted Average (+-15 days)': theme.colors.violet[7],
  }

  // Calculate average hourly budgeted output from ±15 days
  const averageBudgetedHourly = useMemo(() => {
    if (
      !budgetedDataQuery.data ||
      budgetedDataQuery.data.length === 0 ||
      !project.data?.time_zone
    ) {
      return null
    }

    // Group by hour of day (0-23) and calculate average for each hour
    const hourlyAverages: Record<number, number[]> = {}

    budgetedDataQuery.data.forEach((dataPoint) => {
      const timestamp = dayjs.utc(dataPoint.time).tz(project.data?.time_zone)
      const hour = timestamp.hour()

      if (!hourlyAverages[hour]) {
        hourlyAverages[hour] = []
      }

      // Apply degradation if COD is available
      let degradedPower = dataPoint.poi_ac_power
      if (project.data?.cod) {
        const codDate = dayjs(project.data.cod)
        const yearsSinceCOD = timestamp.diff(codDate, 'year', true) // true for decimal years
        const degradationFactor = 1 - (degradationRate / 100) * yearsSinceCOD
        degradedPower = dataPoint.poi_ac_power * Math.max(0, degradationFactor) // Ensure non-negative
      }

      hourlyAverages[hour].push(degradedPower)
    })

    // Calculate average for each hour
    const result: Record<number, number> = {}
    Object.keys(hourlyAverages).forEach((hour) => {
      const hourNum = parseInt(hour)
      const values = hourlyAverages[hourNum]
      result[hourNum] =
        values.reduce((sum, val) => sum + val, 0) / values.length
    })
    return result
  }, [budgetedDataQuery.data, project.data, degradationRate])

  // Process plot data similar to PowerPlotPVZoom
  const plotData = useMemo(() => {
    if (!powerData.data?.data) return []

    return powerData.data.data.map((d: any) => {
      const numericY = d.y.map((val: number | null) =>
        val === null ? null : parseFloat(String(val)),
      )

      // Transform name if it's "Expected Power" from backend
      const displayName =
        d.name === 'Expected Power' ? 'Power Expected at Full Health' : d.name

      // Convert timestamps to project timezone for display
      const convertedTimestamps = d.x.map((timestamp: string) => {
        return dayjs
          .utc(timestamp)
          .tz(project.data?.time_zone || 'UTC')
          .format()
      })

      // Determine mode and fill based on trace name
      const isMeterPower = displayName === 'Meter Active Power'
      const isSetpoint = displayName === 'PPC Active Power Setpoint'
      const isExpectedPower = displayName === 'Power Expected at Full Health'
      const mode: 'lines' | 'lines+markers' =
        isMeterPower || isSetpoint || isExpectedPower
          ? 'lines'
          : 'lines+markers'
      const fill: 'tozeroy' | 'none' = isMeterPower ? 'tozeroy' : 'none'

      return {
        x: convertedTimestamps,
        y: numericY,
        name: displayName,
        type: 'scatter' as const,
        mode: mode,
        connectgaps: isExpectedPower ? false : true,
        hoverlabel: {
          namelength: -1,
        },
        fill: fill,
        line: {
          color:
            colorMap[displayName as keyof typeof colorMap] ||
            theme.colors.gray[7],
          width: 2,
        },
        marker: {
          size: mode.includes('markers') ? 4 : 0,
          opacity: isSetpoint ? 0 : 1,
        },
        visible: true,
      }
    })
  }, [powerData.data, colorMap, theme])

  // Add interconnection limit and budgeted series if available
  const finalPlotData = useMemo(() => {
    let finalData = [...plotData]

    // Add interconnection limit if available
    if (
      plotData.length > 0 &&
      project.data?.poi &&
      powerData.data?.data &&
      powerData.data.data.length > 0
    ) {
      // Convert timestamps for interconnection limit
      const limitTimestamps = powerData.data.data[0].x.map(
        (timestamp: string) => {
          return dayjs
            .utc(timestamp)
            .tz(project.data?.time_zone || 'UTC')
            .format()
        },
      )

      finalData.push({
        x: limitTimestamps,
        y: Array(limitTimestamps.length).fill(project.data.poi),
        name: 'Interconnection Limit',
        type: 'scatter' as const,
        mode: 'lines' as const,
        connectgaps: true,
        fill: 'none' as const,
        line: {
          color: colorMap['Interconnection Limit'],
          width: 2,
          dash: 'dash',
        } as any,
        marker: {
          size: 0,
          opacity: 1,
        },
        hoverlabel: {
          namelength: -1,
        },
        visible: true,
      })
    }

    // Add budgeted series average if available
    if (
      averageBudgetedHourly &&
      powerData.data?.data &&
      powerData.data.data.length > 0
    ) {
      const budgetedTimestamps: string[] = []
      const budgetedY: number[] = []

      // Create hourly data points (one per hour) in project timezone
      // Budgeted data is hour ending, so shift by 30 minutes to center the data
      for (let hour = 0; hour < 24; hour++) {
        const timestamp = dayjs(selectedDate)
          .tz(project.data?.time_zone || 'UTC')
          .hour(hour)
          .minute(30)
          .second(0)
          .utc()
          .tz(project.data?.time_zone || 'UTC')
          .format()

        budgetedTimestamps.push(timestamp)
        // Use current hour's data directly (no shift)
        budgetedY.push(averageBudgetedHourly[hour] || 0)
      }

      finalData.push({
        x: budgetedTimestamps,
        y: budgetedY,
        name: 'Budgeted Average (+-15 days)',
        type: 'scatter' as const,
        mode: 'lines' as const,
        connectgaps: true,
        fill: 'none' as const,
        line: {
          color: colorMap['Budgeted Average (+-15 days)'],
          width: 2,
          dash: 'dot',
        } as any,
        marker: {
          size: 0,
          opacity: 1,
        },
        hoverlabel: {
          namelength: -1,
        },
        visible: true,
      })
    }

    return finalData
  }, [plotData, project.data, powerData.data, colorMap, averageBudgetedHourly])

  if (!selectedDate) {
    return (
      <Text c="dimmed" ta="center" py="xl">
        Please select a date to view daily power comparison
      </Text>
    )
  }

  if (powerData.isLoading || project.isLoading || budgetedDataQuery.isLoading) {
    return (
      <Text ta="center" py="xl">
        Loading...
      </Text>
    )
  }

  return (
    <PlotlyPlot
      data={finalPlotData}
      layout={{
        yaxis: {
          title: { text: 'Power (MW)' },
          fixedrange: true,
          range:
            project.data?.project_type_id === ProjectTypeId.PV_BESS
              ? undefined
              : [0, (project.data?.poi || 0) * 1.05],
        },
        xaxis: {
          type: 'date',
          fixedrange: false,
          tickangle: 0,
          range:
            selectedDate && project.data?.time_zone
              ? [
                  dayjs
                    .tz(selectedDate, project.data.time_zone)
                    .startOf('day')
                    .valueOf(),
                  dayjs
                    .tz(selectedDate, project.data.time_zone)
                    .endOf('day')
                    .valueOf(),
                ]
              : undefined,
        },
        showlegend: true,
        legend: {
          xref: 'paper',
          yref: 'paper',
          x: 0.01,
          y: 0.99,
          xanchor: 'left',
          yanchor: 'top',
          orientation: 'v',
          bgcolor:
            colorScheme === 'dark'
              ? 'rgba(37,38,43,0.8)'
              : 'rgba(255,255,255,0.8)',
          bordercolor:
            colorScheme === 'dark'
              ? 'rgba(255,255,255,0.2)'
              : 'rgba(0,0,0,0.2)',
          borderwidth: 1,
          itemsizing: 'constant',
        },
        margin: { l: 60, r: 30, t: 30, b: 60 },
      }}
      isLoading={powerData.isLoading || project.isLoading}
      error={powerData.error}
      config={{ responsive: true, scrollZoom: true }}
    />
  )
}

// MapCard component from ProjectKPITemplate
const MapCard = ({
  data,
  kpiType,
  cardTitle,
  devices,
  isLoading,
  isError,
  onMapIdle,
}: {
  data: OperationalKPIData | undefined
  kpiType: any
  cardTitle: string
  devices: Device[]
  isLoading: boolean
  isError: boolean
  onMapIdle?: (isIdle: boolean) => void
}) => {
  const context = useContext(GISContext)
  const computedColorScheme = useComputedColorScheme('dark')
  const [hoverInfo, setHoverInfo] = useState<HoverInfo>({
    feature: null,
    x: 0,
    y: 0,
  })
  const blankMapStyle = gisUtils.useBlankMapStyle()

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

  if (isLoading) {
    return (
      <CustomCard title={cardTitle} style={{ height: '50vh' }} fill={true}>
        <Text c="dimmed">Loading...</Text>
      </CustomCard>
    )
  }

  if (isError) {
    return (
      <CustomCard title={cardTitle} style={{ height: '50vh' }} fill={true}>
        <Text c="dimmed">Error loading data</Text>
      </CustomCard>
    )
  }

  if (!devices || devices.length === 0) {
    return (
      <CustomCard title={cardTitle} style={{ height: '50vh' }} fill={true}>
        <Text c="dimmed">No combiner devices found</Text>
      </CustomCard>
    )
  }

  // If no KPI data but we have devices, show them with default values
  if (!data) {
  }

  if (!context) {
    throw new Error('GISContext is not provided')
  }

  const { showLabels, showSatellite, colorsGoodBad } = context

  const device_values = data?.data.device_data_obj?.device_values
  let aggregation: {
    [k: string]: number
  } = {}

  if (device_values && Object.keys(device_values).length > 0) {
    if (kpiType.aggregation_method === 'average') {
      aggregation = Object.fromEntries(
        Object.entries(device_values).map(([key, arr]) => {
          // Filter out null or undefined entries
          const validValues = arr.filter((val) => val != null)
          // Compute average
          const average =
            validValues.reduce((sum, val) => sum + val, 0) /
              validValues.length || 0
          return [key, average]
        }),
      )
    } else if (kpiType.aggregation_method === 'sum') {
      aggregation = Object.fromEntries(
        Object.entries(device_values).map(([key, arr]) => {
          return [
            key,
            arr.reduce((acc, val) => (acc ?? 0) + (val ?? 0), 0) || 0,
          ]
        }),
      )
    }
  } else {
    // No KPI data available, assign default values to all devices
    aggregation = Object.fromEntries(
      devices.map((device) => [device.device_id.toString(), 0.5]), // Default 50% health
    )
  }

  const gisData: FeatureCollection = {
    type: 'FeatureCollection',
    features:
      devices
        ?.map((device) => {
          return {
            type: 'Feature',
            properties: {
              name: device.name_long,
              value: aggregation[device.device_id] || 0,
            },
            geometry:
              typeof device.polygon === 'string'
                ? JSON.parse(device.polygon)
                : device.polygon,
          }
        })
        .filter((feature) => feature.geometry && feature.geometry.type) || [],
  } as FeatureCollection

  // If no valid features, show alternative view
  if (gisData.features.length === 0) {
    return (
      <CustomCard title={cardTitle} style={{ height: '50vh' }} fill={true}>
        <Stack align="center" justify="center" h="100%">
          <Text c="dimmed" size="lg" ta="center">
            No combiner devices with location data available
          </Text>
          <Text c="dimmed" size="sm" ta="center" mt="xs">
            {devices?.length || 0} combiner devices found, but none have
            geographic coordinates for mapping
          </Text>
        </Stack>
      </CustomCard>
    )
  }

  const mapStyleEmpty = false

  const values = Object.values(aggregation || {})
  const numberValues = values.flat().filter((v): v is number => v != null)

  let lowValue: number
  let highValue: number
  let lowLabel: string
  let highLabel: string
  switch (kpiType.unit) {
    case '%':
      lowValue = 0
      highValue = 1
      lowLabel = '0%'
      highLabel = '100%'
      break
    default:
      lowValue = Math.min(0, ...numberValues)
      highValue = Math.max(...numberValues)
      // Handle case where all values are null (Math.max([]) returns -Infinity)
      if (!isFinite(highValue)) {
        lowValue = 0
        highValue = 1
      }
      lowLabel = `${lowValue.toFixed(2)} ${kpiType.unit}`
      highLabel = `${highValue.toFixed(2)} ${kpiType.unit}`
  }

  const colors = colorsGoodBad

  return (
    <CustomCard
      title={cardTitle}
      style={{ height: '50vh' }}
      fill
      info="Map data is aggregated over the requested interval."
    >
      <div
        style={{
          position: 'relative',
          height: '100%',
          width: '100%',
        }}
      >
        <div style={{ height: '100%', width: '100%' }}>
          <>
            <Map
              key="map"
              preserveDrawingBuffer
              onIdle={() => onMapIdle?.(true)}
              initialViewState={{
                bounds: gisUtils.findBoundingBox(gisData),
                fitBoundsOptions: {
                  padding: {
                    top: 25,
                    bottom: 25,
                    left: 65,
                    right: 65,
                  },
                },
              }}
              style={{
                borderBottomLeftRadius: 'inherit',
                borderBottomRightRadius: 'inherit',
              }}
              mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
              interactiveLayerIds={['data']}
              onMouseMove={onHover}
              mapStyle={
                gisUtils.mapStyle({
                  empty: mapStyleEmpty,
                  satellite: showSatellite,
                  theme: computedColorScheme,
                }) ?? blankMapStyle
              }
            >
              <Source id="data" type="geojson" data={gisData}>
                <Layer
                  {...gisUtils.layerData({
                    featureKey: 'value',
                    colors: colors,
                    lowValue: lowValue,
                    highValue: highValue,
                  })}
                />
                <Layer {...gisUtils.layerNonComm({ featureKey: 'value' })} />
                {showLabels && (
                  <Layer {...gisUtils.layerLabel({ textField: 'name' })} />
                )}
              </Source>
              {hoverInfo.feature && (
                <MapHoverCard hoverInfo={hoverInfo} kpiType={kpiType} />
              )}
            </Map>
            <Box
              style={{
                position: 'absolute',
                top: 0,
                right: 0,
                zIndex: 1,
                height: '100%',
              }}
              px="md"
              py={75}
            >
              <ColorBar
                gradient={gisUtils.colorBar({ colors: colors })}
                lowLabel={lowLabel}
                highLabel={highLabel}
              />
            </Box>
          </>
        </div>
        <Box
          style={{ position: 'absolute', bottom: 0, left: 0, zIndex: 10 }}
          px="md"
          py="md"
        >
          <MapSettings disableSatellite={mapStyleEmpty} />
        </Box>
        <Attribution />
      </div>
    </CustomCard>
  )
}

function MapHoverCard({
  hoverInfo,
  kpiType,
}: {
  hoverInfo: HoverInfo
  kpiType: any
}) {
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
    >
      <Text fw={700}>{hoverInfo.feature?.properties?.name}</Text>
      <Text>
        {hoverInfo.feature?.properties?.value != null
          ? kpiType.unit === '%'
            ? `${(hoverInfo.feature.properties.value * 100).toFixed(2)}%`
            : `${hoverInfo.feature.properties.value.toFixed(2)} ${kpiType.unit}`
          : 'No Data'}
      </Text>
    </Paper>
  )
}

const Page: React.FC = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeId.PV, ProjectTypeId.PV_BESS],
  })

  const { projectId } = useParams<{ projectId: string }>()
  const reportRef = useRef<HTMLDivElement>(null)
  const [isPdfLoading, setIsPdfLoading] = useState(false)
  const [isMapIdle, setIsMapIdle] = useState(false)
  const [pdfExportRequested, setPdfExportRequested] = useState(false)

  const handleExportPdf = () => {
    if (!reportRef.current) return
    setIsPdfLoading(true)
    setPdfExportRequested(true)
  }

  React.useEffect(() => {
    if (isMapIdle && pdfExportRequested) {
      if (!reportRef.current) return

      html2canvas(reportRef.current, {
        scale: 2, // Higher scale for better quality
        useCORS: true,
      }).then((canvas) => {
        const imgData = canvas.toDataURL('image/png')
        const pdf = new jsPDF({
          orientation: 'landscape',
          unit: 'px',
          format: [canvas.width, canvas.height],
        })
        pdf.addImage(imgData, 'PNG', 0, 0, canvas.width, canvas.height)
        pdf.save('daily-performance-report.pdf')
        setIsPdfLoading(false)
        setPdfExportRequested(false)
        setIsMapIdle(false) // Reset for next export
      })
    }
  }, [isMapIdle, pdfExportRequested])

  const project = useSelectProject(projectId!)

  const colorScheme = useComputedColorScheme('light')

  // Single date selector
  const [selectedDate, setSelectedDate] = useState<Date | null>(() => {
    const projectTz = project.data?.time_zone || 'UTC'
    return dayjs().tz(projectTz).subtract(1, 'day').toDate()
  })

  // Toggle for cumulative vs daily in the 30-day chart
  const [energyView, setEnergyView] = useState<'cumulative' | 'daily'>(
    'cumulative',
  )

  // Trailing period selection for the energy chart
  const [trailingPeriod, setTrailingPeriod] = useState<number>(30)

  // Selected budgeted series
  const [selectedSeriesId, setSelectedSeriesId] = useState<string | null>(null)

  // Degradation rate (default 0.5% per year)
  const [degradationRate, setDegradationRate] = useState<number>(0.5)
  const [customRateModalOpen, setCustomRateModalOpen] = useState(false)
  const [customRate, setCustomRate] = useState<number | string>(degradationRate)

  const presetDegradationRates = [
    { value: '0', label: '0.0%/yr' },
    { value: '0.25', label: '0.25%/yr' },
    { value: '0.5', label: '0.5%/yr' },
    { value: '0.75', label: '0.75%/yr' },
    { value: '1.0', label: '1.0%/yr' },
    { value: '1.5', label: '1.5%/yr' },
    { value: '2.0', label: '2.0%/yr' },
  ]

  const degradationRateOptions = useMemo(() => {
    const isCustom = !presetDegradationRates.some(
      (option) => parseFloat(option.value) === degradationRate,
    )

    const customOptionLabel = isCustom
      ? `Custom (${degradationRate.toFixed(2)}%/yr)...`
      : 'Custom...'

    return [
      ...presetDegradationRates,
      { value: 'custom', label: customOptionLabel },
    ]
  }, [degradationRate])

  const selectedPresetRateValue =
    presetDegradationRates.find(
      (option) => parseFloat(option.value) === degradationRate,
    )?.value ?? 'custom'

  const { startTime, endTime, selectedDateStr } = useMemo(() => {
    if (!selectedDate || !project.data?.time_zone) {
      return { startTime: null, endTime: null, selectedDateStr: null }
    }
    const projectTz = project.data.time_zone
    const startOfDay = dayjs(selectedDate).tz(projectTz).startOf('day')
    return {
      startTime: startOfDay.toISOString(),
      endTime: startOfDay.endOf('day').toISOString(),
      selectedDateStr: startOfDay.format('YYYY-MM-DD'),
    }
  }, [selectedDate, project.data?.time_zone])

  // Fetch available budgeted series for the project (load once only)
  const budgetedSeriesQuery = useGetPVBudgetedSeries({
    queryParams: {
      project_id: projectId || '',
    },
    queryOptions: {
      enabled: !!projectId,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: Infinity, // Never consider data stale
      gcTime: Infinity, // Keep in cache forever
    },
  })

  // Auto-select the first series when data is loaded
  React.useEffect(() => {
    if (
      budgetedSeriesQuery.data &&
      budgetedSeriesQuery.data.length > 0 &&
      !selectedSeriesId
    ) {
      setSelectedSeriesId(
        budgetedSeriesQuery.data[0].pv_budgeted_series_id.toString(),
      )
    }
  }, [budgetedSeriesQuery.data, selectedSeriesId])

  // Prevent unnecessary refetches when series selection changes
  const stableSelectedSeriesId = React.useMemo(() => {
    return selectedSeriesId
  }, [selectedSeriesId])

  // Calculate trailing period range ending on selected date
  const trailingStart = selectedDate
    ? dayjs(selectedDate)
        .subtract(trailingPeriod - 1, 'days')
        .format('YYYY-MM-DD')
    : null
  const trailingEnd = selectedDate
    ? dayjs(selectedDate).add(1, 'day').format('YYYY-MM-DD')
    : null

  // Calculate range for budgeted data (±1 day around selected date = 3 days total)
  const budgetedStartDate = selectedDate
    ? dayjs(selectedDate).subtract(15, 'days').format('YYYY-MM-DD')
    : null
  const budgetedEndDate = selectedDate
    ? dayjs(selectedDate).add(15, 'days').format('YYYY-MM-DD')
    : null

  // Fetch Met Station devices
  const metStationsQuery = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: [4], // Met Station
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  const metStationDeviceIds = useMemo(
    () => metStationsQuery.data?.map((d) => d.device_id) || [],
    [metStationsQuery.data],
  )

  const poaTimeseriesQuery = useGetTimeSeries({
    pathParams: { projectId: projectId || '' },
    queryParams: {
      device_ids: metStationDeviceIds,
      sensor_type_ids: [4], // POA
      start: startTime || undefined,
      end: endTime || undefined,
    },
    queryOptions: {
      enabled: !!projectId && metStationDeviceIds.length > 0 && !!startTime,
    },
  })

  // Calculate daily total irradiance from timeseries data
  const calculatedIrradiance = useMemo(() => {
    if (!poaTimeseriesQuery.data || poaTimeseriesQuery.data.length === 0) {
      return null
    }

    const allValues = poaTimeseriesQuery.data.flatMap(
      (series) => series.y || [],
    )
    const validValues = allValues.filter(
      (v) => typeof v === 'number' && !isNaN(v) && v !== null,
    )

    if (validValues.length === 0) {
      return 0
    }

    const averageW_m2 =
      validValues.reduce((sum, v) => sum + v, 0) / validValues.length
    const totalWh_m2 = averageW_m2 * 24
    const totalkWh_m2 = totalWh_m2 / 1000

    return totalkWh_m2
  }, [poaTimeseriesQuery.data])

  // Fetch daily KPI data for stats (single day)
  const dailyKpiData = useGetOperationalKPIData({
    queryParams: {
      project_ids: [projectId || ''],
      kpi_type_ids: [1, 2, 34], // 1 = PCS mechanical availability, 2 = generation (MWh), 34 = performance ratio. Removed 3 (irradiance)
      start: selectedDateStr || '',
      end: trailingEnd || '',
      include_device_data: false,
      include_all_dates: false,
    },
    queryOptions: {
      enabled: !!projectId && !!selectedDateStr,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 24 * 60 * 60 * 1000, // 24 hours
      gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days
    },
  })

  // Fetch trailing period KPI data for chart (only generation needed for chart)
  const trailingKpiData = useGetOperationalKPIData({
    queryParams: {
      project_ids: [projectId || ''],
      kpi_type_ids: [2], // Only generation for chart
      start: trailingStart || '',
      end: trailingEnd || '',
      include_device_data: false,
      include_all_dates: true,
    },
    queryOptions: {
      enabled: !!projectId && !!trailingStart,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 24 * 60 * 60 * 1000, // 24 hours
      gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days
    },
  })

  // Fetch events for the selected day (including closed events)
  const eventsData = useGetEventsSummary({
    pathParams: { projectId: projectId || '' },
    queryParams: {
      start: selectedDateStr ? `${selectedDateStr} 00:00:00` : undefined,
      end: selectedDateStr ? `${selectedDateStr} 23:59:59` : undefined,
      open: undefined, // Include both open and closed events
    },
    queryOptions: {
      enabled: !!projectId && !!selectedDateStr,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 24 * 60 * 60 * 1000, // 24 hours
      gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days
    },
  })

  // Fetch DC Combiner Field Health (KPI type 8)
  const combinerHealthKpiData = useGetOperationalKPIData({
    queryParams: {
      project_ids: [projectId || ''],
      kpi_type_ids: [8], // DC combiner field health
      start: selectedDateStr || '',
      end: trailingEnd || '',
      include_device_data: true,
      include_all_dates: false,
    },
    queryOptions: {
      enabled: !!projectId && !!selectedDateStr,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 24 * 60 * 60 * 1000, // 24 hours
      gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days
    },
  })

  // Calculate MTD date range
  const mtdDateRange = useMemo(() => {
    if (!project.data?.time_zone) return null

    const tz = project.data.time_zone
    const end = dayjs().tz(tz).startOf('day')
    const start = end.startOf('month')

    return {
      start: start.format('YYYY-MM-DD'),
      end: end.format('YYYY-MM-DD'),
    }
  }, [project.data?.time_zone])

  // Fetch MTD KPI data for revenue calculation
  const mtdKpiData = useGetOperationalKPIData({
    queryParams: {
      project_ids: [projectId || ''],
      kpi_type_ids: [2], // Generation (MWh) for MTD revenue calculation
      start: mtdDateRange?.start || '',
      end: mtdDateRange?.end || '',
      include_device_data: false,
      include_all_dates: true,
    },
    queryOptions: {
      enabled: !!projectId && !!mtdDateRange,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 24 * 60 * 60 * 1000, // 24 hours
      gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days
    },
  })

  // Fetch DC combiner devices
  const combinerDevices = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: [9], // DC combiner device type ID
    },
    queryOptions: {
      enabled: !!projectId,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 24 * 60 * 60 * 1000, // 24 hours
      gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days
    },
  })

  // Create KPI type for DC combiner health
  const combinerKpiType = {
    kpi_type_id: 8,
    name_long: 'DC Combiner Field Health',
    name_metric: 'DC Combiner Field Health',
    unit: '%',
    aggregation_method: 'average',
    device_type_id: 9,
  }

  // Fetch daily aggregated budgeted series data
  const dailyBudgetedDataQuery = useGetPVBudgetedSeriesDailyData({
    pathParams: {
      pv_budgeted_series_id: stableSelectedSeriesId
        ? parseInt(stableSelectedSeriesId)
        : 0,
    },
    queryParams: {
      project_id: projectId || '',
      start_date: trailingStart || '',
      end_date: selectedDateStr || '',
      degradation_rate: degradationRate,
    },
    queryOptions: {
      enabled:
        !!projectId &&
        !!stableSelectedSeriesId &&
        !!trailingStart &&
        !!selectedDateStr,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 24 * 60 * 60 * 1000, // 24 hours
      gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days
    },
  })

  // Process daily budgeted data from API with degradation applied
  const processedBudgetedData = useMemo(() => {
    if (
      !dailyBudgetedDataQuery.data ||
      dailyBudgetedDataQuery.data.length === 0
    ) {
      return null
    }

    const dates = dailyBudgetedDataQuery.data.map((item) => item.date)
    const budgetedData = dailyBudgetedDataQuery.data.map((item) => {
      const originalEnergy = item.daily_energy_mwh as number | null
      if (originalEnergy === null || !project.data?.cod) {
        return originalEnergy
      }

      // Apply degradation based on COD
      const itemDate = dayjs.tz(item.date, project.data.time_zone)
      const codDate = dayjs(project.data.cod)
      const yearsSinceCOD = itemDate.diff(codDate, 'year', true) // true for decimal years
      const degradationFactor = 1 - (degradationRate / 100) * yearsSinceCOD
      const degradedEnergy = originalEnergy * Math.max(0, degradationFactor) // Ensure non-negative

      return degradedEnergy
    })

    return {
      dates,
      budgetedData,
    }
  }, [dailyBudgetedDataQuery.data, project.data?.cod, degradationRate])

  // Fetch budgeted hourly data for ±15 days around selected date
  const budgetedDataQuery = useGetPVBudgetedDataBySeries({
    pathParams: {
      pv_budgeted_series_id: selectedSeriesId ? parseInt(selectedSeriesId) : 0,
    },
    queryParams: {
      project_id: projectId || '',
      start: budgetedStartDate ? `${budgetedStartDate} 00:00:00` : '',
      end: budgetedEndDate ? `${budgetedEndDate} 23:59:59` : '',
    },
    queryOptions: {
      enabled:
        !!projectId &&
        !!selectedSeriesId &&
        !!budgetedStartDate &&
        !!budgetedEndDate,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 24 * 60 * 60 * 1000, // 24 hours
      gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days
    },
  })

  // Calculate budgeted percentage for generation (energy)
  const generationBudgetInfo = useMemo(() => {
    if (!processedBudgetedData || !selectedDateStr) return null

    const selectedDateIndex = processedBudgetedData.dates.findIndex(
      (date: string) => date === selectedDateStr,
    )

    if (selectedDateIndex === -1) return null

    const budgetedMWh = processedBudgetedData.budgetedData[selectedDateIndex]
    if (!budgetedMWh || budgetedMWh === 0) return null

    // Get the actual generation for the selected day
    const generationKpi = dailyKpiData.data?.find(
      (kpi: OperationalKPIData) => kpi.kpi_type_id === 2,
    )
    const generationMWh = generationKpi?.data?.project_data?.[0] || 0

    return {
      percentage: (generationMWh / budgetedMWh) * 100,
      budgetedMWh,
    }
  }, [processedBudgetedData, selectedDateStr, dailyKpiData.data])

  // Calculate budgeted percentage for irradiance (POA)
  const irradianceBudgetInfo = useMemo(() => {
    if (
      !budgetedDataQuery.data ||
      !selectedDateStr ||
      !project.data?.time_zone
    ) {
      return null
    }

    // Filter budgeted data for the selected date, ignoring the year
    const selectedDateData = budgetedDataQuery.data.filter(
      (item) =>
        dayjs.utc(item.time).tz(project.data?.time_zone).format('MM-DD') ===
        dayjs(selectedDateStr).format('MM-DD'),
    )

    if (selectedDateData.length === 0) {
      return null
    }

    // Sum all hourly POA irradiance for the selected date
    const budgetedPOASumWh = selectedDateData.reduce((sum, item) => {
      const originalPOA = item.poa as number | null
      return sum + (originalPOA || 0)
    }, 0)

    const budgetedPOASumkWh = budgetedPOASumWh / 1000

    if (budgetedPOASumkWh === 0) {
      return null
    }

    // Get the actual irradiance for the selected day from our new calculation
    const actualIrradiance = calculatedIrradiance ?? 0

    return {
      percentage: (actualIrradiance / budgetedPOASumkWh) * 100,
      budgetedPOASumkWh,
    }
  }, [
    budgetedDataQuery.data,
    selectedDateStr,
    calculatedIrradiance,
    project.data?.time_zone,
  ])

  // Calculate stats for StatsGrid
  const stats = useMemo(() => {
    const generationKpi = dailyKpiData.data?.find(
      (kpi: OperationalKPIData) => kpi.kpi_type_id === 2,
    )
    const performanceRatioKpi = dailyKpiData.data?.find(
      (kpi: OperationalKPIData) => kpi.kpi_type_id === 34,
    )
    const availabilityKpi = dailyKpiData.data?.find(
      (kpi: OperationalKPIData) => kpi.kpi_type_id === 1,
    )

    const generationMWh = generationKpi?.data?.project_data?.[0] || 0
    const ppaRate = project.data?.ppa?.rate || 0
    const revenue = generationMWh * ppaRate

    // Calculate MTD revenue
    const mtdGenerationKpi = mtdKpiData.data?.find(
      (kpi: OperationalKPIData) => kpi.kpi_type_id === 2,
    )
    const mtdGenerationMWh =
      mtdGenerationKpi?.data?.project_data?.reduce(
        (sum: number, value: number | null) => sum + (value || 0),
        0,
      ) || 0
    const mtdRevenue = mtdGenerationMWh * ppaRate

    const performanceRatio = performanceRatioKpi?.data?.project_data?.[0] || 0
    const irradianceKWhM2 = calculatedIrradiance ?? 0

    const availability = availabilityKpi?.data?.project_data?.[0] || 0

    const totalEvents = eventsData.data?.length || 0
    const openEvents =
      eventsData.data?.filter((event: EventSummary) => !event.time_end)
        ?.length || 0
    const closedEvents = totalEvents - openEvents

    return [
      {
        title: 'Project Generation',
        value: `${generationMWh.toFixed(2)} MWh`,
        subtitle: generationBudgetInfo
          ? `${generationBudgetInfo.percentage.toFixed(0)}% of Budgeted (${generationBudgetInfo.budgetedMWh.toFixed(2)} MWh)`
          : undefined,
        icon: IconBolt,
        description: 'Total project generation for the selected day',
        kpiTypeId: 6,
        link: `/projects/${projectId}/kpis/type/2`,
      },
      {
        title: 'Resource (Irradiation)',
        value: `${irradianceKWhM2.toFixed(2)} kWh/m²`,
        subtitle: irradianceBudgetInfo
          ? `${irradianceBudgetInfo.percentage.toFixed(0)}% of Budgeted (${irradianceBudgetInfo.budgetedPOASumkWh.toFixed(2)} kWh/m²)`
          : undefined,
        icon: IconSun,
        description: 'Daily irradiance for the selected day',
      },
      {
        title: 'Revenue',
        value:
          revenue > 0
            ? `$${revenue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            : 'N/A',
        subtitle:
          mtdRevenue > 0
            ? `MTD: $${mtdRevenue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            : undefined,
        icon: IconCurrencyDollar,
        description: 'Estimated revenue for the selected day',
      },
      {
        title: 'Performance Ratio',
        value: `${(performanceRatio * 100).toFixed(2)}%`,
        subtitle: 'Daily performance ratio',
        icon: IconChartBar,
        description: 'Performance ratio for the selected day',
        kpiTypeId: 34,
        link: `/projects/${projectId}/kpis/type/34`,
      },
      {
        title: 'Events',
        value: totalEvents.toString(),
        subtitle: `${openEvents} open, ${closedEvents} closed`,
        icon: IconExclamationCircle,
        description: 'Total events for the selected day (open and closed)',
        link: `/projects/${projectId}/events`,
      },
      {
        title: 'PCS Mechanical Availability',
        value: `${(availability * 100).toFixed(2)}%`,
        subtitle: 'Daily mechanical availability',
        icon: IconCash,
        description: 'PCS mechanical availability for the selected day',
        kpiTypeId: 1,
        link: `/projects/${projectId}/kpis/type/1`,
      },
    ]
  }, [
    dailyKpiData.data,
    eventsData.data,
    generationBudgetInfo,
    irradianceBudgetInfo,
    calculatedIrradiance,
  ])

  // Create 30-day energy chart data
  const energyChartData = useMemo(() => {
    // Early return if we don't have essential data yet
    if (!selectedDate || !trailingPeriod) {
      return []
    }

    const generationKpi = trailingKpiData.data?.find(
      (kpi: OperationalKPIData) => kpi.kpi_type_id === 2,
    )

    // If we don't have generation data, try to show budgeted data only
    if (!generationKpi?.data?.dates || !generationKpi?.data?.project_data) {
      if (processedBudgetedData) {
        const { dates, budgetedData } = processedBudgetedData

        // Calculate cumulative if needed
        let budgetedDisplayData = budgetedData
        if (energyView === 'cumulative') {
          budgetedDisplayData = budgetedData.reduce(
            (acc: (number | null)[], val: number | null) => {
              if (val === null) {
                const lastValue =
                  acc.length > 0 && acc[acc.length - 1] !== null
                    ? (acc[acc.length - 1] as number)
                    : null
                acc.push(lastValue)
              } else {
                const prevSum =
                  acc.length > 0 && acc[acc.length - 1] !== null
                    ? (acc[acc.length - 1] as number)
                    : 0
                acc.push(prevSum + val)
              }
              return acc
            },
            [],
          )
        }

        const traces: any[] = []
        if (energyView === 'daily') {
          traces.push({
            x: dates,
            y: budgetedDisplayData,
            name: 'Budgeted',
            type: 'scatter' as const,
            mode: 'markers' as const,
            marker: {
              size: 8,
              symbol: 'diamond',
            },
            error_y: {
              type: 'data',
              array: budgetedDisplayData.map((val) => (val ? val * 0.1 : 0)),
              visible: true,
              thickness: 2,
            },
          })
        } else {
          traces.push({
            x: dates,
            y: budgetedDisplayData,
            name: 'Budgeted',
            type: 'scatter' as const,
            mode: 'lines' as const,
            line: { width: 2, dash: 'dash' },
          })
        }

        return traces
      }
      // Return empty traces array to maintain chart structure
      return []
    }

    const dates = generationKpi.data.dates
    const actualData = generationKpi.data.project_data

    // Calculate cumulative if needed
    let displayData = actualData
    if (energyView === 'cumulative') {
      let lastCumulativeValue = 0
      displayData = actualData.reduce(
        (acc: (number | null)[], val: number | null) => {
          if (val === null) {
            // If current value is null, keep it as null to create a gap
            acc.push(null)
          } else {
            // Add to the last cumulative value (not reset to 0)
            lastCumulativeValue += val
            acc.push(lastCumulativeValue)
          }
          return acc
        },
        [],
      )
    }

    const traces: any[] = []

    if (energyView === 'daily') {
      // For daily view, use column chart for actual data
      traces.push({
        x: dates,
        y: displayData,
        name: 'Actual',
        type: 'bar' as const,
        width: 0.6, // Make bars narrower to leave space for box plots
      })
    } else {
      // For cumulative view, use line chart
      traces.push({
        x: dates,
        y: displayData,
        name: 'Actual',
        type: 'scatter' as const,
        mode: 'lines' as const,
        connectgaps: false, // Show gaps for missing data
        line: { width: 2 },
      })
    }

    // Process budgeted data if available (use pre-processed data)
    if (processedBudgetedData) {
      try {
        // Align budgeted data with actual data dates
        const budgetedData = dates.map((date) => {
          const budgetedIndex = processedBudgetedData.dates.indexOf(date)
          return budgetedIndex >= 0
            ? processedBudgetedData.budgetedData[budgetedIndex]
            : null
        })

        // Calculate cumulative if needed
        let budgetedDisplayData = budgetedData
        if (energyView === 'cumulative') {
          let lastCumulativeValue = 0
          budgetedDisplayData = budgetedData.reduce(
            (acc: (number | null)[], val: number | null) => {
              if (val === null) {
                // If current value is null, keep it as null to create a gap
                acc.push(null)
              } else {
                // Add to the last cumulative value (not reset to 0)
                lastCumulativeValue += val
                acc.push(lastCumulativeValue)
              }
              return acc
            },
            [],
          )
        }

        if (energyView === 'daily') {
          // For daily view, use simple markers for budgeted data
          traces.push({
            x: dates,
            y: budgetedDisplayData,
            name: 'Budgeted',
            type: 'scatter' as const,
            mode: 'markers' as const,
            marker: {
              size: 8,
              symbol: 'diamond',
            },
          })
        } else {
          // For cumulative view, use line chart
          traces.push({
            x: dates,
            y: budgetedDisplayData,
            name: 'Budgeted',
            type: 'scatter' as const,
            mode: 'lines' as const,
            connectgaps: false, // Show gaps for missing data
            line: { width: 2, dash: 'dash' },
          })
        }
      } catch (error) {
        // Continue without budgeted data rather than breaking the chart
      }
    }

    return traces
  }, [
    trailingKpiData.data,
    energyView,
    processedBudgetedData,
    selectedDate,
    trailingPeriod,
  ])

  // Calculate performance summary for the trailing period
  const performanceSummary = useMemo(() => {
    if (!energyChartData.length || energyView !== 'cumulative') {
      return null
    }

    // Find the actual and budgeted traces
    const actualTrace = energyChartData.find(
      (trace: any) => trace.name === 'Actual',
    )
    const budgetedTrace = energyChartData.find(
      (trace: any) => trace.name === 'Budgeted',
    )

    if (!actualTrace || !budgetedTrace || !actualTrace.y || !budgetedTrace.y) {
      return null
    }

    // Get the final values (last point in the cumulative data)
    const actualFinal = actualTrace.y[actualTrace.y.length - 1] as number
    const budgetedFinal = budgetedTrace.y[budgetedTrace.y.length - 1] as number

    if (!actualFinal || !budgetedFinal || budgetedFinal === 0) {
      return null
    }

    const performancePercent =
      ((actualFinal - budgetedFinal) / budgetedFinal) * 100
    const isExceeded = performancePercent > 0

    return {
      actual: actualFinal,
      budgeted: budgetedFinal,
      percent: Math.abs(performancePercent),
      isExceeded,
    }
  }, [energyChartData, energyView])

  // Group events by device type (including closed events)
  const eventsByDeviceType = useMemo(() => {
    if (!eventsData.data) return []

    const grouped = eventsData.data.reduce(
      (
        acc: Record<
          string,
          { device_type_name: string; count: number; revenue_loss: number }
        >,
        event: EventSummary,
      ) => {
        const deviceTypeName = event.device_type_name || 'Unknown'
        if (!acc[deviceTypeName]) {
          acc[deviceTypeName] = {
            device_type_name: deviceTypeName,
            count: 0,
            revenue_loss: 0,
          }
        }
        acc[deviceTypeName].count++
        // Use daily loss instead of total loss
        acc[deviceTypeName].revenue_loss += event.loss_daily_financial || 0
        return acc
      },
      {},
    )

    return Object.values(grouped).sort(
      (a, b) => b.revenue_loss - a.revenue_loss,
    )
  }, [eventsData.data])

  // Calculate AI statistics for daily performance summary
  const aiStats = useMemo((): DailyPerformanceStats | null => {
    if (
      !selectedDate ||
      !project.data ||
      !dailyKpiData.data ||
      !trailingKpiData.data ||
      !processedBudgetedData
    ) {
      return null
    }

    // Get daily generation data
    const dailyGenerationKpi = dailyKpiData.data.find(
      (kpi: OperationalKPIData) => kpi.kpi_type_id === 2,
    )
    const actualEnergyMWh = dailyGenerationKpi?.data?.project_data?.[0] || 0

    // Get budgeted energy for the day
    const budgetedEnergyMWh = generationBudgetInfo?.budgetedMWh || 0
    const energyDifferenceMWh = actualEnergyMWh - budgetedEnergyMWh
    const energyPerformancePercent =
      budgetedEnergyMWh > 0
        ? (energyDifferenceMWh / budgetedEnergyMWh) * 100
        : 0

    // Calculate 30-day trailing statistics
    const trailingGenerationKpi = trailingKpiData.data.find(
      (kpi: OperationalKPIData) => kpi.kpi_type_id === 2,
    )
    const trailingActualMWh =
      trailingGenerationKpi?.data?.project_data?.reduce(
        (sum: number, value: number | null) => sum + (value || 0),
        0,
      ) || 0

    // Calculate 30-day trailing budgeted using actual budgeted data
    const trailingBudgetedMWh = processedBudgetedData.budgetedData.reduce(
      (sum: number, value: number | null) => sum + (value || 0),
      0,
    )
    const trailingDifferenceMWh = trailingActualMWh - trailingBudgetedMWh
    const trailingPerformancePercent =
      trailingBudgetedMWh > 0
        ? (trailingDifferenceMWh / trailingBudgetedMWh) * 100
        : 0

    // Calculate revenue data
    const ppaRate = project.data?.ppa?.rate || 0
    const dailyRevenue = actualEnergyMWh * ppaRate

    // Calculate MTD revenue
    const mtdGenerationKpi = mtdKpiData.data?.find(
      (kpi: OperationalKPIData) => kpi.kpi_type_id === 2,
    )
    const mtdGenerationMWh =
      mtdGenerationKpi?.data?.project_data?.reduce(
        (sum: number, value: number | null) => sum + (value || 0),
        0,
      ) || 0
    const mtdRevenue = mtdGenerationMWh * ppaRate

    // Calculate events data
    const totalEvents = eventsData.data?.length || 0
    const openEvents =
      eventsData.data?.filter((event: EventSummary) => !event.time_end)
        ?.length || 0
    const closedEvents = totalEvents - openEvents
    const totalRevenueLoss =
      eventsData.data?.reduce(
        (sum: number, event: EventSummary) =>
          sum + (event.loss_daily_financial || 0),
        0,
      ) || 0

    // Process events by device type for AI
    const eventsByDeviceType =
      eventsData.data?.reduce(
        (
          acc: Record<
            string,
            {
              device_type_name: string
              count: number
              revenue_loss: number
              status: string
            }
          >,
          event: EventSummary,
        ) => {
          const deviceTypeName = event.device_type_name || 'Unknown'
          const status = event.time_end ? 'closed' : 'open'

          if (!acc[deviceTypeName]) {
            acc[deviceTypeName] = {
              device_type_name: deviceTypeName,
              count: 0,
              revenue_loss: 0,
              status: status,
            }
          }
          acc[deviceTypeName].count++
          acc[deviceTypeName].revenue_loss += event.loss_daily_financial || 0
          return acc
        },
        {},
      ) || {}

    const events = Object.values(eventsByDeviceType)

    return {
      project_name:
        project.data.name_long || project.data.name_short || 'Unknown Project',
      date: dayjs(selectedDate).format('YYYY-MM-DD'),
      actual_energy_mwh: actualEnergyMWh,
      budgeted_energy_mwh: budgetedEnergyMWh,
      energy_difference_mwh: energyDifferenceMWh,
      energy_performance_percent: energyPerformancePercent,
      trailing_30_day_actual: trailingActualMWh,
      trailing_30_day_budgeted: trailingBudgetedMWh,
      trailing_30_day_difference: trailingDifferenceMWh,
      trailing_30_day_performance_percent: trailingPerformancePercent,
      // Revenue data
      daily_revenue: dailyRevenue,
      mtd_revenue: mtdRevenue,
      // Events data
      events: events,
      total_events: totalEvents,
      open_events: openEvents,
      closed_events: closedEvents,
      total_revenue_loss: totalRevenueLoss,
    }
  }, [
    selectedDate,
    project.data,
    dailyKpiData.data,
    trailingKpiData.data,
    mtdKpiData.data,
    eventsData.data,
    generationBudgetInfo,
    processedBudgetedData,
  ])

  const isStatsLoading =
    dailyKpiData.isLoading ||
    eventsData.isLoading ||
    project.isLoading ||
    metStationsQuery.isLoading ||
    poaTimeseriesQuery.isLoading ||
    dailyBudgetedDataQuery.isLoading ||
    budgetedDataQuery.isLoading ||
    mtdKpiData.isLoading ||
    trailingKpiData.isLoading

  // Prepare series options for dropdown (must be before early return)
  const seriesOptions = useMemo(() => {
    if (!budgetedSeriesQuery.data) return []
    return budgetedSeriesQuery.data.map((series) => ({
      value: series.pv_budgeted_series_id.toString(),
      label: `${series.p_value} - ${series.filename}`,
    }))
  }, [budgetedSeriesQuery.data])

  // Prepare trailing period options for dropdown
  const trailingPeriodOptions = useMemo(() => {
    return [
      { value: '7', label: '7 days' },
      { value: '14', label: '14 days' },
      { value: '30', label: '30 days' },
      { value: '60', label: '60 days' },
      { value: '90', label: '90 days' },
      { value: '180', label: '180 days' },
      { value: '365', label: '1 year' },
    ]
  }, [])

  if (project.isLoading) {
    return <PageLoader />
  }

  return (
    <>
      <Stack p="md" gap="md" ref={reportRef}>
        <Group justify="space-between" align="center">
          <Group align="center" gap="md">
            <Title order={2}>PV Performance Daily Report</Title>
            <Tooltip
              label="Select a date to view daily performance metrics and power generation data"
              withArrow
              multiline
              w={300}
            >
              <DatePickerInput
                value={selectedDate}
                onChange={setSelectedDate}
                placeholder="Select date"
                maxDate={dayjs().toDate()}
              />
            </Tooltip>
          </Group>
          <Group align="flex-end">
            {seriesOptions.length > 0 && (
              <Tooltip
                label="Budgeted PV Performance series can be viewed, edited and added in Administrator -> Settings page"
                withArrow
                multiline
                w={300}
              >
                <Select
                  label="Budgeted Series"
                  placeholder="Select series"
                  data={seriesOptions}
                  value={selectedSeriesId}
                  onChange={setSelectedSeriesId}
                  style={{ minWidth: '250px' }}
                />
              </Tooltip>
            )}
            <Tooltip
              label={`Annual degradation rate applied to budgeted series calculations.${
                project.data?.cod
                  ? ` Degradation is calculated from the project's Commercial Operation Date (COD): ${dayjs(project.data.cod).format('MMMM D, YYYY')}.`
                  : ''
              }`}
              withArrow
              multiline
              w={350}
            >
              <Select
                label="Budgeted Degradation Rate"
                placeholder="Select rate"
                data={degradationRateOptions}
                value={selectedPresetRateValue}
                onChange={(value) => {
                  if (value === 'custom') {
                    setCustomRate(degradationRate)
                    setCustomRateModalOpen(true)
                  } else {
                    setDegradationRate(parseFloat(value || '0.5'))
                  }
                }}
                style={{ minWidth: '140px' }}
              />
            </Tooltip>
            <ActionIcon
              size="lg"
              onClick={handleExportPdf}
              loading={isPdfLoading}
            >
              <IconFileTypePdf />
            </ActionIcon>
          </Group>
        </Group>

        {/* Stats Grid */}
        <SimpleGrid cols={{ base: 1, xs: 2, sm: 3, md: 6 }}>
          {isStatsLoading
            ? Array.from({ length: 6 }).map((_, index: number) => (
                <Card key={index} withBorder p="md" radius="md">
                  <Group justify="space-between">
                    <Skeleton height={14} width="60%" />
                    <Skeleton height={20} circle />
                  </Group>
                  <Skeleton height={32} mt={15} width="40%" />
                  <Skeleton height={14} mt={5} width="80%" />
                </Card>
              ))
            : stats.map((stat: any, index: number) => {
                const Icon = stat.icon
                const cardContent = (
                  <Card
                    withBorder
                    p="md"
                    radius="md"
                    style={stat.link ? { cursor: 'pointer' } : {}}
                  >
                    <Group justify="space-between">
                      <Text size="sm" c="dimmed">
                        {stat.title}
                      </Text>
                      <Icon size="1.2rem" stroke={1.5} />
                    </Group>
                    <Group align="flex-end" gap="xs" mt={15}>
                      <Text fz={32} fw={700}>
                        {stat.value}
                      </Text>
                    </Group>
                    {'subtitle' in stat && stat.subtitle && (
                      <Text size="sm" c="dimmed" mt={5}>
                        {stat.subtitle}
                      </Text>
                    )}
                  </Card>
                )

                return (
                  <Tooltip key={index} label={stat.description} withArrow>
                    {stat.link ? (
                      <Link
                        to={stat.link}
                        style={{ textDecoration: 'none', color: 'inherit' }}
                      >
                        {cardContent}
                      </Link>
                    ) : (
                      cardContent
                    )}
                  </Tooltip>
                )
              })}
        </SimpleGrid>

        {/* AI Performance Summary, Daily Energy, and Trailing Energy */}
        <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
          {/* Left Column: AI Performance Summary and Daily Energy */}
          <Stack gap="md">
            {/* AI Performance Summary Card - Much shorter */}
            <AICard stats={aiStats} isLoading={isStatsLoading} />

            {/* Daily Energy Comparison Card */}
            <CustomCard
              title={`Daily Energy Output - ${selectedDate ? dayjs(selectedDate).format('MMM DD, YYYY') : 'Select Date'}`}
              style={{ minHeight: '300px' }}
            >
              <DailyEnergyComparison
                selectedDate={selectedDate}
                projectId={projectId}
                degradationRate={degradationRate}
                budgetedDataQuery={budgetedDataQuery}
              />
            </CustomCard>
          </Stack>

          {/* Trailing Period Energy Chart */}
          <CustomCard
            title={`Trailing ${trailingPeriod}-Day Project Energy (${degradationRate}%/yr degradation)`}
          >
            <Group justify="space-between" mb="md">
              <Group>
                <Select
                  label="Period"
                  placeholder="Select period"
                  data={trailingPeriodOptions}
                  value={trailingPeriod.toString()}
                  onChange={(value) =>
                    setTrailingPeriod(parseInt(value || '30'))
                  }
                  style={{ minWidth: '120px' }}
                />
              </Group>
              <SegmentedControl
                value={energyView}
                onChange={(value) =>
                  setEnergyView(value as 'cumulative' | 'daily')
                }
                data={[
                  { label: 'Cumulative', value: 'cumulative' },
                  { label: 'Daily', value: 'daily' },
                ]}
              />
            </Group>
            {energyChartData.length === 0 &&
            !trailingKpiData.isLoading &&
            !dailyBudgetedDataQuery.isLoading ? (
              <Text c="dimmed" ta="center" py="xl">
                No energy data available for the selected period
              </Text>
            ) : (
              <PlotlyPlot
                data={energyChartData}
                layout={{
                  height: 300,
                  xaxis: {
                    title: { text: 'Date' },
                    type: 'category', // Better for bar charts with dates
                  },
                  yaxis: {
                    title: {
                      text:
                        energyView === 'cumulative'
                          ? 'Cumulative Energy (MWh)'
                          : 'Daily Energy (MWh)',
                    },
                  },
                  showlegend: true,
                  legend: {
                    xref: 'paper',
                    yref: 'paper',
                    x: 0.01,
                    y: 0.99,
                    xanchor: 'left',
                    yanchor: 'top',
                    orientation: 'v',
                    bgcolor:
                      colorScheme === 'dark'
                        ? 'rgba(37,38,43,0.8)'
                        : 'rgba(255,255,255,0.8)',
                    bordercolor:
                      colorScheme === 'dark'
                        ? 'rgba(255,255,255,0.2)'
                        : 'rgba(0,0,0,0.2)',
                    borderwidth: 1,
                    itemsizing: 'constant',
                  },
                  hovermode: energyView === 'daily' ? 'closest' : 'x unified',
                  barmode: energyView === 'daily' ? 'overlay' : undefined,
                  // Adjust margins for better display
                  margin: { l: 60, r: 30, t: 30, b: 60 },
                  annotations:
                    performanceSummary && energyView === 'cumulative'
                      ? [
                          {
                            x: energyChartData[0]?.x?.[
                              energyChartData[0]?.x?.length - 1
                            ],
                            y:
                              (performanceSummary.actual +
                                performanceSummary.budgeted) /
                              2,
                            text: `${performanceSummary.isExceeded ? '+' : '-'}${performanceSummary.percent.toFixed(1)}%`,
                            showarrow: false,
                            font: {
                              color: performanceSummary.isExceeded
                                ? '#00C853'
                                : '#FF5722',
                              size: 40,
                              family: 'Arial, sans-serif',
                              weight: 900,
                            },
                          },
                        ]
                      : [],
                }}
                isLoading={
                  trailingKpiData.isLoading || dailyBudgetedDataQuery.isLoading
                }
              />
            )}
          </CustomCard>
        </SimpleGrid>

        {/* Events Table and Pie Chart */}
        <SimpleGrid cols={{ base: 1, md: 2 }}>
          <CustomCard title="Events by Device Type">
            {eventsByDeviceType.length === 0 ? (
              <Text c="dimmed">No events for this day</Text>
            ) : (
              <Stack gap="xs">
                {eventsByDeviceType.map((item: any, idx: number) => (
                  <Paper key={idx} p="sm" withBorder>
                    <Group justify="space-between">
                      <Text fw={500}>{item.device_type_name}</Text>
                      <Group gap="md">
                        <Text size="sm" c="dimmed">
                          {item.count} event{item.count !== 1 ? 's' : ''}
                        </Text>
                        <Text size="sm" c="dimmed">
                          $
                          {item.revenue_loss.toLocaleString('en-US', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}
                        </Text>
                      </Group>
                    </Group>
                  </Paper>
                ))}
              </Stack>
            )}
          </CustomCard>

          {/* DC Combiner Field Health Map */}
          <MapCard
            data={combinerHealthKpiData.data?.[0]}
            kpiType={combinerKpiType}
            cardTitle="DC Combiner Field Health"
            devices={combinerDevices.data || []}
            isLoading={
              combinerHealthKpiData.isLoading || combinerDevices.isLoading
            }
            isError={combinerHealthKpiData.isError || combinerDevices.isError}
            onMapIdle={setIsMapIdle}
          />
        </SimpleGrid>
      </Stack>
      <Modal
        opened={customRateModalOpen}
        onClose={() => setCustomRateModalOpen(false)}
        title="Set Custom Degradation Rate"
      >
        <Stack>
          <NumberInput
            label="Custom Rate (%/yr)"
            placeholder="e.g., 0.45"
            value={customRate}
            onChange={setCustomRate}
            min={0}
            max={10}
            step={0.01}
            decimalScale={2}
            fixedDecimalScale
          />
          <Button
            onClick={() => {
              setDegradationRate(Number(customRate))
              setCustomRateModalOpen(false)
            }}
          >
            Set Rate
          </Button>
        </Stack>
      </Modal>
    </>
  )
}

export default Page
