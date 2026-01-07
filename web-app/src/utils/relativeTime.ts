/**
 * Formats a date as relative time (e.g., "5 minutes ago", "2 hours ago", "3 days ago")
 * For dates older than 7 days, returns the formatted date.
 * @param dateString - ISO date string or Date object
 * @returns Object with relative time string and full date string for tooltip
 */
export function formatRelativeTime(dateString: string | Date): {
  relative: string
  full: string
} {
  const date =
    typeof dateString === 'string' ? new Date(dateString) : dateString
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSeconds = Math.floor(diffMs / 1000)
  const diffMinutes = Math.floor(diffSeconds / 60)
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)

  // Format full date for tooltip
  const fullDate = date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })

  // Less than 1 minute
  if (diffSeconds < 60) {
    return {
      relative: diffSeconds < 10 ? 'just now' : `${diffSeconds} seconds ago`,
      full: fullDate,
    }
  }

  // Less than 1 hour
  if (diffMinutes < 60) {
    return {
      relative: `${diffMinutes} ${diffMinutes === 1 ? 'minute' : 'minutes'} ago`,
      full: fullDate,
    }
  }

  // Less than 24 hours
  if (diffHours < 24) {
    return {
      relative: `${diffHours} ${diffHours === 1 ? 'hour' : 'hours'} ago`,
      full: fullDate,
    }
  }

  // Less than 7 days
  if (diffDays < 7) {
    return {
      relative: `${diffDays} ${diffDays === 1 ? 'day' : 'days'} ago`,
      full: fullDate,
    }
  }

  // 7+ days: show the actual date
  const dateFormatter = new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
  return {
    relative: dateFormatter.format(date),
    full: fullDate,
  }
}
