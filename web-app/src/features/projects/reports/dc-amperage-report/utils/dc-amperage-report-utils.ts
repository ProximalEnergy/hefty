import type {
  CombinerHealth,
  DCAmperageDataV2,
} from '@/api/v1/analytics/dc_amperage_report'
import type { DataTimeSeries } from '@/hooks/types'
import dayjs from 'dayjs'
import timezonePlugin from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import type { Data, Layout, Shape } from 'plotly.js'
import type {
  DcAmperageReportNormalization,
  DcAmperageReportPoaProcessingResult,
  DcAmperageReportPoaTraceOption,
} from '@/features/projects/reports/dc-amperage-report/types/dc-amperage-report-types'
import { SensorTypeEnum } from '@/api/enumerations'

type HeatmapData = {
  inverters: string[]
  combiners: string[]
  zValues: DcAmperageAnalysisValue[][]
  hoverText: string[][]
}

type DcAmperageAnalysisValue = 1 | 0 | -1 | null

type DcAmperageAnalysisSummaryCounts = {
  numberBelow: number
  numberAbove: number
  numberWithin: number
}

type PoaProcessingConfig = {
  poaData: DataTimeSeries[]
  selectedPoaTraceKeys: string[]
  minPoa: number
  maxPoaDerivative: number
  maxPoaDerivativeStdDev: number
  usePoaDerivative: boolean
  usePoaDerivativeStdDev: boolean
  resampleRate: string
  timezone: string
}

dayjs.extend(utc)
dayjs.extend(timezonePlugin)

const MINUTES_PER_HOUR = 60
const MIN_VALID_POA = 10

function buildPoaTraceKey(trace: DataTimeSeries) {
  return `${trace.tag_id ?? `${trace.device_id}:${trace.name}`}`
}

function humanizeName(value: string | null | undefined) {
  if (!value) {
    return ''
  }

  return value
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(' ')
}

function buildPoaTraceLabel(trace: DataTimeSeries) {
  if (trace.tag_name_full) {
    return trace.tag_name_full
  }

  const deviceName =
    trace.device_name_full ||
    trace.device_name_long ||
    `Device ${trace.device_id}`
  const sensorType =
    trace.sensor_type_name_long ||
    humanizeName(trace.sensor_type_name) ||
    `Sensor ${trace.sensor_type_id}`

  return [deviceName, sensorType].filter(Boolean).join(' ')
}

function classifyDcAmperageAnalysisValue(
  value: number | null,
  deviationThreshold: number,
): DcAmperageAnalysisValue {
  if (value === null) {
    return null
  }

  const diff = value - 1
  if (Math.abs(diff) <= deviationThreshold / 100) {
    return 0
  }

  return diff > 0 ? 1 : -1
}

export function buildPoaTraceOptions(
  poaData: DataTimeSeries[],
): DcAmperageReportPoaTraceOption[] {
  return poaData
    .map((trace) => ({
      key: buildPoaTraceKey(trace),
      label: buildPoaTraceLabel(trace),
      tagId: trace.tag_id,
    }))
    .sort((firstTraceOption, secondTraceOption) =>
      firstTraceOption.label.localeCompare(secondTraceOption.label),
    )
}

function processDcAmperageData(
  data: CombinerHealth | undefined,
  deviationThreshold: number,
): HeatmapData {
  if (!data) {
    return { inverters: [], combiners: [], zValues: [], hoverText: [] }
  }

  const inverters = data.columns
  const combiners = data.index
  const zValues = data.data.map((row) =>
    row.map((value) =>
      classifyDcAmperageAnalysisValue(value, deviationThreshold),
    ),
  )

  const hoverText = data.data.map((row, rowIndex) =>
    row.map((value, columnIndex) => {
      const normalizedValue =
        value === null
          ? 'N/A'
          : `${((value - 1) * 100).toFixed(0).replace('-', '')}%`
      const normalizedValueWithSign =
        value === null || normalizedValue === '0%'
          ? normalizedValue
          : `${value > 1 ? '+' : '-'}${normalizedValue}`
      return [
        `Inverter: ${inverters[columnIndex]}`,
        `Combiner: ${combiners[rowIndex]}`,
        `Current vs. Peers: ${normalizedValueWithSign}`,
      ].join('<br>')
    }),
  )

  return { inverters, combiners, zValues, hoverText }
}

export function buildDcAmperageAnalysisSummaryCounts({
  data,
  deviationThreshold,
}: {
  data: CombinerHealth | undefined
  deviationThreshold: number
}): DcAmperageAnalysisSummaryCounts {
  if (!data) {
    return { numberBelow: 0, numberAbove: 0, numberWithin: 0 }
  }

  return data.data.flat().reduce<DcAmperageAnalysisSummaryCounts>(
    (counts, value) => {
      const analysisValue = classifyDcAmperageAnalysisValue(
        value,
        deviationThreshold,
      )

      if (analysisValue === -1) {
        return { ...counts, numberBelow: counts.numberBelow + 1 }
      }

      if (analysisValue === 1) {
        return { ...counts, numberAbove: counts.numberAbove + 1 }
      }

      if (analysisValue === 0) {
        return { ...counts, numberWithin: counts.numberWithin + 1 }
      }

      return counts
    },
    { numberBelow: 0, numberAbove: 0, numberWithin: 0 },
  )
}

export function buildDcAmperageHeatmapTrace({
  data,
  normalization,
  deviationThreshold,
  colorscale,
}: {
  data: CombinerHealth | undefined
  normalization: DcAmperageReportNormalization
  deviationThreshold: number
  colorscale: [number, string][]
}): Data[] {
  const heatmapData = processDcAmperageData(data, deviationThreshold)
  const normalizationLabel = normalization === 'inv' ? 'inverter' : 'project'

  return [
    {
      z: heatmapData.zValues,
      x: heatmapData.inverters,
      y: heatmapData.combiners,
      type: 'heatmap',
      colorscale,
      showscale: true,
      colorbar: {
        tickmode: 'array',
        tickvals: [-1, 1],
        ticktext: ['Below Peers', 'Above Peers'],
      },
      xgap: 0.1,
      ygap: 0.1,
      zmin: -1,
      zmax: 1,
      hoverinfo: 'text',
      // @ts-expect-error Plotly heatmaps accept 2D hover text.
      text: heatmapData.hoverText.map((row) =>
        row.map((text) => `${text}<br>Normalization: ${normalizationLabel}`),
      ),
      hoverongaps: false,
    },
  ]
}

export function hasPopulatedAnalysisData(
  reportData: DCAmperageDataV2 | undefined,
) {
  return [reportData?.inv, reportData?.proj].some((analysisData) => {
    return (
      analysisData !== undefined &&
      analysisData.columns.length > 0 &&
      analysisData.index.length > 0 &&
      analysisData.data.some((row) => row.length > 0)
    )
  })
}

export function parseResampleRateMinutes(resampleRate: string) {
  const minutes = Number(resampleRate.replace('min', ''))
  return Number.isFinite(minutes) && minutes > 0 ? minutes : 5
}

function rollingAverage(values: Array<number | null>, windowSize: number) {
  return values.map((_, index) => {
    const windowValues = values
      .slice(Math.max(0, index - windowSize + 1), index + 1)
      .filter((value): value is number => value !== null)

    if (windowValues.length === 0) {
      return null
    }

    return (
      windowValues.reduce((sum, value) => sum + value, 0) / windowValues.length
    )
  })
}

function standardDeviation(values: number[]) {
  if (values.length <= 1) {
    return 0
  }

  const average = values.reduce((sum, value) => sum + value, 0) / values.length
  const variance =
    values.reduce((sum, value) => sum + (value - average) ** 2, 0) /
    (values.length - 1)

  return Math.sqrt(variance)
}

function buildApplicableIntervalShapes({
  xValues,
  validIndexes,
  resampleRate,
  timezone,
}: {
  xValues: string[]
  validIndexes: Set<number>
  resampleRate: string
  timezone: string
}): Partial<Shape>[] {
  const halfIntervalMinutes = parseResampleRateMinutes(resampleRate) / 2
  const shapes: Partial<Shape>[] = []
  let currentShape: Partial<Shape> | null = null

  xValues.forEach((xValue, index) => {
    if (validIndexes.has(index)) {
      if (!currentShape) {
        currentShape = {
          type: 'rect',
          xref: 'x',
          yref: 'paper',
          x0: xValue,
          x1: xValue,
          y0: 0,
          y1: 1,
          fillcolor: 'rgba(46, 204, 113, 0.2)',
          line: { width: 0 },
        }
      } else {
        currentShape.x1 = xValue
      }
    } else if (currentShape) {
      shapes.push(currentShape)
      currentShape = null
    }
  })

  if (currentShape) {
    shapes.push(currentShape)
  }

  return shapes.map((shape) => {
    const hourOffset = dayjs(String(shape.x0)).tz(timezone).utcOffset() / 60
    return {
      ...shape,
      x0: dayjs(String(shape.x0))
        .tz(timezone)
        .subtract(halfIntervalMinutes, 'minute')
        .add(hourOffset, 'hour')
        .toISOString(),
      x1: dayjs(String(shape.x1))
        .tz(timezone)
        .add(halfIntervalMinutes, 'minute')
        .add(hourOffset, 'hour')
        .toISOString(),
    }
  })
}

export function processPoaData({
  poaData,
  selectedPoaTraceKeys,
  minPoa,
  maxPoaDerivative,
  maxPoaDerivativeStdDev,
  usePoaDerivative,
  usePoaDerivativeStdDev,
  resampleRate,
  timezone,
}: PoaProcessingConfig): DcAmperageReportPoaProcessingResult {
  const selectedPoaTraceKeySet = new Set(selectedPoaTraceKeys)
  const selectedPoaTraces = poaData.filter((trace) =>
    selectedPoaTraceKeySet.has(buildPoaTraceKey(trace)),
  )
  const selectedPoaTagIds = selectedPoaTraces
    .map((trace) => trace.tag_id)
    .filter((tagId): tagId is number => tagId !== undefined)
  const displayPoaTraces = selectedPoaTraces.map((trace) => ({
    ...trace,
    name: buildPoaTraceLabel(trace),
  }))
  const xValues = selectedPoaTraces[0]?.x ?? []
  const sampleRateMinutes = parseResampleRateMinutes(resampleRate)
  const rollingWindow = Math.max(
    1,
    Math.round(MINUTES_PER_HOUR / sampleRateMinutes),
  )

  const meanPoa = xValues.map((_, index) => {
    const values = selectedPoaTraces
      .map((trace) => trace.y[index])
      .filter((value) => Number.isFinite(value) && value > MIN_VALID_POA)

    if (values.length === 0) {
      return null
    }

    return values.reduce((sum, value) => sum + value, 0) / values.length
  })

  const derivativeByIndex = xValues.map((xValue, index) => {
    if (index === 0) {
      return []
    }

    const previousXValue = xValues[index - 1]
    const minutes = Math.max(1, dayjs(xValue).diff(previousXValue, 'minute'))

    return selectedPoaTraces
      .map((trace) => {
        const currentValue = trace.y[index]
        const previousValue = trace.y[index - 1]

        if (!Number.isFinite(currentValue) || !Number.isFinite(previousValue)) {
          return null
        }

        return (currentValue - previousValue) / minutes
      })
      .filter((value): value is number => value !== null)
  })

  const meanDerivative = derivativeByIndex.map((values) => {
    if (values.length === 0) {
      return null
    }

    return values.reduce((sum, value) => sum + value, 0) / values.length
  })
  const derivativeStdDev = derivativeByIndex.map((values) => {
    if (values.length === 0) {
      return null
    }

    return standardDeviation(values)
  })
  const rollingMeanDerivative = rollingAverage(meanDerivative, rollingWindow)
  const rollingDerivativeStdDev = rollingAverage(
    derivativeStdDev,
    rollingWindow,
  )
  const validIndexes = new Set<number>()

  meanPoa.forEach((poaValue, index) => {
    const derivativeValue = rollingMeanDerivative[index]
    const stdDevValue = rollingDerivativeStdDev[index]
    const hasValidPoa = poaValue !== null && poaValue > minPoa
    const hasValidDerivative =
      !usePoaDerivative ||
      (derivativeValue !== null && Math.abs(derivativeValue) < maxPoaDerivative)
    const hasValidStdDev =
      !usePoaDerivativeStdDev ||
      (stdDevValue !== null && stdDevValue < maxPoaDerivativeStdDev)

    if (hasValidPoa && hasValidDerivative && hasValidStdDev) {
      validIndexes.add(index)
    }
  })

  const metricTraceBase = {
    x: xValues,
    y_range: [],
    sensor_type_name: '',
    device_name_long: '',
    tag_name_scada: '',
    tag_name_long: '',
    device_id: 0,
    sensor_type_id: SensorTypeEnum.GHOST_UNKNOWN,
    tag_id: 0,
    yaxis: 'y2',
  }
  const metricTraces: DataTimeSeries[] = []

  if (usePoaDerivative) {
    metricTraces.push({
      ...metricTraceBase,
      name: 'POA Derivative',
      y: rollingMeanDerivative.map((value) => value ?? Number.NaN),
    })
  }

  if (usePoaDerivativeStdDev) {
    metricTraces.push({
      ...metricTraceBase,
      name: 'POA Derivative Std Dev',
      y: rollingDerivativeStdDev.map((value) => value ?? Number.NaN),
    })
  }

  return {
    plotData: [...displayPoaTraces, ...metricTraces],
    validPoints: validIndexes.size,
    shapes: buildApplicableIntervalShapes({
      xValues,
      validIndexes,
      resampleRate,
      timezone,
    }),
    selectedPoaTagIds,
  }
}

export function buildPoaPlotLayout(shapes: Partial<Shape>[]): Partial<Layout> {
  return {
    shapes,
    showlegend: true,
    hoverlabel: {
      namelength: -1,
    },
    yaxis: {
      title: { text: 'POA' },
    },
    yaxis2: {
      title: { text: 'Filters' },
      showgrid: false,
      zeroline: false,
      side: 'right',
      overlaying: 'y',
    },
  }
}
