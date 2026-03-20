import { CMMSTicket } from '@/api/v1/operational/project/cmms_tickets'
import { Card, Group, Text, ThemeIcon, rem } from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'

import CMMSTicketCard from './CMMSTicketCard'

const PlaceholderTicket = () => {
  const placeholderTicket: CMMSTicket = {
    cmms_ticket_id: -1,
    db_created_at: new Date().toISOString(),
    db_updated_at: new Date().toISOString(),
    source_id: 1,
    key: 'EX-01',
    summary: 'Example Ticket: Inverter Underperformance',
    summary_long:
      'This is an example of a CMMS ticket. The details shown here are for demonstration purposes only, as there is currently no CMMS integration configured for this project.',
    status: 'Open',
    priority: 'Medium',
    source_created_at: new Date().toISOString(),
    reporter: 'System',
    assigned_to: 'Site Manager',
    location: 'Inverter 10, String 3',
    cmms_provider_name_long: 'Jira',
    cmms_device_id: 'INV-10',
    cmms_integration_id: -1,
  }

  return (
    <Card>
      <CMMSTicketCard ticket={placeholderTicket} withBorder={false} />
      <Card.Section withBorder inheritPadding py="md" mt="md">
        <Group align="center" gap="xs">
          <ThemeIcon variant="transparent" size="md" c="dimmed">
            <IconInfoCircle
              style={{
                width: rem(24),
                height: rem(24),
              }}
            />
          </ThemeIcon>
          <Text c="dimmed">
            This is a placeholder ticket. To integrate your CMMS with Proximal,
            please reach out to support via the feedback icon in the bottom
            left.
          </Text>
        </Group>
      </Card.Section>
    </Card>
  )
}

export default PlaceholderTicket
