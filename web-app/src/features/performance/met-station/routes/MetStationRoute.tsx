import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { Stack } from '@mantine/core'
import { useParams } from 'react-router'

import { Tabs } from '../components/Tabs'
import { useMetStationContext } from '../hooks/use-met-station-context'
import { useMetStationTab } from '../hooks/use-met-station-tab'
import { MetStationDayView } from '../views/MetStationDayView'
import { MetStationLongTermView } from '../views/MetStationLongTermView'
import { MetStationRealTimeView } from '../views/MetStationRealTimeView'

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
