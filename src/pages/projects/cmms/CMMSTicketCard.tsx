import { CMMSTicket } from '@/api/v1/operational/project/cmms_tickets'
import { Badge, Box, Card, Group, Stack, Text, rem } from '@mantine/core'
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
import { Link } from 'react-router-dom'

const ICON_PROPS = {
  style: {
    width: rem(24),
    height: rem(24),
  },
  stroke: 1.5,
}

const GAP = 'md'

const getStatusColor = (status: string) => {
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

const getProviderColor = (provider: string) => {
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

const CMMSTicketCard = ({
  ticket,
  withBorder = true,
}: {
  ticket: CMMSTicket
  withBorder?: boolean
}) => {
  return (
    <Card
      withBorder={withBorder}
      shadow="sm"
      p="md"
      w="100%"
      data-testid="cmms-ticket-card"
    >
      <Stack gap={GAP}>
        <Group gap={GAP} justify="space-between">
          <Group gap={GAP}>
            {ticket.link ? (
              <Link to={ticket.link} target="_blank">
                <Badge
                  color={getProviderColor(ticket.cmms_provider)}
                  rightSection={<IconExternalLink size={16} />}
                  variant="light"
                  size="lg"
                  style={{ cursor: 'pointer' }}
                >
                  {ticket.cmms_provider.toUpperCase()}: {ticket.key}
                </Badge>
              </Link>
            ) : (
              <Badge
                variant="light"
                size="lg"
                color={getProviderColor(ticket.cmms_provider)}
              >
                {ticket.cmms_provider.toUpperCase()}: {ticket.key}
              </Badge>
            )}
            {ticket.priority?.toLowerCase() === 'high' && (
              <IconAlertTriangle {...ICON_PROPS} color="red" />
            )}
          </Group>
          <Badge
            color={getStatusColor(ticket.status || '')}
            size="lg"
            leftSection={getStatusIcon(ticket.status || '')}
          >
            {ticket.status}
          </Badge>
        </Group>

        <Text size="lg" style={{ whiteSpace: 'pre-wrap' }}>
          {ticket.summary}
        </Text>

        {ticket.summary_long && (
          <Box size="md" c="dimmed" style={{ whiteSpace: 'pre-wrap' }}>
            <div dangerouslySetInnerHTML={{ __html: ticket.summary_long }} />
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
            <Badge color={getProviderColor(ticket.cmms_provider)} size="md">
              {ticket.cmms_provider}
            </Badge>
          </Group>
          <Group gap="xs">
            <IconClock {...ICON_PROPS} />
            <Text c="dimmed">
              Created: {dayjs(ticket.created_at).format('YYYY-MM-DD HH:mm')}
            </Text>
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
        </Group>

        {ticket.assigned_to && (
          <Group gap={GAP}>
            <IconUserSearch {...ICON_PROPS} />
            <Text>Assigned To</Text>
            <Badge variant="default">{ticket.assigned_to}</Badge>
          </Group>
        )}
      </Stack>
    </Card>
  )
}

export default CMMSTicketCard
