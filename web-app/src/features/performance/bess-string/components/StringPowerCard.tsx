import {
  Box,
  Card,
  Group,
  HoverCard,
  Skeleton,
  Stack,
  Text,
} from '@mantine/core'
import { IconBolt } from '@tabler/icons-react'
import dayjs from 'dayjs'

import {
  barOpacityForTier,
  freshnessLabel,
} from '@/features/performance/bess-string/utils/bess-string-realtime-staleness'
import type { StatsData } from '@/features/performance/bess-string/types/bess-string-realtime'
import { statGridCardStyle } from '@/features/performance/bess-string/utils/stat-grid-card-style'

type StringPowerCardProps = {
  isLoading: boolean
  stats: StatsData
  subtitle: string
}

export const StringPowerCard = ({
  isLoading,
  stats,
  subtitle,
}: StringPowerCardProps) => {
  const freshnessTier = stats.cumulativeStringPowerFreshnessTier
  const valueOpacity = isLoading ? 1 : barOpacityForTier(freshnessTier)
  const includedLabel = `${stats.stringPowerIncludedCount}/${stats.stringPowerTotalCount} strings included`

  return (
    <HoverCard
      width={320}
      shadow="md"
      openDelay={300}
      closeDelay={100}
      disabled={isLoading}
    >
      <HoverCard.Target>
        <Card withBorder p="md" radius="md" style={statGridCardStyle()}>
          <Group justify="space-between" wrap="nowrap" gap="xs">
            <Text size="sm" c="dimmed" lineClamp={1}>
              String Power
            </Text>
            <IconBolt size="1.2rem" stroke={1.5} style={{ flexShrink: 0 }} />
          </Group>
          <Stack gap={4} style={{ flex: 1, minHeight: 0 }}>
            <Text fz={32} fw={700} mt={15} component="div">
              {isLoading ? (
                <Skeleton height={32} width="60%" />
              ) : (
                <Box component="span" display="inline-block" w="100%">
                  <Text
                    component="span"
                    fz={32}
                    fw={700}
                    truncate
                    style={{ opacity: valueOpacity }}
                  >
                    {stats.cumulativeStringPowerMW} MWdc
                  </Text>
                </Box>
              )}
            </Text>
            {!isLoading && (
              <Text size="sm" c="dimmed" mt={5} lineClamp={1}>
                {subtitle}. {includedLabel}
              </Text>
            )}
          </Stack>
        </Card>
      </HoverCard.Target>
      <HoverCard.Dropdown>
        <Stack gap="xs">
          <Text fw={600} size="sm">
            Cumulative String Power
          </Text>
          <Text size="xs" c="dimmed">
            Status: {freshnessLabel(freshnessTier)}
          </Text>
          <Text size="xs" c="dimmed">
            {stats.cumulativeStringPowerTimestamp
              ? `Latest string update: ${dayjs(
                  stats.cumulativeStringPowerTimestamp,
                ).format('MMM D, YYYY HH:mm:ss')}`
              : 'Timestamp not available'}
          </Text>
          <Text size="xs" c="dimmed">
            {includedLabel} with data in the last 10 minutes.
          </Text>
        </Stack>
      </HoverCard.Dropdown>
    </HoverCard>
  )
}
