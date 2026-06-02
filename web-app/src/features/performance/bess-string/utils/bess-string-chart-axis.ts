import type { Layout } from 'plotly.js'

export type StringDeviceRef = {
  device_id: number
  device_model_id?: number | null
  name_long: string | null
}

type StringDeviceAxis = {
  deviceIds: number[]
  deviceModelIds: (number | null | undefined)[]
  deviceNames: string[]
}

export function buildStringDeviceAxis(
  devices: StringDeviceRef[],
): StringDeviceAxis {
  const sorted = [...devices].sort((a, b) =>
    deviceDisplayName(a).localeCompare(deviceDisplayName(b), undefined, {
      numeric: true,
      sensitivity: 'base',
    }),
  )

  return {
    deviceIds: sorted.map((device) => device.device_id),
    deviceModelIds: sorted.map((device) => device.device_model_id),
    deviceNames: sorted.map((device) => deviceDisplayName(device)),
  }
}

function deviceDisplayName(device: StringDeviceRef): string {
  return device.name_long || `String ${device.device_id}`
}

function categoryXAxis(deviceNames: string[]): Partial<Layout['xaxis']> {
  return {
    type: 'category',
    categoryorder: 'array',
    categoryarray: deviceNames,
    range: [-0.5, Math.max(deviceNames.length - 0.5, 0.5)],
    tickangle: -35,
    automargin: false,
  }
}

/** Shared margins so every chart has the same plot area width. */
const BESS_STRING_CHART_MARGIN = {
  l: 72,
  r: 12,
  t: 12,
  b: 64,
  pad: 0,
} as const

const BESS_STRING_GROUPED_LEGEND: Partial<Layout['legend']> = {
  orientation: 'h',
  xref: 'paper',
  yref: 'paper',
  x: 0.5,
  xanchor: 'center',
  y: -0.08,
  yanchor: 'top',
}

export function buildBessStringChartLayout({
  deviceNames,
  yaxis,
  showLegend = false,
  barmode,
}: {
  deviceNames: string[]
  yaxis: Partial<Layout['yaxis']>
  showLegend?: boolean
  barmode?: 'group' | 'overlay'
}): Partial<Layout> {
  return {
    autosize: true,
    bargap: 0.08,
    bargroupgap: 0.06,
    margin: { ...BESS_STRING_CHART_MARGIN },
    barmode,
    xaxis: categoryXAxis(deviceNames),
    yaxis: {
      automargin: false,
      ...yaxis,
    },
    showlegend: showLegend,
    legend: showLegend ? BESS_STRING_GROUPED_LEGEND : undefined,
  }
}

type RealtimeTraceSlice = {
  values?: (number | null)[]
  times?: (string | null | undefined)[]
}

/** Re-index realtime trace arrays onto the canonical project string list. */
export function alignTraceToDeviceAxis(
  trace: RealtimeTraceSlice | undefined,
  realtimeDeviceIds: number[],
  axis: StringDeviceAxis,
): { y: (number | null)[]; times: (string | null | undefined)[] } {
  const valueById = new Map<number, number | null>()
  const timeById = new Map<number, string | null | undefined>()

  realtimeDeviceIds.forEach((deviceId, index) => {
    valueById.set(deviceId, trace?.values?.[index] ?? null)
    timeById.set(deviceId, trace?.times?.[index] ?? null)
  })

  return {
    y: axis.deviceIds.map((deviceId) => valueById.get(deviceId) ?? null),
    times: axis.deviceIds.map((deviceId) => timeById.get(deviceId) ?? null),
  }
}
