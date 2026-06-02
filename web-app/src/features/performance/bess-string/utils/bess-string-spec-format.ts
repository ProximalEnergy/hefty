import type { BessStringSpec } from '@/api/v1/operational/bess_strings'

export function formatSpecValue(
  value: string | number | null | undefined,
): string {
  if (value === null || value === undefined || value === '') {
    return 'N/A'
  }
  return String(value)
}

export function formatKw(kw: number | null | undefined): string {
  if (kw === null || kw === undefined) {
    return 'N/A'
  }
  return `${kw.toFixed(2)} kW`
}

export function formatKwh(kwh: number | null | undefined): string {
  if (kwh === null || kwh === undefined) {
    return 'N/A'
  }
  return `${kwh.toFixed(2)} kWh`
}

export function formatVoltageRange(
  minV: number | null | undefined,
  maxV: number | null | undefined,
): string {
  if (minV == null && maxV == null) {
    return 'N/A'
  }
  if (minV != null && maxV != null) {
    return `${minV.toFixed(0)} – ${maxV.toFixed(0)} V`
  }
  return formatSpecValue(minV ?? maxV)
}

export function formatTempRange(
  minC: number | null | undefined,
  maxC: number | null | undefined,
): string {
  if (minC == null && maxC == null) {
    return 'N/A'
  }
  if (minC != null && maxC != null) {
    return `${minC.toFixed(0)} – ${maxC.toFixed(0)} °C`
  }
  return formatSpecValue(minC ?? maxC)
}

export function formatDimensions(spec: BessStringSpec): string {
  const { dimensions_width_mm, dimensions_depth_mm, dimensions_height_mm } =
    spec
  if (
    dimensions_width_mm == null ||
    dimensions_depth_mm == null ||
    dimensions_height_mm == null
  ) {
    return 'N/A'
  }
  return (
    `${dimensions_width_mm.toFixed(0)} × ` +
    `${dimensions_depth_mm.toFixed(0)} × ` +
    `${dimensions_height_mm.toFixed(0)} mm`
  )
}

type AccuracyRange = {
  temp_min_c?: number
  temp_max_c?: number
  accuracy_mv?: number
  accuracy_c?: number
}

export function formatBmsAccuracyRanges(
  payload: Record<string, unknown> | null | undefined,
  unit: 'mV' | '°C',
): string {
  const ranges = payload?.ranges
  if (!Array.isArray(ranges) || ranges.length === 0) {
    return 'N/A'
  }

  return (ranges as AccuracyRange[])
    .map((range) => {
      const tempLabel = formatTempRange(range.temp_min_c, range.temp_max_c)
      const accuracy = unit === 'mV' ? range.accuracy_mv : range.accuracy_c
      if (accuracy == null) {
        return tempLabel
      }
      return `${tempLabel}: ±${accuracy} ${unit}`
    })
    .join('; ')
}

export function formatStandards(
  standards: BessStringSpec['standards'],
): string {
  if (!standards) {
    return 'N/A'
  }
  if (Array.isArray(standards)) {
    return standards.length > 0 ? standards.join(', ') : 'N/A'
  }
  return 'N/A'
}

export function formatAuxiliaryFrequency(
  value: BessStringSpec['auxiliary_power_frequency_hz'],
): string {
  if (!value) {
    return 'N/A'
  }
  if (Array.isArray(value)) {
    return value.map((hz) => `${hz} Hz`).join(', ')
  }
  return 'N/A'
}

type PowerLimitMap = {
  soc_pct?: (string | number)[]
  temperature_c?: (string | number)[]
  multipliers?: number[][]
  rated_power_kw?: number
}

export function parsePowerLimitMap(
  value: Record<string, unknown> | null | undefined,
): PowerLimitMap | null {
  if (!value || !Array.isArray(value.multipliers)) {
    return null
  }
  return value as PowerLimitMap
}

export function powerLimitMapToMwGrid(map: PowerLimitMap): number[][] | null {
  const ratedKw = map.rated_power_kw
  if (!ratedKw || !Array.isArray(map.multipliers)) {
    return null
  }
  return map.multipliers.map((row) =>
    row.map((multiplier) => (multiplier * ratedKw) / 1000),
  )
}
