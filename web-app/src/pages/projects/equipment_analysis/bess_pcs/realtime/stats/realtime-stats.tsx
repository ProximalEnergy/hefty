import { SensorTypeEnum } from '@/api/enumerations'
import type { components } from '@/api/schema'
import type { CalendarEvent } from '@/api/v1/operational/calendar'
import { BessPCSStatsCards } from '@/components/bess-pcs/StatsCards'
import type { Device } from '@/hooks/types'
import { useRealtimeSources } from '@/pages/projects/equipment_analysis/bess_pcs/realtime/use-realtime-sources'
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import { useMemo } from 'react'
import { rrulestr } from 'rrule'

dayjs.extend(utc)

const PM_BESS_PCS_SHORT_NAME = 'pm_bess_pcs'

type NextPMInfo = {
  formattedDate: string
  calendarItemId: string
  occurrenceDate: Date
  event: CalendarEvent
}

type EventSummary = components['schemas']['EventSummary']

type ActiveEventsHoverSection = {
  label: string
  count: number
  events: Array<{
    eventId: number
    label: string
  }>
  remainingCount: number
}

type RealtimeStatsProps = {
  pcsDevices: Device[] | undefined
  sources: ReturnType<typeof useRealtimeSources>
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

function getNextPreventativeMaintenance(
  events: CalendarEvent[] | undefined,
  pmCategoryId: string | null,
): NextPMInfo | null {
  if (!events?.length || !pmCategoryId) {
    return null
  }

  let earliestDate: Date | null = null
  let earliestEvent: CalendarEvent | null = null

  for (const event of events) {
    if (event.calendar_item_category_id !== pmCategoryId) {
      continue
    }

    const next = getNextOccurrence(event)
    if (next && (!earliestDate || next < earliestDate)) {
      earliestDate = next
      earliestEvent = event
    }
  }

  if (!earliestDate || !earliestEvent) {
    return null
  }

  return {
    formattedDate: formatPreventativeMaintenanceDate(earliestDate),
    calendarItemId: earliestEvent.calendar_item_id,
    occurrenceDate: earliestDate,
    event: earliestEvent,
  }
}

function buildActiveEventsSection(
  label: string,
  events: EventSummary[] | undefined,
): ActiveEventsHoverSection {
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

export function RealtimeStats({ pcsDevices, sources }: RealtimeStatsProps) {
  const stats = useMemo(() => {
    const powerTrace = sources.pcsRealtime.data?.traces?.find(
      (trace) => trace.sensor_type_id === SensorTypeEnum.BESS_PCS_AC_POWER,
    )

    const powerValues =
      powerTrace?.values?.filter((value): value is number => value !== null) ||
      []
    const totalPowerMw = powerValues.reduce((sum, value) => sum + value, 0)

    const pcsPowerTimestamp =
      powerTrace?.times && powerTrace.times.length > 0
        ? powerTrace.times[powerTrace.times.length - 1] || null
        : null

    const latestPowerTimestamp = powerTrace?.times?.reduce<number | null>(
      (latest, time) => {
        if (!time) {
          return latest
        }

        const timestamp = new Date(time).getTime()
        if (Number.isNaN(timestamp)) {
          return latest
        }

        if (latest === null || timestamp > latest) {
          return timestamp
        }

        return latest
      },
      null,
    )
    const stalenessThreshold =
      latestPowerTimestamp !== null
        ? dayjs(latestPowerTimestamp).subtract(1, 'hour').valueOf()
        : null
    const staleDeviceIds: number[] = []

    if (
      powerTrace?.times &&
      sources.pcsRealtime.data?.device_ids &&
      powerTrace.times.length === sources.pcsRealtime.data.device_ids.length
    ) {
      powerTrace.times.forEach((time, index) => {
        const deviceId = sources.pcsRealtime.data?.device_ids?.[index]

        if (time) {
          const timestamp = new Date(time).getTime()
          if (
            Number.isNaN(timestamp) ||
            (stalenessThreshold !== null && timestamp < stalenessThreshold)
          ) {
            if (deviceId !== undefined && deviceId !== null) {
              staleDeviceIds.push(deviceId)
            }
          }
          return
        }

        if (deviceId !== undefined && deviceId !== null) {
          staleDeviceIds.push(deviceId)
        }
      })
    }

    const dailyRevenueLoss =
      (sources.activeEvents.data?.reduce((sum, event) => {
        return sum + (event.loss_daily_financial || 0)
      }, 0) || 0) +
      (sources.moduleEvents.data?.reduce((sum, event) => {
        return sum + (event.loss_daily_financial || 0)
      }, 0) || 0) +
      (sources.moduleGroupEvents.data?.reduce((sum, event) => {
        return sum + (event.loss_daily_financial || 0)
      }, 0) || 0)

    const pcsEventsCount = sources.activeEvents.data?.length || 0
    const moduleEventsCount = sources.moduleEvents.data?.length || 0
    const moduleGroupEventsCount = sources.moduleGroupEvents.data?.length || 0
    const totalEventsCount =
      pcsEventsCount + moduleEventsCount + moduleGroupEventsCount

    const poiData =
      sources.meterLastData.data && sources.meterLastData.data.length > 0
        ? sources.meterLastData.data
        : sources.bessMeterLastData.data &&
            sources.bessMeterLastData.data.length > 0
          ? sources.bessMeterLastData.data
          : null

    let poiPowerMw: number | null = null
    let poiPowerTimestamp: string | null = null

    if (poiData) {
      let totalPoi = 0
      let latestTime: string | null = null

      poiData.forEach((row) => {
        const value =
          row.value_double ??
          row.value_real ??
          row.value_bigint ??
          row.value_integer

        if (value !== null && value !== undefined) {
          totalPoi += value
        }

        if (row.time && (!latestTime || row.time > latestTime)) {
          latestTime = row.time
        }
      })

      if (
        totalPoi !== 0 ||
        poiData.some((row) => {
          return (
            (row.value_double ??
              row.value_real ??
              row.value_bigint ??
              row.value_integer) !== null
          )
        })
      ) {
        poiPowerMw = totalPoi
      }

      poiPowerTimestamp = latestTime
    }

    const staleDeviceNames: string[] = []
    pcsDevices?.forEach((device) => {
      if (staleDeviceIds.includes(device.device_id)) {
        staleDeviceNames.push(device.name_long || `Device ${device.device_id}`)
      }
    })

    const poiPowerStatus: 'Charging' | 'Discharging' | 'Idling' | null =
      poiPowerMw !== null
        ? Math.abs(poiPowerMw) < 0.25
          ? 'Idling'
          : poiPowerMw < 0
            ? 'Charging'
            : 'Discharging'
        : null

    const linkedCmmsTicketIds = new Set<number>()
    sources.eventCmmsLinks.data?.forEach((link) => {
      if (link.cmms_ticket_id !== null && link.cmms_ticket_id !== undefined) {
        linkedCmmsTicketIds.add(link.cmms_ticket_id)
      }
    })

    const cmmsHoverTickets = (sources.linkedCmmsTickets.data?.data ?? [])
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

    return {
      poiPowerMW: poiPowerMw !== null ? poiPowerMw.toFixed(2) : null,
      poiPowerTimestamp,
      poiPowerStatus,
      cumulativePCSPowerMW: totalPowerMw.toFixed(2),
      cumulativePCSPowerTimestamp: pcsPowerTimestamp,
      totalEventsCount,
      pcsEventsCount,
      moduleEventsCount,
      moduleGroupEventsCount,
      dailyRevenueLoss: dailyRevenueLoss.toFixed(2),
      openCMMSTickets: linkedCmmsTicketIds.size,
      cmmsHoverTickets,
      staleDeviceIds,
      staleDeviceNames,
      staleDevicesCount: staleDeviceIds.length,
      isCharging: totalPowerMw < 0,
      isDischarging: totalPowerMw > 0,
    }
  }, [
    pcsDevices,
    sources.activeEvents.data,
    sources.bessMeterLastData.data,
    sources.eventCmmsLinks.data,
    sources.linkedCmmsTickets.data,
    sources.meterLastData.data,
    sources.moduleEvents.data,
    sources.moduleGroupEvents.data,
    sources.pcsRealtime.data,
  ])

  const userIdToName = useMemo(() => {
    const map = new Map<string, string>()

    ;(sources.companyUsers.data ?? []).forEach((user) => {
      map.set(user.user_id, user.name_long)
    })

    return map
  }, [sources.companyUsers.data])

  const teamIdToName = useMemo(() => {
    const map = new Map<string, string>()

    ;(sources.teamsWithMembers.data ?? []).forEach((team) => {
      map.set(team.team_id, team.name_long)
    })

    return map
  }, [sources.teamsWithMembers.data])

  const nextPreventativeMaintenance = useMemo(() => {
    const pmCategoryId =
      sources.calendarCategories.data?.find((category) => {
        return category.short_name === PM_BESS_PCS_SHORT_NAME
      })?.category_id ?? null

    const result = getNextPreventativeMaintenance(
      sources.calendarEvents.data,
      pmCategoryId,
    )
    if (!result) {
      return null
    }

    const userNames = (result.event.assignee_user_ids ?? [])
      .map((id) => userIdToName.get(id) ?? `User ${id}`)
      .join(', ')
    const teamNames = (result.event.assignee_team_ids ?? [])
      .map((id) => teamIdToName.get(id) ?? `Team ${id}`)
      .join(', ')
    const assignees = [userNames, teamNames].filter(Boolean).join(' • ')

    return {
      formattedDate: result.formattedDate,
      calendarItemId: result.calendarItemId,
      occurrenceDateStr: dayjs.utc(result.occurrenceDate).format('YYYY-MM-DD'),
      hoverContent: {
        title: result.event.title,
        description: result.event.description ?? undefined,
        assignees: assignees || undefined,
      },
    }
  }, [
    sources.calendarCategories.data,
    sources.calendarEvents.data,
    teamIdToName,
    userIdToName,
  ])

  const activeEventsHoverSections = useMemo(() => {
    return [
      buildActiveEventsSection('PCS', sources.activeEvents.data),
      buildActiveEventsSection(
        'PCS Module Group',
        sources.moduleGroupEvents.data,
      ),
      buildActiveEventsSection('PCS Module', sources.moduleEvents.data),
    ]
  }, [
    sources.activeEvents.data,
    sources.moduleEvents.data,
    sources.moduleGroupEvents.data,
  ])

  return (
    <BessPCSStatsCards
      stats={stats}
      isLoading={{
        realtime: sources.pcsRealtime.isLoading,
        events:
          sources.activeEvents.isLoading ||
          sources.moduleEvents.isLoading ||
          sources.moduleGroupEvents.isLoading,
        cmms:
          sources.cmmsTickets.isLoading ||
          sources.eventCmmsLinks.isLoading ||
          sources.linkedCmmsTickets.isLoading,
        meter:
          sources.meterLastData.isLoading ||
          sources.bessMeterLastData.isLoading,
      }}
      activeEventsHoverSections={activeEventsHoverSections}
      nextPreventativeMaintenance={nextPreventativeMaintenance}
      isLoadingCalendar={sources.calendarEvents.isLoading}
      hasCMMSIntegration={
        sources.cmmsTickets.data?.integration_configured === true
      }
    />
  )
}
