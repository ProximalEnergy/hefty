import { ProjectTypeEnum } from '@/api/enumerations'
import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { useProjectFilter } from '@/hooks/custom'
import { Stack, Tabs } from '@mantine/core'
import { useParams } from 'react-router'

import { BessStringHeader } from '@/features/performance/bess-string/components/BessStringHeader'
import { useBessStringContext } from '@/features/performance/bess-string/hooks/use-bess-string-context'
import { useBessStringTab } from '@/features/performance/bess-string/hooks/use-bess-string-tab'
import { BessStringDayView } from '@/features/performance/bess-string/views/BessStringDayView'
import { BessStringLongTermView } from '@/features/performance/bess-string/views/BessStringLongTermView'
import { BessStringRealtimeView } from '@/features/performance/bess-string/views/BessStringRealtimeView'

export function BessStringRoute() {
  useProjectFilter({
    projectTypes: [ProjectTypeEnum.BESS, ProjectTypeEnum.PVS],
  })

  const { projectId } = useParams()
  const context = useBessStringContext({ projectId })
  const { activeTab, setTab } = useBessStringTab({
    isSuperadmin: context.isSuperadmin,
  })

  if (context.isLoading) {
    return <PageLoader />
  }

  if (context.error !== null) {
    return <PageError text="Error loading BESS string data" />
  }

  if (context.project === undefined || context.project === null) {
    return <PageError text="Project not found" />
  }

  return (
    <Stack p="md" h="100%">
      <PageTitle>BESS String Performance</PageTitle>
      <BessStringHeader context={context} />

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
          <Tabs.Tab value="current-day">Day View</Tabs.Tab>
          {context.isSuperadmin && (
            <Tabs.Tab value="long-term">Long Term</Tabs.Tab>
          )}
        </Tabs.List>

        <Tabs.Panel value="realtime" pt="md">
          <BessStringRealtimeView context={context} />
        </Tabs.Panel>

        <Tabs.Panel
          value="current-day"
          pt="md"
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            minHeight: 0,
            width: '100%',
          }}
        >
          <BessStringDayView context={context} />
        </Tabs.Panel>

        {context.isSuperadmin && (
          <Tabs.Panel value="long-term" pt="md">
            <BessStringLongTermView />
          </Tabs.Panel>
        )}
      </Tabs>
    </Stack>
  )
}
