import { useGetUserSelf } from '@/api/v1/admin/users'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetRealtimePrice } from '@/api/v1/protected/web-application/projects/financial/market_performance'
import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { Group, Skeleton, Stack, Tabs, Text } from '@mantine/core'
import { useMemo } from 'react'
import { useParams, useSearchParams } from 'react-router'

import { LongTermTab } from './LongTermTab'
import { RealtimeTab } from './RealtimeTab'
import { WeekViewTab } from './WeekViewTab'

const SABLE_POINT_COMPANY_ID = '38a8e696-dafa-44c0-b817-e3aee8cdfe8c'

const MarketPerformance = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const project = useSelectProject(projectId!)
  const [searchParams, setSearchParams] = useSearchParams()

  const self = useGetUserSelf({})

  const activeTab = useMemo(() => {
    const tab = searchParams.get('tab')
    if (tab === 'realtime' || tab === 'week-view' || tab === 'long-term') {
      return tab
    }
    return 'realtime'
  }, [searchParams])

  const setTab = (value: string | null) => {
    const nextTab = value || 'realtime'
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('tab', nextTab)
    setSearchParams(nextParams, { replace: true })
  }

  // Get QSE provider and node name from realtime price endpoint
  const { data: priceData, isLoading: priceLoading } = useGetRealtimePrice({
    pathParams: { projectId: projectId! },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  // Grid is ERCOT-specific; not exposed by PTP API, so hardcoded
  const GRID = 'ERCOT'

  // Early return - MUST be after all hooks
  if (project.isLoading) {
    return <PageLoader />
  }

  if (self.isLoading) {
    return <PageLoader />
  }
  if (self.data?.company_id === SABLE_POINT_COMPANY_ID) {
    return (
      <PageError text="Please provide a Tenaska API key to see Market Performance" />
    )
  }

  return (
    <Stack p="md" h="100%">
      <Group justify="space-between" align="flex-start">
        <Stack gap={4}>
          <PageTitle>Market Performance</PageTitle>
          <Group gap="xs" align="center" wrap="wrap">
            {priceLoading ? (
              <Skeleton height={14} width={280} radius="xl" mt={-8} />
            ) : (
              <Text size="sm" c="dimmed" mt={-8}>
                Grid: {GRID} :: Node: {priceData?.node_name ?? '—'}
              </Text>
            )}
          </Group>
        </Stack>
        {priceData?.qse_provider_name && (
          <Group gap="xs">
            <Text size="sm" c="dimmed">
              Data provided by
            </Text>
            <Text size="sm" fw={500}>
              {priceData.qse_provider_name}
            </Text>
          </Group>
        )}
      </Group>

      <Tabs
        value={activeTab}
        onChange={setTab}
        variant="outline"
        keepMounted={false}
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          minHeight: 0,
          width: '100%',
        }}
      >
        <Tabs.List>
          <Tabs.Tab value="realtime">Real-time</Tabs.Tab>
          <Tabs.Tab value="week-view">Week View</Tabs.Tab>
          <Tabs.Tab value="long-term">Long Term</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="realtime" pt="md">
          <RealtimeTab projectId={projectId!} />
        </Tabs.Panel>

        <Tabs.Panel value="week-view" pt="md">
          <WeekViewTab projectId={projectId!} />
        </Tabs.Panel>

        <Tabs.Panel value="long-term" pt="md">
          <LongTermTab projectId={projectId!} />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  )
}

export default MarketPerformance
