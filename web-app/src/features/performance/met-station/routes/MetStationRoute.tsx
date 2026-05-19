import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { Tabs } from '@/features/performance/met-station/components/Tabs'
import { useMetStationContext } from '@/features/performance/met-station/hooks/use-met-station-context'
import { useMetStationTab } from '@/features/performance/met-station/hooks/use-met-station-tab'
import { MetStationDayView } from '@/features/performance/met-station/views/MetStationDayView'
import { MetStationLongTermView } from '@/features/performance/met-station/views/MetStationLongTermView'
import { MetStationRealTimeView } from '@/features/performance/met-station/views/MetStationRealTimeView'
import { Stack } from '@mantine/core'
import { useParams } from 'react-router'

export function MetStationRoute() {
  const { projectId } = useParams()
  const context = useMetStationContext({ projectId })
  const { activeTab, setActiveTab } = useMetStationTab({
    isSuperadmin: context.isSuperadmin,
  })

  if (context.isLoading) {
    return <PageLoader />
  }

  if (context.error !== null) {
    return <PageError text="Error loading met station data" />
  }

  if (context.project === undefined || context.project === null) {
    return <PageError text="Project not found" />
  }

  return (
    <Stack p="md" h="100%">
      <PageTitle>Met Station Performance</PageTitle>

      <Tabs
        value={activeTab}
        onChange={setActiveTab}
        isSuperadmin={context.isSuperadmin}
      >
        {activeTab === 'realtime' && context.isSuperadmin && (
          <MetStationRealTimeView context={context} />
        )}

        {activeTab === 'current-day' && <MetStationDayView context={context} />}

        {activeTab === 'long-term' && context.isSuperadmin && (
          <MetStationLongTermView context={context} />
        )}
      </Tabs>
    </Stack>
  )
}
