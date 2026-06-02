import { useGetCompanyTeamsWithMembers } from '@/api/admin'
import { DeviceTypeEnum, KPITypeEnum, SensorTypeEnum } from '@/api/enumerations'
import { useGetSelfCompanyUsers } from '@/api/v1/admin/users'
import { useGetBessStrings } from '@/api/v1/operational/bess_strings'
import type { CalendarEvent } from '@/api/v1/operational/calendar'
import {
  useGetCalendarEventCategories,
  useGetCalendarEvents,
} from '@/api/v1/operational/calendar'
import { useGetOperationalKPIData } from '@/api/v1/operational/kpi_data'
import {
  type CMMSTicket,
  useGetCMMSTickets,
} from '@/api/v1/operational/project/cmms_tickets'
import { useGetEventsSummary } from '@/api/v1/operational/project/events'
import { useGetSensorTypes } from '@/api/v1/operational/sensor_types'
import {
  useGetDataTimeseriesLast,
  useGetRealTimeByDeviceTypeID,
} from '@/api/v1/protected/web-application/projects/real_time'
import { useGetDevicesV2, useGetTags } from '@/hooks/api'
import { findAncestorDeviceIdByType, type Device } from '@/hooks/devices'
import type { EventSummary } from '@/hooks/types'
import {
  BESS_STRING_CHART_SENSOR_IDS,
  BESS_STRING_REALTIME_SENSOR_IDS,
} from '@/features/performance/bess-string/components/BessStringRealtimeCharts'
import { buildStringDeviceAxis } from '@/features/performance/bess-string/utils/bess-string-chart-axis'
import {
  type DataFreshnessTier,
  getWorstFreshnessTier,
  isDeviceNotReporting,
} from '@/features/performance/bess-string/utils/bess-string-realtime-staleness'
import type { BessStringContext } from '@/features/performance/bess-string/hooks/use-bess-string-context'
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import { useMemo } from 'react'
import { useNavigate } from 'react-router'
import { rrulestr } from 'rrule'

function buildActiveEventsSection(
  label: string,
  events: EventSummary[] | undefined,
) {
  const items = (events ?? [])
    .filter((event) => event.event_id !== null && event.event_id !== undefined)
    .map((event) => ({
      eventId: event.event_id,
      label: event.device_name_full || `Event ${event.event_id}`,
    }))

  return {
    label,
    count: items.length,
    events: items.slice(0, 5),
    remainingCount: Math.max(items.length - 5, 0),
  }
}

function sortHoverTickets(tickets: CMMSTicket[] | undefined) {
  return (tickets ?? [])
    .slice()
    .sort((left, right) => {
      const leftTime = left.source_created_at
        ? new Date(left.source_created_at).getTime()
        : new Date(left.db_created_at).getTime()
      const rightTime = right.source_created_at
        ? new Date(right.source_created_at).getTime()
        : new Date(right.db_created_at).getTime()

      return rightTime - leftTime
    })
    .slice(0, 5)
    .map((ticket) => ({
      key: ticket.key,
      summary: ticket.summary || ticket.summary_long || 'Untitled ticket',
      status: ticket.status || undefined,
    }))
}

dayjs.extend(utc)

const BESS_STRING_DEVICE_TYPE_ID = DeviceTypeEnum.BESS_STRING
const BESS_ENCLOSURE_DEVICE_TYPE_ID = DeviceTypeEnum.BESS_ENCLOSURE
const RECENT_STRING_POWER_MS = 10 * 60 * 1000

/** Types needed to walk String → … → PCS for IntraPCS balance grouping. */
const BESS_TREE_FOR_PCS_LOOKUP: number[] = [
  DeviceTypeEnum.BESS_STRING,
  DeviceTypeEnum.BESS_ENCLOSURE,
  DeviceTypeEnum.BESS_DC_SKID,
  DeviceTypeEnum.BESS_BANK,
  DeviceTypeEnum.BESS_PCS_MODULE_GROUP,
  DeviceTypeEnum.BESS_PCS_MODULE,
  DeviceTypeEnum.BESS_PCS,
]

/** Operational calendar_item_categories.short_name values for BESS DC PM. */
const PM_CATEGORY_SHORT_BESS_DC_ENCLOSURE = 'pm_bess_dc_enclosure'
const PM_CATEGORY_SHORT_BESS_DC_STRING = 'pm_bess_dc_string'

const PM_CATEGORY_SHORT_NAMES_MAINTENANCE = new Set([
  PM_CATEGORY_SHORT_BESS_DC_ENCLOSURE,
  PM_CATEGORY_SHORT_BESS_DC_STRING,
])

/** Categories treated as maintenance for this tile (short_name or long text). */
function isMaintenanceRelatedCategory(cat: {
  short_name: string
  long_name: string
}): boolean {
  const sn = cat.short_name.trim().toLowerCase()
  if (PM_CATEGORY_SHORT_NAMES_MAINTENANCE.has(sn)) {
    return true
  }
  const label = `${sn} ${cat.long_name}`.toLowerCase()
  return (
    /prevent(?:ive|ative)\s+maintenance/.test(label) ||
    /scheduled\s+maintenance/.test(label)
  )
}

const DC_ENCLOSURE_IN_TEXT =
  /\b(dc\s+)?enclosure\b|\bbess\s+dc\s+enclosure\b|\bdc\s+skid\b/i
const BESS_STRING_IN_TEXT = /\bbess\s+string\b|\bdc\s+string\b/i

function eventHay(event: CalendarEvent): string {
  return `${event.title}\n${event.description ?? ''}`.toLowerCase()
}

/** Match calendar text to project devices (names or whole device id). */
function textMentionsDevice(event: CalendarEvent, devices: Device[]): boolean {
  if (devices.length === 0) return false
  const hay = eventHay(event)
  for (const d of devices) {
    for (const raw of [d.name_long, d.name_short, d.name_full]) {
      const n = raw?.trim()
      if (n && n.length >= 2 && hay.includes(n.toLowerCase())) {
        return true
      }
    }
    const idRe = new RegExp(`\\b${d.device_id}\\b`)
    if (idRe.test(hay)) {
      return true
    }
  }
  return false
}

function mentionsDcEnclosure(event: CalendarEvent, devices: Device[]): boolean {
  if (textMentionsDevice(event, devices)) return true
  return DC_ENCLOSURE_IN_TEXT.test(eventHay(event))
}

function mentionsBessString(event: CalendarEvent, devices: Device[]): boolean {
  if (textMentionsDevice(event, devices)) return true
  return BESS_STRING_IN_TEXT.test(eventHay(event))
}

function pmCategoryShortName(
  event: CalendarEvent,
  categoryShortById: Map<string, string>,
): string | undefined {
  return categoryShortById.get(event.calendar_item_category_id)
}

function scopeLabelForPmEvent(
  event: CalendarEvent,
  enclosureDevices: Device[],
  stringDevices: Device[],
  usedFallback: boolean,
  categoryShortById: Map<string, string>,
): string {
  if (usedFallback) {
    return 'Other maintenance (e.g. PCS)'
  }
  const sn = pmCategoryShortName(event, categoryShortById)
  if (sn === PM_CATEGORY_SHORT_BESS_DC_ENCLOSURE) {
    return 'DC enclosure'
  }
  if (sn === PM_CATEGORY_SHORT_BESS_DC_STRING) {
    return 'BESS string'
  }
  const en = mentionsDcEnclosure(event, enclosureDevices)
  const str = mentionsBessString(event, stringDevices)
  if (en && str) {
    return 'DC enclosure & BESS string'
  }
  if (en) {
    return 'DC enclosure'
  }
  if (str) {
    return 'BESS string'
  }
  return 'Preventative maintenance'
}

/** Raw SOC → 0–1 fraction (matches Excel-style fractional SOC). */
function socRawToFraction(raw: number): number {
  if (Number.isNaN(raw)) return NaN
  return raw > 1.01 ? raw / 100 : raw
}

/**
 * Excel STDEV.P (population stdev over the data set; divisor n).
 * Empty input → 0.
 */
function stdevP(nums: number[]): number {
  if (nums.length === 0) return 0
  const mean = nums.reduce((a, b) => a + b, 0) / nums.length
  const v = nums.reduce((acc, x) => acc + (x - mean) ** 2, 0) / nums.length
  return Math.sqrt(v)
}

/** System balance: 1 − 2σ; σ = STDEV.P over all string SOC fractions. */
function systemBalanceScore01(socs01: number[]): number {
  if (socs01.length === 0) return 0
  return 1 - 2 * stdevP(socs01)
}

/**
 * Intra-PCS balance: per PCS, 1 − 2σ with σ = STDEV.P over that PCS’s string
 * SOCs; overall value is string-weighted. PCS grouping uses BESS_PCS ancestor
 * device_id (not immediate parent).
 */
function intraPcsBalanceScore01(
  entries: { soc01: number; pcsGroupKey: number }[],
): number {
  if (entries.length === 0) return 0
  const by = new Map<number, number[]>()
  for (const e of entries) {
    const arr = by.get(e.pcsGroupKey) ?? []
    arr.push(e.soc01)
    by.set(e.pcsGroupKey, arr)
  }
  let weighted = 0
  let nStrings = 0
  for (const arr of by.values()) {
    if (arr.length === 0) continue
    const sigma = stdevP(arr)
    const score = 1 - 2 * sigma
    weighted += score * arr.length
    nStrings += arr.length
  }
  return nStrings > 0 ? weighted / nStrings : 0
}

function clampUnitIntervalToPercent(x: number): number {
  return Math.max(0, Math.min(100, x * 100))
}

/**
 * Overall balance: average of system and intra-PCS scores (each 1 − 2×STDEV.P),
 * on 0–100 % display scale.
 */
function balanceScoresFromSoc(
  deviceIds: number[],
  socValues: (number | null)[] | undefined,
  deviceById: Map<number, Device>,
): {
  overallPct: number | null
  systemPct: number | null
  intraPcsPct: number | null
} {
  const entries: { soc01: number; pcsGroupKey: number }[] = []
  for (let i = 0; i < deviceIds.length; i++) {
    const id = deviceIds[i]
    const raw = socValues?.[i]
    if (id === undefined || raw === null || raw === undefined) continue
    const f = socRawToFraction(raw)
    if (Number.isNaN(f)) continue
    const pcsKey =
      findAncestorDeviceIdByType(id, DeviceTypeEnum.BESS_PCS, deviceById) ?? -1
    entries.push({ soc01: f, pcsGroupKey: pcsKey })
  }
  if (entries.length === 0) {
    return { overallPct: null, systemPct: null, intraPcsPct: null }
  }
  const socs = entries.map((e) => e.soc01)
  const systemScore = systemBalanceScore01(socs)
  const intraScore = intraPcsBalanceScore01(entries)
  const overall = (systemScore + intraScore) / 2
  return {
    overallPct: clampUnitIntervalToPercent(overall),
    systemPct: clampUnitIntervalToPercent(systemScore),
    intraPcsPct: clampUnitIntervalToPercent(intraScore),
  }
}

function realtimeTraceHasAnyValue(
  values: (number | null)[] | undefined,
): boolean {
  return (values ?? []).some(
    (v) => v !== null && v !== undefined && !Number.isNaN(v),
  )
}

function latestTimestamp(times: (string | null | undefined)[]): string | null {
  let latest: string | null = null
  let latestTs = -Infinity

  for (const time of times) {
    if (!time) continue
    const ts = new Date(time).getTime()
    if (Number.isNaN(ts)) continue
    if (ts > latestTs) {
      latestTs = ts
      latest = time
    }
  }

  return latest
}

function powerValueOrZero(value: number | null | undefined): number {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 0
  }

  return value
}

function isRecentTimestamp(
  time: string | null | undefined,
  nowMs: number,
): boolean {
  if (!time) return false
  const ts = new Date(time).getTime()
  return !Number.isNaN(ts) && nowMs - ts <= RECENT_STRING_POWER_MS
}

/**
 * Prefer BESS_STRING_SOC when it has data; many sites only publish
 * BESS_STRING_SOC_PERCENT.
 */
function pickBessStringSocTrace(
  traces: { sensor_type_id: number; values: (number | null)[] }[] | undefined,
): { sensor_type_id: number; values: (number | null)[] } | undefined {
  if (!traces?.length) return undefined
  const primary = traces.find(
    (t) => t.sensor_type_id === SensorTypeEnum.BESS_STRING_SOC,
  )
  if (primary && realtimeTraceHasAnyValue(primary.values)) {
    return primary
  }
  const pct = traces.find(
    (t) => t.sensor_type_id === SensorTypeEnum.BESS_STRING_SOC_PERCENT,
  )
  if (pct && realtimeTraceHasAnyValue(pct.values)) return pct
  return primary ?? pct
}

function getNextOccurrence(event: CalendarEvent): Date | null {
  const now = new Date()
  const exdates = new Set(event.exdates ?? [])
  if (event.rrule) {
    try {
      const rule = rrulestr(event.rrule)
      let next = rule.after(now, true)
      while (next && exdates.has(next.toISOString().slice(0, 10))) {
        next = rule.after(next)
      }
      return next
    } catch {
      return null
    }
  }
  const start = new Date(event.start_time)
  return start >= now ? start : null
}

function formatPreventativeMaintenanceDate(date: Date): string {
  const nextDate = dayjs.utc(date)
  const now = dayjs.utc()
  const isOutsideCurrentYear = nextDate.year() !== now.year()
  const isMoreThan180DaysAway = nextDate.diff(now, 'day') > 180

  if (!isOutsideCurrentYear || !isMoreThan180DaysAway) {
    return nextDate.format('MMMM D')
  }

  return nextDate.format('MMMM D, YYYY')
}

type NextPMInfo = {
  formattedDate: string
  calendarItemId: string
  occurrenceDate: Date
  event: CalendarEvent
}

/** Earliest next occurrence among already-filtered calendar rows. */
function getNextMaintenanceOccurrence(
  events: CalendarEvent[] | undefined,
): NextPMInfo | null {
  if (!events?.length) return null
  let earliest: {
    date: Date
    event: CalendarEvent
  } | null = null
  for (const event of events) {
    const next = getNextOccurrence(event)
    if (next && (!earliest || next < earliest.date)) {
      earliest = { date: next, event }
    }
  }
  if (!earliest) return null
  return {
    formattedDate: formatPreventativeMaintenanceDate(earliest.date),
    calendarItemId: earliest.event.calendar_item_id,
    occurrenceDate: earliest.date,
    event: earliest.event,
  }
}

/**
 * Prefer DC enclosure maintenance, then BESS string, then any other maintenance
 * (e.g. PCS) so PCS PM does not override enclosure/string entries.
 */
function pickNextMaintenancePreferringDcAssets(
  pmEvents: CalendarEvent[],
  enclosureDevices: Device[],
  stringDevices: Device[],
  categoryShortById: Map<string, string>,
): { result: NextPMInfo | null; usedFallback: boolean } {
  if (pmEvents.length === 0) {
    return { result: null, usedFallback: false }
  }
  const enclosureTier = pmEvents.filter((e) => {
    const sn = pmCategoryShortName(e, categoryShortById)
    if (sn === PM_CATEGORY_SHORT_BESS_DC_ENCLOSURE) {
      return true
    }
    if (sn === PM_CATEGORY_SHORT_BESS_DC_STRING) {
      return false
    }
    return mentionsDcEnclosure(e, enclosureDevices)
  })
  const stringTier = pmEvents.filter((e) => {
    const sn = pmCategoryShortName(e, categoryShortById)
    if (sn === PM_CATEGORY_SHORT_BESS_DC_STRING) {
      return true
    }
    if (sn === PM_CATEGORY_SHORT_BESS_DC_ENCLOSURE) {
      return false
    }
    return (
      mentionsBessString(e, stringDevices) &&
      !mentionsDcEnclosure(e, enclosureDevices)
    )
  })
  let result = getNextMaintenanceOccurrence(enclosureTier)
  if (result) {
    return { result, usedFallback: false }
  }
  result = getNextMaintenanceOccurrence(stringTier)
  if (result) {
    return { result, usedFallback: false }
  }
  result = getNextMaintenanceOccurrence(pmEvents)
  return { result, usedFallback: result != null }
}

type UseBessStringRealtimeViewModelProps = {
  context: BessStringContext
}

export function useBessStringRealtimeViewModel({
  context,
}: UseBessStringRealtimeViewModelProps) {
  const { projectId } = context
  const devices = useGetDevicesV2({
    pathParams: {
      projectId: projectId || '-1',
    },
    filters: {
      device_type_ids: [BESS_STRING_DEVICE_TYPE_ID],
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  const bessTreeDevices = useGetDevicesV2({
    pathParams: {
      projectId: projectId || '-1',
    },
    filters: {
      device_type_ids: BESS_TREE_FOR_PCS_LOOKUP,
    },
    queryOptions: {
      enabled: !!projectId,
      staleTime: 60_000,
    },
  })

  const pmScopeDevices = useGetDevicesV2({
    pathParams: {
      projectId: projectId || '-1',
    },
    filters: {
      device_type_ids: [
        BESS_STRING_DEVICE_TYPE_ID,
        BESS_ENCLOSURE_DEVICE_TYPE_ID,
      ],
    },
    queryOptions: {
      enabled: !!projectId,
      staleTime: 60_000,
    },
  })

  const realtimeData = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: BESS_STRING_DEVICE_TYPE_ID,
    },
    queryParams: {
      sensor_type_ids: BESS_STRING_REALTIME_SENSOR_IDS,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 30000,
      staleTime: 15000,
    },
  })

  const chartSensorTypes = useGetSensorTypes({
    queryParams: {
      sensor_type_ids: BESS_STRING_CHART_SENSOR_IDS,
    },
    queryOptions: {
      enabled: BESS_STRING_CHART_SENSOR_IDS.length > 0,
    },
  })

  const chartTags = useGetTags({
    pathParams: {
      projectId: projectId || '-1',
    },
    queryParams: {
      device_type_ids: [BESS_STRING_DEVICE_TYPE_ID],
      sensor_type_ids: BESS_STRING_CHART_SENSOR_IDS,
      in_tsdb: true,
    },
    queryOptions: {
      enabled: !!projectId,
      staleTime: 60_000,
    },
  })

  const stringDeviceModelIds = useMemo(() => {
    const ids = new Set<number>()
    ;(devices.data ?? []).forEach((device) => {
      if (device.device_model_id != null) {
        ids.add(device.device_model_id)
      }
    })
    return Array.from(ids).sort((a, b) => a - b)
  }, [devices.data])

  const bessStringSpecs = useGetBessStrings({
    queryParams: {
      device_model_ids: stringDeviceModelIds,
    },
    queryOptions: {
      enabled: stringDeviceModelIds.length > 0,
      staleTime: Infinity,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
    },
  })

  const dcStringVoltageLimits = useMemo(() => {
    const minValues = (bessStringSpecs.data ?? [])
      .map((spec) => spec.operating_voltage_min_v)
      .filter((value): value is number => value != null)
    const maxValues = (bessStringSpecs.data ?? [])
      .map((spec) => spec.operating_voltage_max_v)
      .filter((value): value is number => value != null)

    return {
      lowerV: minValues.length > 0 ? Math.min(...minValues) : null,
      upperV: maxValues.length > 0 ? Math.max(...maxValues) : null,
    }
  }, [bessStringSpecs.data])

  const lifetimeKpiStart = dayjs().subtract(30, 'day').format('YYYY-MM-DD')
  const lifetimeKpiEnd = dayjs().add(1, 'day').format('YYYY-MM-DD')

  const lifetimeEnergyKpiData = useGetOperationalKPIData({
    queryParams: {
      project_ids: [projectId || '-1'],
      kpi_type_ids: [
        KPITypeEnum.BESS_STRING_ENERGY_CHARGED,
        KPITypeEnum.BESS_STRING_ENERGY_DISCHARGED,
      ],
      include_device_data: true,
      start: lifetimeKpiStart,
      end: lifetimeKpiEnd,
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  const lifetimeEnergyTotals = useMemo(() => {
    const sumSeries = (
      values: (number | null)[] | undefined,
    ): number | null => {
      if (!values) return null
      const nums = values.filter((value): value is number => value !== null)
      if (nums.length === 0) return null
      return nums.reduce((sum, value) => sum + value, 0)
    }

    const pairedEfficiency = ({
      chargeValues,
      dischargeValues,
    }: {
      chargeValues: (number | null)[] | undefined
      dischargeValues: (number | null)[] | undefined
    }): number | null => {
      if (!chargeValues || !dischargeValues) return null

      const length = Math.max(chargeValues.length, dischargeValues.length)
      let chargeSum = 0
      let dischargeSum = 0
      let pairedDays = 0

      for (let i = 0; i < length; i += 1) {
        const charge = chargeValues[i]
        const discharge = dischargeValues[i]
        if (charge === null || discharge === null) continue
        chargeSum += charge
        dischargeSum += discharge
        pairedDays += 1
      }

      if (pairedDays === 0 || chargeSum <= 0) return null
      return (dischargeSum / chargeSum) * 100
    }

    const deviceAxis = buildStringDeviceAxis(devices.data ?? [])

    const charged = lifetimeEnergyKpiData.data?.find(
      (kpi) => kpi.kpi_type_id === KPITypeEnum.BESS_STRING_ENERGY_CHARGED,
    )
    const discharged = lifetimeEnergyKpiData.data?.find(
      (kpi) => kpi.kpi_type_id === KPITypeEnum.BESS_STRING_ENERGY_DISCHARGED,
    )

    const chargeDeviceValues =
      charged?.data.device_data_obj?.device_values || {}
    const dischargeDeviceValues =
      discharged?.data.device_data_obj?.device_values || {}

    return {
      deviceIds: deviceAxis.deviceIds,
      deviceNames: deviceAxis.deviceNames,
      chargeTotalsMWh: deviceAxis.deviceIds.map((deviceId) =>
        sumSeries(chargeDeviceValues[String(deviceId)]),
      ),
      dischargeTotalsMWh: deviceAxis.deviceIds.map((deviceId) =>
        sumSeries(dischargeDeviceValues[String(deviceId)]),
      ),
      impliedEfficiencyPct: deviceAxis.deviceIds.map((deviceId) =>
        pairedEfficiency({
          chargeValues: chargeDeviceValues[String(deviceId)],
          dischargeValues: dischargeDeviceValues[String(deviceId)],
        }),
      ),
      isLoading: lifetimeEnergyKpiData.isLoading || devices.isLoading,
    }
  }, [
    devices.data,
    devices.isLoading,
    lifetimeEnergyKpiData.data,
    lifetimeEnergyKpiData.isLoading,
  ])

  const activeEvents = useGetEventsSummary({
    pathParams: {
      projectId: projectId || '-1',
    },
    queryParams: {
      device_type_ids: [BESS_STRING_DEVICE_TYPE_ID],
      open: true,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 60000,
    },
  })

  const cmmsTickets = useGetCMMSTickets({
    pathParams: {
      project_id: projectId || '-1',
    },
    queryParams: {
      device_type_ids: [BESS_STRING_DEVICE_TYPE_ID],
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 60000,
    },
  })

  const calendarEvents = useGetCalendarEvents({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: { enabled: !!projectId, staleTime: 60_000 },
  })
  const calendarCategories = useGetCalendarEventCategories({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: { enabled: !!projectId },
  })
  const { data: companyUsers } = useGetSelfCompanyUsers({
    queryOptions: { enabled: !!projectId },
  })
  const { data: teamsWithMembers } = useGetCompanyTeamsWithMembers({
    queryOptions: { enabled: !!projectId },
  })

  const meterLastData = useGetDataTimeseriesLast({
    pathParams: {
      projectId: projectId || '-1',
    },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.METER_ACTIVE_POWER],
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 30000,
      staleTime: 15000,
    },
  })

  const bessMeterLastData = useGetDataTimeseriesLast({
    pathParams: {
      projectId: projectId || '-1',
    },
    queryParams: {
      sensor_type_ids: [
        SensorTypeEnum.BESS_MV_COLLECTOR_CIRCUIT_METER_ACTIVE_POWER,
      ],
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 30000,
      staleTime: 15000,
    },
  })

  const stats = useMemo(() => {
    const powerTrace = realtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.BESS_STRING_POWER,
    )
    const socTrace = pickBessStringSocTrace(realtimeData.data?.traces)

    const deviceIds = realtimeData.data?.device_ids ?? []
    const nowMs = Date.now()
    let totalPowerMW = 0
    let powerTimestamp: string | null = null
    const recentPowerTimes: string[] = []
    let stringPowerIncludedCount = 0
    const stringPowerTotalCount = Math.max(
      deviceIds.length,
      powerTrace?.values?.length ?? 0,
    )

    ;(powerTrace?.values ?? []).forEach((value, index) => {
      const time = powerTrace?.times?.[index]
      if (isRecentTimestamp(time, nowMs)) {
        stringPowerIncludedCount += 1
        totalPowerMW += powerValueOrZero(value)
        if (time) {
          recentPowerTimes.push(time)
        }
      }
    })
    powerTimestamp =
      latestTimestamp(recentPowerTimes) ??
      latestTimestamp(powerTrace?.times ?? [])
    const cumulativeStringPowerFreshnessTier: DataFreshnessTier = powerTimestamp
      ? getWorstFreshnessTier([powerTimestamp])
      : 'missing'

    const deviceById = new Map<number, Device>()
    ;(bessTreeDevices.data ?? []).forEach((d) => {
      deviceById.set(d.device_id, d)
    })
    const balanceScores =
      deviceIds.length > 0 &&
      socTrace?.values &&
      deviceIds.length === socTrace.values.length
        ? balanceScoresFromSoc(deviceIds, socTrace.values, deviceById)
        : {
            overallPct: null,
            systemPct: null,
            intraPcsPct: null,
          }

    const staleDeviceIds: number[] = []
    if (
      powerTrace?.times &&
      deviceIds.length > 0 &&
      powerTrace.times.length === deviceIds.length
    ) {
      powerTrace.times.forEach((time, idx) => {
        const deviceId = deviceIds[idx]
        if (
          isDeviceNotReporting(time) &&
          deviceId !== undefined &&
          deviceId !== null
        ) {
          staleDeviceIds.push(deviceId)
        }
      })
    }

    const dailyRevenueLoss =
      activeEvents.data?.reduce(
        (sum, event) => sum + (event.loss_daily_financial || 0),
        0,
      ) || 0
    const dailyEventLossEnergyMWh =
      activeEvents.data?.reduce(
        (sum, event) => sum + (event.loss_daily_energy || 0),
        0,
      ) || 0

    const totalEventsCount = activeEvents.data?.length || 0

    let poiPowerMW: number | null = null
    let poiPowerTimestamp: string | null = null

    const poiData =
      meterLastData.data && meterLastData.data.length > 0
        ? meterLastData.data
        : bessMeterLastData.data && bessMeterLastData.data.length > 0
          ? bessMeterLastData.data
          : null

    if (poiData) {
      let totalPoi = 0
      let latestTime: string | null = null

      for (const row of poiData) {
        const val =
          row.value_double ??
          row.value_real ??
          row.value_bigint ??
          row.value_integer
        if (val !== null && val !== undefined) {
          totalPoi += val
        }
        if (row.time && (!latestTime || row.time > latestTime)) {
          latestTime = row.time
        }
      }

      if (
        totalPoi !== 0 ||
        poiData.some(
          (r) =>
            (r.value_double ??
              r.value_real ??
              r.value_bigint ??
              r.value_integer) !== null,
        )
      ) {
        poiPowerMW = totalPoi
      }
      poiPowerTimestamp = latestTime
    }

    const staleDeviceNames: string[] = []
    if (devices.data && staleDeviceIds.length > 0) {
      staleDeviceIds.forEach((deviceId) => {
        const device = devices.data.find((d) => d.device_id === deviceId)
        if (device) {
          staleDeviceNames.push(device.name_long || `Device ${deviceId}`)
        }
      })
    }

    const poiPowerStatus: 'Charging' | 'Discharging' | 'Idling' | null =
      poiPowerMW !== null
        ? Math.abs(poiPowerMW) < 0.25
          ? 'Idling'
          : poiPowerMW < 0
            ? 'Charging'
            : 'Discharging'
        : null
    const cmmsHoverTickets = sortHoverTickets(cmmsTickets.data?.data)

    return {
      poiPowerMW: poiPowerMW !== null ? poiPowerMW.toFixed(2) : null,
      poiPowerTimestamp,
      poiPowerStatus,
      cumulativeStringPowerMW: totalPowerMW.toFixed(2),
      cumulativeStringPowerTimestamp: powerTimestamp,
      cumulativeStringPowerFreshnessTier,
      stringPowerIncludedCount,
      stringPowerTotalCount,
      totalEventsCount,
      dailyRevenueLoss: dailyRevenueLoss.toFixed(2),
      dailyEventLossEnergyMWh,
      openCMMSTickets: cmmsTickets.data?.data?.length || 0,
      cmmsHoverTickets,
      staleDeviceIds,
      staleDeviceNames,
      staleDevicesCount: staleDeviceIds.length,
      isCharging: totalPowerMW < 0,
      isDischarging: totalPowerMW > 0,
      balanceScoreOverallPct: balanceScores.overallPct,
      balanceScoreSystemPct: balanceScores.systemPct,
      balanceScoreIntraPcsPct: balanceScores.intraPcsPct,
    }
  }, [
    realtimeData.data,
    activeEvents.data,
    cmmsTickets.data,
    devices.data,
    bessTreeDevices.data,
    meterLastData.data,
    bessMeterLastData.data,
  ])

  const userIdToName = useMemo(() => {
    const m = new Map<string, string>()
    ;(companyUsers ?? []).forEach((u) => m.set(u.user_id, u.name_long))
    return m
  }, [companyUsers])
  const teamIdToName = useMemo(() => {
    const m = new Map<string, string>()
    ;(teamsWithMembers ?? []).forEach((t) => m.set(t.team_id, t.name_long))
    return m
  }, [teamsWithMembers])

  const nextPreventativeMaintenance = useMemo(() => {
    const categoryShortById = new Map<string, string>()
    ;(calendarCategories.data ?? []).forEach((c) => {
      categoryShortById.set(c.category_id, c.short_name.trim().toLowerCase())
    })

    const pmCategoryIds = new Set(
      (calendarCategories.data ?? [])
        .filter(isMaintenanceRelatedCategory)
        .map((c) => c.category_id),
    )
    const enclosureDevices = (pmScopeDevices.data ?? []).filter(
      (d) => d.device_type_id === BESS_ENCLOSURE_DEVICE_TYPE_ID,
    )
    const stringDevicesForPm = (pmScopeDevices.data ?? []).filter(
      (d) => d.device_type_id === BESS_STRING_DEVICE_TYPE_ID,
    )

    const pmEvents = (calendarEvents.data ?? []).filter((e) =>
      pmCategoryIds.has(e.calendar_item_category_id),
    )

    const { result, usedFallback } = pickNextMaintenancePreferringDcAssets(
      pmEvents,
      enclosureDevices,
      stringDevicesForPm,
      categoryShortById,
    )

    if (!result) return null
    const userNames = (result.event.assignee_user_ids ?? [])
      .map((id: string) => userIdToName.get(id) ?? `User ${id}`)
      .join(', ')
    const teamNames = (result.event.assignee_team_ids ?? [])
      .map((id: string) => teamIdToName.get(id) ?? `Team ${id}`)
      .join(', ')
    const assignees = [userNames, teamNames].filter(Boolean).join(' • ')
    return {
      formattedDate: result.formattedDate,
      calendarItemId: result.calendarItemId,
      occurrenceDateStr: dayjs.utc(result.occurrenceDate).format('YYYY-MM-DD'),
      scopeLabel: scopeLabelForPmEvent(
        result.event,
        enclosureDevices,
        stringDevicesForPm,
        usedFallback,
        categoryShortById,
      ),
      hoverContent: {
        title: result.event.title,
        description: result.event.description ?? undefined,
        assignees: assignees || undefined,
      },
    }
  }, [
    calendarEvents.data,
    calendarCategories.data,
    pmScopeDevices.data,
    userIdToName,
    teamIdToName,
  ])

  const activeEventsHoverSections = useMemo(() => {
    return [buildActiveEventsSection('BESS String', activeEvents.data)]
  }, [activeEvents.data])

  const navigate = useNavigate()
  const hasCMMSIntegration = cmmsTickets.data?.integration_configured === true

  const powerSubtitle = [
    stats.isCharging
      ? 'Charging'
      : stats.isDischarging
        ? 'Discharging'
        : 'Idle',
    stats.poiPowerMW !== null
      ? `POI Power: ${stats.poiPowerMW} MW`
      : 'POI Power: N/A',
  ].join('. ')

  const navigateToDataAvailability = () => {
    navigate(`/projects/${projectId}/device-details/data-availability`)
  }
  const navigateToEvents = () => {
    navigate(`/projects/${projectId}/events`)
  }
  const navigateToEvent = (eventId: number) => {
    navigate(`/projects/${projectId}/events/event?eventId=${eventId}`)
  }
  const navigateToCMMS = () => {
    navigate(`/projects/${projectId}/cmms/ticket-display`)
  }
  const navigateToCalendar = () => {
    if (nextPreventativeMaintenance?.calendarItemId) {
      const q = new URLSearchParams({
        event: nextPreventativeMaintenance.calendarItemId,
      })
      if (nextPreventativeMaintenance.occurrenceDateStr) {
        q.set('date', nextPreventativeMaintenance.occurrenceDateStr)
      }
      navigate(`/projects/${projectId}/calendar?${q.toString()}`)
    } else {
      navigate(`/projects/${projectId}/calendar`)
    }
  }

  return {
    activeEventsHoverSections,
    chartProps: {
      projectId: projectId ?? '',
      realtimeData,
      lifetimeEnergyTotals,
      stringDevices: devices.data ?? [],
      dcStringVoltageLimits,
      bessStringSpecs: bessStringSpecs.data ?? [],
      sensorTypes: chartSensorTypes.data ?? [],
      projectTags: chartTags.data ?? [],
    },
    statsGridProps: {
      realtimeLoading: realtimeData.isLoading,
      eventsLoading: activeEvents.isLoading,
      cmmsLoading: cmmsTickets.isLoading,
      hasCMMSIntegration,
      maintenanceLoading:
        calendarEvents.isLoading ||
        calendarCategories.isLoading ||
        pmScopeDevices.isLoading,
      stats,
      powerSubtitle,
      activeEventsHoverSections,
      nextPreventativeMaintenance,
      onNavigateDataAvailability: navigateToDataAvailability,
      onNavigateEvents: navigateToEvents,
      onNavigateEvent: navigateToEvent,
      onNavigateCMMS: navigateToCMMS,
      onNavigateCalendar: navigateToCalendar,
    },
    statusCodesProjectId: projectId ?? '',
  }
}
