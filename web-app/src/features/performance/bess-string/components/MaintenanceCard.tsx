import { Card, Group, HoverCard, Skeleton, Stack, Text } from '@mantine/core'
import { IconCalendar } from '@tabler/icons-react'

import type { NextMaintenanceData } from '@/features/performance/bess-string/types/bess-string-realtime'
import { statGridCardStyle } from '@/features/performance/bess-string/utils/stat-grid-card-style'

type MaintenanceCardProps = {
  isLoading: boolean
  nextPreventativeMaintenance: NextMaintenanceData | null
  onClick: () => void
}

export const MaintenanceCard = ({
  isLoading,
  nextPreventativeMaintenance,
  onClick,
}: MaintenanceCardProps) => (
  <HoverCard width={320} shadow="md" openDelay={300} closeDelay={100}>
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
            Maintenance
          </Text>
          <IconCalendar size="1.2rem" stroke={1.5} style={{ flexShrink: 0 }} />
        </Group>
        <Stack gap={4} style={{ flex: 1, minHeight: 0 }}>
          <Text fz={32} fw={700} mt={15} component="div">
            {isLoading ? (
              <Skeleton height={32} width="60%" />
            ) : nextPreventativeMaintenance ? (
              <Text component="span" fz={32} fw={700} truncate>
                {nextPreventativeMaintenance.formattedDate}
              </Text>
            ) : (
              'N/A'
            )}
          </Text>
          <Text size="sm" c="dimmed" mt={5} lineClamp={1}>
            Next PM (DC enclosure / string)
          </Text>
        </Stack>
      </Card>
    </HoverCard.Target>
    <HoverCard.Dropdown>
      <Stack gap="xs">
        <Text fw={600} size="sm">
          {nextPreventativeMaintenance
            ? 'Next Preventative Maintenance'
            : 'Set Preventative Maintenance'}
        </Text>
        {!nextPreventativeMaintenance && (
          <Text size="xs" c="dimmed">
            Click to set the next Preventative Maintenance date. In the
            calendar, click a date and add a new item with a preventative
            maintenance category for this equipment.
          </Text>
        )}
        {nextPreventativeMaintenance?.hoverContent?.title && (
          <Stack gap={2}>
            <Text fw={600} size="sm">
              {nextPreventativeMaintenance.hoverContent.title}
            </Text>
            {nextPreventativeMaintenance.hoverContent.description && (
              <Text size="xs" c="dimmed" lineClamp={4}>
                {nextPreventativeMaintenance.hoverContent.description}
              </Text>
            )}
            {nextPreventativeMaintenance.hoverContent.assignees && (
              <Text size="xs" c="dimmed" lineClamp={2}>
                {nextPreventativeMaintenance.hoverContent.assignees}
              </Text>
            )}
          </Stack>
        )}
      </Stack>
    </HoverCard.Dropdown>
  </HoverCard>
)
