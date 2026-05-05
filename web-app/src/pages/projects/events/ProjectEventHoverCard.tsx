import { HoverInfo } from '@/pages/projects/gis/utils'
import { Group, Paper, Stack, Text, useMantineTheme } from '@mantine/core'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'

import {
  getDailyLossColor,
  isProjectEventClusterProperties,
  isProjectEventPointProperties,
} from './ProjectEventOverlayLayers'

dayjs.extend(utc)
dayjs.extend(timezone)

interface ProjectEventHoverCardProps {
  hoverInfo: HoverInfo
  timeZone?: string | null
}

const formatCurrency = (value: number | null | undefined): string | null => {
  if (value === null || value === undefined) {
    return null
  }

  return value.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

const formatEnergy = (value: number | null | undefined): string | null => {
  if (value === null || value === undefined) {
    return null
  }

  return `${value.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} MWh`
}

const formatLossSummary = (
  financial: number | null | undefined,
  energy: number | null | undefined,
) => {
  const parts = [formatCurrency(financial), formatEnergy(energy)].filter(
    Boolean,
  )

  return parts.length > 0 ? parts.join(' | ') : 'No Data'
}

const formatDateTime = (value: string, timeZone?: string | null) =>
  timeZone
    ? dayjs(value).tz(timeZone).format('MM/DD/YYYY HH:mm:ss')
    : dayjs(value).format('MM/DD/YYYY HH:mm:ss')

const formatDuration = (start: string, end: string | null) => {
  const durationMinutes = dayjs(end ?? undefined).diff(dayjs(start), 'minute')

  if (!Number.isFinite(durationMinutes) || durationMinutes < 0) {
    return null
  }

  const days = Math.floor(durationMinutes / (24 * 60))
  const hours = Math.floor((durationMinutes % (24 * 60)) / 60)
  const minutes = durationMinutes % 60
  const parts: string[] = []

  if (days > 0) {
    parts.push(`${days}d`)
  }
  if (hours > 0 || days > 0) {
    parts.push(`${hours}h`)
  }
  parts.push(`${minutes}m`)

  return parts.join(' ')
}

const getEventTitle = (
  deviceTypeName: string,
  deviceName: string,
  eventId: number,
) => `${deviceTypeName}: ${deviceName} (#${eventId})`

const sharedCardStyle = (hoverInfo: HoverInfo) => ({
  left: hoverInfo.x,
  top: hoverInfo.y,
  maxWidth: 320,
  position: 'absolute' as const,
  zIndex: 9,
  pointerEvents: 'none' as const,
})

const lossDotStyle = (color: string) => ({
  width: 8,
  height: 8,
  minWidth: 8,
  borderRadius: '50%',
  backgroundColor: color,
})

const ProjectEventHoverCard = ({
  hoverInfo,
  timeZone,
}: ProjectEventHoverCardProps) => {
  const properties = hoverInfo.feature?.properties
  const theme = useMantineTheme()

  if (!properties) {
    return null
  }

  if (isProjectEventPointProperties(properties)) {
    const duration = formatDuration(properties.timeStart, properties.timeEnd)
    const isRootCauseUseful =
      properties.rootCause != null &&
      properties.rootCause.trim() !== '' &&
      properties.rootCause !== properties.failureMode
    const dailyLossColor = getDailyLossColor({
      dailyLossFinancial: properties.lossDailyFinancial,
      minColor: theme.colors.red[6],
      maxColor: theme.colors.violet[6],
    })

    return (
      <Paper p="xs" withBorder style={sharedCardStyle(hoverInfo)}>
        <Stack gap={2}>
          <Text fw={700}>
            {getEventTitle(
              properties.deviceTypeName,
              properties.deviceName,
              properties.eventId,
            )}
          </Text>
          <Text size="sm">
            Status: {properties.isClosed ? 'Closed' : 'Open'}
          </Text>
          <Text size="sm">Failure Mode: {properties.failureMode}</Text>
          {isRootCauseUseful ? (
            <Text size="sm">Root Cause: {properties.rootCause}</Text>
          ) : null}
          <Text size="sm">
            Started: {formatDateTime(properties.timeStart, timeZone)}
          </Text>
          {properties.timeEnd ? (
            <Text size="sm">
              Ended: {formatDateTime(properties.timeEnd, timeZone)}
            </Text>
          ) : null}
          {duration ? <Text size="sm">Duration: {duration}</Text> : null}
          <Group gap={6} wrap="nowrap">
            <span style={lossDotStyle(dailyLossColor)} />
            <Text size="sm">
              Daily Loss:{' '}
              {formatLossSummary(
                properties.lossDailyFinancial,
                properties.lossDailyEnergy,
              )}
            </Text>
          </Group>
          <Text size="sm">
            Total Loss:{' '}
            {formatLossSummary(
              properties.lossTotalFinancial,
              properties.lossTotalEnergy,
            )}
          </Text>
        </Stack>
      </Paper>
    )
  }

  if (isProjectEventClusterProperties(properties)) {
    const dailyLossColor = getDailyLossColor({
      dailyLossFinancial: properties.dailyLossFinancial,
      minColor: theme.colors.red[6],
      maxColor: theme.colors.violet[6],
    })

    return (
      <Paper p="xs" withBorder style={sharedCardStyle(hoverInfo)}>
        <Stack gap={2}>
          <Text fw={700}>Event Cluster</Text>
          <Text size="sm">Events: {properties.point_count}</Text>
          <Text size="sm">Open: {properties.openEventCount}</Text>
          <Text size="sm">Closed: {properties.closedEventCount}</Text>
          <Group gap={6} wrap="nowrap">
            <span style={lossDotStyle(dailyLossColor)} />
            <Text size="sm">
              Daily Loss:{' '}
              {formatLossSummary(
                properties.dailyLossFinancial,
                properties.dailyLossEnergy,
              )}
            </Text>
          </Group>
          <Text size="sm">
            Total Loss:{' '}
            {formatLossSummary(
              properties.totalLossFinancial,
              properties.totalLossEnergy,
            )}
          </Text>
          <Text size="sm" c="dimmed">
            Click to zoom in
          </Text>
        </Stack>
      </Paper>
    )
  }

  return null
}

export default ProjectEventHoverCard
