import { CMMSTicket } from '@/api/v1/operational/project/cmms_tickets'
import { Card, Text, ThemeIcon, rem } from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'

import CMMSTicketCard from './CMMSTicketCard'

const PlaceholderTicket = () => {
  const placeholderTicket: CMMSTicket = {
    id: 1,
    key: 'EX-01',
    summary: 'Example Ticket: Inverter Underperformance',
    summary_long:
      'This is an example of a CMMS ticket. The details shown here are for demonstration purposes only, as there is currently no CMMS integration configured for this project.',
    status: 'Open',
    priority: 'Medium',
    created_at: new Date().toISOString(),
    reporter: 'System',
    assigned_to: 'Site Manager',
    location: 'Inverter 10, String 3',
    cmms_provider: 'Jira',
    cmms_device_id: 'INV-10',
  }

  return (
    <Card>
      <CMMSTicketCard ticket={placeholderTicket} withBorder={false} />
      <Card.Section withBorder inheritPadding py="md" mt="md">
        <Text c="dimmed">
          <ThemeIcon variant="transparent" size="lg" c="dimmed">
            <IconInfoCircle
              style={{
                width: rem(24),
                height: rem(24),
              }}
            />
          </ThemeIcon>
          This is a placeholder ticket. To integrate your CMMS with Proximal,
          please reach out to support via the feedback icon in the bottom left.
        </Text>
      </Card.Section>
    </Card>
  )
}

export default PlaceholderTicket
