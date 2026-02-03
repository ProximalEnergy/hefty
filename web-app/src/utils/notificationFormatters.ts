interface NotificationData {
  [key: string]: unknown
}

interface FormattedNotification {
  title: string
  body: string
  link?: string
}

// Map of name_long (from admin.notification_types.name_long) to formatter functions
// Add new notification types by adding entries here with the name_long value
const formattersByName: Record<
  string,
  (data: NotificationData, createdAt: string | Date) => FormattedNotification
> = {
  hail: formatHailAlert,
  fire: formatFireAlert,
  tornado: formatTornadoAlert,
  wind: formatWindAlert,
  event_chat_message: formatEventChatMessage,
  'calendar reminder': formatCalendarReminder,
}

/**
 * Helper function to get notification type name_long from data structure.
 * Looks for 'weather_type' or 'notification_type' field (or other fields as needed) that contains
 * the name_long value matching admin.notification_types.name_long.
 */
function getNotificationTypeName(data: NotificationData): string | undefined {
  if (
    typeof data === 'object' &&
    data !== null &&
    'weather_type' in data &&
    typeof data.weather_type === 'string'
  ) {
    return data.weather_type.toLowerCase()
  }
  if (
    typeof data === 'object' &&
    data !== null &&
    'notification_type' in data &&
    typeof data.notification_type === 'string'
  ) {
    return data.notification_type.toLowerCase()
  }
  return undefined
}

/**
 * Formats notification data into a title and body based on the notification type.
 * Each notification type has its own formatter function.
 *
 * Looks up formatter by name_long value from the notification data structure.
 * The name_long must match the value in admin.notification_types.name_long.
 */
export function formatNotification(
  _notificationTypeId: number,
  data: NotificationData,
  createdAt: string | Date,
): FormattedNotification {
  // Find formatter by name_long from data structure
  const typeName = getNotificationTypeName(data)
  if (typeName && typeName in formattersByName) {
    return formattersByName[typeName](data, createdAt)
  }

  // Default formatter if no specific formatter is found
  return {
    title: 'Notification',
    body: JSON.stringify(data),
  }
}

const dateFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
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
 * Formats a Hail Alert notification.
 * Data structure: {"day": "day2", "severity": "CRITICAL", "probability": 80.0, "weather_type": "hail"}
 */
function formatHailAlert(
  data: NotificationData,
  createdAt: string | Date,
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
  const title = `Hail Alert - ${formattedDate}`

  // Format body
  const body = `${formattedDate} hail forecast with a ${probability}% probability.`

  return {
    title,
    body,
    link: '/portfolio/map',
  }
}

/**
 * Formats a Fire Alert notification.
 * Data structure: {"day": "day1", "value": "Elevated", "severity": "info", "weather_type": "fire"}
 */
function formatFireAlert(
  data: NotificationData,
  createdAt: string | Date,
): FormattedNotification {
  const day = String(data.day || '')
  const value = String(data.value || '')

  const formattedDate = formatAlertDate(day, createdAt)

  const title = `Fire Alert - ${formattedDate}`
  const body = `${formattedDate} fire weather outlook: ${value}.`

  return {
    title,
    body,
    link: '/portfolio/map',
  }
}

/**
 * Formats a Tornado Alert notification.
 * Data structure: {"day": "day1", "value": 2, "severity": "info", "weather_type": "tornado"}
 * Note: value is a percentage risk (0-100)
 */
function formatTornadoAlert(
  data: NotificationData,
  createdAt: string | Date,
): FormattedNotification {
  const day = String(data.day || '')
  const probability =
    typeof data.value === 'number'
      ? data.value
      : typeof data.value === 'string'
        ? parseFloat(data.value) || 0
        : 0

  const formattedDate = formatAlertDate(day, createdAt)

  const title = `Tornado Alert - ${formattedDate}`
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
 * Formats a Wind Alert notification.
 * Data structure: {"day": "day1", "value": 15, "severity": "info", "weather_type": "wind"}
 * Note: value is a percentage risk (0-100)
 */
function formatWindAlert(
  data: NotificationData,
  createdAt: string | Date,
): FormattedNotification {
  const day = String(data.day || '')
  const probability =
    typeof data.value === 'number'
      ? data.value
      : typeof data.value === 'string'
        ? parseFloat(data.value) || 0
        : 0

  const formattedDate = formatAlertDate(day, createdAt)

  const title = `Wind Alert - ${formattedDate}`
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
