import { useGetDataLastUpdated } from '@/api/v1/operational/project/project_data_last_updated'
import { ProjectDataLastUpdated } from '@/api/v1/operational/project_data_last_updated'
import { useSelectProject } from '@/api/v1/operational/projects'
import classes from '@/pages/layout/header/DataStatus.module.css'
import { StatusIconWrapper } from '@/pages/layout/header/StatusIconWrapper'
import { formatRelativeTime } from '@/utils/relativeTime'
import { Box, Indicator, Tooltip } from '@mantine/core'
import dayjs from 'dayjs'
import duration from 'dayjs/plugin/duration'
import type { Duration } from 'dayjs/plugin/duration'
import { useMemo } from 'react'
import { useNavigate, useParams } from 'react-router'

dayjs.extend(duration)

const DataStatus = ({
  data,
  data_receive_schedule,
  isLoading,
  isError,
  projectId,
}: {
  data?: ProjectDataLastUpdated
  data_receive_schedule?: string
  isLoading: boolean
  isError: boolean
  projectId?: string
}) => {
  const navigate = useNavigate()
  const { color, label } = useMemo(() => {
    if (isLoading || isError || !data || !data_receive_schedule) {
      return { color: 'gray', label: null }
    }

    const validTimes = Object.entries(data).filter(
      (entry): entry is [string, string] => {
        const [key, value] = entry
        return key !== 'project_id' && typeof value === 'string'
      },
    )

    if (validTimes.length === 0) {
      return {
        color: 'red',
        label: 'Data has not been received yet for this project.',
      }
    }

    const dateTimes = validTimes.map(
      ([key, value]) => [key, dayjs(value)] as [string, dayjs.Dayjs],
    )
    dateTimes.sort((a, b) => b[1].diff(a[1]))

    const [recentKey, recentTime] = dateTimes[0]
    const fromNow = formatRelativeTime(recentTime.toDate()).relative
    const recentTimeFormatted = recentTime.format('YYYY-MM-DD HH:mm:ss')

    if (recentKey === 'time_error') {
      return {
        color: 'red',
        label: `Error in data collection as of ${fromNow} (${recentTimeFormatted})`,
      }
    }

    if (recentKey === 'time_empty') {
      return {
        color: 'red',
        label: `No data available as of ${fromNow} (${recentTimeFormatted})`,
      }
    }

    try {
      const { lastExpected, nextExpected, gracePeriod } = checkDataStatus(
        data_receive_schedule,
      )

      const timeCheck = dayjs(lastExpected).subtract(gracePeriod)

      const color = recentTime.isBefore(timeCheck) ? 'red' : 'green'
      const label = `Last received data ${fromNow} (${recentTimeFormatted}). Next data expected around ${dayjs(nextExpected).format('YYYY-MM-DD HH:mm:ss')}.`

      return { color, label }
    } catch {
      return { color: 'grey', label: null }
    }
  }, [isLoading, isError, data, data_receive_schedule])

  const size = 16

  const handleDataStatusClick = () => {
    if (projectId) {
      navigate(`/projects/${projectId}/device-details/data-availability`)
    }
  }

  const statusColor = color === 'green' ? 'green' : 'red'

  return (
    <StatusIconWrapper label="DATA" color={statusColor}>
      <Tooltip label={label} disabled={isLoading || !label}>
        <Box
          w={size}
          h={size}
          onClick={handleDataStatusClick}
          style={{
            cursor: projectId ? 'pointer' : 'default',
          }}
        >
          <Indicator
            size={size}
            offset={size / 2}
            processing={!isLoading && !!label}
            color={color}
            classNames={classes}
          />
        </Box>
      </Tooltip>
    </StatusIconWrapper>
  )
}

export const DataStatusContainer = ({
  projectId: projectIdProp,
}: {
  projectId?: string
}) => {
  let { projectId } = useParams()

  // If the projectId is provided through the props, use it instead of the one from the URL
  if (projectIdProp) {
    projectId = projectIdProp
  }

  const project = useSelectProject(projectId!)

  const lastUpdated = useGetDataLastUpdated({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: { enabled: !!projectId },
  })

  const isLoading = project.isLoading || lastUpdated.isLoading
  const isError = project.isError || lastUpdated.isError

  if (!projectId) {
    return null
  }

  return (
    <DataStatus
      data={lastUpdated.data}
      data_receive_schedule={project.data?.data_receive_schedule}
      isLoading={isLoading}
      isError={isError}
      projectId={projectId}
    />
  )
}

/**
 * Represents the expected timing information for data collection status checks
 * @property lastExpected - The timestamp when the last data collection was expected
 * @property nextExpected - The timestamp when the next data collection is expected
 * @property gracePeriod - The allowed time window after lastExpected before considering data late
 */
type DataStatusCheck = {
  lastExpected: Date
  nextExpected: Date
  gracePeriod: Duration
}

/**
 * Analyzes a cron schedule to determine data collection timing expectations.
 *
 * Supported cron formats:
 * - Every minute: "every minute"
 * - Every N minutes: "every N minutes"
 * - Once daily: "daily at HH:MM UTC"
 *
 * NOTE: If more complex cron parsing is needed, consider using the cron-parser library
 *
 * @param cron - The cron schedule string to analyze
 * @returns DataStatusCheck object with timing expectations
 * @throws Error if cron format is not supported
 */
function checkDataStatus(cron: string): DataStatusCheck {
  // Get current time in UTC
  const now = new Date(new Date().toISOString())
  const [minutePart] = cron.split(' ')

  let lastExpected: Date
  let nextExpected: Date

  if (cron === '* * * * *') {
    // Handle "every minute" schedule
    const normalizedNow = new Date(now)
    normalizedNow.setUTCSeconds(0, 0) // Round down to nearest minute
    lastExpected = new Date(normalizedNow.getTime())
    nextExpected = new Date(normalizedNow.getTime() + 60 * 1000) // Add one minute
  } else if (minutePart.startsWith('*/')) {
    // Handle "every N minutes" schedule
    const interval = parseInt(minutePart.slice(2), 10)
    const normalizedNow = new Date(now)
    normalizedNow.setUTCSeconds(0, 0)
    const currentMinute = normalizedNow.getUTCMinutes()
    const currentHour = normalizedNow.getUTCHours()

    // Calculate last and next expected minutes based on interval
    const lastMinute = Math.floor(currentMinute / interval) * interval
    const nextMinute = lastMinute + interval

    lastExpected = new Date(normalizedNow)
    lastExpected.setUTCMinutes(lastMinute)

    if (nextMinute < 60) {
      // Next expected time is within current hour
      nextExpected = new Date(normalizedNow)
      nextExpected.setUTCMinutes(nextMinute)
    } else {
      // Next expected time is in next hour
      nextExpected = new Date(normalizedNow)
      nextExpected.setUTCHours(currentHour + 1, 0, 0, 0)
    }
  } else if (/^\d+ \d+ \* \* \*$/.test(cron)) {
    // Handle "once daily" schedule (HH:MM UTC)
    const [min, hour] = cron.split(' ').map(Number)
    const today = new Date(now)
    today.setUTCHours(hour, min, 0, 0)

    if (now < today) {
      // Current time is before today's scheduled time
      lastExpected = new Date(today.getTime() - 24 * 60 * 60 * 1000) // Yesterday
      nextExpected = today
    } else {
      // Current time is after today's scheduled time
      lastExpected = today
      nextExpected = new Date(today.getTime() + 24 * 60 * 60 * 1000) // Tomorrow
    }
  } else {
    throw new Error(`Unsupported cron format: ${cron}`)
  }

  // Calculate grace period as the minimum of:
  // 1. Time between last and next expected data
  // 2. 1 hour
  const gracePeriod = dayjs.duration(
    Math.min(
      dayjs(nextExpected).diff(dayjs(lastExpected)),
      dayjs.duration(1, 'hour').asMilliseconds(),
    ),
    'milliseconds',
  )

  return {
    lastExpected,
    nextExpected,
    gracePeriod,
  }
}

export default DataStatus
