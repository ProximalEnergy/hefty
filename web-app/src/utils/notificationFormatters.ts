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
}

/**
 * Helper function to get notification type name_long from data structure.
 * Looks for 'weather_type' field (or other fields as needed) that contains
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
