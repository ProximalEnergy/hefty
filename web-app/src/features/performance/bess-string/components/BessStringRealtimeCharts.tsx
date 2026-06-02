import { SensorTypeEnum } from '@/api/enumerations'
import type { BessStringSpec } from '@/api/v1/operational/bess_strings'
import type { SensorType } from '@/api/v1/operational/sensor_types'
import type { useGetRealTimeByDeviceTypeID } from '@/api/v1/protected/web-application/projects/real_time'
import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import type { Tag } from '@/hooks/projectTags'
import {
  Center,
  Divider,
  Loader,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Text,
} from '@mantine/core'
import type { Data, Layout, PlotMouseEvent } from 'plotly.js'
import type { CSSProperties } from 'react'
import { useCallback, useMemo, useState } from 'react'
import { useNavigate } from 'react-router'

import {
  alignTraceToDeviceAxis,
  buildBessStringChartLayout,
  buildStringDeviceAxis,
  type StringDeviceRef,
} from '@/features/performance/bess-string/utils/bess-string-chart-axis'
import {
  barMarkerWithFreshness,
  formatUpdatedHover,
  oldestTimestamp,
} from '@/features/performance/bess-string/utils/bess-string-realtime-staleness'

type RealtimeQuery = ReturnType<typeof useGetRealTimeByDeviceTypeID>

type SingleChartSpec = {
  kind: 'single'
  sensorTypeId: number
  title: string
  yLabel: string
  info: string
}

type GroupedChartSpec = {
  kind: 'grouped'
  title: string
  yLabel: string
  info: string
  traces: { sensorTypeId: number; label: string }[]
}

type LifetimeEnergyTotals = {
  deviceIds: number[]
  deviceNames: string[]
  chargeTotalsMWh: (number | null)[]
  dischargeTotalsMWh: (number | null)[]
  impliedEfficiencyPct: (number | null)[]
  isLoading: boolean
}

type SensorPatternSummary = {
  pattern: string
  count: number
  unitScada: string | null
  unitScale: number | null
  unitOffset: number | null
}

type AccuracyItem = {
  label: string
  value: string
}

const PCS_ACTIVE_POWER_COLOR = '#2ecc71'
const PCS_REACTIVE_POWER_COLOR = '#9b59b6'
const PCS_DC_VOLTAGE_COLOR = '#f39c12'
const PCS_TEMP_COLOR = '#3498db'
const PCS_PHASE_COLORS = ['#e74c3c', '#3498db', '#2ecc71']
const PCS_POWER_GROUP_COLORS = ['#27ae60', '#2ecc71']
const PCS_CURRENT_GROUP_COLORS = ['#5dade2', '#3498db']
const PCS_ENERGY_GROUP_COLORS = ['#1abc9c', '#16a085']
const AVAILABLE_CHARGE_POWER_COLOR = '#c0392b'
const AVAILABLE_DISCHARGE_POWER_COLOR = '#1e8449'
const AVAILABLE_POWER_MARKER_SIZE = 4
const NOT_REPORTING_WARNING_COLOR = '#f59f00'
const NOT_REPORTING_WARNING_MARKER_SIZE = 14
const DC_STRING_VOLTAGE_CHART_TITLE = 'DC string voltage'
const CELL_VOLTAGE_CHART_TITLE = 'Cell voltage (max / min / avg)'
const LIFETIME_ENERGY_CHART_TITLE = 'Last 30 days energy (charge / discharge)'
const NOT_REPORTING_WARNING_SENSOR_IDS = new Set<number>([
  SensorTypeEnum.BESS_STRING_POWER,
  SensorTypeEnum.BESS_STRING_SOC,
])

/** Fixed card height so PlotlyPlot’s `height: 100%` resolves (see PCS realtime). */
const CHART_CARD_HEIGHT_PX = 280

const CHART_CARD_SHELL = {
  style: { height: CHART_CARD_HEIGHT_PX, width: '100%' },
  fill: true,
  bodyStyle: {
    position: 'relative' as const,
    height: '100%',
  },
}

/** Absolute fill so PlotlyPlot width/height match every card. */
const CHART_PLOT_WRAPPER_STYLE: CSSProperties = {
  position: 'absolute',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  width: '100%',
}

const CHART_SPECS: (SingleChartSpec | GroupedChartSpec)[] = [
  {
    kind: 'single',
    sensorTypeId: SensorTypeEnum.BESS_STRING_POWER,
    title: 'DC power',
    yLabel: 'MW',
    info: 'Latest DC power per string. Positive = discharging, negative = charging.',
  },
  {
    kind: 'single',
    sensorTypeId: SensorTypeEnum.BESS_STRING_SOC,
    title: 'State of charge',
    yLabel: 'SOC',
    info: 'State of charge reported for each string.',
  },
  {
    kind: 'single',
    sensorTypeId: SensorTypeEnum.BESS_STRING_SOC_PERCENT,
    title: 'SOC (percent tag)',
    yLabel: '%',
    info: 'Alternate SOC percent signal when present in SCADA.',
  },
  {
    kind: 'grouped',
    title: 'Available charge / discharge power',
    yLabel: 'MW',
    info: 'Headroom reported for charge and discharge at the string level.',
    traces: [
      {
        sensorTypeId: SensorTypeEnum.BESS_STRING_AVAILABLE_CHARGE_POWER,
        label: 'Avail. charge',
      },
      {
        sensorTypeId: SensorTypeEnum.BESS_STRING_AVAILABLE_DISCHARGE_POWER,
        label: 'Avail. discharge',
      },
    ],
  },
  {
    kind: 'single',
    sensorTypeId: SensorTypeEnum.BESS_STRING_CURRENT,
    title: 'DC current',
    yLabel: 'A',
    info: 'String DC current.',
  },
  {
    kind: 'single',
    sensorTypeId: SensorTypeEnum.BESS_STRING_VOLTAGE,
    title: DC_STRING_VOLTAGE_CHART_TITLE,
    yLabel: 'V',
    info: 'String-level DC voltage with configured operating voltage limits.',
  },
  {
    kind: 'single',
    sensorTypeId: SensorTypeEnum.BESS_STRING_SUM_CELL_VOLTAGE,
    title: 'Sum of cell voltages',
    yLabel: 'V',
    info: 'Aggregated cell voltage sum where reported.',
  },
  {
    kind: 'grouped',
    title: CELL_VOLTAGE_CHART_TITLE,
    yLabel: 'V',
    info: 'Extremes and average cell voltage per string.',
    traces: [
      {
        sensorTypeId: SensorTypeEnum.BESS_STRING_MAX_CELL_VOLTAGE,
        label: 'Max',
      },
      {
        sensorTypeId: SensorTypeEnum.BESS_STRING_MIN_CELL_VOLTAGE,
        label: 'Min',
      },
      {
        sensorTypeId: SensorTypeEnum.BESS_STRING_AVG_CELL_VOLTAGE,
        label: 'Avg',
      },
    ],
  },
  {
    kind: 'grouped',
    title: 'Module temperature (max / min / avg)',
    yLabel: '°C',
    info: 'Module-level temperature extremes and average.',
    traces: [
      {
        sensorTypeId: SensorTypeEnum.BESS_STRING_MAX_MODULE_TEMPERATURE,
        label: 'Max',
      },
      {
        sensorTypeId: SensorTypeEnum.BESS_STRING_MIN_MODULE_TEMPERATURE,
        label: 'Min',
      },
      {
        sensorTypeId: SensorTypeEnum.BESS_STRING_AVG_MODULE_TEMPERATURE,
        label: 'Avg',
      },
    ],
  },
  {
    kind: 'grouped',
    title: 'Cell temperature (max / min / avg)',
    yLabel: '°C',
    info: 'Cell-level temperature extremes and average.',
    traces: [
      {
        sensorTypeId: SensorTypeEnum.BESS_STRING_MAX_CELL_TEMPERATURE,
        label: 'Max',
      },
      {
        sensorTypeId: SensorTypeEnum.BESS_STRING_MIN_CELL_TEMPERATURE,
        label: 'Min',
      },
      {
        sensorTypeId: SensorTypeEnum.BESS_STRING_AVG_CELL_TEMPERATURE,
        label: 'Avg',
      },
    ],
  },
  {
    kind: 'single',
    sensorTypeId: SensorTypeEnum.BESS_STRING_SOH_PERCENT,
    title: 'State of health',
    yLabel: 'SOH %',
    info: 'String state of health where available.',
  },
  {
    kind: 'grouped',
    title: 'State of energy (charge / discharge)',
    yLabel: '%',
    info: 'SOE headroom for charging and discharging.',
    traces: [
      {
        sensorTypeId: SensorTypeEnum.BESS_STRING_SOE_CHARGE_PERCENT,
        label: 'SOE charge %',
      },
      {
        sensorTypeId: SensorTypeEnum.BESS_STRING_SOE_DISCHARGE_PERCENT,
        label: 'SOE discharge %',
      },
    ],
  },
  {
    kind: 'grouped',
    title: 'Max allowable charge / discharge current',
    yLabel: 'A',
    info: 'BMS-reported current limits.',
    traces: [
      {
        sensorTypeId: SensorTypeEnum.BESS_STRING_MAX_ALLOWABLE_CHARGE_CURRENT,
        label: 'Max charge A',
      },
      {
        sensorTypeId:
          SensorTypeEnum.BESS_STRING_MAX_ALLOWABLE_DISCHARGE_CURRENT,
        label: 'Max discharge A',
      },
    ],
  },
  {
    kind: 'grouped',
    title: LIFETIME_ENERGY_CHART_TITLE,
    yLabel: 'MWh',
    info: 'Per-string charge and discharge energy totals over the last 30 days.',
    traces: [
      {
        sensorTypeId: SensorTypeEnum.BESS_STRING_CHARGE_ENERGY_TOTAL,
        label: 'Charge total',
      },
      {
        sensorTypeId: SensorTypeEnum.BESS_STRING_DISCHARGE_ENERGY_TOTAL,
        label: 'Discharge total',
      },
    ],
  },
]

function singleChartColor(sensorTypeId: number): string {
  switch (sensorTypeId) {
    case SensorTypeEnum.BESS_STRING_POWER:
      return PCS_ACTIVE_POWER_COLOR
    case SensorTypeEnum.BESS_STRING_VOLTAGE:
    case SensorTypeEnum.BESS_STRING_SUM_CELL_VOLTAGE:
      return PCS_DC_VOLTAGE_COLOR
    case SensorTypeEnum.BESS_STRING_CURRENT:
      return PCS_TEMP_COLOR
    case SensorTypeEnum.BESS_STRING_SOH_PERCENT:
    case SensorTypeEnum.BESS_STRING_SOC:
    case SensorTypeEnum.BESS_STRING_SOC_PERCENT:
      return PCS_REACTIVE_POWER_COLOR
    default:
      return PCS_TEMP_COLOR
  }
}

function groupedChartColors(title: string): string[] {
  switch (title) {
    case 'Available charge / discharge power':
    case 'State of energy (charge / discharge)':
      return PCS_POWER_GROUP_COLORS
    case CELL_VOLTAGE_CHART_TITLE:
      return PCS_PHASE_COLORS
    case 'Module temperature (max / min / avg)':
    case 'Cell temperature (max / min / avg)':
      return PCS_PHASE_COLORS
    case 'Max allowable charge / discharge current':
      return PCS_CURRENT_GROUP_COLORS
    case LIFETIME_ENERGY_CHART_TITLE:
      return PCS_ENERGY_GROUP_COLORS
    default:
      return PCS_PHASE_COLORS
  }
}

export const BESS_STRING_CHART_SENSOR_IDS: number[] = [
  ...new Set(
    CHART_SPECS.flatMap((spec) =>
      spec.kind === 'single'
        ? [spec.sensorTypeId]
        : spec.traces.map((t) => t.sensorTypeId),
    ),
  ),
]

export const BESS_STRING_REALTIME_SENSOR_IDS: number[] = [
  ...new Set(
    CHART_SPECS.flatMap((spec) =>
      spec.title === LIFETIME_ENERGY_CHART_TITLE
        ? []
        : spec.kind === 'single'
          ? [spec.sensorTypeId]
          : spec.traces.map((t) => t.sensorTypeId),
    ),
  ),
]

function valuesLookLikeFraction(values: (number | null)[]): boolean {
  const nums = values.filter((v): v is number => v != null && !Number.isNaN(v))
  if (nums.length === 0) return false
  return Math.max(...nums) <= 1.0001 && Math.min(...nums) >= -0.0001
}

function traceHasAnyValue(values: (number | null)[] | undefined): boolean {
  return (values ?? []).some((v) => v !== null && v !== undefined)
}

function notReportingWarningTrace({
  x,
  y,
  deviceIds,
  highlightedDeviceIds,
}: {
  x: string[]
  y: (number | null | undefined)[]
  deviceIds: (number | null | undefined)[]
  highlightedDeviceIds: Set<number>
}): Partial<Data> | null {
  if (highlightedDeviceIds.size === 0) return null

  const warningX: string[] = []
  const warningY: number[] = []

  deviceIds.forEach((deviceId, index) => {
    if (deviceId == null || !highlightedDeviceIds.has(deviceId)) return
    const value = y[index]
    const name = x[index]
    if (value == null || Number.isNaN(value) || name == null) return
    warningX.push(name)
    warningY.push(value)
  })

  if (warningX.length === 0) return null

  return {
    type: 'scatter',
    mode: 'markers',
    name: 'Not reporting',
    x: warningX,
    y: warningY,
    marker: {
      color: NOT_REPORTING_WARNING_COLOR,
      size: NOT_REPORTING_WARNING_MARKER_SIZE,
      symbol: 'triangle-up',
      line: { color: 'white', width: 1.5 },
    },
    hovertemplate: '%{x}<br>Not reporting<extra></extra>',
    showlegend: false,
  }
}

const DC_POWER_Y_DEFAULT_HALF_RANGE_MW = 0.3
const DC_CURRENT_Y_DEFAULT_HALF_RANGE_A = 200
const DC_STRING_VOLTAGE_RANGE_STEP_V = 100

/** Symmetric Y range: at least ±0.3 MW, wider if |values| exceed that. */
function yRangeForDcPowerMw(values: (number | null)[]): [number, number] {
  const nums = values.filter((v): v is number => v != null && !Number.isNaN(v))
  if (nums.length === 0) {
    return [-DC_POWER_Y_DEFAULT_HALF_RANGE_MW, DC_POWER_Y_DEFAULT_HALF_RANGE_MW]
  }
  const maxAbs = Math.max(...nums.map((v) => Math.abs(v)))
  const half = Math.max(DC_POWER_Y_DEFAULT_HALF_RANGE_MW, maxAbs)
  return [-half, half]
}

/** Symmetric Y range: at least ±200 A, wider if |values| exceed that. */
function yRangeForDcCurrentA(values: (number | null)[]): [number, number] {
  const nums = values.filter((v): v is number => v != null && !Number.isNaN(v))
  if (nums.length === 0) {
    return [
      -DC_CURRENT_Y_DEFAULT_HALF_RANGE_A,
      DC_CURRENT_Y_DEFAULT_HALF_RANGE_A,
    ]
  }
  const maxAbs = Math.max(...nums.map((v) => Math.abs(v)))
  const half = Math.max(DC_CURRENT_Y_DEFAULT_HALF_RANGE_A, maxAbs)
  return [-half, half]
}

function yRangeForDcStringVoltage({
  values,
  lowerLimitV,
  upperLimitV,
}: {
  values: (number | null)[]
  lowerLimitV: number | null
  upperLimitV: number | null
}): [number, number] | undefined {
  const nums = values.filter((v): v is number => v != null && !Number.isNaN(v))
  const axisValues = [
    ...nums,
    ...(lowerLimitV != null ? [lowerLimitV] : []),
    ...(upperLimitV != null ? [upperLimitV] : []),
  ]
  if (axisValues.length === 0) return undefined
  return [
    Math.floor(Math.min(...axisValues) / DC_STRING_VOLTAGE_RANGE_STEP_V) *
      DC_STRING_VOLTAGE_RANGE_STEP_V,
    (Math.floor(Math.max(...axisValues) / DC_STRING_VOLTAGE_RANGE_STEP_V) + 1) *
      DC_STRING_VOLTAGE_RANGE_STEP_V,
  ]
}

function dcStringVoltageLimitLayout({
  lowerLimitV,
  upperLimitV,
}: {
  lowerLimitV: number | null
  upperLimitV: number | null
}): Pick<Partial<Layout>, 'shapes' | 'annotations'> {
  const limits = [
    { value: lowerLimitV, label: 'Lower limit', color: '#e74c3c' },
    { value: upperLimitV, label: 'Upper limit', color: '#e74c3c' },
  ].filter(
    (limit): limit is { value: number; label: string; color: string } =>
      limit.value != null,
  )

  return {
    shapes: limits.map((limit) => ({
      type: 'line',
      xref: 'paper',
      x0: 0,
      x1: 1,
      yref: 'y',
      y0: limit.value,
      y1: limit.value,
      line: { color: limit.color, width: 2, dash: 'dash' },
    })),
    annotations: limits.map((limit) => ({
      xref: 'paper',
      x: 1,
      xanchor: 'right',
      yref: 'y',
      y: limit.value,
      yanchor: 'bottom',
      text: `${limit.label}: ${limit.value.toFixed(0)} V`,
      showarrow: false,
      font: { size: 11, color: limit.color },
      bgcolor: 'rgba(255,255,255,0.75)',
    })),
  }
}

/**
 * SOC axis: 0–100 % domain; widen only if telemetry is outside that band.
 * Supports 0–1 fraction or 0–100 percent values.
 */
function yAxisForSoc(
  values: (number | null)[],
  yLabel: string,
  isFraction: boolean,
): Partial<Layout['yaxis']> {
  const nums = values.filter((v): v is number => v != null && !Number.isNaN(v))
  if (isFraction) {
    const maxV = nums.length ? Math.max(...nums) : 0
    const minV = nums.length ? Math.min(...nums) : 0
    const hi = maxV > 1 ? maxV * 1.02 : 1
    const lo = minV < 0 ? minV * 1.02 : 0
    return {
      title: { text: yLabel },
      range: [lo, hi],
      tickformat: ',.0%',
      autorange: false,
    }
  }
  const maxV = nums.length ? Math.max(...nums) : 0
  const minV = nums.length ? Math.min(...nums) : 0
  const hi = maxV > 100 ? maxV * 1.02 : 100
  const lo = minV < 0 ? minV * 1.02 : 0
  return {
    title: { text: yLabel },
    range: [lo, hi],
    tickformat: ',.0f',
    ticksuffix: '%',
    autorange: false,
  }
}

function formatHoverValue({
  value,
  yLabel,
  isFraction,
}: {
  value: number | null
  yLabel: string
  isFraction: boolean
}): string {
  if (value === null || Number.isNaN(value)) return 'N/A'

  if (yLabel === 'SOC' || yLabel === '%' || yLabel === 'SOH %') {
    const pct = isFraction ? value * 100 : value
    return `${pct.toFixed(2)}%`
  }

  return `${value.toFixed(2)} ${yLabel}`
}

function createTagPattern(nameScada: string): string {
  return nameScada.replace(/\d+/g, '[INT]')
}

function formatOptionalNumber(value: number | null | undefined): string | null {
  if (value == null || Number.isNaN(value)) return null
  return Number.isInteger(value) ? String(value) : value.toFixed(4)
}

function formatRangeValues({
  values,
  unit,
  prefix = '',
}: {
  values: (number | null | undefined)[]
  unit: string
  prefix?: string
}): string | null {
  const nums = values.filter(
    (value): value is number => value != null && !Number.isNaN(value),
  )
  if (nums.length === 0) return null
  const unique = [...new Set(nums)].sort((a, b) => a - b)
  if (unique.length === 1) {
    return `${prefix}${formatOptionalNumber(unique[0])} ${unit}`
  }
  return (
    `${prefix}${formatOptionalNumber(unique[0])} - ` +
    `${formatOptionalNumber(unique[unique.length - 1])} ${unit}`
  )
}

function formatAccuracyRanges(
  payloads: (Record<string, unknown> | null | undefined)[],
  unit: 'mV' | '°C',
): string | null {
  const formatted = new Set<string>()
  payloads.forEach((payload) => {
    const ranges = payload?.ranges
    if (!Array.isArray(ranges)) return
    ranges.forEach((range) => {
      const record = range as Record<string, unknown>
      const min = record.temp_min_c
      const max = record.temp_max_c
      const accuracy = unit === 'mV' ? record.accuracy_mv : record.accuracy_c
      if (typeof accuracy !== 'number') return
      const tempRange =
        typeof min === 'number' && typeof max === 'number'
          ? `${min} - ${max} °C`
          : 'all temperatures'
      formatted.add(`${tempRange}: ±${accuracy} ${unit}`)
    })
  })
  return formatted.size > 0 ? [...formatted].join('; ') : null
}

function specsAccuracyItems({
  sensorTypeIds,
  specs,
}: {
  sensorTypeIds: number[]
  specs: BessStringSpec[]
}): AccuracyItem[] {
  if (specs.length === 0) return []
  const ids = new Set(sensorTypeIds)
  const items: AccuracyItem[] = []
  const add = (label: string, value: string | null) => {
    if (value) items.push({ label, value })
  }

  if (
    ids.has(SensorTypeEnum.BESS_STRING_VOLTAGE) ||
    ids.has(SensorTypeEnum.BESS_STRING_SUM_CELL_VOLTAGE)
  ) {
    add(
      'BMS total voltage accuracy',
      formatRangeValues({
        values: specs.map((spec) => spec.bms_total_voltage_accuracy_pct),
        unit: '%',
        prefix: '±',
      }),
    )
  }

  if (
    ids.has(SensorTypeEnum.BESS_STRING_MAX_CELL_VOLTAGE) ||
    ids.has(SensorTypeEnum.BESS_STRING_MIN_CELL_VOLTAGE) ||
    ids.has(SensorTypeEnum.BESS_STRING_AVG_CELL_VOLTAGE)
  ) {
    add(
      'BMS cell voltage accuracy',
      formatAccuracyRanges(
        specs.map((spec) => spec.bms_cell_voltage_accuracy_mv),
        'mV',
      ),
    )
  }

  if (
    ids.has(SensorTypeEnum.BESS_STRING_CURRENT) ||
    ids.has(SensorTypeEnum.BESS_STRING_MAX_ALLOWABLE_CHARGE_CURRENT) ||
    ids.has(SensorTypeEnum.BESS_STRING_MAX_ALLOWABLE_DISCHARGE_CURRENT)
  ) {
    add(
      'BMS current accuracy',
      formatRangeValues({
        values: specs.map((spec) => spec.bms_current_accuracy_pct),
        unit: '%',
        prefix: '±',
      }),
    )
  }

  if (
    ids.has(SensorTypeEnum.BESS_STRING_MAX_MODULE_TEMPERATURE) ||
    ids.has(SensorTypeEnum.BESS_STRING_MIN_MODULE_TEMPERATURE) ||
    ids.has(SensorTypeEnum.BESS_STRING_AVG_MODULE_TEMPERATURE) ||
    ids.has(SensorTypeEnum.BESS_STRING_MAX_CELL_TEMPERATURE) ||
    ids.has(SensorTypeEnum.BESS_STRING_MIN_CELL_TEMPERATURE) ||
    ids.has(SensorTypeEnum.BESS_STRING_AVG_CELL_TEMPERATURE)
  ) {
    add(
      'BMS temperature accuracy',
      formatAccuracyRanges(
        specs.map((spec) => spec.bms_temperature_accuracy_c),
        '°C',
      ),
    )
  }

  if (
    ids.has(SensorTypeEnum.BESS_STRING_SOC) ||
    ids.has(SensorTypeEnum.BESS_STRING_SOC_PERCENT) ||
    ids.has(SensorTypeEnum.BESS_STRING_SOH_PERCENT) ||
    ids.has(SensorTypeEnum.BESS_STRING_SOE_CHARGE_PERCENT) ||
    ids.has(SensorTypeEnum.BESS_STRING_SOE_DISCHARGE_PERCENT)
  ) {
    add(
      'BMS SOC accuracy',
      formatRangeValues({
        values: specs.map((spec) => spec.bms_soc_accuracy_pct),
        unit: '%',
        prefix: '±',
      }),
    )
    const notes = [
      ...new Set(
        specs
          .map((spec) => spec.bms_soc_accuracy_notes)
          .filter((note): note is string => !!note),
      ),
    ]
    add('BMS SOC accuracy notes', notes.length ? notes.join('; ') : null)
  }

  return items
}

function sensorPatterns({
  sensorTypeId,
  tags,
}: {
  sensorTypeId: number
  tags: Tag[]
}): SensorPatternSummary[] {
  const summaries = new Map<string, SensorPatternSummary>()
  tags
    .filter((tag) => tag.sensor_type_id === sensorTypeId && tag.name_scada)
    .forEach((tag) => {
      const pattern = createTagPattern(tag.name_scada)
      const key = [
        pattern,
        tag.unit_scada ?? '',
        tag.unit_scale ?? '',
        tag.unit_offset ?? '',
      ].join('|')
      const current = summaries.get(key)
      if (current) {
        current.count += 1
        return
      }
      summaries.set(key, {
        pattern,
        count: 1,
        unitScada: tag.unit_scada,
        unitScale: tag.unit_scale,
        unitOffset: tag.unit_offset,
      })
    })
  return [...summaries.values()].sort((a, b) => b.count - a.count)
}

function sensorTypeLabel(
  sensorType: SensorType | undefined,
  id: number,
): string {
  if (!sensorType) return `Sensor type ${id}`
  return `${sensorType.name_long} (${sensorType.name_short}, id ${id})`
}

function chartSensorTypeIds(
  spec: SingleChartSpec | GroupedChartSpec,
): number[] {
  if (spec.kind === 'single') return [spec.sensorTypeId]
  return spec.traces.map((trace) => trace.sensorTypeId)
}

function InfoSection({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <Stack gap={6}>
      <Text size="sm" fw={700}>
        {title}
      </Text>
      {children}
    </Stack>
  )
}

function InfoMetric({ label, value }: { label: string; value: string }) {
  return (
    <Stack gap={0}>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text size="sm" fw={600}>
        {value}
      </Text>
    </Stack>
  )
}

function ChartInfoPopover({
  summary,
  sensorTypeIds,
  sensorTypes,
  tags,
  bessStringSpecs,
  dcStringVoltageLimits,
}: {
  summary: string
  sensorTypeIds: number[]
  sensorTypes: SensorType[]
  tags: Tag[]
  bessStringSpecs: BessStringSpec[]
  dcStringVoltageLimits?: {
    lowerV: number | null
    upperV: number | null
  }
}) {
  const sensorTypeById = new Map(
    sensorTypes.map((sensorType) => [sensorType.sensor_type_id, sensorType]),
  )
  const accuracyItems = specsAccuracyItems({
    sensorTypeIds,
    specs: bessStringSpecs,
  })

  return (
    <Stack gap="md">
      <Text size="sm" c="dimmed">
        {summary}
      </Text>

      <InfoSection title="Sensor Type">
        <Stack gap={4}>
          {sensorTypeIds.map((id) => (
            <Text key={id} size="sm">
              {sensorTypeLabel(sensorTypeById.get(id), id)}
            </Text>
          ))}
        </Stack>
      </InfoSection>

      <Divider />

      <InfoSection title="Raw Tag Patterns">
        {sensorTypeIds.length === 0 ? (
          <Text size="sm" c="dimmed">
            No sensor types configured.
          </Text>
        ) : (
          <Stack gap="xs">
            {sensorTypeIds.map((id) => {
              const patterns = sensorPatterns({ sensorTypeId: id, tags }).slice(
                0,
                3,
              )
              return (
                <Stack key={id} gap={4}>
                  {sensorTypeIds.length > 1 && (
                    <Text size="xs" fw={700}>
                      {sensorTypeById.get(id)?.name_long ?? `Sensor type ${id}`}
                    </Text>
                  )}
                  {patterns.length === 0 ? (
                    <Text size="sm" c="dimmed">
                      No matching project tags found.
                    </Text>
                  ) : (
                    patterns.map((pattern) => (
                      <Stack
                        key={[
                          pattern.pattern,
                          pattern.unitScada,
                          pattern.unitScale,
                          pattern.unitOffset,
                        ].join('|')}
                        gap={3}
                      >
                        <Text
                          size="sm"
                          c="dimmed"
                          style={{
                            fontFamily: 'monospace',
                            wordBreak: 'break-word',
                          }}
                        >
                          {pattern.pattern}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {pattern.count} tags
                          {pattern.unitScada
                            ? ` · unit ${pattern.unitScada}`
                            : ''}
                          {pattern.unitScale != null
                            ? ` · scale ${pattern.unitScale}`
                            : ''}
                          {pattern.unitOffset != null
                            ? ` · offset ${pattern.unitOffset}`
                            : ''}
                        </Text>
                      </Stack>
                    ))
                  )}
                </Stack>
              )
            })}
          </Stack>
        )}
      </InfoSection>

      {dcStringVoltageLimits && (
        <>
          <Divider />

          <InfoSection title="Operating Limits">
            <SimpleGrid cols={2} spacing="sm">
              <InfoMetric
                label="Lower"
                value={
                  dcStringVoltageLimits.lowerV != null
                    ? `${dcStringVoltageLimits.lowerV.toFixed(0)} V`
                    : 'N/A'
                }
              />
              <InfoMetric
                label="Upper"
                value={
                  dcStringVoltageLimits.upperV != null
                    ? `${dcStringVoltageLimits.upperV.toFixed(0)} V`
                    : 'N/A'
                }
              />
            </SimpleGrid>
          </InfoSection>
        </>
      )}

      <Divider />

      <InfoSection title="Measurement Accuracy">
        {accuracyItems.length > 0 ? (
          <Stack gap={4}>
            {accuracyItems.map((item) => (
              <InfoMetric
                key={item.label}
                label={item.label}
                value={item.value}
              />
            ))}
          </Stack>
        ) : (
          <Text size="sm" c="dimmed">
            No vendor measurement accuracy is listed for this chart in the BESS
            string spec.
          </Text>
        )}
      </InfoSection>
    </Stack>
  )
}

type BessStringRealtimeChartsProps = {
  projectId: string
  realtimeData: RealtimeQuery
  lifetimeEnergyTotals: LifetimeEnergyTotals
  stringDevices: StringDeviceRef[]
  dcStringVoltageLimits: {
    lowerV: number | null
    upperV: number | null
  }
  bessStringSpecs: BessStringSpec[]
  sensorTypes: SensorType[]
  projectTags: Tag[]
  highlightedNotReportingDeviceIds: number[]
}

export const BessStringRealtimeCharts = ({
  projectId,
  realtimeData,
  lifetimeEnergyTotals,
  stringDevices,
  dcStringVoltageLimits,
  bessStringSpecs,
  sensorTypes,
  projectTags,
  highlightedNotReportingDeviceIds,
}: BessStringRealtimeChartsProps) => {
  const navigate = useNavigate()
  const [cellVoltageMode, setCellVoltageMode] = useState<'current' | 'delta'>(
    'current',
  )
  const [lifetimeEnergyMode, setLifetimeEnergyMode] = useState<
    'totals' | 'efficiency'
  >('totals')

  const handleBarClick = useCallback(
    (event: Readonly<PlotMouseEvent>) => {
      const pt = event.points?.[0]
      const raw = pt?.customdata
      const id = Array.isArray(raw) ? raw[0] : raw
      if (typeof id !== 'number' && typeof id !== 'string') return
      navigate(`/projects/${projectId}/device-details/single/${id}`)
    },
    [navigate, projectId],
  )

  const baseContext = useMemo(() => {
    const rt = realtimeData.data
    const axisSource =
      stringDevices.length > 0
        ? stringDevices
        : (rt?.device_ids ?? []).map((deviceId, index) => ({
            device_id: deviceId,
            name_long: rt?.device_names?.[index] ?? null,
          }))

    if (axisSource.length === 0) {
      return null
    }

    const axis = buildStringDeviceAxis(axisSource)
    const x = axis.deviceNames

    return {
      d: rt,
      axis,
      x,
      rtDeviceIds: rt?.device_ids ?? [],
    }
  }, [realtimeData.data, stringDevices])

  const chartElements = useMemo(() => {
    if (!baseContext) return []

    const { d, axis, x, rtDeviceIds } = baseContext
    const highlightedDeviceIds = new Set(highlightedNotReportingDeviceIds)

    return CHART_SPECS.map((spec, specIdx) => {
      if (spec.kind === 'single') {
        const trace = d?.traces?.find(
          (t) => t.sensor_type_id === spec.sensorTypeId,
        )
        const aligned = alignTraceToDeviceAxis(trace, rtDeviceIds, axis)
        if (!traceHasAnyValue(aligned.y)) {
          return null
        }
        const y = aligned.y
        const yFrac =
          spec.sensorTypeId === SensorTypeEnum.BESS_STRING_POWER
            ? false
            : valuesLookLikeFraction(y)
        const times = aligned.times
        const barColor = singleChartColor(spec.sensorTypeId)
        const dcPowerTrace = {
          type: 'bar',
          x,
          y,
          marker: barMarkerWithFreshness(barColor, times),
          customdata: axis.deviceIds.map((deviceId, index) => {
            const t = times[index]
            const value = y[index] ?? null
            const updated = formatUpdatedHover(t)
            return [
              deviceId,
              updated.relative,
              formatHoverValue({
                value,
                yLabel: spec.yLabel,
                isFraction: yFrac,
              }),
              updated.freshness,
            ]
          }),
          hovertemplate:
            '%{x}<br>%{customdata[2]}<br>Updated: %{customdata[1]} · ' +
            '%{customdata[3]}<extra></extra>',
        } satisfies Partial<Data>
        const data: Partial<Data>[] = [dcPowerTrace]
        const isDcPowerChart =
          spec.sensorTypeId === SensorTypeEnum.BESS_STRING_POWER
        const availablePowerValues: (number | null)[] = []
        let layoutDeviceNames = x
        let warningX = x
        let warningY = y
        let warningDeviceIds: (number | null | undefined)[] = axis.deviceIds

        if (isDcPowerChart) {
          const availableDischargeTrace = d?.traces?.find(
            (t) =>
              t.sensor_type_id ===
              SensorTypeEnum.BESS_STRING_AVAILABLE_DISCHARGE_POWER,
          )
          const availableChargeTrace = d?.traces?.find(
            (t) =>
              t.sensor_type_id ===
              SensorTypeEnum.BESS_STRING_AVAILABLE_CHARGE_POWER,
          )
          const alignedAvailableDischarge = alignTraceToDeviceAxis(
            availableDischargeTrace,
            rtDeviceIds,
            axis,
          )
          const alignedAvailableCharge = alignTraceToDeviceAxis(
            availableChargeTrace,
            rtDeviceIds,
            axis,
          )
          const availableDischarge = alignedAvailableDischarge.y
          const availableCharge = alignedAvailableCharge.y.map((value) =>
            value !== null ? -value : null,
          )
          const visibleIndices = axis.deviceIds
            .map((_deviceId, index) => index)
            .filter(
              (index) =>
                y[index] != null ||
                availableDischarge[index] != null ||
                availableCharge[index] != null,
            )
          const visibleX = visibleIndices.map((index) => x[index] ?? '')
          const visibleY = visibleIndices.map((index) => y[index] ?? null)
          const visibleTimes = visibleIndices.map((index) => times[index])
          const visibleDeviceIds = visibleIndices.map(
            (index) => axis.deviceIds[index] ?? null,
          )
          const visibleAvailableDischarge = visibleIndices.map(
            (index) => availableDischarge[index] ?? null,
          )
          const visibleAvailableDischargeTimes = visibleIndices.map(
            (index) => alignedAvailableDischarge.times[index],
          )
          const visibleAvailableCharge = visibleIndices.map(
            (index) => availableCharge[index] ?? null,
          )
          const visibleAvailableChargeTimes = visibleIndices.map(
            (index) => alignedAvailableCharge.times[index],
          )

          layoutDeviceNames = visibleX
          warningX = visibleX
          warningY = visibleY
          warningDeviceIds = visibleDeviceIds

          dcPowerTrace.x = visibleX
          dcPowerTrace.y = visibleY
          dcPowerTrace.marker = barMarkerWithFreshness(barColor, visibleTimes)
          dcPowerTrace.customdata = visibleTimes.map((t, i) => {
            const value = visibleY[i] ?? null
            const updated = formatUpdatedHover(t)
            return [
              visibleDeviceIds[i],
              updated.relative,
              formatHoverValue({
                value,
                yLabel: spec.yLabel,
                isFraction: yFrac,
              }),
              updated.freshness,
            ]
          })

          availablePowerValues.push(
            ...visibleAvailableDischarge,
            ...visibleAvailableCharge,
          )

          if (traceHasAnyValue(visibleAvailableDischarge)) {
            data.push({
              type: 'scatter',
              mode: 'markers',
              name: 'Available discharge',
              x: visibleX,
              y: visibleAvailableDischarge,
              marker: {
                ...barMarkerWithFreshness(
                  AVAILABLE_DISCHARGE_POWER_COLOR,
                  visibleAvailableDischargeTimes,
                ),
                size: AVAILABLE_POWER_MARKER_SIZE,
              },
              customdata: visibleAvailableDischargeTimes.map((time) => {
                const updated = formatUpdatedHover(time)
                return [updated.relative, updated.freshness]
              }),
              hovertemplate:
                '%{x}<br>Available discharge: %{y:.2f} MWdc<br>Updated: ' +
                '%{customdata[0]} · %{customdata[1]}<extra></extra>',
            })
          }

          if (traceHasAnyValue(visibleAvailableCharge)) {
            data.push({
              type: 'scatter',
              mode: 'markers',
              name: 'Available charge',
              x: visibleX,
              y: visibleAvailableCharge,
              customdata: visibleAvailableCharge.map((value, index) => {
                const updated = formatUpdatedHover(
                  visibleAvailableChargeTimes[index],
                )
                return [
                  value !== null ? Math.abs(value).toFixed(2) : 'N/A',
                  updated.relative,
                  updated.freshness,
                ]
              }),
              marker: {
                ...barMarkerWithFreshness(
                  AVAILABLE_CHARGE_POWER_COLOR,
                  visibleAvailableChargeTimes,
                ),
                size: AVAILABLE_POWER_MARKER_SIZE,
              },
              hovertemplate:
                '%{x}<br>Available charge: %{customdata[0]} MWdc<br>Updated: ' +
                '%{customdata[1]} · %{customdata[2]}<extra></extra>',
            })
          }
        }

        if (NOT_REPORTING_WARNING_SENSOR_IDS.has(spec.sensorTypeId)) {
          const warningTrace = notReportingWarningTrace({
            x: warningX,
            y: warningY,
            deviceIds: warningDeviceIds,
            highlightedDeviceIds,
          })
          if (warningTrace) {
            data.push(warningTrace)
          }
        }

        let yaxis: Partial<Layout['yaxis']> = {
          title: { text: spec.yLabel },
          tickformat: yFrac ? ',.0%' : undefined,
        }
        if (spec.sensorTypeId === SensorTypeEnum.BESS_STRING_POWER) {
          yaxis = {
            ...yaxis,
            range: yRangeForDcPowerMw([...y, ...availablePowerValues]),
            autorange: false,
            tickformat: '.4~f',
          }
        } else if (spec.sensorTypeId === SensorTypeEnum.BESS_STRING_CURRENT) {
          yaxis = {
            ...yaxis,
            range: yRangeForDcCurrentA(y),
            autorange: false,
          }
        } else if (spec.title === DC_STRING_VOLTAGE_CHART_TITLE) {
          const range = yRangeForDcStringVoltage({
            values: y,
            lowerLimitV: dcStringVoltageLimits.lowerV,
            upperLimitV: dcStringVoltageLimits.upperV,
          })
          yaxis = {
            ...yaxis,
            range,
            autorange: range ? false : undefined,
          }
        } else if (
          spec.sensorTypeId === SensorTypeEnum.BESS_STRING_SOC ||
          spec.sensorTypeId === SensorTypeEnum.BESS_STRING_SOC_PERCENT
        ) {
          yaxis = yAxisForSoc(y, spec.yLabel, yFrac)
        }

        const layout = buildBessStringChartLayout({
          deviceNames: layoutDeviceNames,
          yaxis,
        })
        const limitLayout =
          spec.title === DC_STRING_VOLTAGE_CHART_TITLE
            ? dcStringVoltageLimitLayout({
                lowerLimitV: dcStringVoltageLimits.lowerV,
                upperLimitV: dcStringVoltageLimits.upperV,
              })
            : {}

        return (
          <CustomCard
            key={`s-${spec.sensorTypeId}-${specIdx}`}
            title={spec.title}
            info={
              <ChartInfoPopover
                summary={spec.info}
                sensorTypeIds={chartSensorTypeIds(spec)}
                sensorTypes={sensorTypes}
                tags={projectTags}
                bessStringSpecs={bessStringSpecs}
                dcStringVoltageLimits={
                  spec.title === DC_STRING_VOLTAGE_CHART_TITLE
                    ? dcStringVoltageLimits
                    : undefined
                }
              />
            }
            {...CHART_CARD_SHELL}
          >
            <div style={CHART_PLOT_WRAPPER_STYLE}>
              <PlotlyPlot
                data={data}
                layout={{ ...layout, ...limitLayout }}
                isLoading={realtimeData.isLoading}
                onClick={handleBarClick}
              />
            </div>
          </CustomCard>
        )
      }

      if (spec.title === LIFETIME_ENERGY_CHART_TITLE) {
        const hasLifetimeEnergyData =
          lifetimeEnergyTotals.chargeTotalsMWh.some(
            (value) => value !== null,
          ) ||
          lifetimeEnergyTotals.dischargeTotalsMWh.some(
            (value) => value !== null,
          )
        if (!hasLifetimeEnergyData && !lifetimeEnergyTotals.isLoading) {
          return null
        }

        const efficiencyMax =
          lifetimeEnergyTotals.impliedEfficiencyPct.reduce<number>(
            (max, value) => {
              if (value === null || Number.isNaN(value)) return max
              return Math.max(max, value)
            },
            100,
          )
        const energyMax = Math.max(
          0,
          ...lifetimeEnergyTotals.chargeTotalsMWh.filter(
            (v): v is number => v !== null && !Number.isNaN(v) && v >= 0,
          ),
          ...lifetimeEnergyTotals.dischargeTotalsMWh.filter(
            (v): v is number => v !== null && !Number.isNaN(v) && v >= 0,
          ),
        )
        const showLifetimeEfficiency = lifetimeEnergyMode === 'efficiency'
        const efficiencyMarkerColors =
          lifetimeEnergyTotals.impliedEfficiencyPct.map((value) =>
            value !== null && value > 100
              ? 'rgba(46, 204, 113, 0.5)'
              : PCS_ACTIVE_POWER_COLOR,
          )

        return (
          <CustomCard
            key={`g-${spec.title}-${specIdx}`}
            title={spec.title}
            info={
              <ChartInfoPopover
                summary={
                  showLifetimeEfficiency
                    ? 'Implied DC efficiency per string calculated as last-30-day discharge total divided by last-30-day charge total from daily KPI history.'
                    : 'Per-string totals built by summing the daily BESS string charged/discharged KPI values over the last 30 days.'
                }
                sensorTypeIds={chartSensorTypeIds(spec)}
                sensorTypes={sensorTypes}
                tags={projectTags}
                bessStringSpecs={bessStringSpecs}
              />
            }
            headerChildren={
              <SegmentedControl
                value={lifetimeEnergyMode}
                onChange={(value) =>
                  setLifetimeEnergyMode(value as 'totals' | 'efficiency')
                }
                data={[
                  { label: 'Totals', value: 'totals' },
                  { label: 'Efficiency', value: 'efficiency' },
                ]}
                size="xs"
                onClick={(event) => event.stopPropagation()}
              />
            }
            {...CHART_CARD_SHELL}
          >
            <div style={CHART_PLOT_WRAPPER_STYLE}>
              <PlotlyPlot
                data={
                  showLifetimeEfficiency
                    ? [
                        {
                          type: 'bar',
                          name: 'Implied DC efficiency',
                          x: lifetimeEnergyTotals.deviceNames,
                          y: lifetimeEnergyTotals.impliedEfficiencyPct,
                          marker: { color: efficiencyMarkerColors },
                          customdata:
                            lifetimeEnergyTotals.impliedEfficiencyPct.map(
                              (value) => [
                                formatHoverValue({
                                  value,
                                  yLabel: '%',
                                  isFraction: false,
                                }),
                                value !== null && value > 100
                                  ? '<br><i>Likely data issue in selected date range.</i>'
                                  : '',
                              ],
                            ),
                          hovertemplate:
                            '%{x}<br>%{fullData.name}: %{customdata[0]}' +
                            '%{customdata[1]}' +
                            '<extra></extra>',
                          showlegend: false,
                        } as Partial<Data>,
                      ]
                    : [
                        {
                          type: 'bar',
                          name: 'Charge total',
                          x: lifetimeEnergyTotals.deviceNames,
                          y: lifetimeEnergyTotals.chargeTotalsMWh,
                          marker: { color: PCS_ENERGY_GROUP_COLORS[0] },
                          customdata: lifetimeEnergyTotals.chargeTotalsMWh.map(
                            (value) =>
                              formatHoverValue({
                                value,
                                yLabel: spec.yLabel,
                                isFraction: false,
                              }),
                          ),
                          hovertemplate:
                            '%{x}<br>%{fullData.name}: %{customdata}<extra></extra>',
                        } as Partial<Data>,
                        {
                          type: 'bar',
                          name: 'Discharge total',
                          x: lifetimeEnergyTotals.deviceNames,
                          y: lifetimeEnergyTotals.dischargeTotalsMWh,
                          marker: { color: PCS_ENERGY_GROUP_COLORS[1] },
                          customdata:
                            lifetimeEnergyTotals.dischargeTotalsMWh.map(
                              (value) =>
                                formatHoverValue({
                                  value,
                                  yLabel: spec.yLabel,
                                  isFraction: false,
                                }),
                            ),
                          hovertemplate:
                            '%{x}<br>%{fullData.name}: %{customdata}<extra></extra>',
                        } as Partial<Data>,
                      ]
                }
                layout={buildBessStringChartLayout({
                  deviceNames: lifetimeEnergyTotals.deviceNames,
                  yaxis: {
                    title: {
                      text: showLifetimeEfficiency ? '%' : spec.yLabel,
                    },
                    range: showLifetimeEfficiency
                      ? [0, Math.max(100, (efficiencyMax ?? 100) * 1.05)]
                      : [0, Math.max(0.1, energyMax * 1.05)],
                    tickformat: showLifetimeEfficiency ? ',.0f' : undefined,
                    ticksuffix: showLifetimeEfficiency ? '%' : undefined,
                  },
                  showLegend: !showLifetimeEfficiency,
                  barmode: showLifetimeEfficiency ? 'overlay' : 'group',
                })}
                isLoading={lifetimeEnergyTotals.isLoading}
              />
            </div>
          </CustomCard>
        )
      }

      const plotTraces: Partial<Data>[] = []
      const seriesColors = groupedChartColors(spec.title)
      const isCellVoltageChart = spec.title === CELL_VOLTAGE_CHART_TITLE
      const showCellVoltageDelta =
        isCellVoltageChart && cellVoltageMode === 'delta'
      let any = false

      if (showCellVoltageDelta) {
        const maxTrace = d?.traces?.find(
          (t) =>
            t.sensor_type_id === SensorTypeEnum.BESS_STRING_MAX_CELL_VOLTAGE,
        )
        const minTrace = d?.traces?.find(
          (t) =>
            t.sensor_type_id === SensorTypeEnum.BESS_STRING_MIN_CELL_VOLTAGE,
        )
        const alignedMax = alignTraceToDeviceAxis(maxTrace, rtDeviceIds, axis)
        const alignedMin = alignTraceToDeviceAxis(minTrace, rtDeviceIds, axis)

        if (traceHasAnyValue(alignedMax.y) || traceHasAnyValue(alignedMin.y)) {
          const deltaY = axis.deviceIds.map((_deviceId, index) => {
            const maxValue = alignedMax.y[index]
            const minValue = alignedMin.y[index]
            if (maxValue == null || minValue == null) return null
            return maxValue - minValue
          })
          any = deltaY.some((value) => value !== null && value !== undefined)
          const deltaTimes = axis.deviceIds.map((_deviceId, index) =>
            oldestTimestamp([alignedMax.times[index], alignedMin.times[index]]),
          )
          plotTraces.push({
            type: 'bar',
            name: 'Delta',
            x,
            y: deltaY,
            marker: barMarkerWithFreshness(PCS_DC_VOLTAGE_COLOR, deltaTimes),
            customdata: axis.deviceIds.map((deviceId, index) => {
              const maxValue = alignedMax.y[index] ?? null
              const minValue = alignedMin.y[index] ?? null
              const deltaValue =
                maxValue !== null && minValue !== null
                  ? maxValue - minValue
                  : null
              const referenceTime = oldestTimestamp([
                alignedMax.times[index],
                alignedMin.times[index],
              ])
              const updated = formatUpdatedHover(referenceTime)
              return [
                deviceId,
                updated.relative,
                formatHoverValue({
                  value: deltaValue,
                  yLabel: spec.yLabel,
                  isFraction: false,
                }),
                updated.freshness,
                formatHoverValue({
                  value: maxValue,
                  yLabel: spec.yLabel,
                  isFraction: false,
                }),
                formatHoverValue({
                  value: minValue,
                  yLabel: spec.yLabel,
                  isFraction: false,
                }),
              ]
            }),
            hovertemplate:
              '%{x}<br>Delta: %{customdata[2]}<br>Max: %{customdata[4]}' +
              '<br>Min: %{customdata[5]}<br>Updated: %{customdata[1]} · ' +
              '%{customdata[3]}<extra></extra>',
          })
        }
      } else {
        spec.traces.forEach((sub, j) => {
          const trace = d?.traces?.find(
            (t) => t.sensor_type_id === sub.sensorTypeId,
          )
          const aligned = alignTraceToDeviceAxis(trace, rtDeviceIds, axis)
          if (!traceHasAnyValue(aligned.y)) return
          any = true
          const y = aligned.y
          const traceYFrac =
            spec.yLabel === 'MW' ? false : valuesLookLikeFraction(y)
          const times = aligned.times
          const seriesColor = seriesColors[j % seriesColors.length]
          plotTraces.push({
            type: 'bar',
            name: sub.label,
            x,
            y,
            marker: barMarkerWithFreshness(seriesColor, times),
            customdata: axis.deviceIds.map((deviceId, index) => {
              const t = times[index]
              const value = y[index] ?? null
              const updated = formatUpdatedHover(t)
              return [
                deviceId,
                updated.relative,
                formatHoverValue({
                  value,
                  yLabel: spec.yLabel,
                  isFraction: traceYFrac,
                }),
                updated.freshness,
              ]
            }),
            hovertemplate:
              '%{x}<br>%{fullData.name}: %{customdata[2]}<br>Updated: ' +
              '%{customdata[1]} · %{customdata[3]}<extra></extra>',
          })
        })
      }

      if (!any) return null

      const flatY: (number | null)[] = []
      for (const tr of plotTraces) {
        if (tr && 'y' in tr && Array.isArray(tr.y)) {
          for (const v of tr.y as (number | null)[]) {
            flatY.push(v ?? null)
          }
        }
      }
      const yFrac = showCellVoltageDelta
        ? false
        : spec.yLabel === 'MW'
          ? false
          : valuesLookLikeFraction(flatY.map((v) => v ?? null))

      const layout = buildBessStringChartLayout({
        deviceNames: x,
        yaxis: {
          title: { text: spec.yLabel },
          tickformat:
            spec.yLabel === 'MW' ? '.4~f' : yFrac ? ',.0%' : undefined,
        },
        showLegend: !showCellVoltageDelta,
        barmode: 'group',
      })

      return (
        <CustomCard
          key={`g-${spec.title}-${specIdx}`}
          title={spec.title}
          info={
            <ChartInfoPopover
              summary={spec.info}
              sensorTypeIds={chartSensorTypeIds(spec)}
              sensorTypes={sensorTypes}
              tags={projectTags}
              bessStringSpecs={bessStringSpecs}
            />
          }
          headerChildren={
            isCellVoltageChart ? (
              <SegmentedControl
                value={cellVoltageMode}
                onChange={(value) =>
                  setCellVoltageMode(value as 'current' | 'delta')
                }
                data={[
                  { label: 'Current', value: 'current' },
                  { label: 'Delta', value: 'delta' },
                ]}
                size="xs"
                onClick={(event) => event.stopPropagation()}
              />
            ) : undefined
          }
          {...CHART_CARD_SHELL}
        >
          <div style={CHART_PLOT_WRAPPER_STYLE}>
            <PlotlyPlot
              data={plotTraces}
              layout={layout}
              isLoading={realtimeData.isLoading}
              onClick={handleBarClick}
            />
          </div>
        </CustomCard>
      )
    })
  }, [
    baseContext,
    bessStringSpecs,
    cellVoltageMode,
    dcStringVoltageLimits,
    handleBarClick,
    highlightedNotReportingDeviceIds,
    lifetimeEnergyMode,
    lifetimeEnergyTotals,
    projectTags,
    realtimeData.isLoading,
    sensorTypes,
  ])

  const visibleCharts = chartElements.filter(Boolean)

  if (realtimeData.error) {
    return (
      <Text size="sm" c="red">
        Could not load string telemetry for charts.
      </Text>
    )
  }

  return (
    <Stack gap="md">
      {realtimeData.isLoading ? (
        <Stack gap="md" w="100%" align="stretch">
          {CHART_SPECS.map((spec) => (
            <CustomCard
              key={spec.title}
              title={spec.title}
              {...CHART_CARD_SHELL}
            >
              <Center h="100%">
                <Loader size="md" />
              </Center>
            </CustomCard>
          ))}
        </Stack>
      ) : visibleCharts.length === 0 ? (
        <Text size="sm" c="dimmed">
          No BESS string telemetry matched these charts yet. Tags may be missing
          or names may differ in SCADA.
        </Text>
      ) : (
        <Stack gap="md" w="100%" align="stretch">
          {visibleCharts}
        </Stack>
      )}
    </Stack>
  )
}
