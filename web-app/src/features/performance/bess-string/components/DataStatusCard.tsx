import { Card, Group, HoverCard, Skeleton, Stack, Text } from '@mantine/core'
import { IconDatabaseX } from '@tabler/icons-react'

import type { StatsData } from '@/features/performance/bess-string/types/bess-string-realtime'
import { statGridCardStyle } from '@/features/performance/bess-string/utils/stat-grid-card-style'

type DataStatusCardProps = {
  isLoading: boolean
  stats: StatsData
  onClick: () => void
  onHoverChange: (isHovered: boolean) => void
}

export const DataStatusCard = ({
  isLoading,
  stats,
  onClick,
  onHoverChange,
}: DataStatusCardProps) => (
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
        onMouseEnter={() => onHoverChange(true)}
        onMouseLeave={() => onHoverChange(false)}
      >
        <Group justify="space-between" wrap="nowrap" gap="xs">
          <Text size="sm" c="dimmed" lineClamp={1}>
            Data Status
          </Text>
          <IconDatabaseX size="1.2rem" stroke={1.5} style={{ flexShrink: 0 }} />
        </Group>
        <Stack gap={4} style={{ flex: 1, minHeight: 0 }}>
          <Text fz={32} fw={700} mt={15} component="div">
            {isLoading ? (
              <Skeleton height={32} width="60%" />
            ) : (
              <Group gap="xs" align="center" wrap="nowrap">
                <div
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    flexShrink: 0,
                    backgroundColor:
                      stats.staleDevicesCount === 0 ? 'green' : 'red',
                  }}
                />
                <Text component="span" fz={32} fw={700} truncate>
                  {stats.staleDevicesCount === 0
                    ? 'OK'
                    : stats.staleDevicesCount}
                </Text>
              </Group>
            )}
          </Text>
          {!isLoading && stats.staleDevicesCount > 0 && (
            <Text size="sm" c="dimmed" mt={5} lineClamp={1}>
              Not Reporting
            </Text>
          )}
        </Stack>
      </Card>
    </HoverCard.Target>
    <HoverCard.Dropdown>
      <Stack gap="xs">
        <Text fw={600} size="sm">
          Data Status
        </Text>
        <Text size="xs" c="dimmed">
          {stats.staleDevicesCount === 0
            ? 'All strings reported data in the last hour.'
            : `Strings ${
                stats.staleDeviceNames.length > 10
                  ? `${stats.staleDeviceNames.slice(0, 10).join(', ')}, ...`
                  : stats.staleDeviceNames.join(', ')
              } not reporting data.`}
        </Text>
      </Stack>
    </HoverCard.Dropdown>
  </HoverCard>
)
