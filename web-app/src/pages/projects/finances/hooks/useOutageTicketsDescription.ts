import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useMemo } from 'react'

dayjs.extend(utc)
dayjs.extend(timezone)

export function useOutageTicketsDescription(
  outageTicketsData:
    | {
        active_tickets?: number
        tickets?: Array<{
          planned_start_time?: string | null
          planned_end_time?: string | null
          actual_end_time?: string | null
          data_points?: { HSL?: unknown; LSL?: unknown } | null
        }>
      }
    | undefined,
  projectTimeZone?: string | null,
) {
  return useMemo(() => {
    const tickets = outageTicketsData?.tickets ?? []

    // Filter tickets to only those currently active (now() between planned_start
    // and end).
    const now = projectTimeZone ? dayjs().tz(projectTimeZone) : dayjs().utc()
    const currentlyActiveTickets = tickets.filter((ticket) => {
      if (!ticket.planned_start_time) return false

      const startTime = projectTimeZone
        ? dayjs(ticket.planned_start_time).tz(projectTimeZone)
        : dayjs(ticket.planned_start_time).utc()

      // Use actual_end_time if available, otherwise fallback to planned_end_time
      const endTimeStr = ticket.actual_end_time || ticket.planned_end_time
      if (!endTimeStr) return false

      const endTime = projectTimeZone
        ? dayjs(endTimeStr).tz(projectTimeZone)
        : dayjs(endTimeStr).utc()

      // Check if now() is between start and end (inclusive boundaries)
      const nowValue = now.valueOf()
      const startValue = startTime.valueOf()
      const endValue = endTime.valueOf()
      return nowValue >= startValue && nowValue <= endValue
    })

    const hslValues = currentlyActiveTickets
      .map((t) => t.data_points?.HSL)
      .filter((v) => v !== null && v !== undefined && v !== '')

    const lslValues = currentlyActiveTickets
      .map((t) => t.data_points?.LSL)
      .filter((v) => v !== null && v !== undefined && v !== '')

    let desc = 'Number of currently active outage tickets'
    if (hslValues.length > 0 || lslValues.length > 0) {
      const hslText =
        hslValues.length > 0 ? `HSL: ${hslValues.join(', ')} MW` : ''
      const lslText =
        lslValues.length > 0 ? `LSL: ${lslValues.join(', ')} MW` : ''
      const limitsText = [hslText, lslText].filter(Boolean).join(' | ')
      desc = `${desc} (${limitsText})`
    }
    return desc
  }, [outageTicketsData, projectTimeZone])
}
