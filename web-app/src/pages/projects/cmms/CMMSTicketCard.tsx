import { CMMSTicket } from '@/api/v1/operational/project/cmms_tickets'
import { Project } from '@/api/v1/operational/projects'
import { EventCMMSTicket } from '@/api/v1/protected/web-application/projects/event-cmms-tickets/event_cmms_tickets'
import TicketFirstModal from '@/components/event-ticket-links/TicketFirstModal'
import {
  Badge,
  Box,
  Button,
  Card,
  Group,
  Stack,
  Text,
  rem,
} from '@mantine/core'
import {
  IconAlertCircle,
  IconAlertTriangle,
  IconCalendarDue,
  IconCircleCheck,
  IconClock,
  IconExternalLink,
  IconMapPinFilled,
  IconSettingsFilled,
  IconUser,
  IconUserSearch,
} from '@tabler/icons-react'
import dayjs from 'dayjs'
import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router'

const ICON_PROPS = {
  style: {
    width: rem(24),
    height: rem(24),
  },
  stroke: 1.5,
}

const GAP = 'md'
const DESCRIPTION_COLLAPSED_LINES = 1
const TICKET_ACTIVITY_COLLAPSED_LINES = 3
const DESCRIPTION_COLLAPSE_CHARACTER_LIMIT = 300

const getCMMSTicketStatusColor = (status: string) => {
  switch (status.toLowerCase()) {
    case 'open':
      return 'green'
    case 'in progress':
      return 'yellow'
    case 'resolved':
      return 'green'
    case 'closed':
      return 'gray'
    case 'awaiting triage':
      return 'yellow'
    default:
      return 'blue'
  }
}

const getProviderColor = (provider?: string) => {
  if (!provider) {
    return 'gray'
  }
  switch (provider.toLowerCase()) {
    case 'jira':
      return 'blue'
    case 'qe solar':
      return 'orange'
    default:
      return 'gray'
  }
}

const getStatusIcon = (status: string) => {
  switch (status.toLowerCase()) {
    case 'closed':
      return <IconCircleCheck size={18} />
    case 'open':
      return <IconAlertCircle size={18} />
    case 'awaiting triage':
      return <IconUserSearch size={18} />
    default:
      return null
  }
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

type TicketActivityMessage = {
  date?: string
  text: string
}

const formatUnknownValue = (value: unknown) => {
  if (typeof value === 'string') {
    return value
  }
  return JSON.stringify(value, null, 2) ?? String(value)
}

const formatTicketActivityEntry = (entry: unknown): TicketActivityMessage => {
  if (!isRecord(entry)) {
    return { text: formatUnknownValue(entry) }
  }

  const date =
    typeof entry.Date === 'string'
      ? dayjs(entry.Date).format('YYYY-MM-DD')
      : undefined
  const material =
    entry.Material == null
      ? undefined
      : `Material: ${formatUnknownValue(entry.Material)}`
  const description =
    entry.Description == null
      ? undefined
      : formatUnknownValue(entry.Description)

  return {
    date,
    text: [material, description].filter(Boolean).join('\n'),
  }
}

const formatTicketActivityMessages = (
  activity: unknown,
): TicketActivityMessage[] => {
  if (Array.isArray(activity)) {
    return [...activity]
      .sort((firstEntry: unknown, secondEntry: unknown) => {
        const firstDate =
          isRecord(firstEntry) && typeof firstEntry.Date === 'string'
            ? dayjs(firstEntry.Date).valueOf()
            : 0
        const secondDate =
          isRecord(secondEntry) && typeof secondEntry.Date === 'string'
            ? dayjs(secondEntry.Date).valueOf()
            : 0

        return secondDate - firstDate
      })
      .map(formatTicketActivityEntry)
      .filter((entry: TicketActivityMessage) => entry.text)
  }
  if (activity == null) {
    return []
  }
  return [{ text: formatUnknownValue(activity) }]
}

const CMMSTicketCard = ({
  ticket,
  project = undefined,
  withBorder = true,
  eventCMMSTickets = undefined,
  isLinked = true,
  onLink,
  onUnlink,
  isLinking = false,
  isUnlinking = false,
  canLink = false,
}: {
  ticket: CMMSTicket
  project?: Project
  withBorder?: boolean
  eventCMMSTickets?: EventCMMSTicket[]
  isLinked?: boolean
  onLink?: () => void
  onUnlink?: () => void
  isLinking?: boolean
  isUnlinking?: boolean
  canLink?: boolean
}) => {
  const { projectId } = useParams()
  const [opened, setOpened] = useState(false)
  const [descriptionExpanded, setDescriptionExpanded] = useState(false)
  const [ticketActivityExpanded, setTicketActivityExpanded] = useState(false)
  const provider = ticket.cmms_provider_name_long?.trim()
  const providerLabel = provider ? provider.toUpperCase() : 'UNKNOWN'
  const providerText = provider ?? 'Unknown'
  const providerColor = getProviderColor(provider)
  const { summary, shouldCollapseDescription } = useMemo(() => {
    const s = ticket.summary ?? ''
    const lineCount = s.split('\n').length
    return {
      summary: s,
      shouldCollapseDescription:
        lineCount > DESCRIPTION_COLLAPSED_LINES ||
        s.length > DESCRIPTION_COLLAPSE_CHARACTER_LIMIT,
    }
  }, [ticket.summary])
  const { ticketActivityMessages, shouldCollapseTicketActivity } = useMemo(() => {
    const activity = isRecord(ticket.json_raw)
      ? ticket.json_raw.TicketActivity
      : undefined
    const messages =
      provider?.toLowerCase() === 'qe solar'
        ? formatTicketActivityMessages(activity)
        : []
    let shouldCollapse = messages.length > 1
    if (!shouldCollapse && messages.length === 1) {
      const text = [messages[0].date, messages[0].text].filter(Boolean).join('\n')
      shouldCollapse =
        text.split('\n').length > TICKET_ACTIVITY_COLLAPSED_LINES ||
        text.length > DESCRIPTION_COLLAPSE_CHARACTER_LIMIT
    }
    return { ticketActivityMessages: messages, shouldCollapseTicketActivity: shouldCollapse }
  }, [ticket.json_raw, provider])
  const displayedTicketActivityMessages = useMemo(() => {
    return shouldCollapseTicketActivity && !ticketActivityExpanded
      ? ticketActivityMessages.slice(0, 1)
      : ticketActivityMessages
  }, [shouldCollapseTicketActivity, ticketActivityExpanded, ticketActivityMessages])
  const hasExternalLinkHandlers =
    typeof onLink === 'function' || typeof onUnlink === 'function'
  const actionLabel = isLinked ? 'Unlink Ticket' : 'Link Ticket'
  const actionLoading = hasExternalLinkHandlers
    ? isLinked
      ? isUnlinking
      : isLinking
    : false
  const actionDisabled = hasExternalLinkHandlers
    ? isLinked
      ? !onUnlink || isUnlinking
      : !onLink || isLinking
    : false
  const canShowActionButton = canLink
  const handleActionClick = () => {
    if (!canShowActionButton) {
      return
    }
    if (!hasExternalLinkHandlers) {
      setOpened(true)
      return
    }
    if (isLinked) {
      onUnlink?.()
      return
    }
    onLink?.()
  }
  return (
    <>
      <Card
        withBorder={withBorder}
        shadow="sm"
        p="md"
        w="100%"
        data-testid="cmms-ticket-card"
      >
        <Stack gap={GAP} w="100%" h="100%">
          <Group w="100%" h="100%" justify="space-between" align="flex-start">
            <Stack h="100%" flex={1}>
              <Group gap={GAP}>
                {ticket.link ? (
                  <Link to={ticket.link} target="_blank">
                    <Badge
                      color={providerColor}
                      rightSection={<IconExternalLink size={16} />}
                      variant="light"
                      size="lg"
                      style={{ cursor: 'pointer' }}
                    >
                      {providerLabel}: {ticket.key}
                    </Badge>
                  </Link>
                ) : (
                  <Badge variant="light" size="lg" color={providerColor}>
                    {providerLabel}: {ticket.key}
                  </Badge>
                )}
                {ticket.priority?.toLowerCase() === 'high' && (
                  <IconAlertTriangle {...ICON_PROPS} color="red" />
                )}
              </Group>
              <Text
                size="lg"
                lineClamp={
                  shouldCollapseDescription && !descriptionExpanded
                    ? DESCRIPTION_COLLAPSED_LINES
                    : undefined
                }
                style={{ whiteSpace: 'pre-wrap' }}
              >
                {summary}
              </Text>
              {shouldCollapseDescription && (
                <Button
                  variant="subtle"
                  size="compact-sm"
                  w="fit-content"
                  onClick={() =>
                    setDescriptionExpanded((expanded) => !expanded)
                  }
                  type="button"
                >
                  {descriptionExpanded ? 'Show less' : 'Show more'}
                </Button>
              )}
              {ticket.summary_long && (
                <Box size="md" c="dimmed" style={{ whiteSpace: 'pre-wrap' }}>
                  <div
                    dangerouslySetInnerHTML={{ __html: ticket.summary_long }}
                  />
                </Box>
              )}
              {ticket.location && (
                <Group gap={GAP}>
                  <IconMapPinFilled {...ICON_PROPS} />
                  <Text>{ticket.location}</Text>
                </Group>
              )}
              {(ticket.cmms_device_id || ticket.cmms_device_name) && (
                <Group gap={GAP} align="start">
                  <IconSettingsFilled {...ICON_PROPS} />
                  <Stack gap="xs">
                    {ticket.cmms_device_id && (
                      <Text>Device ID: {ticket.cmms_device_id}</Text>
                    )}
                    {ticket.cmms_device_name && (
                      <Text>Device Name: {ticket.cmms_device_name}</Text>
                    )}
                  </Stack>
                </Group>
              )}
              <Group gap={GAP}>
                <Group gap="xs">
                  <IconUser {...ICON_PROPS} />
                  <Badge color={providerColor} size="md">
                    {providerText}
                  </Badge>
                </Group>
                <Group gap="xs">
                  <IconClock {...ICON_PROPS} />
                  <Text c="dimmed">
                    Created:{' '}
                    {dayjs(ticket.source_created_at).format('YYYY-MM-DD HH:mm')}
                  </Text>
                </Group>
              </Group>
              {ticket.status_change_at && (
                <Group gap="xs">
                  <IconCalendarDue {...ICON_PROPS} />
                  <Text c="dimmed">
                    Status changed:{' '}
                    {dayjs(ticket.status_change_at).format('YYYY-MM-DD HH:mm')}
                  </Text>
                </Group>
              )}
              {ticket.assigned_to && (
                <Group gap={GAP}>
                  <IconUserSearch {...ICON_PROPS} />
                  <Text>Assigned To</Text>
                  <Badge variant="default">{ticket.assigned_to}</Badge>
                </Group>
              )}
            </Stack>
            {ticketActivityMessages.length > 0 && (
              <Stack h="100%" flex={1} miw={240} gap="xs">
                <Text fw={600}>Ticket Activity</Text>
                {displayedTicketActivityMessages.map((message, index) => (
                  <Stack key={`${message.date ?? 'activity'}-${index}`} gap={4}>
                    {message.date && (
                      <Text size="xs" c="dimmed">
                        {message.date}
                      </Text>
                    )}
                    <Box
                      p="xs"
                      bg="gray.0"
                      style={{
                        border: '1px solid var(--mantine-color-gray-3)',
                        borderRadius: 'var(--mantine-radius-sm)',
                      }}
                    >
                      <Text
                        size="sm"
                        lineClamp={
                          shouldCollapseTicketActivity &&
                          !ticketActivityExpanded
                            ? TICKET_ACTIVITY_COLLAPSED_LINES
                            : undefined
                        }
                        style={{ whiteSpace: 'pre-wrap' }}
                      >
                        {message.text}
                      </Text>
                    </Box>
                  </Stack>
                ))}
                {shouldCollapseTicketActivity && (
                  <Button
                    variant="subtle"
                    size="compact-sm"
                    w="fit-content"
                    onClick={() =>
                      setTicketActivityExpanded((expanded) => !expanded)
                    }
                    type="button"
                  >
                    {ticketActivityExpanded ? 'Show less' : 'Show more'}
                  </Button>
                )}
              </Stack>
            )}
            <Stack h="100%" align="flex-end" gap="xs">
              <Badge
                color={getCMMSTicketStatusColor(ticket.status || '')}
                size="lg"
                leftSection={getStatusIcon(ticket.status || '')}
              >
                {ticket.status}
              </Badge>
              {canShowActionButton && (
                <Button
                  size="xs"
                  variant="light"
                  color="gray"
                  onClick={handleActionClick}
                  loading={actionLoading}
                  disabled={actionDisabled}
                  type="button"
                >
                  {actionLabel}
                </Button>
              )}
              {eventCMMSTickets &&
                !!project &&
                project.has_event_integration && (
                  <Stack gap="xs" align="flex-end">
                    <Badge
                      color={eventCMMSTickets.length > 0 ? 'green' : 'grey'}
                      size="md"
                    >
                      Linked to {eventCMMSTickets.length} event
                      {eventCMMSTickets.length !== 1 ? 's' : ''}
                    </Badge>
                    <Button
                      size="xs"
                      variant="light"
                      color="gray"
                      onClick={() => setOpened(true)}
                    >
                      Open Event Linkage Suite
                    </Button>
                  </Stack>
                )}
            </Stack>
          </Group>
        </Stack>
      </Card>
      {opened && (
        <TicketFirstModal
          opened={opened}
          onClose={() => setOpened(false)}
          ticket={ticket}
          linkedEventIds={
            eventCMMSTickets?.map(
              (eventCMMSTicket) => eventCMMSTicket.event_id,
            ) || []
          }
          projectId={projectId || ''}
        />
      )}
    </>
  )
}

export default CMMSTicketCard
