import { Card, Group, HoverCard, Skeleton, Stack, Text } from '@mantine/core'
import { IconTicket } from '@tabler/icons-react'

import type { StatsData } from '@/features/performance/bess-string/types/bess-string-realtime'
import { statGridCardStyle } from '@/features/performance/bess-string/utils/stat-grid-card-style'

type CMMSTicketsCardProps = {
  isLoading: boolean
  hasIntegration: boolean
  stats: StatsData
  onClick: () => void
}

export const CMMSTicketsCard = ({
  isLoading,
  hasIntegration,
  stats,
  onClick,
}: CMMSTicketsCardProps) => (
  <HoverCard
    width={320}
    shadow="md"
    openDelay={300}
    closeDelay={100}
    disabled={isLoading}
  >
    <HoverCard.Target>
      <Card
        withBorder
        p="md"
        radius="md"
        style={statGridCardStyle({ cursor: 'pointer' })}
        onClick={onClick}
      >
        <Group justify="space-between" wrap="nowrap" gap="xs">
          <Text size="sm" c="dimmed" lineClamp={1}>
            CMMS Tickets
          </Text>
          <IconTicket size="1.2rem" stroke={1.5} style={{ flexShrink: 0 }} />
        </Group>
        <Stack gap={4} style={{ flex: 1, minHeight: 0 }}>
          <Text fz={32} fw={700} mt={15} component="div">
            {isLoading ? (
              <Skeleton height={32} width="60%" />
            ) : !hasIntegration ? (
              'N/A'
            ) : (
              stats.openCMMSTickets
            )}
          </Text>
          {!isLoading && (
            <Text size="sm" c="dimmed" mt={5} lineClamp={1}>
              {hasIntegration ? 'Open tickets' : 'No integration configured'}
            </Text>
          )}
        </Stack>
      </Card>
    </HoverCard.Target>
    <HoverCard.Dropdown>
      <Stack gap="xs">
        <Text fw={600} size="sm">
          CMMS Tickets
        </Text>
        {!hasIntegration ? (
          <Text size="xs" c="dimmed">
            Use the feedback button (bottom left) to get CMMS integration set
            up.
          </Text>
        ) : stats.cmmsHoverTickets.length === 0 ? (
          <Text size="xs" c="dimmed">
            No open linked CMMS tickets.
          </Text>
        ) : (
          stats.cmmsHoverTickets.map((ticket) => (
            <Stack key={ticket.key} gap={2}>
              <Text fw={600} size="sm">
                {ticket.key}
                {ticket.status ? ` (${ticket.status})` : ''}
              </Text>
              <Text size="xs" c="dimmed" lineClamp={3}>
                {ticket.summary}
              </Text>
            </Stack>
          ))
        )}
      </Stack>
    </HoverCard.Dropdown>
  </HoverCard>
)
