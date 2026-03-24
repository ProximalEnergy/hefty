import { NotificationTypeEnum } from '@/api/enumerations'

interface NotificationData {
  [key: string]: unknown
}

interface FormattedNotification {
  title: string
  body: string
  link?: string
}

/** Optional fields from the parent notification for formatters that need them. */
interface FormatNotificationContext {
  severity?: string
  projectName?: string
  projectId?: string
}

type NotificationFormatterFn = (
  data: NotificationData,
  createdAt: string | Date,
  context?: FormatNotificationContext,
) => FormattedNotification

const formatters: Partial<Record<number, NotificationFormatterFn>> = {
  [NotificationTypeEnum.HAIL]: formatHailAlert,
  [NotificationTypeEnum.FIRE]: formatFireAlert,
  [NotificationTypeEnum.TORNADO]: formatTornadoAlert,
  [NotificationTypeEnum.WIND]: formatWindAlert,
  [NotificationTypeEnum.CALENDAR_REMINDER]: formatCalendarReminder,
  [NotificationTypeEnum.EVENT_CHAT_MESSAGE]: formatEventChatMessage,
  [NotificationTypeEnum.PROJECT_CAPACITY_REDUCTION]:
    formatProjectCapacityReduction,
}

export function formatNotification(
  notificationTypeId: number,
  data: NotificationData,
  createdAt: string | Date,
  context?: FormatNotificationContext,
): FormattedNotification {
  return (
    formatters[notificationTypeId]?.(data, createdAt, context) ?? {
      title: 'Notification',
      body: JSON.stringify(data),
    }
  )
}

const dateFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
})

const createdAtDetailFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
})

function formatAlertDate(day: string, createdAt: string | Date): string {
  const dayMatch = day.match(/day(\d+)/)
  const dayOffset = dayMatch ? parseInt(dayMatch[1], 10) : 0

  const createdDate = new Date(createdAt)
  const targetDate = new Date(createdDate)
  targetDate.setDate(targetDate.getDate() + dayOffset)

  return dateFormatter.format(targetDate)
}

/**
 * Formats a Hail Risk notification.
 * Data structure: {"day": "day2", "severity": "CRITICAL", "probability": 80.0, "weather_type": "hail"}
 */
function formatHailAlert(
  data: NotificationData,
  createdAt: string | Date,
  _context?: FormatNotificationContext,
): FormattedNotification {
  const day = String(data.day || '')
  const probability =
    typeof data.value === 'number'
      ? data.value
      : typeof data.probability === 'number'
        ? data.probability
        : 0

  const formattedDate = formatAlertDate(day, createdAt)

  // Format title - severity will be added by the component
  const title = `Hail Risk - ${formattedDate}`

  // Format body
  const body = `${formattedDate} hail forecast with a ${probability}% probability.`

  return {
    title,
    body,
    link: '/portfolio/map',
  }
}

/**
 * Formats a Fire Risk notification.
 * Data structure: {"day": "day1", "value": "Elevated", "severity": "info", "weather_type": "fire"}
 */
function formatFireAlert(
  data: NotificationData,
  createdAt: string | Date,
  _context?: FormatNotificationContext,
): FormattedNotification {
  const day = String(data.day || '')
  const value = String(data.value || '')

  const formattedDate = formatAlertDate(day, createdAt)

  const title = `Fire Risk - ${formattedDate}`
  const body = `${formattedDate} fire weather outlook: ${value}.`

  return {
    title,
    body,
    link: '/portfolio/map',
  }
}

/**
 * Formats a Tornado Risk notification.
 * Data structure: {"day": "day1", "value": 2, "severity": "info", "weather_type": "tornado"}
 * Note: value is a percentage risk (0-100)
 */
function formatTornadoAlert(
  data: NotificationData,
  createdAt: string | Date,
  _context?: FormatNotificationContext,
): FormattedNotification {
  const day = String(data.day || '')
  const probability =
    typeof data.value === 'number'
      ? data.value
      : typeof data.value === 'string'
        ? parseFloat(data.value) || 0
        : 0

  const formattedDate = formatAlertDate(day, createdAt)

  const title = `Tornado Risk - ${formattedDate}`
  const body = `${formattedDate} tornado forecast with a ${probability}% risk.`

  return {
    title,
    body,
    link: '/portfolio/map',
  }
}

/**
 * Formats an Event Chat Message notification.
 * Data structure: { notification_type, event_id, project_id, sender_name,
 *   message_body, is_first_message, ... }
 */
function formatEventChatMessage(
  data: NotificationData,
  _createdAt: string | Date,
  _context?: FormatNotificationContext,
): FormattedNotification {
  const senderName = String(data.sender_name ?? 'Someone')
  const eventId = String(data.event_id ?? '')
  const projectId = String(data.project_id ?? '')
  const messagePreview =
    typeof data.message_body === 'string'
      ? data.message_body.slice(0, 80) +
        (data.message_body.length > 80 ? '…' : '')
      : ''
  const title = `Event chat: ${senderName}`
  const body = messagePreview
    ? `${senderName} posted: ${messagePreview}`
    : `${senderName} posted a message on event #${eventId}.`
  const link =
    projectId && eventId
      ? `/projects/${projectId}/events/event?eventId=${eventId}`
      : undefined
  return { title, body, link }
}

/**
 * Formats a Wind Risk notification.
 * Data structure: {"day": "day1", "value": 15, "severity": "info", "weather_type": "wind"}
 * Note: value is a percentage risk (0-100)
 */
function formatWindAlert(
  data: NotificationData,
  createdAt: string | Date,
  _context?: FormatNotificationContext,
): FormattedNotification {
  const day = String(data.day || '')
  const probability =
    typeof data.value === 'number'
      ? data.value
      : typeof data.value === 'string'
        ? parseFloat(data.value) || 0
        : 0

  const formattedDate = formatAlertDate(day, createdAt)

  const title = `Wind Risk - ${formattedDate}`
  const body = `${formattedDate} wind forecast with a ${probability}% risk.`

  return {
    title,
    body,
    link: '/portfolio/map',
  }
}

/**
 * Formats a Calendar Reminder notification.
 * Data structure: {
 *   "notification_type": "calendar reminder",
 *   "calendar_item_id": "uuid",
 *   "title": "Event Title",
 *   "description": "Event description",
 *   "start_time": "2025-01-30T10:00:00Z",
 *   "end_time": "2025-01-30T11:00:00Z",
 *   "all_day": false,
 *   "offset": "1d"
 * }
 */
function formatCalendarReminder(
  data: NotificationData,
  _createdAt: string | Date,
  _context?: FormatNotificationContext,
): FormattedNotification {
  const title = String(data.title || 'Calendar Event')
  const description = String(data.description || '')
  const startTime = String(data.start_time || '')

  // Parse start time to format the date
  let formattedDate = 'Unknown date'
  try {
    const startDate = new Date(startTime)
    if (!isNaN(startDate.getTime())) {
      formattedDate = dateFormatter.format(startDate)
    }
  } catch {
    // Keep default formattedDate
  }

  // Build body
  let body = `Reminder: ${title} is scheduled for ${formattedDate}.`
  if (description) {
    body += ` ${description}`
  }

  return {
    title: `Calendar Reminder: ${title}`,
    body,
    link: '/portfolio/calendar',
  }
}

/**
 * Formats a Project Capacity Reduction notification.
 * Data (flexible): capacity_reduction (e.g. "50%"), event_count,
 * plus optional context from the API row: severity, projectName, projectId.
 *
 * List row title is built by the UI as
 * ``{severityLabel} {title} - {projectName}``; keep title here to "Capacity Reduction"
 * only so that line reads e.g. "Critical Capacity Reduction - Snipesville 2".
 */
function formatProjectCapacityReduction(
  data: NotificationData,
  createdAt: string | Date,
  context?: FormatNotificationContext,
): FormattedNotification {
  const capacityReduction = String(
    data.capacity_reduction ?? data.capacityReduction ?? '',
  ).trim()
  const reductionLine = capacityReduction
    ? `${capacityReduction} reduction in capacity`
    : 'Reduction in capacity'

  const rawCount = data.event_count ?? data.eventCount
  const eventCount =
    typeof rawCount === 'number'
      ? rawCount
      : parseInt(String(rawCount ?? '0'), 10) || 0
  const eventNoun = eventCount === 1 ? 'event' : 'events'

  const created = new Date(createdAt)
  const createdDisplay = Number.isNaN(created.getTime())
    ? String(createdAt)
    : createdAtDetailFormatter.format(created)

  const body = [
    `${reductionLine} from ${eventCount} ${eventNoun}.`,
    `Created at ${createdDisplay}.`,
  ].join('\n')

  const projectId = context?.projectId ?? String(data.project_id ?? '')
  const link =
    projectId !== '' ? `/projects/${projectId}/events` : '/portfolio/map'

  return {
    title: 'Capacity Reduction',
    body,
    link,
  }
}
