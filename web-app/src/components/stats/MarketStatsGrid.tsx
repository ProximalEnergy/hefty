import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetActiveOutageTickets } from '@/api/v1/protected/web-application/projects/financial/ptp_data'
import { Sparkline } from '@/components/stats/Sparkline'
import { StatsGrid } from '@/components/stats/StatsGrid'
import { useBatterySOC } from '@/components/stats/hooks/useBatterySOC'
import { useMarketPrices } from '@/components/stats/hooks/useMarketPrices'
import { useMarketRevenue } from '@/components/stats/hooks/useMarketRevenue'
import { usePowerDispatch } from '@/components/stats/hooks/usePowerDispatch'
import { Statistic } from '@/hooks/types'
import { OutageTicketsValue } from '@/pages/projects/finances/components/OutageTicketsValue'
import { useOutageTicketsDescription } from '@/pages/projects/finances/hooks/useOutageTicketsDescription'
import {
  Box,
  Group,
  Skeleton,
  Stack,
  Text,
  useMantineTheme,
} from '@mantine/core'
import { useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router'

interface MarketStatsGridProps {
  projectId: string
}

export function MarketStatsGrid({ projectId }: MarketStatsGridProps) {
  const project = useSelectProject(projectId)
  const theme = useMantineTheme()
  const navigate = useNavigate()

  const goToMarketPerformance = useCallback(() => {
    navigate(`/projects/${projectId}/finances/market-performance`)
  }, [navigate, projectId])

  const {
    rtPriceValue,
    daPrice,
    priceDiff,
    isLoading: priceLoading,
  } = useMarketPrices(projectId)

  const {
    rtRevenue,
    daRevenue,
    daASRevenue,
    realizedRevenue,
    unrealizedRevenue,
    revenueDate,
    isLoading: revenueLoading,
  } = useMarketRevenue(projectId)

  const {
    currentNetDispatchValue,
    sparklineData,
    dispatchState,
    isLoading: powerLoading,
  } = usePowerDispatch(projectId)

  const {
    socValue,
    remainingMWh,
    isLoading: socLoading,
  } = useBatterySOC(projectId)

  const { data: outageTicketsData } = useGetActiveOutageTickets({
    pathParams: { projectId },
    queryOptions: { enabled: !!projectId },
  })

  const outageTicketsDescription = useOutageTicketsDescription(
    outageTicketsData,
    project.data?.time_zone,
  )

  // --- Presentation helpers (JSX-producing) ---

  const revenueTodayValue = useMemo(() => {
    if (revenueLoading) return null
    if (realizedRevenue === null || unrealizedRevenue === null) return 'N/A'
    const fmt = (v: number) =>
      v.toLocaleString('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      })
    const str = `$${fmt(realizedRevenue)}`
    if (unrealizedRevenue > 0) {
      return (
        <>
          {str}{' '}
          <Text component="span" size="sm" c="dimmed">
            (+${fmt(unrealizedRevenue)} unrealized)
          </Text>
        </>
      )
    }
    return str
  }, [revenueLoading, realizedRevenue, unrealizedRevenue])

  const revenueBreakdown = useMemo(() => {
    if (revenueLoading) return null
    if (rtRevenue === null || daRevenue === null) return null
    const fmt = (v: number) =>
      v.toLocaleString('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      })
    const asVal = daASRevenue ?? 0
    return (
      <Text size="xs" c="dimmed">
        <Text component="span" c={theme.colors.orange[6]} fw={500}>
          RT:
        </Text>{' '}
        <Text component="span">${fmt(rtRevenue)}</Text>{' '}
        <Text component="span" c={theme.colors.blue[6]} fw={500}>
          DA:
        </Text>{' '}
        <Text component="span">${daRevenue === 0 ? '0' : fmt(daRevenue)}</Text>{' '}
        <Text component="span" c={theme.colors.yellow[6]} fw={500}>
          AS:
        </Text>{' '}
        <Text component="span">${asVal === 0 ? '0' : fmt(asVal)}</Text>
      </Text>
    )
  }, [revenueLoading, rtRevenue, daRevenue, daASRevenue, theme])

  // --- Stats array ---

  const realtimeStats: Statistic[] = useMemo(
    () => [
      {
        title: 'RT Price on Node',
        description: 'Real-time settlement point price',
        value: priceLoading ? null : (
          <Stack gap={2}>
            <Text fz={32} fw={700}>
              {rtPriceValue}
            </Text>
            {daPrice !== null && priceDiff !== null && (
              <Text size="xs" c="dimmed">
                DA: ${daPrice.toFixed(2)} / MWh ({priceDiff >= 0 ? '+' : ''}$
                {priceDiff.toFixed(2)} /MWh DART Spread)
              </Text>
            )}
          </Stack>
        ),
        icon: 'price',
        onClick: goToMarketPerformance,
      },
      {
        title: `Revenue Today${revenueDate ? ` (${revenueDate})` : ''}`,
        description: 'Total revenue generated today',
        value: (
          <Stack gap={2}>
            {revenueTodayValue === null ? (
              <Skeleton height={32} width={120} radius="xl" />
            ) : (
              <Text fz={32} fw={700}>
                {revenueTodayValue}
              </Text>
            )}
            {revenueBreakdown}
          </Stack>
        ),
        icon: 'revenue',
        onClick: goToMarketPerformance,
      },
      {
        title: 'Active Outage Tickets',
        description: outageTicketsDescription,
        value: (
          <OutageTicketsValue
            projectId={projectId}
            projectTimeZone={project.data?.time_zone}
          />
        ),
        icon: 'events',
      },
      {
        title: 'Power',
        description: 'Current net dispatch (+discharge/-charge)',
        value: (
          <Stack gap={2}>
            <Group gap="xs" align="center">
              {currentNetDispatchValue === null ? (
                <Skeleton height={32} width={120} radius="xl" />
              ) : (
                <Text fz={32} fw={700}>
                  {currentNetDispatchValue}
                </Text>
              )}
              {sparklineData.length > 0 && (
                <Sparkline data={sparklineData} width={60} height={20} />
              )}
            </Group>
            {dispatchState && (
              <Text size="xs" c="dimmed">
                {dispatchState}
              </Text>
            )}
          </Stack>
        ),
        icon: 'dispatch',
      },
      {
        title: 'State of Charge',
        description: 'Current battery state of charge',
        value: (
          <Stack gap={2}>
            {socValue === null ? (
              <Skeleton height={32} width={80} radius="xl" />
            ) : (
              <Text fz={32} fw={700}>
                {socValue}
              </Text>
            )}
            {remainingMWh !== null && (
              <Text size="xs" c="dimmed">
                ≈ {remainingMWh.toFixed(1)} MWh remaining
              </Text>
            )}
          </Stack>
        ),
        icon: 'soc',
      },
    ],
    [
      priceLoading,
      rtPriceValue,
      daPrice,
      priceDiff,
      revenueTodayValue,
      revenueBreakdown,
      revenueDate,
      outageTicketsDescription,
      projectId,
      project.data,
      currentNetDispatchValue,
      sparklineData,
      dispatchState,
      socValue,
      remainingMWh,
      goToMarketPerformance,
    ],
  )

  const statsLoading =
    priceLoading || revenueLoading || powerLoading || socLoading

  return (
    <Box>
      <StatsGrid data={realtimeStats} isLoading={statsLoading} />
    </Box>
  )
}
