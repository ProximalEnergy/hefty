import {
  DeviceTypeEnum,
  KPITypeEnum,
  ProjectTypeEnum,
  ReportTypeEnum,
  SensorTypeEnum,
} from '@/api/enumerations'
import type { DailyPerformanceStats } from '@/api/v1/ai/daily_performance_summary'
import type { OperationalKPIData } from '@/api/v1/operational/kpi_data'
import { useGetOperationalKPIData } from '@/api/v1/operational/kpi_data'
import { KPIType, useGetKPITypes } from '@/api/v1/operational/kpi_types'
import { useGetEventsSummary } from '@/api/v1/operational/project/events'
import { useGetTimeSeries } from '@/api/v1/operational/project/project_data'
import { useGetWaterfall } from '@/api/v1/operational/project/waterfall'
import { useSelectProject } from '@/api/v1/operational/projects'
import {
  useGetPVBudgetedData,
  useGetPVBudgetedDataBySeries,
  useGetPVBudgetedSeries,
  useGetPVBudgetedSeriesDailyData,
} from '@/api/v1/operational/pv_budgeted_data'
import { useGetMeterPowerAndExpectedPowerV3 } from '@/api/v1/protected/system'
import AICard from '@/components/AICard'
import CustomCard from '@/components/CustomCard'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import LossWaterfall from '@/components/plots/LossWaterfall'
import { LossWaterfallCardInfo } from '@/components/plots/LossWaterfallCardInfo'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { AutoFitStatValue } from '@/components/stats/AutoFitStatValue'
import { useGetDevicesV2 } from '@/hooks/api'
import { useProjectFilter } from '@/hooks/custom'
import type { EventSummary } from '@/hooks/types'
import { EventTable } from '@/pages/projects/ProjectEvents'
import { PerformanceReportMapCard } from '@/pages/projects/reports/PerformanceReportMapCard'
import { QUERY_TIME } from '@/utils/queryTiming'
import {
  ActionIcon,
  Box,
  Button,
  Card,
  Group,
  List,
  Modal,
  NumberInput,
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
  IconFileTypePdf,
  IconSun,
} from '@tabler/icons-react'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import html2canvas from 'html2canvas-pro'
import jsPDF from 'jspdf'
import type * as Plotly from 'plotly.js'
import React, { useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router'

dayjs.extend(utc)
dayjs.extend(timezone)

// Waterfall API bar names (must match backend project_waterfall.py)
const WATERFALL_NAME_PV_ENERGY_OUTPUT = 'PV Energy Output'
const WATERFALL_NAME_PV_EXPECTED = 'PV Expected'

// Daily Energy Comparison Component - Power Plot Style
const DailyEnergyComparison = ({
  selectedDate,
  projectId,
  degradationRate,
  budgetedDataQuery,
  comparisonMode,
}: {
  selectedDate: dayjs.Dayjs | null
  projectId: string | undefined
  degradationRate: number
  budgetedDataQuery: ReturnType<typeof useGetPVBudgetedData>
  comparisonMode: '15days' | 'dayof'
}) => {
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme('light')

  // Get project data
  const project = useSelectProject(projectId!)

  // Calculate start and end times for the selected date (already in project timezone)
  const startTime = selectedDate
    ? selectedDate.startOf('day').toISOString()
    : null
  const endTime = selectedDate
    ? selectedDate.startOf('day').endOf('day').toISOString()
    : null

  // TODO: Remove this in favor of a new database table.
  const includeSoiling = !['sigurd'].includes(project.data?.name_short || '')
  const includeDegradation = ['sigurd'].includes(project.data?.name_short || '')

  // Use the same hook as PowerPlotPVZoom for power data
  const powerData = useGetMeterPowerAndExpectedPowerV3({
    pathParams: { project_id: projectId || '-1' },
    queryParams: {
      start: startTime || '',
      end: endTime || '',
      interval: '15min', // 15-minute intervals for daily view
      include_storage: project.data?.project_type_id === ProjectTypeEnum.PVS,
      include_setpoint: true,
      include_soiling: includeSoiling,
      include_degradation: includeDegradation,
      nighttime_losses: true,
    },
    queryOptions: {
      enabled: !!projectId && !!startTime && !!endTime,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: QUERY_TIME.ONE_MINUTE, // 1 minute
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

  // Calculate average hourly budgeted output from ±15 days or Day of
  const averageBudgetedHourly = useMemo(() => {
    if (
      !budgetedDataQuery.data ||
      budgetedDataQuery.data.length === 0 ||
      !project.data?.time_zone ||
      !selectedDate
    ) {
      return null
    }

    // Filter data based on comparison mode
    let filteredData = budgetedDataQuery.data
    if (comparisonMode === 'dayof') {
      // Only use data from the selected date (ignoring year)
      const selectedMonthDay = selectedDate.format('MM-DD')
      filteredData = budgetedDataQuery.data.filter((dataPoint) => {
        const timestamp = dayjs.utc(dataPoint.time).tz(project.data?.time_zone)
        return timestamp.format('MM-DD') === selectedMonthDay
      })
    }

    if (filteredData.length === 0) {
      return null
    }

    // Group by hour of day (0-23) and calculate average for each hour
    const hourlyAverages: Record<number, number[]> = {}

    filteredData.forEach((dataPoint) => {
      const timestamp = dayjs.utc(dataPoint.time).tz(project.data?.time_zone)
      const hour = timestamp.hour()

      if (!hourlyAverages[hour]) {
        hourlyAverages[hour] = []
      }

      // Apply degradation if COD is available
      // Degradation should be calculated from COD to the selected date, not the budgeted data timestamp
      let degradedPower = dataPoint.poi_ac_power
      if (project.data?.cod && selectedDate) {
        const codDate = dayjs(project.data.cod)
        const yearsSinceCOD = selectedDate.diff(codDate, 'year', true) // true for decimal years
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
  }, [
    budgetedDataQuery.data,
    project.data,
    degradationRate,
    comparisonMode,
    selectedDate,
  ])

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
        visible: true,
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

    // Add budgeted series average if available
    if (averageBudgetedHourly && powerData.data && powerData.data.length > 0) {
      const budgetedTimestamps: string[] = []
      const budgetedY: number[] = []

      // Create hourly data points (one per hour) in project timezone
      // Budgeted data is hour ending, so shift by 30 minutes to center the data
      if (!selectedDate) {
        return finalData
      }
      const baseDate = selectedDate.startOf('day')
      for (let hour = 0; hour < 24; hour++) {
        const timestamp = baseDate
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
        name:
          comparisonMode === 'dayof'
            ? 'Budgeted (Day of)'
            : 'Budgeted Avg (+-15 days)',
        type: 'scatter' as const,
        mode: 'lines' as const,
        connectgaps: true,
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

    return finalData
  }, [
    plotData,
    project.data,
    powerData.data,
    colorMap,
    averageBudgetedHourly,
    selectedDate,
    comparisonMode,
  ])

  if (!project.data) return null

  if (!selectedDate) {
    return (
      <Text c="dimmed" ta="center" py="xl">
        Please select a date to view daily power comparison
      </Text>
    )
  }

  // Only wait for required data - budgeted data is optional and can be added later
  if (powerData.isLoading || project.isLoading) {
    return (
      <Text ta="center" py="xl">
        Loading...
      </Text>
    )
  }

  const dailyMeterPowerYRange =
    project.data.project_type_id === ProjectTypeEnum.PVS
      ? undefined
      : ([0, project.data.poi * 1.05] as [number, number])

  const dailyMeterPowerPlotLayout = {
    yaxis: {
      title: { text: 'Power (MW)' },
      fixedrange: true,
      range: dailyMeterPowerYRange,
    },
    xaxis: {
      type: 'date' as const,
      fixedrange: false,
      tickangle: 0,
      range: selectedDate
        ? [
            selectedDate.startOf('day').valueOf(),
            selectedDate.startOf('day').endOf('day').valueOf(),
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
        colorScheme === 'dark' ? 'rgba(37,38,43,0.8)' : 'rgba(255,255,255,0.8)',
      bordercolor:
        colorScheme === 'dark' ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)',
      borderwidth: 1,
      itemsizing: 'constant' as const,
      tracegroupgap: 10,
    },
    margin: { l: 60, r: 30, t: 10, b: 20 },
  }

  return (
    <PlotlyPlot
      data={finalPlotData}
      layout={dailyMeterPowerPlotLayout}
      isLoading={powerData.isLoading || project.isLoading}
      error={powerData.error}
      config={{ responsive: true, scrollZoom: false }}
    />
  )
}

const Page: React.FC = () => {
  useProjectFilter({
    reportTypeId: ReportTypeEnum.PV_PERFORMANCE_DAILY,
  })

  const { projectId } = useParams<{ projectId: string }>()
  const reportRef = useRef<HTMLDivElement>(null)
  const [isPdfLoading, setIsPdfLoading] = useState(false)
  const [isMapIdle, setIsMapIdle] = useState(false)
  const [pdfExportRequested, setPdfExportRequested] = useState(false)
  const [pendingThemeSwitch, setPendingThemeSwitch] = useState(false)
  const { setColorScheme } = useMantineColorScheme()

  const handleDailyPerformanceExportPdf = () => {
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
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme('light')

  React.useEffect(() => {
    if (!pendingThemeSwitch) return
    if (colorScheme !== 'light') return

    setPdfExportRequested(true)
    setPendingThemeSwitch(false)
  }, [pendingThemeSwitch, colorScheme])

  // Get date from URL params via AdvancedDatePicker (already in project timezone)
  const { start: selectedDate } = useValidateDateRange({
    maxDays: 1,
    timeZone: project.data?.time_zone,
  })

  // Toggle for cumulative vs daily in the 30-day chart
  const [energyView, setEnergyView] = useState<'cumulative' | 'daily'>(
    'cumulative',
  )

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

  // selectedDate is already a dayjs object in project timezone, so just use it directly
  const { startTime, endTime, selectedDateStr } = useMemo(() => {
    if (!selectedDate) {
      return { startTime: null, endTime: null, selectedDateStr: null }
    }
    const startOfDay = selectedDate.startOf('day')
    return {
      startTime: startOfDay.toISOString(),
      endTime: startOfDay.endOf('day').toISOString(),
      selectedDateStr: startOfDay.format('YYYY-MM-DD'),
    }
  }, [selectedDate])

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
      staleTime: QUERY_TIME.TWENTY_FOUR_HOURS,
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
      staleTime: QUERY_TIME.NEVER, // Never consider data stale
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

  // Calculate trailing period range ending on selected date (selectedDate is already in project timezone)
  const trailingStart = useMemo(() => {
    if (!selectedDate) return null
    return selectedDate
      .subtract(trailingPeriod - 1, 'days')
      .format('YYYY-MM-DD')
  }, [selectedDate, trailingPeriod])
  const trailingEnd = useMemo(() => {
    if (!selectedDate) return null
    return selectedDate.add(1, 'day').format('YYYY-MM-DD')
  }, [selectedDate])

  // Calculate range for budgeted data (±15 days around selected date)
  const budgetedStartDate = useMemo(() => {
    if (!selectedDate) return null
    return selectedDate.subtract(15, 'days').format('YYYY-MM-DD')
  }, [selectedDate])
  const budgetedEndDate = useMemo(() => {
    if (!selectedDate) return null
    return selectedDate.add(15, 'days').format('YYYY-MM-DD')
  }, [selectedDate])

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
      staleTime: QUERY_TIME.TWENTY_FOUR_HOURS, // 24 hours - met stations don't change often
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
      staleTime: QUERY_TIME.ONE_HOUR, // 1 hour
      gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days
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

  // Fetch daily KPI data for stats (single day).
  // For PVS projects we also need PV-only generation (PV_INVERTER or PV_INVERTER_MODULE).
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
      staleTime: QUERY_TIME.TWENTY_FOUR_HOURS, // 24 hours
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
      staleTime: QUERY_TIME.TWENTY_FOUR_HOURS, // 24 hours
      gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days
    },
  })

  // Fetch events for the selected day (including both open and closed events)
  const eventsData = useGetEventsSummary({
    pathParams: { projectId: projectId || '' },
    queryParams: {
      start: selectedDateStr ? `${selectedDateStr} 00:00:00` : undefined,
      end: selectedDateStr ? `${selectedDateStr} 23:59:59` : undefined,
      open: false, // false means no filter, so returns both open and closed events
    },
    queryOptions: {
      enabled: !!projectId && !!selectedDateStr,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: QUERY_TIME.TWENTY_FOUR_HOURS, // 24 hours
      gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days
    },
  })

  // Fetch DC Combiner Field Health (KPI type 8)
  const combinerHealthKpiData = useGetOperationalKPIData({
    queryParams: {
      project_ids: [projectId || ''],
      kpi_type_ids: [KPITypeEnum.PV_DC_COMBINER_FIELD_HEALTH],
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
      staleTime: QUERY_TIME.TWENTY_FOUR_HOURS, // 24 hours
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
      staleTime: QUERY_TIME.TWENTY_FOUR_HOURS, // 24 hours
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
      staleTime: QUERY_TIME.TWENTY_FOUR_HOURS, // 24 hours
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
      end_date: selectedDateStr || '', // API is inclusive, so this includes selectedDateStr
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
      staleTime: QUERY_TIME.TWENTY_FOUR_HOURS, // 24 hours
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
      staleTime: QUERY_TIME.TWENTY_FOUR_HOURS, // 24 hours
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
      staleTime: QUERY_TIME.NEVER,
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

  // Calculate budgeted percentage for generation (energy)
  const generationBudgetInfo = useMemo(() => {
    if (!processedBudgetedData || !selectedDateStr) return null

    let budgetedMWh: number | null = null

    if (budgetedComparisonMode === '15days') {
      // Calculate average of +/- 15 days around selected date
      const selectedDateIndex = processedBudgetedData.dates.findIndex(
        (date: string) => date === selectedDateStr,
      )
      if (selectedDateIndex === -1) return null

      // Get +/- 15 days around the selected date
      const startIndex = Math.max(0, selectedDateIndex - 15)
      const endIndex = Math.min(
        processedBudgetedData.dates.length - 1,
        selectedDateIndex + 15,
      )

      const budgetedValues = processedBudgetedData.budgetedData
        .slice(startIndex, endIndex + 1)
        .filter((val): val is number => val !== null && val !== undefined)

      if (budgetedValues.length === 0) return null

      budgetedMWh =
        budgetedValues.reduce((sum, val) => sum + val, 0) /
        budgetedValues.length
    } else {
      // Use Day of comparison
      const selectedDateIndex = processedBudgetedData.dates.findIndex(
        (date: string) => date === selectedDateStr,
      )

      if (selectedDateIndex === -1) return null

      budgetedMWh = processedBudgetedData.budgetedData[selectedDateIndex]
    }

    if (!budgetedMWh || budgetedMWh === 0) return null

    // Get the actual generation for the selected day
    const generationKpi = dailyKpiData.data?.find(
      (kpi: OperationalKPIData) =>
        kpi.kpi_type_id === KPITypeEnum.PROJECT_ENERGY_PRODUCTION,
    )
    const generationMWh = generationKpi?.data?.project_data?.[0] || 0

    return {
      percentage: (generationMWh / budgetedMWh) * 100,
      budgetedMWh,
    }
  }, [
    processedBudgetedData,
    selectedDateStr,
    dailyKpiData.data,
    budgetedComparisonMode,
  ])

  // Calculate budgeted percentage for irradiance (POA)
  const irradianceBudgetInfo = useMemo(() => {
    if (!budgetedDataQuery.data || !selectedDate || !project.data?.time_zone) {
      return null
    }

    let budgetedPOASumkWh: number

    if (budgetedComparisonMode === '15days') {
      // Calculate average daily irradiation for +/- 15 days around selected date
      // Note: budgeted data may be from a different year, so we match by MM-DD
      // Create array of MM-DD dates within +/- 15 days
      const targetMMDDs = new Set<string>()
      for (let i = -15; i <= 15; i++) {
        const date = selectedDate.add(i, 'days')
        targetMMDDs.add(date.format('MM-DD'))
      }

      const filteredData = budgetedDataQuery.data.filter((item) => {
        const itemDate = dayjs.utc(item.time).tz(project.data?.time_zone)
        const itemMMDD = itemDate.format('MM-DD')
        return targetMMDDs.has(itemMMDD)
      })

      if (filteredData.length === 0) {
        return null
      }

      // Get all hourly POA values and calculate average
      const poaValues = filteredData
        .map((item) => item.poa as number | null)
        .filter((val): val is number => val !== null && val !== undefined)

      if (poaValues.length === 0) {
        return null
      }

      // Calculate average hourly POA, then multiply by 24 to get daily average
      const averageHourlyPOAWh =
        poaValues.reduce((sum, val) => sum + val, 0) / poaValues.length
      const averageDailyPOAWh = averageHourlyPOAWh * 24

      budgetedPOASumkWh = averageDailyPOAWh / 1000
    } else {
      // Use Day of comparison - filter budgeted data for the selected date, ignoring the year
      const selectedDateData = budgetedDataQuery.data.filter(
        (item) =>
          dayjs.utc(item.time).tz(project.data?.time_zone).format('MM-DD') ===
          selectedDate.format('MM-DD'),
      )

      if (selectedDateData.length === 0) {
        return null
      }

      // Sum all hourly POA irradiance for the selected date
      const budgetedPOASumWh = selectedDateData.reduce((sum, item) => {
        const originalPOA = item.poa as number | null
        return sum + (originalPOA || 0)
      }, 0)

      budgetedPOASumkWh = budgetedPOASumWh / 1000
    }

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
    selectedDate,
    calculatedIrradiance,
    project.data?.time_zone,
    budgetedComparisonMode,
  ])

  // For PV+Storage projects use PV-only generation (circuit/inverters), not POI.
  const isPvs = project.data?.project_type_id === ProjectTypeEnum.PVS

  // Shared daily actual/expected (used by stats and aiStats).
  const dailyActualExpected = useMemo(() => {
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
    const actualMWh = fromWaterfall
      ? fromWaterfall.actualMWh
      : isPvs
        ? (pvPcsKpi?.data?.project_data?.[0] ??
          pvPcsModuleKpi?.data?.project_data?.[0] ??
          0)
        : poiKpi?.data?.project_data?.[0] || 0
    const expectedMWh = fromWaterfall
      ? fromWaterfall.expectedMWh
      : expectedKpi?.data?.project_data?.[0] || 0
    const curtailmentMWh = curtailmentKpi?.data?.project_data?.[0] || 0
    const poiMWh = poiKpi?.data?.project_data?.[0] || 0
    return {
      actualMWh,
      expectedMWh,
      curtailmentMWh,
      poiMWh,
      fromWaterfall,
    }
  }, [dailyKpiData.data, isPvs, waterfallActualExpected])

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

    // Calculate Performance Index = (actual / expected) * 100
    const performanceIndex =
      expectedMWh > 0 ? (generationMWh / expectedMWh) * 100 : 0
    const irradianceKWhM2 = calculatedIrradiance ?? 0

    const availability = availabilityKpi?.data?.project_data?.[0] || 0

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
        value: `${generationMWh.toFixed(1)} MWh${curtailmentMWh !== 0 ? '*' : ''}`,
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
        description: 'Total irradiation that day',
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
        description: 'Estimated revenue for that day',
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
          : `Performance Index: ratio of actual generation to expected generation for the selected day. Note: Expected energy does not take curtailment into account.${
              curtailmentMWh !== 0
                ? ` Energy curtailment: ${curtailmentMWh.toFixed(1)} MWh`
                : ''
            }`,
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
        title: 'PCS Mech. Availability',
        value: `${(availability * 100).toFixed(2)}%${curtailmentMWh !== 0 ? '*' : ''}`,
        subtitle: 'Daily mechanical availability',
        icon: IconCash,
        description: `${
          kpiTypeDescriptions[1] ||
          'PCS mechanical availability for the selected day'
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
    mtdKpiData.data,
    project.data?.ppa?.rate,
    projectId,
    kpiTypeDescriptions,
  ])

  // Create 30-day energy chart data
  const energyChartData = useMemo(() => {
    // Early return if we don't have essential data yet
    if (!selectedDate || !trailingPeriod) {
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
    selectedDate,
    trailingPeriod,
    theme.colors.orange,
    theme.colors.violet,
    theme.colors.green,
  ])

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

  const dailyTrailingEnergyChartLayout = useMemo(() => {
    const yAxisTitle =
      energyView === 'cumulative'
        ? 'Cumulative Energy (MWh)'
        : 'Daily Energy (MWh)'

    const annotations: NonNullable<Plotly.Layout['annotations']> =
      performanceSummary && energyView === 'cumulative'
        ? (() => {
            const firstTrace = energyChartData[0] as { x?: unknown[] }
            const firstTraceX = firstTrace?.x
            const xValue =
              Array.isArray(firstTraceX) && firstTraceX.length > 0
                ? (firstTraceX[firstTraceX.length - 1] as string | number)
                : undefined
            const annotationY =
              (performanceSummary.actual + performanceSummary.budgeted) / 2
            const signChar = performanceSummary.isExceeded ? '+' : '-'
            const pctText = `${signChar}${performanceSummary.percent.toFixed(
              1,
            )}%`
            const fontColor = performanceSummary.isExceeded
              ? '#00C853'
              : '#FF5722'
            return [
              {
                x: xValue,
                y: annotationY,
                text: pctText,
                showarrow: false,
                font: {
                  color: fontColor,
                  size: 40,
                  family: 'Arial, sans-serif',
                  weight: 900,
                },
              },
            ]
          })()
        : []

    return {
      height: 300,
      xaxis: {
        title: { text: 'Date' },
        type: 'category' as const,
      },
      yaxis: {
        title: { text: yAxisTitle },
      },
      showlegend: true,
      legend: {
        xref: 'paper',
        yref: 'paper',
        x: 0.01,
        y: 0.99,
        xanchor: 'left',
        yanchor: 'top',
        orientation: 'h',
        bgcolor:
          colorScheme === 'dark'
            ? 'rgba(37,38,43,0.8)'
            : 'rgba(255,255,255,0.8)',
        bordercolor:
          colorScheme === 'dark' ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)',
        borderwidth: 1,
        itemsizing: 'constant',
      },
      hovermode: (energyView === 'daily' ? 'closest' : 'x unified') as
        | 'closest'
        | 'x unified',
      barmode: energyView === 'daily' ? ('overlay' as const) : undefined,
      margin: { l: 60, r: 30, t: 30, b: 60 },
      annotations,
    } satisfies Partial<Plotly.Layout>
  }, [colorScheme, energyChartData, energyView, performanceSummary])

  // Calculate AI statistics for daily performance summary
  const aiStats = useMemo((): DailyPerformanceStats | null => {
    if (
      !selectedDate ||
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
      date: selectedDateStr || '',
      project_id: projectId,
      cmms_period_start: startTime ?? undefined,
      cmms_period_end: endTime ?? undefined,
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
    selectedDate,
    selectedDateStr,
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
                        Displays hourly actual vs. budgeted power, optionally
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
                        date, grouped by device type with financial and energy
                        loss details.
                      </Text>
                    </List.Item>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500}>
                          Daily Loss Waterfall:
                        </Text>{' '}
                        Visualizes energy losses for the selected day in a
                        waterfall format.
                      </Text>
                    </List.Item>
                  </List>
                </Stack>
              }
            >
              PV Performance Daily Report
            </PageTitle>
            <Tooltip
              label="Select a date to view daily performance metrics and power generation data"
              withArrow
              multiline
              w={300}
            >
              <AdvancedDatePicker
                maxDays={1}
                defaultRange="yesterday"
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
              onClick={handleDailyPerformanceExportPdf}
              loading={isPdfLoading}
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
            <AICard
              stats={aiStats}
              isLoading={isAICardLoading}
              hasBudgetedSeries={seriesOptions.length > 0}
              hasSelectedDate={!!selectedDate}
            />

            {/* Daily Energy Comparison Card */}
            <CustomCard
              title={`Meter Power - ${selectedDateStr ? dayjs(selectedDateStr).format('MMM DD, YYYY') : 'Select Date'}`}
              style={{ minHeight: '300px' }}
              info={
                <Stack gap="xs">
                  <Text fw={600}>Understanding Meter Power</Text>
                  <Text size="sm">
                    This chart displays the actual meter power output compared
                    to budgeted power for the selected date. The chart may also
                    show the{' '}
                    <Text component="span" fw={500}>
                      PPC Active Power Setpoint
                    </Text>{' '}
                    if available for the project. Use the{' '}
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
                        Shows the average hourly meter power based on the
                        budgeted series uploaded in the{' '}
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
                        Shows the budgeted power for the exact same calendar
                        date (MM-DD) from the budgeted year, adjusted for
                        degradation.
                      </Text>
                    </List.Item>
                  </List>
                  <Text size="sm">
                    The{' '}
                    <Text component="span" fw={500}>
                      Budgeted Degradation Rate
                    </Text>{' '}
                    selector at the top controls how much degradation is applied
                    to the budgeted data based on the project&apos;s Commercial
                    Operation Date (COD) to account for expected performance
                    decline over time.
                  </Text>
                </Stack>
              }
            >
              <DailyEnergyComparison
                selectedDate={selectedDate}
                projectId={projectId}
                degradationRate={degradationRate}
                budgetedDataQuery={budgetedDataQuery}
                comparisonMode={budgetedComparisonMode}
              />
            </CustomCard>
          </Stack>

          {/* Trailing Period Energy Chart */}
          <CustomCard
            title={`Trailing ${trailingPeriod}-Day Project Energy (${degradationRate}%/yr degradation)`}
            info={
              <Stack gap="xs">
                <Text fw={600}>Understanding Trailing Period Energy</Text>
                <Text size="sm">
                  This chart shows cumulative or daily energy production over
                  the trailing period (default 30 days) ending on the selected
                  date.
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
                      Shows daily energy production as individual bars, allowing
                      you to see day-to-day variations.
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
              <PlotlyPlot
                data={energyChartData}
                layout={dailyTrailingEnergyChartLayout}
                isLoading={
                  trailingKpiData.isLoading || dailyBudgetedDataQuery.isLoading
                }
              />
            )}
          </CustomCard>
        </SimpleGrid>

        {/* Events Table and Pie Chart */}
        <SimpleGrid cols={{ base: 1, md: 2 }}>
          <CustomCard
            title="Events by Device Type"
            info={
              <Stack gap="xs">
                <Text fw={600}>Understanding Events by Device Type</Text>
                <Text size="sm">
                  This table displays all events (both open and closed) that
                  occurred on the selected date, grouped by device type.
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
                      The energy loss associated with the event for the selected
                      day.
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
                  Events are automatically grouped by device type. Click on any
                  row to view detailed event information, or use the external
                  link icon to open the event in a new tab. Aggregated values
                  are shown for each device type group.
                </Text>
              </Stack>
            }
          >
            {eventsData.isLoading ? (
              <Skeleton height={200} />
            ) : !eventsData.data || eventsData.data.length === 0 ? (
              <Text c="dimmed" ta="center" py="xl">
                No events for this day
              </Text>
            ) : (
              project.data && (
                <EventTable
                  data={eventsData.data || []}
                  project={project.data}
                />
              )
            )}
          </CustomCard>

          {/* DC Combiner Field Health Map */}
          <PerformanceReportMapCard
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

        {/* Waterfall Loss Chart */}
        <CustomCard
          title="Daily Loss Waterfall"
          info={<LossWaterfallCardInfo />}
        >
          {startTime && endTime ? (
            <LossWaterfall
              level="device_type"
              startQuery={startTime}
              endQuery={endTime}
            />
          ) : (
            <Text c="dimmed" ta="center" py="xl">
              Please select a date to view waterfall data
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
