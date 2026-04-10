import {
  DeviceTypeEnum,
  EventLossTypeEnum,
  KPITypeEnum,
  ProjectTypeEnum,
  ReportTypeEnum,
  SensorTypeEnum,
} from '@/api/enumerations'
import type { DailyPerformanceStats } from '@/api/v1/ai/daily_performance_summary'
import { useGetDeviceTypes } from '@/api/v1/operational/device_types'
import type { OperationalKPIData } from '@/api/v1/operational/kpi_data'
import { useGetOperationalKPIData } from '@/api/v1/operational/kpi_data'
import { KPIType, useGetKPITypes } from '@/api/v1/operational/kpi_types'
import {
  type EventLosses5Min,
  type EventLosses5MinGroup,
  useGetEventLosses5Min,
  useGetEventsSummary,
} from '@/api/v1/operational/project/events'
import { useGetTimeSeries } from '@/api/v1/operational/project/project_data'
import { useGetWaterfall } from '@/api/v1/operational/project/waterfall'
import { useSelectProject } from '@/api/v1/operational/projects'
import {
  useGetPVBudgetedDataBySeries,
  useGetPVBudgetedSeries,
  useGetPVBudgetedSeriesDailyData,
} from '@/api/v1/operational/pv_budgeted_data'
import { useGetMeterPowerAndExpectedPowerV3 } from '@/api/v1/protected/system'
import AICard from '@/components/AICard'
import CustomCard from '@/components/CustomCard'
import { ColorBar, MapSettings } from '@/components/GIS'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { getQueryParamDateRange } from '@/components/datepicker/utils'
import Attribution from '@/components/gis/Attribution'
import LossWaterfall from '@/components/plots/LossWaterfall'
import { LossWaterfallCardInfo } from '@/components/plots/LossWaterfallCardInfo'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { AutoFitStatValue } from '@/components/stats/AutoFitStatValue'
import { GISContext } from '@/contexts/GISContext'
import { useGetDevicesV2 } from '@/hooks/api'
import { useProjectFilter } from '@/hooks/custom'
import type { DataTimeSeries, Device, EventSummary } from '@/hooks/types'
import * as gisUtils from '@/utils/GIS'
import { alignLossSeries } from '@/utils/alignLossSeries'
import { calculateMovingAverage } from '@/utils/movingAverage'
import {
  ActionIcon,
  Box,
  Button,
  Card,
  Center,
  Group,
  List,
  Loader,
  Modal,
  NumberInput,
  Paper,
  SegmentedControl,
  Select,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  Tooltip,
  useComputedColorScheme,
  useMantineColorScheme,
  useMantineTheme,
} from '@mantine/core'
import {
  IconBolt,
  IconCash,
  IconChartBar,
  IconCurrencyDollar,
  IconExclamationCircle,
  IconExternalLink,
  IconFileTypePdf,
  IconPencil,
  IconSun,
} from '@tabler/icons-react'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { FeatureCollection } from 'geojson'
import html2canvas from 'html2canvas-pro'
import jsPDF from 'jspdf'
import {
  type MRT_Cell,
  MRT_ColumnDef,
  MantineReactTable,
  useMantineReactTable,
} from 'mantine-react-table'
import type * as Plotly from 'plotly.js'
import React, {
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from 'react'
import type { MapMouseEvent } from 'react-map-gl/mapbox'
import Map, { Layer, Source } from 'react-map-gl/mapbox'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'

import { HoverInfo } from '../gis/utils'

dayjs.extend(utc)
dayjs.extend(timezone)

// Waterfall API bar names (must match backend project_waterfall.py)
const WATERFALL_NAME_PV_ENERGY_OUTPUT = 'PV Energy Output'
const WATERFALL_NAME_PV_EXPECTED = 'PV Expected'

type BudgetedRow = NonNullable<
  ReturnType<typeof useGetPVBudgetedDataBySeries>['data']
>[number]

/** Hour-of-day (0–23) → average budgeted MW for overlay traces. */
function buildHourlyBudgetedAverages(
  anchorDay: dayjs.Dayjs,
  comparisonMode: '15days' | 'dayof',
  budgetRows: BudgetedRow[],
  timeZone: string,
  cod: string | null | undefined,
  degradationRate: number,
): Record<number, number> | null {
  if (!budgetRows.length) {
    return null
  }
  let filteredData = budgetRows
  if (comparisonMode === 'dayof') {
    const selectedMonthDay = anchorDay.format('MM-DD')
    filteredData = budgetRows.filter((dataPoint) => {
      const timestamp = dayjs.utc(dataPoint.time).tz(timeZone)
      return timestamp.format('MM-DD') === selectedMonthDay
    })
  }
  if (filteredData.length === 0) {
    return null
  }
  const hourlyAverages: Record<number, number[]> = {}
  filteredData.forEach((dataPoint) => {
    const timestamp = dayjs.utc(dataPoint.time).tz(timeZone)
    const hour = timestamp.hour()
    if (!hourlyAverages[hour]) {
      hourlyAverages[hour] = []
    }
    let degradedPower = dataPoint.poi_ac_power
    if (cod) {
      const codDate = dayjs(cod)
      const yearsSinceCOD = anchorDay.diff(codDate, 'year', true)
      const degradationFactor = 1 - (degradationRate / 100) * yearsSinceCOD
      degradedPower = dataPoint.poi_ac_power * Math.max(0, degradationFactor)
    }
    hourlyAverages[hour].push(degradedPower)
  })
  const result: Record<number, number> = {}
  Object.keys(hourlyAverages).forEach((hour) => {
    const hourNum = parseInt(hour, 10)
    const values = hourlyAverages[hourNum]
    result[hourNum] = values.reduce((sum, val) => sum + val, 0) / values.length
  })
  return result
}

const isEventLossGroup = (
  entry: EventLosses5Min,
): entry is EventLosses5MinGroup =>
  typeof entry === 'object' &&
  entry !== null &&
  'data' in entry &&
  Array.isArray((entry as EventLosses5MinGroup).data)

// Weekly meter power: full date range + repeated budgeted curve per day.
const WeeklyEnergyComparison = ({
  rangeStart,
  rangeEnd,
  projectId,
  degradationRate,
  budgetedDataQuery,
  comparisonMode,
  viewMode,
  movingAverageWindow,
}: {
  rangeStart: dayjs.Dayjs | null
  rangeEnd: dayjs.Dayjs | null
  projectId: string | undefined
  degradationRate: number
  budgetedDataQuery: ReturnType<typeof useGetPVBudgetedDataBySeries>
  comparisonMode: '15days' | 'dayof'
  viewMode: 'standard' | 'delta'
  movingAverageWindow: number
}) => {
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme('light')

  // Get project data
  const project = useSelectProject(projectId!)

  const startTime =
    rangeStart && rangeEnd ? rangeStart.startOf('day').toISOString() : null
  const endTime =
    rangeStart && rangeEnd ? rangeEnd.endOf('day').toISOString() : null

  const deviceTypes = useGetDeviceTypes({
    queryOptions: {
      enabled: viewMode === 'delta' && !!projectId,
    },
  })

  const eventLosses5Min = useGetEventLosses5Min({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: startTime || '',
      end: endTime || '',
      event_loss_type_ids: [EventLossTypeEnum.PROXIMAL_ENERGY],
      aggregation_column: 'device_type_id',
    },
    queryOptions: {
      enabled: viewMode === 'delta' && !!projectId && !!startTime && !!endTime,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 60 * 1000,
      gcTime: 7 * 24 * 60 * 60 * 1000,
    },
  })

  // TODO: Remove this in favor of a new database table.
  const includeSoiling = !['sigurd'].includes(project.data?.name_short || '')
  const includeDegradation = ['sigurd'].includes(project.data?.name_short || '')

  // Use the same hook as PowerPlotPVZoom for power data
  const powerData = useGetMeterPowerAndExpectedPowerV3({
    pathParams: { project_id: projectId || '-1' },
    queryParams: {
      start: startTime || '',
      end: endTime || '',
      interval: '5min',
      include_storage: project.data?.project_type_id === ProjectTypeEnum.PVS,
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
  const colorMap = useMemo<Record<string, string>>(
    () => ({
      [SensorTypeEnum.METER_ACTIVE_POWER]: theme.colors.green[7],
      [SensorTypeEnum.PV_EXPECTED_POWER]: theme.colors.orange[7],
      [SensorTypeEnum.PPC_ACTIVE_POWER_SETPOINT]: theme.colors.blue[7],
      [SensorTypeEnum.PV_MV_COLLECTOR_CIRCUIT_METER_ACTIVE_POWER]:
        theme.colors.cyan[7],
      [SensorTypeEnum.BESS_MV_COLLECTOR_CIRCUIT_METER_ACTIVE_POWER]:
        theme.colors.yellow[7],
      [-1]: theme.colors.gray[7],
      [-2]: theme.colors.violet[7],
    }),
    [theme],
  )

  // Process plot data similar to PowerPlotPVZoom
  const plotData = useMemo(() => {
    if (!powerData.data) return []

    return powerData.data.map((d) => {
      const numericY = d.y.map((val: number | null) =>
        val === null ? null : parseFloat(String(val)),
      )

      // Transform name for PV Expected Power
      const displayName =
        d.sensor_type_id === SensorTypeEnum.PV_EXPECTED_POWER
          ? 'Power Expected at Full Health'
          : d.name

      // Convert timestamps to project timezone for display
      const convertedTimestamps = d.x.map((timestamp: string) => {
        return dayjs
          .utc(timestamp)
          .tz(project.data?.time_zone || 'UTC')
          .format()
      })

      // Determine mode and fill based on trace name
      const isMeterPower =
        d.sensor_type_id === SensorTypeEnum.METER_ACTIVE_POWER
      const isSetpoint =
        d.sensor_type_id === SensorTypeEnum.PPC_ACTIVE_POWER_SETPOINT
      const isExpectedPower =
        d.sensor_type_id === SensorTypeEnum.PV_EXPECTED_POWER
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
          color: colorMap[d.sensor_type_id] || theme.colors.gray[7],
          width: 2,
        },
        marker: {
          size: mode.includes('markers') ? 4 : 0,
          opacity: isSetpoint ? 0 : 1,
        },
        visible: isSetpoint ? ('legendonly' as const) : true,
      }
    })
  }, [powerData.data, colorMap, theme, project.data?.time_zone])

  // Add interconnection limit and budgeted series if available
  const finalPlotData = useMemo(() => {
    let finalData = [...plotData]

    // Add interconnection limit if available
    if (
      plotData.length > 0 &&
      project.data?.poi &&
      powerData.data &&
      powerData.data.length > 0
    ) {
      // Convert timestamps for interconnection limit
      const limitTimestamps = powerData.data[0].x.map((timestamp: string) => {
        return dayjs
          .utc(timestamp)
          .tz(project.data?.time_zone || 'UTC')
          .format()
      })

      finalData.push({
        x: limitTimestamps,
        y: Array(limitTimestamps.length).fill(project.data.poi),
        name: 'Interconnection Limit',
        type: 'scatter' as const,
        mode: 'lines' as const,
        connectgaps: true,
        fill: 'none' as const,
        line: {
          color: colorMap[-1],
          width: 2,
          dash: 'dash',
        } as { color: string; width: number; dash: string },
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

    if (
      budgetedDataQuery.data?.length &&
      powerData.data &&
      powerData.data.length > 0 &&
      rangeStart &&
      rangeEnd &&
      project.data?.time_zone
    ) {
      const budgetedTimestamps: string[] = []
      const budgetedY: number[] = []
      const tz = project.data.time_zone
      let day = rangeStart.startOf('day')
      const endDay = rangeEnd.startOf('day')
      while (!day.isAfter(endDay)) {
        const hourlyMap = buildHourlyBudgetedAverages(
          day,
          comparisonMode,
          budgetedDataQuery.data,
          tz,
          project.data.cod,
          degradationRate,
        )
        if (hourlyMap) {
          for (let hour = 0; hour < 24; hour++) {
            budgetedTimestamps.push(
              day.hour(hour).minute(30).second(0).utc().tz(tz).format(),
            )
            budgetedY.push(hourlyMap[hour] || 0)
          }
        }
        day = day.add(1, 'day')
      }
      if (budgetedTimestamps.length > 0) {
        finalData.push({
          x: budgetedTimestamps,
          y: budgetedY,
          name:
            comparisonMode === 'dayof'
              ? 'Budgeted (Day of)'
              : 'Budgeted Avg (±15 days)',
          type: 'scatter' as const,
          mode: 'lines' as const,
          connectgaps: false,
          fill: 'none' as const,
          line: {
            color: colorMap[-2],
            width: 2,
            dash: 'dot',
          } as { color: string; width: number; dash: string },
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
    }

    return finalData
  }, [
    plotData,
    project.data,
    powerData.data,
    colorMap,
    budgetedDataQuery.data,
    rangeStart,
    rangeEnd,
    comparisonMode,
    degradationRate,
  ])

  const meterPowerPlotLayout = useMemo(
    () => ({
      yaxis: {
        title: { text: 'Power (MW)' },
        fixedrange: true,
        range:
          project.data?.project_type_id === ProjectTypeEnum.PVS
            ? undefined
            : [0, (project.data?.poi || 0) * 1.05],
      },
      xaxis: {
        type: 'date' as const,
        fixedrange: false,
        tickangle: 0,
        range:
          rangeStart && rangeEnd
            ? [
                rangeStart.startOf('day').valueOf(),
                rangeEnd.endOf('day').valueOf(),
              ]
            : undefined,
      },
      showlegend: true,
      legend: {
        xref: 'paper' as const,
        yref: 'paper' as const,
        x: 0.5,
        y: -0.25,
        xanchor: 'center' as const,
        yanchor: 'top' as const,
        orientation: 'h' as const,
        bgcolor:
          colorScheme === 'dark'
            ? 'rgba(37,38,43,0.8)'
            : 'rgba(255,255,255,0.8)',
        bordercolor:
          colorScheme === 'dark' ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)',
        borderwidth: 1,
        itemsizing: 'constant' as const,
        tracegroupgap: 10,
      },
      margin: { l: 60, r: 30, t: 10, b: 20 },
    }),
    [
      project.data?.project_type_id,
      project.data?.poi,
      colorScheme,
      rangeStart,
      rangeEnd,
    ],
  )

  const meterPowerPlotConfig = useMemo(
    () => ({ responsive: true, scrollZoom: false }),
    [],
  )

  const deviceTypeNameById = useMemo(() => {
    const m = new globalThis.Map<number, string>()
    deviceTypes.data?.forEach((dt) => {
      m.set(dt.device_type_id, dt.name_long)
    })
    return m
  }, [deviceTypes.data])

  const deltaPlotData = useMemo((): Partial<Plotly.Data>[] => {
    if (viewMode !== 'delta' || !powerData.data || !project.data) {
      return []
    }
    const tz = project.data.time_zone ?? 'UTC'
    const meterSensorId =
      project.data.project_type_id === ProjectTypeEnum.PVS
        ? SensorTypeEnum.PV_MV_COLLECTOR_CIRCUIT_METER_ACTIVE_POWER
        : SensorTypeEnum.METER_ACTIVE_POWER
    const meterTrace = powerData.data.find(
      (t) => t.sensor_type_id === meterSensorId,
    ) as DataTimeSeries | undefined
    const expectedTrace = powerData.data.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_EXPECTED_POWER,
    ) as DataTimeSeries | undefined
    if (!meterTrace || !expectedTrace) {
      return []
    }
    const xs = meterTrace.x as string[]
    const convertedX = xs.map((timestamp: string) =>
      dayjs.utc(timestamp).tz(tz).format(),
    )
    const deltaY = xs.map((_, i) => {
      const mVal = meterTrace.y[i]
      const eVal = expectedTrace.y[i]
      if (mVal == null || eVal == null) return null
      const mn = parseFloat(String(mVal))
      const en = parseFloat(String(eVal))
      if (!Number.isFinite(mn) || !Number.isFinite(en)) return null
      return en - mn
    })
    const deltaSmoothed = calculateMovingAverage(deltaY, movingAverageWindow)
    const traces: Partial<Plotly.Data>[] = [
      {
        x: convertedX,
        y: deltaSmoothed,
        name: 'Expected - Actual (smoothed)',
        type: 'scatter',
        mode: 'lines',
        fill: 'tozeroy',
        fillcolor:
          colorScheme === 'dark'
            ? 'rgba(255, 107, 107, 0.2)'
            : 'rgba(250, 82, 82, 0.15)',
        line: { color: theme.colors.red[6], width: 1 },
        hoverlabel: { namelength: -1 },
      },
    ]
    // Curtailment MW when actual is near PPC setpoint ceiling (same gate as
    // PV_PROJECT_CURTAILMENT KPI / project_curtailed_energy_kwh_d).
    const setpointTrace = powerData.data.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PPC_ACTIVE_POWER_SETPOINT,
    ) as DataTimeSeries | undefined
    const curtailmentMw = xs.map((_, i) => {
      if (!setpointTrace) {
        return null
      }
      const mVal = meterTrace.y[i]
      const eVal = expectedTrace.y[i]
      const sVal = setpointTrace.y[i]
      if (mVal == null || eVal == null || sVal == null) {
        return null
      }
      const actualMw = parseFloat(String(mVal))
      const expectedMw = parseFloat(String(eVal))
      const setpointMw = parseFloat(String(sVal))
      if (
        ![actualMw, expectedMw, setpointMw].every((v) => Number.isFinite(v))
      ) {
        return null
      }
      const deltaHours = 5 / 60
      const actualMwh = actualMw * deltaHours
      const setpointMwh = setpointMw * deltaHours
      if (actualMwh <= 0.98 * setpointMwh) {
        return 0
      }
      const diffMw = expectedMw - actualMw
      return diffMw > 0 ? diffMw : 0
    })
    const hasCurtailmentLoss = curtailmentMw.some((v) => v != null && v > 0)
    if (hasCurtailmentLoss) {
      traces.push({
        x: convertedX,
        y: curtailmentMw,
        name: 'Curtailment',
        type: 'scatter',
        mode: 'lines',
        fill: 'tonexty',
        stackgroup: 'losses',
        fillcolor:
          colorScheme === 'dark'
            ? 'rgba(253, 126, 20, 0.25)'
            : 'rgba(253, 126, 20, 0.15)',
        line: { color: theme.colors.orange[6], width: 1 },
        hoverlabel: { namelength: -1 },
      })
    }
    const groups = (eventLosses5Min.data ?? []).filter(isEventLossGroup)
    const sorted = [...groups].sort((a, b) => {
      const idA = a.device_type_id ?? 0
      const idB = b.device_type_id ?? 0
      return idA - idB
    })
    sorted.forEach((group, index) => {
      const series = group.data.find(
        (s) => s.event_loss_type_id === EventLossTypeEnum.PROXIMAL_ENERGY,
      )
      if (!series?.losses.time.length) {
        return
      }
      const dtId = group.device_type_id
      const label =
        (dtId != null ? deviceTypeNameById.get(dtId) : undefined) ??
        (dtId != null ? `Device type ${dtId}` : 'Unknown type')
      const aligned = alignLossSeries(
        convertedX,
        series.losses.time,
        series.losses.loss,
        5,
        tz,
      )
      const hasAny = aligned.some((v) => v !== null && Number.isFinite(v))
      if (!hasAny) {
        return
      }
      traces.push({
        x: convertedX,
        y: aligned,
        name: `Event losses — ${label}`,
        type: 'scatter',
        mode: 'lines',
        fill: 'tonexty',
        stackgroup: 'losses',
        fillcolor: theme.colors.gray[2],
        line: {
          color: theme.colors.gray[Math.max(3, 6 - (index % 4))],
        },
        hoverlabel: { namelength: -1 },
      })
    })
    return traces
  }, [
    viewMode,
    powerData.data,
    project.data,
    eventLosses5Min.data,
    deviceTypeNameById,
    movingAverageWindow,
    theme.colors.red,
    theme.colors.orange,
    theme.colors.gray,
    colorScheme,
  ])

  const deltaPlotLayout = useMemo(
    () => ({
      yaxis: {
        title: { text: 'Power difference & losses (MW)' },
        fixedrange: true,
        zeroline: true,
        autorange: true,
      },
      xaxis: {
        type: 'date' as const,
        fixedrange: false,
        tickangle: 0,
        range:
          rangeStart && rangeEnd
            ? [
                rangeStart.startOf('day').valueOf(),
                rangeEnd.endOf('day').valueOf(),
              ]
            : undefined,
      },
      showlegend: true,
      legend: {
        xref: 'paper' as const,
        yref: 'paper' as const,
        x: 0.5,
        y: -0.25,
        xanchor: 'center' as const,
        yanchor: 'top' as const,
        orientation: 'h' as const,
        bgcolor:
          colorScheme === 'dark'
            ? 'rgba(37,38,43,0.8)'
            : 'rgba(255,255,255,0.8)',
        bordercolor:
          colorScheme === 'dark' ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)',
        borderwidth: 1,
        itemsizing: 'constant' as const,
        tracegroupgap: 10,
      },
      margin: { l: 60, r: 30, t: 10, b: 20 },
    }),
    [colorScheme, rangeStart, rangeEnd],
  )

  if (!project.data) return null

  if (!rangeStart || !rangeEnd) {
    return (
      <Text c="dimmed" ta="center" py="xl">
        Please select a date range to view meter power
      </Text>
    )
  }

  const meterSensorIdForDelta =
    project.data.project_type_id === ProjectTypeEnum.PVS
      ? SensorTypeEnum.PV_MV_COLLECTOR_CIRCUIT_METER_ACTIVE_POWER
      : SensorTypeEnum.METER_ACTIVE_POWER
  const deltaMissingTraces =
    viewMode === 'delta' &&
    !!powerData.data &&
    (!powerData.data.some((t) => t.sensor_type_id === meterSensorIdForDelta) ||
      !powerData.data.some(
        (t) => t.sensor_type_id === SensorTypeEnum.PV_EXPECTED_POWER,
      ))

  // Only wait for required data - budgeted data is optional and can be added later
  if (
    powerData.isLoading ||
    project.isLoading ||
    (viewMode === 'delta' && eventLosses5Min.isLoading)
  ) {
    return (
      <Center py="xl" style={{ minHeight: 'clamp(380px, 48vh, 640px)' }}>
        <Loader />
      </Center>
    )
  }

  if (deltaMissingTraces) {
    return (
      <Text c="dimmed" ta="center" py="xl">
        Model expected power is not available for delta view on this project.
      </Text>
    )
  }

  const plotDataOut = viewMode === 'standard' ? finalPlotData : deltaPlotData
  const layoutOut =
    viewMode === 'standard' ? meterPowerPlotLayout : deltaPlotLayout
  const plotError =
    viewMode === 'standard'
      ? powerData.error
      : (powerData.error ?? eventLosses5Min.error)

  return (
    <Box
      w="100%"
      miw={0}
      style={{
        flexShrink: 0,
        height: 'clamp(380px, 48vh, 640px)',
        minHeight: 'clamp(380px, 48vh, 640px)',
      }}
    >
      <PlotlyPlot
        data={plotDataOut}
        layout={layoutOut}
        isLoading={false}
        error={plotError}
        config={meterPowerPlotConfig}
      />
    </Box>
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
  kpiType: KPIType
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
    return null
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
  kpiType: KPIType
}) {
  const rawValue = hoverInfo.feature?.properties?.value
  const hoverValueText =
    rawValue == null
      ? 'No Data'
      : kpiType.unit === '%'
        ? `${(rawValue * 100).toFixed(2)}%`
        : `${rawValue.toLocaleString('en-US', {
            maximumFractionDigits: 0,
            minimumFractionDigits: 0,
          })} ${kpiType.unit}`

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
      <Text>{hoverValueText}</Text>
    </Paper>
  )
}

function sumKpiInDateRange(
  kpi: OperationalKPIData | undefined,
  lo: string,
  hi: string,
): number {
  if (!kpi?.data?.dates || !kpi.data.project_data) {
    return 0
  }
  let sum = 0
  kpi.data.dates.forEach((d, i) => {
    if (d >= lo && d <= hi) {
      sum += kpi.data!.project_data![i] ?? 0
    }
  })
  return sum
}

function avgKpiInDateRange(
  kpi: OperationalKPIData | undefined,
  lo: string,
  hi: string,
): number {
  if (!kpi?.data?.dates || !kpi.data.project_data) {
    return 0
  }
  const vals: number[] = []
  kpi.data.dates.forEach((d, i) => {
    if (d >= lo && d <= hi) {
      const v = kpi.data!.project_data![i]
      if (v != null && typeof v === 'number') {
        vals.push(v)
      }
    }
  })
  if (vals.length === 0) {
    return 0
  }
  return vals.reduce((a, b) => a + b, 0) / vals.length
}

const Page: React.FC = () => {
  useProjectFilter({
    reportTypeId: ReportTypeEnum.PV_PERFORMANCE_WEEKLY,
  })

  const { projectId } = useParams<{ projectId: string }>()
  const reportRef = useRef<HTMLDivElement>(null)
  const [isPdfLoading, setIsPdfLoading] = useState(false)
  const [isMapIdle, setIsMapIdle] = useState(false)
  const [pdfExportRequested, setPdfExportRequested] = useState(false)
  const [pendingThemeSwitch, setPendingThemeSwitch] = useState(false)
  const { setColorScheme } = useMantineColorScheme()

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
        pdf.save('weekly-performance-report.pdf')
        setIsPdfLoading(false)
        setPdfExportRequested(false)
        setIsMapIdle(false) // Reset for next export
      })
    }
  }, [isMapIdle, pdfExportRequested])

  const project = useSelectProject(projectId!)
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme('light')

  React.useEffect(() => {
    if (!pendingThemeSwitch) return
    if (colorScheme !== 'light') return

    setPdfExportRequested(true)
    setPendingThemeSwitch(false)
  }, [pendingThemeSwitch, colorScheme])

  const [searchParams] = useSearchParams()
  const { start: rangeStart, end: rangeEnd } = useMemo(
    () =>
      getQueryParamDateRange({
        searchParams,
        timeZone: project.data?.time_zone,
        maxDays: 7,
        endExclusive: false,
      }),
    [searchParams, project.data?.time_zone],
  )

  // Toggle for cumulative vs daily in the 30-day chart
  const [energyView, setEnergyView] = useState<'cumulative' | 'daily'>(
    'cumulative',
  )

  const [meterPowerChartView, setMeterPowerChartView] = useState<
    'standard' | 'delta'
  >('standard')
  const [meterPowerMaWindow, setMeterPowerMaWindow] = useState(20)

  // Toggle for budgeted comparison: '+/- 15 days' vs 'Day of'
  const [budgetedComparisonMode, setBudgetedComparisonMode] = useState<
    '15days' | 'dayof'
  >('15days')

  // Trailing period selection for the energy chart
  const [trailingPeriod, setTrailingPeriod] = useState<number>(30)

  // Selected budgeted series
  const [selectedSeriesId, setSelectedSeriesId] = useState<string | null>(null)

  // Degradation rate (default 0.5% per year)
  const [degradationRate, setDegradationRate] = useState<number>(0.5)
  const [customRateModalOpen, setCustomRateModalOpen] = useState(false)
  const [customRate, setCustomRate] = useState<number | string>(degradationRate)

  const presetDegradationRates = useMemo(
    () => [
      { value: '0', label: '0.0%/yr' },
      { value: '0.25', label: '0.25%/yr' },
      { value: '0.5', label: '0.5%/yr' },
      { value: '0.75', label: '0.75%/yr' },
      { value: '1.0', label: '1.0%/yr' },
      { value: '1.5', label: '1.5%/yr' },
      { value: '2.0', label: '2.0%/yr' },
    ],
    [],
  )

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
  }, [degradationRate, presetDegradationRates])

  const selectedPresetRateValue =
    presetDegradationRates.find(
      (option) => parseFloat(option.value) === degradationRate,
    )?.value ?? 'custom'

  const {
    startTime,
    endTime,
    rangeStartStr,
    rangeEndStr,
    rangeEndExclusiveStr,
  } = useMemo(() => {
    if (!rangeStart || !rangeEnd) {
      return {
        startTime: null,
        endTime: null,
        rangeStartStr: null,
        rangeEndStr: null,
        rangeEndExclusiveStr: null,
      }
    }
    return {
      startTime: rangeStart.startOf('day').toISOString(),
      endTime: rangeEnd.endOf('day').toISOString(),
      rangeStartStr: rangeStart.format('YYYY-MM-DD'),
      rangeEndStr: rangeEnd.format('YYYY-MM-DD'),
      rangeEndExclusiveStr: rangeEnd.add(1, 'day').format('YYYY-MM-DD'),
    }
  }, [rangeStart, rangeEnd])

  // Waterfall uses same Actual/Expected as the loss chart (meter + pv_expected).
  // Use for PI and Project Generation when available so they match the chart.
  const waterfallQuery = useGetWaterfall({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      level: 'device_type',
      start: startTime || '',
      end: endTime || '',
    },
    queryOptions: {
      enabled: !!projectId && !!startTime && !!endTime,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 24 * 60 * 60 * 1000,
      gcTime: 7 * 24 * 60 * 60 * 1000,
    },
  })

  // Same queries as WeeklyEnergyComparison; TanStack Query dedupes — used to
  // disable PDF export until the meter chart has finished loading.
  const includeSoilingPdfGate = !['sigurd'].includes(
    project.data?.name_short || '',
  )
  const includeDegradationPdfGate = ['sigurd'].includes(
    project.data?.name_short || '',
  )
  const meterPowerPdfGate = useGetMeterPowerAndExpectedPowerV3({
    pathParams: { project_id: projectId || '-1' },
    queryParams: {
      start: startTime || '',
      end: endTime || '',
      interval: '5min',
      include_storage: project.data?.project_type_id === ProjectTypeEnum.PVS,
      include_setpoint: true,
      include_soiling: includeSoilingPdfGate,
      include_degradation: includeDegradationPdfGate,
    },
    queryOptions: {
      enabled: !!projectId && !!startTime && !!endTime,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 60 * 1000,
      gcTime: 7 * 24 * 60 * 60 * 1000,
    },
  })
  const eventLossesPdfGate = useGetEventLosses5Min({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: startTime || '',
      end: endTime || '',
      event_loss_type_ids: [EventLossTypeEnum.PROXIMAL_ENERGY],
      aggregation_column: 'device_type_id',
    },
    queryOptions: {
      enabled:
        meterPowerChartView === 'delta' &&
        !!projectId &&
        !!startTime &&
        !!endTime,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 60 * 1000,
      gcTime: 7 * 24 * 60 * 60 * 1000,
    },
  })

  const waterfallActualExpected = useMemo(() => {
    const data = waterfallQuery.data
    if (!data?.name?.length || !data?.value?.length) return null
    const idxActual = data.name.indexOf(WATERFALL_NAME_PV_ENERGY_OUTPUT)
    if (idxActual === -1) return null
    const idxExpected = data.name.indexOf(WATERFALL_NAME_PV_EXPECTED)
    if (idxExpected === -1) return null

    const expected = data.value[idxExpected]
    const actual = data.value[idxActual]
    if (typeof actual !== 'number' || typeof expected !== 'number') return null
    return { actualMWh: actual, expectedMWh: expected }
  }, [waterfallQuery.data])

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
    if (budgetedSeriesQuery.data && budgetedSeriesQuery.data.length > 0) {
      // If no series is selected, or the selected series is no longer available, select the first one
      const selectedSeriesExists = selectedSeriesId
        ? budgetedSeriesQuery.data.some(
            (series) =>
              series.pv_budgeted_series_id.toString() === selectedSeriesId,
          )
        : false

      if (!selectedSeriesId || !selectedSeriesExists) {
        setSelectedSeriesId(
          budgetedSeriesQuery.data[0].pv_budgeted_series_id.toString(),
        )
      }
    }
  }, [budgetedSeriesQuery.data, selectedSeriesId])

  // Prevent unnecessary refetches when series selection changes
  const stableSelectedSeriesId = React.useMemo(() => {
    return selectedSeriesId
  }, [selectedSeriesId])

  // Trailing window ends on the last day of the selected range (rangeEnd).
  const trailingStart = useMemo(() => {
    if (!rangeEnd) return null
    return rangeEnd.subtract(trailingPeriod - 1, 'days').format('YYYY-MM-DD')
  }, [rangeEnd, trailingPeriod])
  const trailingEnd = useMemo(() => {
    if (!rangeEnd) return null
    return rangeEnd.add(1, 'day').format('YYYY-MM-DD')
  }, [rangeEnd])

  const budgetedStartDate = useMemo(() => {
    if (!rangeEnd) return null
    return rangeEnd.subtract(15, 'days').format('YYYY-MM-DD')
  }, [rangeEnd])
  const budgetedEndDate = useMemo(() => {
    if (!rangeEnd) return null
    return rangeEnd.add(15, 'days').format('YYYY-MM-DD')
  }, [rangeEnd])

  // Fetch Met Station devices
  const metStationsQuery = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: [DeviceTypeEnum.MET_STATION],
    },
    queryOptions: {
      enabled: !!projectId,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 24 * 60 * 60 * 1000, // 24 hours - met stations don't change often
      gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days
    },
  })

  const metStationDeviceIds = useMemo(
    () => metStationsQuery.data?.map((d) => d.device_id) || [],
    [metStationsQuery.data],
  )

  // Don't block on metStationsQuery - use empty array if still loading
  // This allows other content to load while we wait for met stations
  const poaTimeseriesQuery = useGetTimeSeries({
    pathParams: { project_id: projectId || '' },
    queryParams: {
      device_ids: metStationDeviceIds,
      sensor_type_ids: [SensorTypeEnum.MET_STATION_POA],
      start: startTime || undefined,
      end: endTime || undefined,
    },
    queryOptions: {
      enabled:
        !!projectId &&
        !!startTime &&
        (metStationDeviceIds.length > 0 || !metStationsQuery.isLoading),
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 60 * 60 * 1000, // 1 hour
      gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days
    },
  })

  // Sum of daily kWh/m² (same daily heuristic as daily report, per calendar day).
  const calculatedIrradiance = useMemo(() => {
    if (
      !poaTimeseriesQuery.data ||
      poaTimeseriesQuery.data.length === 0 ||
      !project.data?.time_zone ||
      !rangeStartStr ||
      !rangeEndStr
    ) {
      return null
    }
    const tz = project.data.time_zone
    const byDay: Record<string, number[]> = {}
    for (const series of poaTimeseriesQuery.data) {
      const xs = series.x || []
      const ys = series.y || []
      xs.forEach((timestamp: string, i: number) => {
        const dKey = dayjs.utc(timestamp).tz(tz).format('YYYY-MM-DD')
        if (dKey < rangeStartStr || dKey > rangeEndStr) {
          return
        }
        const y = ys[i]
        if (typeof y !== 'number' || isNaN(y)) {
          return
        }
        if (!byDay[dKey]) {
          byDay[dKey] = []
        }
        byDay[dKey].push(y)
      })
    }
    let totalKwhM2 = 0
    for (const arr of Object.values(byDay)) {
      const avgWm2 = arr.reduce((s, v) => s + v, 0) / arr.length
      totalKwhM2 += (avgWm2 * 24) / 1000
    }
    return totalKwhM2
  }, [
    poaTimeseriesQuery.data,
    project.data?.time_zone,
    rangeStartStr,
    rangeEndStr,
  ])

  // KPI data for stats (entire selected range, one value per day).
  const dailyKpiData = useGetOperationalKPIData({
    queryParams: {
      project_ids: [projectId || ''],
      kpi_type_ids: [
        KPITypeEnum.PV_INVERTER_MECHANICAL_AVAILABILITY,
        KPITypeEnum.PROJECT_ENERGY_PRODUCTION,
        KPITypeEnum.PV_INVERTER_ENERGY_PRODUCTION,
        KPITypeEnum.PV_INVERTER_MODULE_ENERGY_PRODUCTION,
        KPITypeEnum.PERFORMANCE_RATIO,
        KPITypeEnum.PV_PROJECT_EXPECTED_ENERGY_DELIVERED,
        KPITypeEnum.PV_PROJECT_CURTAILMENT,
      ],
      start: rangeStartStr || '',
      end: rangeEndExclusiveStr || '',
      include_device_data: false,
      include_all_dates: true,
    },
    queryOptions: {
      enabled: !!projectId && !!rangeStartStr && !!rangeEndExclusiveStr,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 24 * 60 * 60 * 1000, // 24 hours
      gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days
    },
  })

  // Fetch trailing period KPI data for chart (generation and expected generation).
  // For PVS we need PV-only generation for the chart.
  const trailingKpiData = useGetOperationalKPIData({
    queryParams: {
      project_ids: [projectId || ''],
      kpi_type_ids: [
        KPITypeEnum.PROJECT_ENERGY_PRODUCTION,
        KPITypeEnum.PV_INVERTER_ENERGY_PRODUCTION,
        KPITypeEnum.PV_INVERTER_MODULE_ENERGY_PRODUCTION,
        KPITypeEnum.PV_PROJECT_EXPECTED_ENERGY_DELIVERED,
      ],
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

  const eventsData = useGetEventsSummary({
    pathParams: { projectId: projectId || '' },
    queryParams: {
      start: rangeStartStr ? `${rangeStartStr} 00:00:00` : undefined,
      end: rangeEndStr ? `${rangeEndStr} 23:59:59` : undefined,
      open: false, // false means no filter, so returns both open and closed events
    },
    queryOptions: {
      enabled: !!projectId && !!rangeStartStr && !!rangeEndStr,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 24 * 60 * 60 * 1000, // 24 hours
      gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days
    },
  })

  const combinerHealthKpiData = useGetOperationalKPIData({
    queryParams: {
      project_ids: [projectId || ''],
      kpi_type_ids: [KPITypeEnum.PV_DC_COMBINER_FIELD_HEALTH],
      start: rangeStartStr || '',
      end: rangeEndExclusiveStr || '',
      include_device_data: true,
      include_all_dates: true,
    },
    queryOptions: {
      enabled: !!projectId && !!rangeStartStr && !!rangeEndExclusiveStr,
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
      kpi_type_ids: [KPITypeEnum.PROJECT_ENERGY_PRODUCTION],
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
      device_type_ids: [DeviceTypeEnum.PV_DC_COMBINER],
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
  const combinerKpiType: KPIType = {
    kpi_type_id: KPITypeEnum.PV_DC_COMBINER_FIELD_HEALTH,
    name_long: 'DC Combiner Field Health', // noqa: hardcoded-name-long
    name_short: 'DC Combiner Field Health', // noqa: hardcoded-name-short
    name_metric: 'DC Combiner Field Health',
    description: 'DC Combiner Field Health',
    unit: '%',
    aggregation_method: 'average',
    device_type_id: DeviceTypeEnum.PV_DC_COMBINER,
  }

  // Fetch daily aggregated budgeted series data
  // Ensure we include the selected date by using it as end_date (API is inclusive)
  const dailyBudgetedDataQuery = useGetPVBudgetedSeriesDailyData({
    pathParams: {
      pv_budgeted_series_id: stableSelectedSeriesId
        ? parseInt(stableSelectedSeriesId)
        : 0,
    },
    queryParams: {
      project_id: projectId || '',
      start_date: trailingStart || '',
      end_date: rangeEndStr || '',
      degradation_rate: degradationRate,
    },
    queryOptions: {
      enabled:
        !!projectId &&
        !!stableSelectedSeriesId &&
        !!trailingStart &&
        !!rangeEndStr,
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
  }, [dailyBudgetedDataQuery.data, project.data, degradationRate])

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

  // Fetch KPI types for Performance Ratio (34) and PCS Mechanical Availability (1)
  const kpiTypesQuery = useGetKPITypes({
    queryParams: {
      kpi_type_ids: [
        KPITypeEnum.PV_INVERTER_MECHANICAL_AVAILABILITY,
        KPITypeEnum.PERFORMANCE_RATIO,
      ],
    },
    queryOptions: {
      enabled: true,
      refetchOnWindowFocus: false,
      staleTime: Infinity,
    },
  })

  // Create a map of KPI type ID to description
  const kpiTypeDescriptions = useMemo(() => {
    if (!kpiTypesQuery.data) return {} as Record<number, string>
    const map: Record<number, string> = {}
    kpiTypesQuery.data.forEach((kpiType) => {
      if (kpiType.description) {
        map[kpiType.kpi_type_id] = kpiType.description
      }
    })
    return map
  }, [kpiTypesQuery.data])

  const generationBudgetInfo = useMemo(() => {
    if (
      !processedBudgetedData ||
      !rangeStartStr ||
      !rangeEndStr ||
      !dailyKpiData.data
    ) {
      return null
    }

    let budgetedMWh = 0
    processedBudgetedData.dates.forEach((dateStr, i) => {
      if (dateStr < rangeStartStr || dateStr > rangeEndStr) {
        return
      }
      if (budgetedComparisonMode === '15days') {
        const startIndex = Math.max(0, i - 15)
        const endIndex = Math.min(
          processedBudgetedData.dates.length - 1,
          i + 15,
        )
        const budgetedValues = processedBudgetedData.budgetedData
          .slice(startIndex, endIndex + 1)
          .filter((val): val is number => val != null)
        if (budgetedValues.length === 0) {
          return
        }
        budgetedMWh +=
          budgetedValues.reduce((sum, val) => sum + val, 0) /
          budgetedValues.length
      } else {
        const v = processedBudgetedData.budgetedData[i]
        if (v != null) {
          budgetedMWh += v
        }
      }
    })

    if (budgetedMWh === 0) {
      return null
    }

    const poiKpi = dailyKpiData.data.find(
      (kpi: OperationalKPIData) =>
        kpi.kpi_type_id === KPITypeEnum.PROJECT_ENERGY_PRODUCTION,
    )
    const pvKpi = dailyKpiData.data.find(
      (kpi: OperationalKPIData) =>
        kpi.kpi_type_id === KPITypeEnum.PV_INVERTER_ENERGY_PRODUCTION,
    )
    const pvModuleKpi = dailyKpiData.data.find(
      (kpi: OperationalKPIData) =>
        kpi.kpi_type_id === KPITypeEnum.PV_INVERTER_MODULE_ENERGY_PRODUCTION,
    )
    const isPvsLocal = project.data?.project_type_id === ProjectTypeEnum.PVS
    const generationMWh = isPvsLocal
      ? sumKpiInDateRange(pvKpi, rangeStartStr, rangeEndStr) ||
        sumKpiInDateRange(pvModuleKpi, rangeStartStr, rangeEndStr)
      : sumKpiInDateRange(poiKpi, rangeStartStr, rangeEndStr)

    return {
      percentage: (generationMWh / budgetedMWh) * 100,
      budgetedMWh,
    }
  }, [
    processedBudgetedData,
    rangeStartStr,
    rangeEndStr,
    dailyKpiData.data,
    budgetedComparisonMode,
    project.data?.project_type_id,
  ])

  const irradianceBudgetInfo = useMemo(() => {
    if (
      !budgetedDataQuery.data ||
      !rangeStart ||
      !rangeEnd ||
      !rangeStartStr ||
      !rangeEndStr ||
      !project.data?.time_zone
    ) {
      return null
    }
    const tz = project.data.time_zone
    let budgetedPOASumkWh = 0
    for (
      let d = rangeStart.startOf('day');
      !d.isAfter(rangeEnd.startOf('day'));
      d = d.add(1, 'day')
    ) {
      if (budgetedComparisonMode === '15days') {
        const targetMMDDs = new Set<string>()
        for (let i = -15; i <= 15; i++) {
          targetMMDDs.add(d.add(i, 'days').format('MM-DD'))
        }
        const filteredData = budgetedDataQuery.data.filter((item) => {
          const itemDate = dayjs.utc(item.time).tz(tz)
          return targetMMDDs.has(itemDate.format('MM-DD'))
        })
        if (filteredData.length === 0) {
          continue
        }
        const poaValues = filteredData
          .map((item) => item.poa as number | null)
          .filter((val): val is number => val != null && val !== undefined)
        if (poaValues.length === 0) {
          continue
        }
        const averageHourlyPOAWh =
          poaValues.reduce((sum, val) => sum + val, 0) / poaValues.length
        budgetedPOASumkWh += (averageHourlyPOAWh * 24) / 1000
      } else {
        const selectedDateData = budgetedDataQuery.data.filter(
          (item) =>
            dayjs.utc(item.time).tz(tz).format('MM-DD') === d.format('MM-DD'),
        )
        if (selectedDateData.length === 0) {
          continue
        }
        const budgetedPOASumWh = selectedDateData.reduce((sum, item) => {
          const originalPOA = item.poa as number | null
          return sum + (originalPOA || 0)
        }, 0)
        budgetedPOASumkWh += budgetedPOASumWh / 1000
      }
    }

    if (budgetedPOASumkWh === 0) {
      return null
    }

    const actualIrradiance = calculatedIrradiance ?? 0

    return {
      percentage: (actualIrradiance / budgetedPOASumkWh) * 100,
      budgetedPOASumkWh,
    }
  }, [
    budgetedDataQuery.data,
    rangeStart,
    rangeEnd,
    rangeStartStr,
    rangeEndStr,
    calculatedIrradiance,
    project.data?.time_zone,
    budgetedComparisonMode,
  ])

  // For PV+Storage projects use PV-only generation (circuit/inverters), not POI.
  const isPvs = project.data?.project_type_id === ProjectTypeEnum.PVS

  const dailyActualExpected = useMemo(() => {
    const lo = rangeStartStr
    const hi = rangeEndStr
    const poiKpi = dailyKpiData.data?.find(
      (kpi: OperationalKPIData) =>
        kpi.kpi_type_id === KPITypeEnum.PROJECT_ENERGY_PRODUCTION,
    )
    const pvPcsKpi = dailyKpiData.data?.find(
      (kpi: OperationalKPIData) =>
        kpi.kpi_type_id === KPITypeEnum.PV_INVERTER_ENERGY_PRODUCTION,
    )
    const pvPcsModuleKpi = dailyKpiData.data?.find(
      (kpi: OperationalKPIData) =>
        kpi.kpi_type_id === KPITypeEnum.PV_INVERTER_MODULE_ENERGY_PRODUCTION,
    )
    const expectedKpi = dailyKpiData.data?.find(
      (kpi: OperationalKPIData) =>
        kpi.kpi_type_id === KPITypeEnum.PV_PROJECT_EXPECTED_ENERGY_DELIVERED,
    )
    const curtailmentKpi = dailyKpiData.data?.find(
      (kpi: OperationalKPIData) =>
        kpi.kpi_type_id === KPITypeEnum.PV_PROJECT_CURTAILMENT,
    )
    const fromWaterfall = waterfallActualExpected
    if (!lo || !hi) {
      return {
        actualMWh: 0,
        expectedMWh: 0,
        curtailmentMWh: 0,
        poiMWh: 0,
        fromWaterfall,
      }
    }
    const actualMWh = fromWaterfall
      ? fromWaterfall.actualMWh
      : isPvs
        ? sumKpiInDateRange(pvPcsKpi, lo, hi) ||
          sumKpiInDateRange(pvPcsModuleKpi, lo, hi)
        : sumKpiInDateRange(poiKpi, lo, hi)
    const expectedMWh = fromWaterfall
      ? fromWaterfall.expectedMWh
      : sumKpiInDateRange(expectedKpi, lo, hi)
    const curtailmentMWh = sumKpiInDateRange(curtailmentKpi, lo, hi)
    const poiMWh = sumKpiInDateRange(poiKpi, lo, hi)
    return {
      actualMWh,
      expectedMWh,
      curtailmentMWh,
      poiMWh,
      fromWaterfall,
    }
  }, [
    dailyKpiData.data,
    isPvs,
    waterfallActualExpected,
    rangeStartStr,
    rangeEndStr,
  ])

  // Calculate stats for StatsGrid
  const stats = useMemo(() => {
    const availabilityKpi = dailyKpiData.data?.find(
      (kpi: OperationalKPIData) =>
        kpi.kpi_type_id === KPITypeEnum.PV_INVERTER_MECHANICAL_AVAILABILITY,
    )
    const {
      actualMWh: generationMWh,
      expectedMWh,
      curtailmentMWh,
      poiMWh,
      fromWaterfall,
    } = dailyActualExpected
    const ppaRate = project.data?.ppa?.rate || 0
    const revenue = poiMWh * ppaRate

    // Calculate Performance Index = (actual / expected) * 100
    const performanceIndex =
      expectedMWh > 0 ? (generationMWh / expectedMWh) * 100 : 0
    const irradianceKWhM2 = calculatedIrradiance ?? 0

    const lo = rangeStartStr ?? ''
    const hi = rangeEndStr ?? ''
    const availability =
      lo && hi
        ? avgKpiInDateRange(availabilityKpi, lo, hi)
        : availabilityKpi?.data?.project_data?.[0] || 0

    const totalEvents = eventsData.data?.length || 0
    const openEvents =
      eventsData.data?.filter((event: EventSummary) => !event.time_end)
        ?.length || 0
    const closedEvents = totalEvents - openEvents

    // Build Project Generation description (sensor type for waterfall source)
    let generationDescription = fromWaterfall
      ? isPvs
        ? 'PV Energy Output (PV MV circuit meter)'
        : 'PV Energy Output (POI)'
      : isPvs
        ? 'Cumulative PV circuit/inverter generation (PV-only, excludes storage)'
        : 'Total project generation'
    if (curtailmentMWh !== 0) {
      generationDescription += `. Energy curtailment: ${curtailmentMWh.toFixed(1)} MWh`
    }

    const generationKpiTypeId = isPvs
      ? undefined
      : KPITypeEnum.PROJECT_ENERGY_PRODUCTION
    return [
      {
        title: 'Project Generation',
        value: `${Math.round(generationMWh).toLocaleString('en-US')} MWh${
          curtailmentMWh !== 0 ? '*' : ''
        }`,
        subtitle: generationBudgetInfo
          ? `${generationBudgetInfo.percentage.toFixed(0)}% of Budgeted`
          : undefined,
        icon: IconBolt,
        description: generationDescription,
        ...(generationKpiTypeId != null && {
          kpiTypeId: generationKpiTypeId,
          link: `/projects/${projectId}/kpis/type/${generationKpiTypeId}`,
        }),
      },
      {
        title: 'Resource (Insolation)',
        value: `${irradianceKWhM2.toFixed(2)} kWh/m²`,
        subtitle: irradianceBudgetInfo
          ? `${irradianceBudgetInfo.percentage.toFixed(0)}% of Budgeted`
          : undefined,
        icon: IconSun,
        description: 'Total irradiation over the selected period',
      },
      {
        title: 'Revenue',
        value:
          revenue > 0
            ? `$${revenue.toLocaleString('en-US', { maximumFractionDigits: 0 })}`
            : 'N/A',
        subtitle:
          ppaRate > 0 ? `PPA Price: $${ppaRate.toFixed(2)}/MWh` : undefined,
        subtitleEditHref:
          ppaRate > 0
            ? `/projects/${projectId}/settings?tab=project-info`
            : undefined,
        icon: IconCurrencyDollar,
        description: 'Estimated revenue for the selected period (POI)',
      },
      {
        title: 'Performance Index',
        value: `${performanceIndex.toFixed(2)}%${curtailmentMWh !== 0 ? '*' : ''}`,
        subtitle: 'Actual vs Expected',
        icon: IconChartBar,
        description: fromWaterfall
          ? `Actual: PV Energy Output${isPvs ? ' (PV MV circuit meter)' : ' (POI)'}. Expected: PV Expected.${
              curtailmentMWh !== 0
                ? ` Energy curtailment: ${curtailmentMWh.toFixed(1)} MWh`
                : ''
            }`
          : `Performance Index: ratio of actual generation to expected generation for the selected period. Note: Expected energy does not take curtailment into account.${
              curtailmentMWh !== 0
                ? ` Energy curtailment: ${curtailmentMWh.toFixed(1)} MWh`
                : ''
            }`,
      },
      {
        title: 'Events',
        value: totalEvents.toLocaleString('en-US'),
        subtitle: `${openEvents.toLocaleString('en-US')} open, ${closedEvents.toLocaleString(
          'en-US',
        )} closed`,
        icon: IconExclamationCircle,
        description: 'Total events in the selected period (open and closed)',
        link: `/projects/${projectId}/events`,
      },
      {
        title: 'PCS Mech. Availability',
        value: `${(availability * 100).toFixed(2)}%${curtailmentMWh !== 0 ? '*' : ''}`,
        subtitle: 'Avg. mechanical availability',
        icon: IconCash,
        description: `${
          kpiTypeDescriptions[1] ||
          'PCS mechanical availability averaged over the selected period'
        }${curtailmentMWh !== 0 ? `. Energy curtailment: ${curtailmentMWh.toFixed(1)} MWh` : ''}`,
        kpiTypeId: KPITypeEnum.PV_INVERTER_MECHANICAL_AVAILABILITY,
        link: `/projects/${projectId}/kpis/type/1`,
      },
    ]
  }, [
    dailyActualExpected,
    dailyKpiData.data,
    eventsData.data,
    generationBudgetInfo,
    irradianceBudgetInfo,
    calculatedIrradiance,
    isPvs,
    project.data?.ppa?.rate,
    projectId,
    kpiTypeDescriptions,
    rangeStartStr,
    rangeEndStr,
  ])

  // Create 30-day energy chart data
  const energyChartData = useMemo(() => {
    // Early return if we don't have essential data yet
    if (!rangeEnd || !trailingPeriod) {
      return []
    }

    const poiKpi = trailingKpiData.data?.find(
      (kpi: OperationalKPIData) =>
        kpi.kpi_type_id === KPITypeEnum.PROJECT_ENERGY_PRODUCTION,
    )
    const pvPcsKpi = trailingKpiData.data?.find(
      (kpi: OperationalKPIData) =>
        kpi.kpi_type_id === KPITypeEnum.PV_INVERTER_ENERGY_PRODUCTION,
    )
    const pvPcsModuleKpi = trailingKpiData.data?.find(
      (kpi: OperationalKPIData) =>
        kpi.kpi_type_id === KPITypeEnum.PV_INVERTER_MODULE_ENERGY_PRODUCTION,
    )
    // PV+Storage: prefer PV Inverter energy; fall back to POI for chart only when no PV Inverter data
    const generationKpi = isPvs
      ? (pvPcsKpi ?? pvPcsModuleKpi ?? poiKpi)
      : poiKpi

    const expectedKpi = trailingKpiData.data?.find(
      (kpi: OperationalKPIData) =>
        kpi.kpi_type_id === KPITypeEnum.PV_PROJECT_EXPECTED_ENERGY_DELIVERED,
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

        const traces: Partial<Plotly.Data>[] = []
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
              color: theme.colors.violet[7],
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
            line: { width: 2, dash: 'dot', color: theme.colors.violet[7] },
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
      displayData = actualData.reduce(
        (
          acc: { values: (number | null)[]; lastSum: number },
          val: number | null,
        ) => {
          if (val === null) {
            // If current value is null, keep it as null to create a gap
            acc.values.push(null)
          } else {
            // Add to the last cumulative value (not reset to 0)
            acc.lastSum += val
            acc.values.push(acc.lastSum)
          }
          return acc
        },
        { values: [], lastSum: 0 },
      ).values
    }

    const traces: Partial<Plotly.Data>[] = []

    if (energyView === 'daily') {
      // For daily view, use column chart for actual data
      traces.push({
        x: dates,
        y: displayData,
        name: 'Actual',
        type: 'bar' as const,
        width: 0.6, // Make bars narrower to leave space for box plots
        marker: { color: theme.colors.green[7] },
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
        line: { width: 2, color: theme.colors.green[7] },
      })
    }

    // Calculate percentage differences for legend
    // Get the final actual value (last point for cumulative, or sum for daily)
    const getFinalActualValue = (): number | null => {
      if (displayData.length === 0) return null
      if (energyView === 'cumulative') {
        const lastValue = displayData[displayData.length - 1]
        return typeof lastValue === 'number' ? lastValue : null
      } else {
        // For daily view, sum all values
        return displayData.reduce((sum: number, val) => {
          return sum + (typeof val === 'number' && val !== null ? val : 0)
        }, 0)
      }
    }

    const finalActualValue = getFinalActualValue()

    // Process Expected Energy (KPI 102)
    let expectedDisplayData: (number | null)[] = []
    if (expectedKpi?.data?.dates && expectedKpi?.data?.project_data) {
      try {
        // Align expected data with actual data dates
        const expectedDates = expectedKpi.data.dates
        const expectedValues = expectedKpi.data.project_data

        const alignedExpectedData = dates.map((date) => {
          const index = expectedDates.indexOf(date)
          if (index >= 0) {
            return expectedValues[index]
          }
          return null
        })

        // Calculate cumulative if needed
        if (energyView === 'cumulative') {
          expectedDisplayData = alignedExpectedData.reduce(
            (
              acc: { values: (number | null)[]; lastSum: number },
              val: number | null,
            ) => {
              if (val === null) {
                acc.values.push(acc.lastSum > 0 ? acc.lastSum : null)
              } else {
                acc.lastSum += val
                acc.values.push(acc.lastSum)
              }
              return acc
            },
            { values: [], lastSum: 0 },
          ).values
        } else {
          expectedDisplayData = alignedExpectedData
        }

        // Calculate percentage difference for Expected
        const getFinalExpectedValue = (): number | null => {
          if (expectedDisplayData.length === 0) return null
          if (energyView === 'cumulative') {
            const lastValue =
              expectedDisplayData[expectedDisplayData.length - 1]
            return typeof lastValue === 'number' ? lastValue : null
          } else {
            return expectedDisplayData.reduce((sum: number, val) => {
              return sum + (typeof val === 'number' && val !== null ? val : 0)
            }, 0)
          }
        }

        const finalExpectedValue = getFinalExpectedValue()
        let expectedName = 'Expected'
        if (
          finalActualValue !== null &&
          finalActualValue !== 0 &&
          finalExpectedValue !== null
        ) {
          const expectedDiff =
            ((finalExpectedValue - finalActualValue) / finalActualValue) * 100
          const sign = expectedDiff >= 0 ? '+' : ''
          expectedName = `Expected (${sign}${expectedDiff.toFixed(1)}%)`
        }

        if (energyView === 'daily') {
          traces.push({
            x: dates,
            y: expectedDisplayData,
            name: expectedName,
            type: 'scatter' as const,
            mode: 'lines+markers' as const,
            line: { width: 2, color: theme.colors.orange[7] },
            marker: { size: 6 },
          })
        } else {
          traces.push({
            x: dates,
            y: expectedDisplayData,
            name: expectedName,
            type: 'scatter' as const,
            mode: 'lines' as const,
            connectgaps: false,
            line: { width: 2, color: theme.colors.orange[7] },
          })
        }
      } catch {
        // Ignore errors in expected data processing
      }
    }

    // Process budgeted data if available (use pre-processed data)
    if (processedBudgetedData) {
      try {
        // Align budgeted data with actual data dates
        // If exact date match fails, try MM-DD match (for historical dates)
        const budgetedData = dates.map((date) => {
          const budgetedIndex = processedBudgetedData.dates.indexOf(date)
          if (budgetedIndex >= 0) {
            return processedBudgetedData.budgetedData[budgetedIndex]
          }
          // Try MM-DD match for historical dates
          const dateMMDD = dayjs(date).format('MM-DD')
          const mmddMatchIndex = processedBudgetedData.dates.findIndex(
            (bd) => dayjs(bd).format('MM-DD') === dateMMDD,
          )
          return mmddMatchIndex >= 0
            ? processedBudgetedData.budgetedData[mmddMatchIndex]
            : null
        })

        // Calculate cumulative if needed
        let budgetedDisplayData = budgetedData
        if (energyView === 'cumulative') {
          budgetedDisplayData = budgetedData.reduce(
            (
              acc: { values: (number | null)[]; lastSum: number },
              val: number | null,
            ) => {
              if (val === null) {
                // If current value is null, use the last cumulative value to maintain continuity
                // This ensures the final point has a value for the annotation
                acc.values.push(acc.lastSum > 0 ? acc.lastSum : null)
              } else {
                // Add to the last cumulative value (not reset to 0)
                acc.lastSum += val
                acc.values.push(acc.lastSum)
              }
              return acc
            },
            { values: [], lastSum: 0 },
          ).values
        }

        // Calculate percentage difference for Budgeted
        const getFinalBudgetedValue = (): number | null => {
          if (budgetedDisplayData.length === 0) return null
          if (energyView === 'cumulative') {
            const lastValue =
              budgetedDisplayData[budgetedDisplayData.length - 1]
            return typeof lastValue === 'number' ? lastValue : null
          } else {
            return budgetedDisplayData.reduce((sum: number, val) => {
              return sum + (typeof val === 'number' && val !== null ? val : 0)
            }, 0)
          }
        }

        const finalBudgetedValue = getFinalBudgetedValue()
        let budgetedName = 'Budgeted'
        if (
          finalActualValue !== null &&
          finalActualValue !== 0 &&
          finalBudgetedValue !== null
        ) {
          const budgetedDiff =
            ((finalBudgetedValue - finalActualValue) / finalActualValue) * 100
          const sign = budgetedDiff >= 0 ? '+' : ''
          budgetedName = `Budgeted (${sign}${budgetedDiff.toFixed(1)}%)`
        }

        if (energyView === 'daily') {
          // For daily view, use simple markers for budgeted data
          traces.push({
            x: dates,
            y: budgetedDisplayData,
            name: budgetedName,
            type: 'scatter' as const,
            mode: 'markers' as const,
            marker: {
              size: 8,
              symbol: 'diamond',
              color: theme.colors.violet[7],
            },
          })
        } else {
          // For cumulative view, use line chart
          traces.push({
            x: dates,
            y: budgetedDisplayData,
            name: budgetedName,
            type: 'scatter' as const,
            mode: 'lines' as const,
            connectgaps: false, // Show gaps for missing data
            line: { width: 2, dash: 'dot', color: theme.colors.violet[7] },
          })
        }
      } catch {
        // Continue without budgeted data rather than breaking the chart
      }
    }

    return traces
  }, [
    isPvs,
    trailingKpiData.data,
    energyView,
    processedBudgetedData,
    rangeEnd,
    trailingPeriod,
    theme.colors.orange,
    theme.colors.violet,
    theme.colors.green,
  ])

  const energyChartHighlightShapes = useMemo(
    () =>
      rangeStartStr && rangeEndStr
        ? [
            {
              fillcolor: 'rgba(34, 197, 94, 0.22)',
              layer: 'below' as const,
              line: { width: 0 },
              type: 'rect' as const,
              xref: 'x' as const,
              x0: rangeStartStr,
              x1: rangeEndStr,
              y0: 0,
              y1: 1,
              yref: 'paper' as const,
            },
          ]
        : [],
    [rangeStartStr, rangeEndStr],
  )

  // Calculate performance summary for the trailing period
  const performanceSummary = useMemo(() => {
    if (!energyChartData.length || energyView !== 'cumulative') {
      return null
    }

    // Find the actual and budgeted traces
    const actualTrace = energyChartData.find(
      (trace: Partial<Plotly.Data>) => trace.name === 'Actual',
    )
    const budgetedTrace = energyChartData.find(
      (trace: Partial<Plotly.Data>) => trace.name === 'Budgeted',
    )

    if (!actualTrace || !budgetedTrace) {
      return null
    }

    const actualY = (actualTrace as { y?: unknown[] }).y
    const budgetedY = (budgetedTrace as { y?: unknown[] }).y

    if (
      !Array.isArray(actualY) ||
      !Array.isArray(budgetedY) ||
      actualY.length === 0 ||
      budgetedY.length === 0
    ) {
      return null
    }

    // Get the final values (last point in the cumulative data)
    const actualFinal = actualY[actualY.length - 1] as number
    const budgetedFinal = budgetedY[budgetedY.length - 1] as number

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

  const weeklyTrailingEnergyChartLayout = useMemo(() => {
    const legendBg =
      colorScheme === 'dark' ? 'rgba(37,38,43,0.8)' : 'rgba(255,255,255,0.8)'
    const legendBorder =
      colorScheme === 'dark' ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)'

    const annotations =
      performanceSummary && energyView === 'cumulative'
        ? (() => {
            const firstTrace = energyChartData[0] as { x?: unknown[] }
            const firstTraceX = firstTrace?.x
            const xValue =
              Array.isArray(firstTraceX) && firstTraceX.length > 0
                ? (firstTraceX[firstTraceX.length - 1] as string | number)
                : undefined
            return [
              {
                x: xValue,
                y:
                  (performanceSummary.actual + performanceSummary.budgeted) / 2,
                text: `${performanceSummary.isExceeded ? '+' : '-'}${performanceSummary.percent.toFixed(1)}%`,
                showarrow: false,
                font: {
                  color: performanceSummary.isExceeded ? '#00C853' : '#FF5722',
                  size: 40,
                  family: 'Arial, sans-serif',
                  weight: 900,
                },
              },
            ]
          })()
        : []

    return {
      autosize: true,
      xaxis: {
        title: { text: 'Date' },
        type: 'category' as const,
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
        xref: 'paper' as const,
        yref: 'paper' as const,
        x: 0.01,
        y: 0.99,
        xanchor: 'left' as const,
        yanchor: 'top' as const,
        orientation: 'h' as const,
        bgcolor: legendBg,
        bordercolor: legendBorder,
        borderwidth: 1,
        itemsizing: 'constant' as const,
      },
      hovermode:
        energyView === 'daily' ? ('closest' as const) : ('x unified' as const),
      barmode: energyView === 'daily' ? ('overlay' as const) : undefined,
      margin: { l: 60, r: 30, t: 30, b: 60 },
      shapes: energyChartHighlightShapes,
      annotations,
    }
  }, [
    colorScheme,
    energyView,
    energyChartHighlightShapes,
    performanceSummary,
    energyChartData,
  ])

  const navigate = useNavigate()
  const [navigateType, setNavigateType] = useState<'newTab' | 'navigate'>(
    'navigate',
  )

  // Table columns for events (similar to ProjectEvents.tsx)
  const eventsColumns = useMemo<MRT_ColumnDef<EventSummary>[]>(
    () => [
      {
        header: '',
        accessorKey: 'actions',
        enableSorting: false,
        enableColumnFilter: false,
        enableColumnActions: false,
        size: 24,
        Cell: ({ cell }: { cell: MRT_Cell<EventSummary> }) => (
          <ActionIcon
            onMouseEnter={() => {
              setNavigateType('newTab')
            }}
            onMouseLeave={() => {
              setNavigateType('navigate')
            }}
            variant="transparent"
            onClick={() => {
              window.open(
                `${window.location.origin}/projects/${projectId}/events/event/?eventId=${cell.row.original.event_id}`,
              )
            }}
          >
            <IconExternalLink size={16} />
          </ActionIcon>
        ),
      },
      {
        header: 'Device Type',
        accessorKey: 'device_type_name',
      },
      {
        header: 'Device',
        accessorKey: 'device_name_full',
      },
      {
        header: 'Daily Loss ($)',
        accessorKey: 'loss_daily_financial',
        aggregationFn: 'sum',
        mantineTableHeadCellProps: {
          align: 'right',
        },
        mantineTableBodyCellProps: {
          align: 'right',
        },
        Cell: ({ cell }: { cell: MRT_Cell<EventSummary> }) => (
          <Text size="sm">
            {cell.getValue<number | null>() !== null
              ? cell.getValue<number>().toLocaleString('en-US', {
                  style: 'currency',
                  currency: 'USD',
                })
              : ''}
          </Text>
        ),
        AggregatedCell: ({ cell }: { cell: MRT_Cell<EventSummary> }) => (
          <Text size="sm">
            {cell.getValue<number | null>() !== null &&
            cell.getValue<number>() !== 0
              ? cell.getValue<number>().toLocaleString('en-US', {
                  style: 'currency',
                  currency: 'USD',
                })
              : ''}
          </Text>
        ),
      },
      {
        header: 'Start Time',
        accessorKey: 'time_start',
        Cell: ({ cell }: { cell: MRT_Cell<EventSummary> }) => (
          <Text size="sm">
            {dayjs(cell.getValue<string>())
              .tz(project.data?.time_zone)
              .format('MM/DD/YYYY HH:mm:ss')}
          </Text>
        ),
      },
      {
        header: 'End Time',
        accessorKey: 'time_end',
        Cell: ({ cell }: { cell: MRT_Cell<EventSummary> }) => (
          <Text size="sm">
            {cell.getValue<string | null>() !== null
              ? dayjs(cell.getValue<string>())
                  .tz(project.data?.time_zone)
                  .format('MM/DD/YYYY HH:mm:ss')
              : ''}
          </Text>
        ),
      },
      {
        header: 'Failure Mode',
        accessorKey: 'failure_mode',
      },
      {
        header: 'Root Cause',
        accessorKey: 'root_cause',
      },
      {
        header: 'Daily Loss (MWh)',
        accessorKey: 'loss_daily_energy',
        aggregationFn: 'sum',
        mantineTableHeadCellProps: {
          align: 'right',
        },
        mantineTableBodyCellProps: {
          align: 'right',
        },
        Cell: ({ cell }: { cell: MRT_Cell<EventSummary> }) => (
          <Text size="sm">
            {cell.getValue<number | null>() !== null
              ? `${cell.getValue<number>().toLocaleString('en-US', {
                  style: 'decimal',
                  maximumFractionDigits: 2,
                  minimumFractionDigits: 2,
                })} MWh`
              : ''}
          </Text>
        ),
        AggregatedCell: ({ cell }: { cell: MRT_Cell<EventSummary> }) => (
          <Text size="sm">
            {cell.getValue<number | null>() !== null &&
            cell.getValue<number>() !== 0
              ? `${cell.getValue<number>().toLocaleString('en-US', {
                  style: 'decimal',
                  maximumFractionDigits: 2,
                  minimumFractionDigits: 2,
                })} MWh`
              : ''}
          </Text>
        ),
      },
    ],
    [project.data?.time_zone, projectId],
  )

  const eventsTable = useMantineReactTable({
    columns: eventsColumns,
    data: eventsData.data ?? [],
    enableGrouping: true,
    enableColumnDragging: false,
    initialState: {
      density: 'xs',
      grouping: ['device_type_name'],
      sorting: [{ id: 'loss_daily_financial', desc: true }],
    },
    mantineTableBodyRowProps: ({ row }) => ({
      onClick: () => {
        if (row.subRows?.length == 0 && navigateType == 'navigate') {
          navigate(
            `/projects/${projectId}/events/event/?eventId=${row.original.event_id}`,
          )
        }
      },
      style: {
        cursor: row.subRows?.length == 0 ? 'pointer' : 'default',
      },
    }),
  })

  const aiStats = useMemo((): DailyPerformanceStats | null => {
    if (
      !rangeStart ||
      !rangeEnd ||
      !rangeStartStr ||
      !rangeEndStr ||
      !project.data ||
      !dailyKpiData.data ||
      !trailingKpiData.data
    ) {
      return null
    }

    const {
      actualMWh: actualEnergyMWh,
      expectedMWh,
      curtailmentMWh,
      poiMWh,
    } = dailyActualExpected

    // Calculate Performance Index = (actual / expected) * 100
    const performanceIndex =
      expectedMWh > 0 ? (actualEnergyMWh / expectedMWh) * 100 : 0

    // Get budgeted energy for the day
    const budgetedEnergyMWh = generationBudgetInfo?.budgetedMWh || 0
    const energyDifferenceMWh = actualEnergyMWh - budgetedEnergyMWh
    const energyPerformancePercent =
      budgetedEnergyMWh > 0
        ? (energyDifferenceMWh / budgetedEnergyMWh) * 100
        : 0

    // Calculate 30-day trailing statistics (PV-only for PVS)
    const trailingPoiKpi = trailingKpiData.data.find(
      (kpi: OperationalKPIData) =>
        kpi.kpi_type_id === KPITypeEnum.PROJECT_ENERGY_PRODUCTION,
    )
    const trailingPvPcsKpi = trailingKpiData.data.find(
      (kpi: OperationalKPIData) =>
        kpi.kpi_type_id === KPITypeEnum.PV_INVERTER_ENERGY_PRODUCTION,
    )
    const trailingPvPcsModuleKpi = trailingKpiData.data.find(
      (kpi: OperationalKPIData) =>
        kpi.kpi_type_id === KPITypeEnum.PV_INVERTER_MODULE_ENERGY_PRODUCTION,
    )
    const trailingGenerationKpi = isPvs
      ? (trailingPvPcsKpi ?? trailingPvPcsModuleKpi)
      : trailingPoiKpi
    const trailingActualMWh =
      trailingGenerationKpi?.data?.project_data?.reduce(
        (sum: number, value: number | null) => sum + (value || 0),
        0,
      ) || 0

    // Calculate 30-day trailing budgeted using actual budgeted data
    const trailingBudgetedMWh = processedBudgetedData
      ? processedBudgetedData.budgetedData.reduce(
          (sum: number, value: number | null) => sum + (value || 0),
          0,
        )
      : 0
    const trailingDifferenceMWh = trailingActualMWh - trailingBudgetedMWh
    const trailingPerformancePercent =
      trailingBudgetedMWh > 0
        ? (trailingDifferenceMWh / trailingBudgetedMWh) * 100
        : 0

    // Calculate revenue data (POI-based)
    const ppaRate = project.data?.ppa?.rate || 0
    const dailyRevenue = poiMWh * ppaRate

    // Calculate MTD revenue
    const mtdGenerationKpi = mtdKpiData.data?.find(
      (kpi: OperationalKPIData) =>
        kpi.kpi_type_id === KPITypeEnum.PROJECT_ENERGY_PRODUCTION,
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
      date: `${rangeStartStr} – ${rangeEndStr}`,
      project_id: projectId,
      cmms_period_start: startTime || undefined,
      cmms_period_end: endTime || undefined,
      actual_energy_mwh: actualEnergyMWh,
      expected_energy_mwh: expectedMWh,
      budgeted_energy_mwh: budgetedEnergyMWh,
      energy_difference_mwh: energyDifferenceMWh,
      energy_performance_percent: energyPerformancePercent,
      trailing_30_day_actual: trailingActualMWh,
      trailing_30_day_budgeted: trailingBudgetedMWh,
      trailing_30_day_difference: trailingDifferenceMWh,
      trailing_30_day_performance_percent: trailingPerformancePercent,
      // Performance Index and Curtailment
      performance_index: performanceIndex,
      curtailment_mwh: curtailmentMWh,
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
    projectId,
    startTime,
    endTime,
    rangeStart,
    rangeEnd,
    rangeStartStr,
    rangeEndStr,
    project.data,
    dailyKpiData.data,
    trailingKpiData.data,
    mtdKpiData.data,
    eventsData.data,
    generationBudgetInfo,
    processedBudgetedData,
    dailyActualExpected,
    isPvs,
  ])

  // Stats grid only needs these essential queries - budgeted data can load separately
  // Don't block on metStationsQuery, poaTimeseriesQuery, or budgeted queries - they enhance but aren't required
  const isStatsLoading =
    dailyKpiData.isLoading ||
    eventsData.isLoading ||
    project.isLoading ||
    mtdKpiData.isLoading

  // AICard needs trailingKpiData in addition to stats data
  const isAICardLoading = isStatsLoading || trailingKpiData.isLoading

  const isReportPageLoading =
    isAICardLoading ||
    dailyBudgetedDataQuery.isLoading ||
    combinerHealthKpiData.isLoading ||
    combinerDevices.isLoading ||
    budgetedDataQuery.isLoading ||
    waterfallQuery.isLoading ||
    meterPowerPdfGate.isLoading ||
    (meterPowerChartView === 'delta' && eventLossesPdfGate.isLoading)

  const handleExportPdf = () => {
    if (isReportPageLoading) return
    if (!reportRef.current) return
    setIsPdfLoading(true)
    if (colorScheme === 'dark') {
      setIsMapIdle(false)
      setPendingThemeSwitch(true)
      setColorScheme('light')
      return
    }
    setPdfExportRequested(true)
  }

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
            <PageTitle
              order={2}
              info={
                <Stack gap="xs">
                  <Text fw={600}>PV Performance Daily Report</Text>
                  <Text size="sm">
                    This page provides a comprehensive daily performance
                    analysis for PV projects, comparing actual performance
                    against budgeted expectations with customizable degradation
                    adjustments.
                  </Text>
                  <Text size="sm" fw={500} mt="xs">
                    User Inputs:
                  </Text>
                  <List spacing={4} withPadding>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500}>
                          Date Selector:
                        </Text>{' '}
                        Select the date to analyze. All metrics, charts, and
                        events are filtered to show data for this specific day.
                        The date cannot be in the future.
                      </Text>
                    </List.Item>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500}>
                          Budgeted Series:
                        </Text>{' '}
                        Choose which budgeted performance series to use for
                        comparisons. Series can be managed in the{' '}
                        <Link
                          to={`/projects/${projectId}/settings?tab=pv-budgeted`}
                          style={{ textDecoration: 'underline' }}
                        >
                          Settings page
                        </Link>
                        . This affects all budgeted comparisons throughout the
                        report.
                      </Text>
                    </List.Item>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500}>
                          Budgeted Degradation Rate:
                        </Text>{' '}
                        Set the annual degradation percentage (default 0.5%/yr)
                        applied to budgeted data. Degradation is calculated from
                        the project&apos;s Commercial Operation Date (COD) to
                        the selected date. This affects all budgeted values in
                        charts and statistics.
                      </Text>
                    </List.Item>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500}>
                          Budgeted Comparison Toggle:
                        </Text>{' '}
                        Switch between two comparison modes:
                        <List spacing={2} withPadding mt={4}>
                          <List.Item>
                            <Text size="sm">
                              <Text component="span" fw={500}>
                                ± 15 days:
                              </Text>{' '}
                              Uses the average hourly meter power from the
                              budgeted series across ±15 days around the
                              selected date, providing seasonal context. This
                              affects the Meter Power chart, Stats Grid
                              percentages, and Trailing Period chart.
                            </Text>
                          </List.Item>
                          <List.Item>
                            <Text size="sm">
                              <Text component="span" fw={500}>
                                Day of:
                              </Text>{' '}
                              Uses budgeted data for the exact same calendar
                              date (MM-DD) from the budgeted year, adjusted for
                              degradation. This provides a direct year-over-year
                              comparison.
                            </Text>
                          </List.Item>
                        </List>
                      </Text>
                    </List.Item>
                  </List>
                  <Text size="sm" fw={500} mt="xs">
                    Page Components:
                  </Text>
                  <List spacing={4} withPadding>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500}>
                          Stats Grid:
                        </Text>{' '}
                        Shows key metrics (Generation, Resource, Revenue,
                        Performance Index, Events, Availability) with budgeted
                        comparisons based on the selected comparison mode.
                      </Text>
                    </List.Item>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500}>
                          Meter Power Chart:
                        </Text>{' '}
                        Displays 5-minute actual vs. budgeted power, optionally
                        including PPC Active Power Setpoint. Budgeted line
                        reflects the selected comparison mode and degradation
                        rate.
                      </Text>
                    </List.Item>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500}>
                          Trailing Period Energy Chart:
                        </Text>{' '}
                        Shows cumulative or daily energy over a trailing period
                        (default 30 days) with budgeted comparison. Degradation
                        rate affects budgeted values.
                      </Text>
                    </List.Item>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500}>
                          Events Table:
                        </Text>{' '}
                        Lists all events (open and closed) for the selected
                        period, grouped by device type with financial and energy
                        loss details.
                      </Text>
                    </List.Item>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500}>
                          Loss Waterfall:
                        </Text>{' '}
                        Visualizes energy losses for the selected period in a
                        waterfall format.
                      </Text>
                    </List.Item>
                  </List>
                </Stack>
              }
            >
              PV Performance Weekly Report
            </PageTitle>
            <Tooltip
              label="Select up to 7 days (defaults to the past week ending yesterday)"
              withArrow
              multiline
              w={300}
            >
              <AdvancedDatePicker
                maxDays={7}
                defaultRange="past-week"
                includeClearButton={false}
                includeTodayInDateRange={false}
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
            <Tooltip
              label="Toggle between +/- 15 days average or Day of comparison for budgeted data in charts and stats"
              withArrow
              multiline
              w={300}
            >
              <Stack gap={4}>
                <Text size="sm" fw={500}>
                  Budgeted Comparison
                </Text>
                <SegmentedControl
                  value={budgetedComparisonMode}
                  onChange={(value) =>
                    setBudgetedComparisonMode(value as '15days' | 'dayof')
                  }
                  data={[
                    { label: '± 15 days', value: '15days' },
                    { label: 'Day of', value: 'dayof' },
                  ]}
                />
              </Stack>
            </Tooltip>
            <ActionIcon
              size="lg"
              onClick={handleExportPdf}
              loading={isPdfLoading}
              disabled={isReportPageLoading}
            >
              <IconFileTypePdf />
            </ActionIcon>
          </Group>
        </Group>

        {/* Stats Grid */}
        <SimpleGrid cols={{ base: 1, xs: 2, sm: 3, md: 3, lg: 6 }}>
          {isStatsLoading
            ? Array.from({ length: 6 }).map((_, index: number) => (
                <Card
                  key={index}
                  withBorder
                  p="md"
                  radius="md"
                  style={{ height: '100%', minWidth: '140px' }}
                >
                  <Group justify="space-between">
                    <Skeleton height={14} width="60%" />
                    <Skeleton height={20} circle />
                  </Group>
                  <Skeleton height={32} mt={15} width="40%" />
                  <Skeleton height={14} mt={5} width="80%" />
                </Card>
              ))
            : stats.map((stat, index: number) => {
                const Icon = stat.icon
                const cardContent = (
                  <Card
                    withBorder
                    p="md"
                    radius="md"
                    style={{
                      height: '100%',
                      minWidth: '140px',
                      ...(stat.link ? { cursor: 'pointer' } : {}),
                    }}
                  >
                    <Group justify="space-between">
                      <Text size="sm" c="dimmed">
                        {stat.title}
                      </Text>
                      <Icon size="1.2rem" stroke={1.5} />
                    </Group>
                    <Group align="flex-end" gap="xs" mt={15} wrap="nowrap">
                      <Box style={{ flex: 1, minWidth: 0 }}>
                        <AutoFitStatValue>{stat.value}</AutoFitStatValue>
                      </Box>
                    </Group>
                    {'subtitle' in stat &&
                      stat.subtitle &&
                      ('subtitleEditHref' in stat && stat.subtitleEditHref ? (
                        <Group gap={4} mt={5} wrap="nowrap" align="center">
                          <Text
                            size="sm"
                            c="dimmed"
                            style={{ flex: 1, minWidth: 0 }}
                          >
                            {stat.subtitle}
                          </Text>
                          <Tooltip label="Edit in project settings" withArrow>
                            <ActionIcon
                              component={Link}
                              to={stat.subtitleEditHref}
                              variant="transparent"
                              size="xs"
                              color="dimmed"
                              aria-label="Edit PPA price in project settings"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <IconPencil size={12} stroke={1.5} />
                            </ActionIcon>
                          </Tooltip>
                        </Group>
                      ) : (
                        <Text size="sm" c="dimmed" mt={5}>
                          {stat.subtitle}
                        </Text>
                      ))}
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

        <CustomCard
          title={
            rangeStartStr && rangeEndStr
              ? `Meter Power - ${dayjs(rangeStartStr).format('MMM DD, YYYY')} – ${dayjs(rangeEndStr).format('MMM DD, YYYY')}`
              : 'Meter Power - Select date range'
          }
          headerChildren={
            <Group gap="sm" wrap="wrap" justify="flex-end">
              <SegmentedControl
                size="xs"
                value={meterPowerChartView}
                onChange={(v) =>
                  setMeterPowerChartView(v as 'standard' | 'delta')
                }
                data={[
                  { label: 'Standard', value: 'standard' },
                  { label: 'Delta & losses', value: 'delta' },
                ]}
              />
              {meterPowerChartView === 'delta' && (
                <Tooltip label="Moving average window (number of points)">
                  <Select
                    size="xs"
                    w={118}
                    data={[
                      { value: '12', label: '12 pt smooth' },
                      { value: '20', label: '20 pt smooth' },
                      { value: '36', label: '36 pt smooth' },
                    ]}
                    value={String(meterPowerMaWindow)}
                    onChange={(v) => v && setMeterPowerMaWindow(Number(v))}
                  />
                </Tooltip>
              )}
            </Group>
          }
          style={{ minHeight: 'clamp(420px, 52vh, 760px)' }}
          bodyStyle={{
            flex: 1,
            minHeight: 0,
            display: 'flex',
            flexDirection: 'column',
          }}
          info={
            <Stack gap="xs">
              <Text fw={600}>Understanding Meter Power</Text>
              <Text size="sm">
                This chart displays actual meter power compared to budgeted
                power for each day in the selected range. The chart may also
                show the{' '}
                <Text component="span" fw={500}>
                  PPC Active Power Setpoint
                </Text>{' '}
                if available for the project. Use the{' '}
                <Text component="span" fw={500}>
                  Standard
                </Text>{' '}
                /{' '}
                <Text component="span" fw={500}>
                  Delta &amp; losses
                </Text>{' '}
                control on this card to switch views. Use the{' '}
                <Text component="span" fw={500}>
                  Budgeted Comparison
                </Text>{' '}
                toggle at the top of the page to switch between comparison
                modes:
              </Text>
              <List spacing={4} withPadding>
                <List.Item>
                  <Text size="sm">
                    <Text component="span" fw={500}>
                      ± 15 days:
                    </Text>{' '}
                    Shows the average hourly meter power based on the budgeted
                    series uploaded in the{' '}
                    <Link
                      to={`/projects/${projectId}/settings?tab=pv-budgeted`}
                      style={{ textDecoration: 'underline' }}
                    >
                      Settings page
                    </Link>
                    , averaged across ±15 days around the selected date and
                    adjusted for the selected degradation rate.
                  </Text>
                </List.Item>
                <List.Item>
                  <Text size="sm">
                    <Text component="span" fw={500}>
                      Day of:
                    </Text>{' '}
                    Shows the budgeted power for the exact same calendar date
                    (MM-DD) from the budgeted year, adjusted for degradation.
                  </Text>
                </List.Item>
              </List>
              <Text size="sm">
                The{' '}
                <Text component="span" fw={500}>
                  Budgeted Degradation Rate
                </Text>{' '}
                selector at the top controls how much degradation is applied to
                the budgeted data based on the project&apos;s Commercial
                Operation Date (COD) to account for expected performance decline
                over time.
              </Text>
              <Text size="sm" mt="xs">
                <Text component="span" fw={500}>
                  Delta &amp; losses:
                </Text>{' '}
                Shows a smoothed curve of model expected power minus actual
                meter power (positive when output is below expected; window size
                is selectable above); stacked Proximal energy losses by device
                type; and a{' '}
                <Text component="span" fw={500}>
                  Curtailment
                </Text>{' '}
                layer when delivered power is near the PPC active-power setpoint
                (same rule as the PV_PROJECT_CURTAILMENT KPI), as max(0,
                expected &minus; actual) in MW. Loss traces use the same
                5-minute timestamps as the power series (multiple 5-minute loss
                samples in one interval are averaged). The vertical axis is
                megawatts (MW).
              </Text>
            </Stack>
          }
        >
          <WeeklyEnergyComparison
            rangeEnd={rangeEnd}
            rangeStart={rangeStart}
            projectId={projectId}
            degradationRate={degradationRate}
            budgetedDataQuery={budgetedDataQuery}
            comparisonMode={budgetedComparisonMode}
            viewMode={meterPowerChartView}
            movingAverageWindow={meterPowerMaWindow}
          />
        </CustomCard>

        <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
          <Stack gap="md">
            <AICard
              stats={aiStats}
              isLoading={isAICardLoading}
              hasBudgetedSeries={seriesOptions.length > 0}
              hasSelectedDate={!!rangeStart && !!rangeEnd}
            />
            <CustomCard
              title="Events by Device Type"
              info={
                <Stack gap="xs">
                  <Text fw={600}>Understanding Events by Device Type</Text>
                  <Text size="sm">
                    This table displays all events (both open and closed) that
                    occurred in the selected period, grouped by device type.
                  </Text>
                  <Text size="sm" fw={500}>
                    Event Information:
                  </Text>
                  <List spacing={4} withPadding>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500}>
                          Daily Loss ($):
                        </Text>{' '}
                        The financial impact of the event for the selected day.
                      </Text>
                    </List.Item>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500}>
                          Daily Loss (MWh):
                        </Text>{' '}
                        The energy loss associated with the event for the
                        selected day.
                      </Text>
                    </List.Item>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500}>
                          Failure Mode & Root Cause:
                        </Text>{' '}
                        Classification of the event type and underlying cause.
                      </Text>
                    </List.Item>
                  </List>
                  <Text size="sm">
                    Events are automatically grouped by device type. Click on
                    any row to view detailed event information, or use the
                    external link icon to open the event in a new tab.
                    Aggregated values are shown for each device type group.
                  </Text>
                </Stack>
              }
            >
              {eventsData.isLoading ? (
                <Skeleton height={200} />
              ) : !eventsData.data || eventsData.data.length === 0 ? (
                <Text c="dimmed" ta="center" py="xl">
                  No events in this period
                </Text>
              ) : (
                <MantineReactTable table={eventsTable} />
              )}
            </CustomCard>
          </Stack>
          <Stack gap="md">
            <CustomCard
              title={`Trailing ${trailingPeriod}-Day Project Energy (${degradationRate}%/yr degradation)`}
              info={
                <Stack gap="xs">
                  <Text fw={600}>Understanding Trailing Period Energy</Text>
                  <Text size="sm">
                    This chart shows cumulative or daily energy production over
                    the trailing period (default 30 days) ending on the last day
                    of your selected date range.
                  </Text>
                  <Text size="sm" fw={500}>
                    View Modes:
                  </Text>
                  <List spacing={4} withPadding>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500}>
                          Cumulative:
                        </Text>{' '}
                        Shows the running total of energy production over the
                        period, with a percentage delta annotation comparing
                        actual vs. budgeted at the end of the period.
                      </Text>
                    </List.Item>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500}>
                          Daily:
                        </Text>{' '}
                        Shows daily energy production as individual bars,
                        allowing you to see day-to-day variations.
                      </Text>
                    </List.Item>
                  </List>
                  <Text size="sm">
                    The budgeted energy is adjusted for degradation using the{' '}
                    <Text component="span" fw={500}>
                      Budgeted Degradation Rate
                    </Text>{' '}
                    selector at the top of the page, based on the project&apos;s
                    COD. The percentage delta shows how actual performance
                    compares to the degraded budgeted values.
                  </Text>
                  {isPvs && (
                    <Text size="sm">
                      <Text component="span" fw={500}>
                        PV+Storage:
                      </Text>{' '}
                      Actual energy is PV Inverter Energy (PV-only, excludes
                      storage). If PV Inverter data is not available, the chart
                      falls back to POI energy so the Actual series still
                      displays.
                    </Text>
                  )}
                </Stack>
              }
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
                <Box
                  w="100%"
                  miw={0}
                  style={{
                    flexShrink: 0,
                    height: 'clamp(360px, 42vh, 640px)',
                  }}
                >
                  <PlotlyPlot
                    data={energyChartData}
                    layout={weeklyTrailingEnergyChartLayout}
                    isLoading={
                      trailingKpiData.isLoading ||
                      dailyBudgetedDataQuery.isLoading
                    }
                  />
                </Box>
              )}
            </CustomCard>
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
          </Stack>
        </SimpleGrid>

        {/* Waterfall Loss Chart */}
        <CustomCard title="Loss Waterfall" info={<LossWaterfallCardInfo />}>
          {startTime && endTime ? (
            <LossWaterfall
              level="device_type"
              startQuery={startTime}
              endQuery={endTime}
            />
          ) : (
            <Text c="dimmed" ta="center" py="xl">
              Please select a date range to view waterfall data
            </Text>
          )}
        </CustomCard>
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
