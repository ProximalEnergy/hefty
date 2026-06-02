import {
  Box,
  Card,
  Group,
  HoverCard,
  Skeleton,
  Stack,
  Text,
} from '@mantine/core'
import { IconScale } from '@tabler/icons-react'

import type { StatsData } from '@/features/performance/bess-string/types/bess-string-realtime'
import { statGridCardStyle } from '@/features/performance/bess-string/utils/stat-grid-card-style'

type RealtimeBalanceScoreCardProps = {
  isLoading: boolean
  stats: StatsData
}

export const RealtimeBalanceScoreCard = ({
  isLoading,
  stats,
}: RealtimeBalanceScoreCardProps) => (
  <Card withBorder p="md" radius="md" style={statGridCardStyle()}>
    <Group justify="space-between" wrap="nowrap" gap="xs">
      <Text size="sm" c="dimmed" lineClamp={1}>
        Realtime Balance Score
      </Text>
      <IconScale size="1.2rem" stroke={1.5} style={{ flexShrink: 0 }} />
    </Group>
    <Stack gap={4} style={{ flex: 1, minHeight: 0 }}>
      <Text fz={32} fw={700} mt={15} component="div" truncate>
        {isLoading ? (
          <Skeleton height={32} width="60%" />
        ) : stats.balanceScoreOverallPct != null ? (
          <HoverCard width={320} shadow="md" openDelay={300} closeDelay={100}>
            <HoverCard.Target>
              <Box component="span" display="inline-block" w="100%">
                <Text component="span" fz={32} fw={700} truncate>
                  {stats.balanceScoreOverallPct.toFixed(1)}%
                </Text>
              </Box>
            </HoverCard.Target>
            <HoverCard.Dropdown>
              <Stack gap="xs">
                <Text fw={600} size="sm">
                  Realtime Balance Score
                </Text>
                <Text size="xs" c="dimmed">
                  Snapshot from the latest string SOC values (normalized to
                  0–1). The large figure is the simple average of System and
                  Intra-PCS, each expressed as 0–100%. Higher means strings are
                  closer together in SOC.
                </Text>
                <Text size="xs" c="dimmed">
                  Both parts use{' '}
                  <Text span fw={600} c="dimmed">
                    1 − 2σ
                  </Text>{' '}
                  with σ the population standard deviation of the SOC fractions
                  in scope. System σ is across all project strings. Intra-PCS
                  computes σ per PCS over that PCS’s strings only, then averages
                  those scores giving every string equal weight.
                </Text>
              </Stack>
            </HoverCard.Dropdown>
          </HoverCard>
        ) : (
          'N/A'
        )}
      </Text>
      {!isLoading && (
        <Text size="sm" c="dimmed" mt={5} lineClamp={1} truncate>
          Sys:{' '}
          {stats.balanceScoreSystemPct != null
            ? `${stats.balanceScoreSystemPct.toFixed(1)}%`
            : 'N/A'}
          {' · '}
          IntraPCS:{' '}
          {stats.balanceScoreIntraPcsPct != null
            ? `${stats.balanceScoreIntraPcsPct.toFixed(1)}%`
            : 'N/A'}
        </Text>
      )}
    </Stack>
  </Card>
)
