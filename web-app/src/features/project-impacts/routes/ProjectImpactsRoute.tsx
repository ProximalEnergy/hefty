import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { Stack, Tabs, Text } from '@mantine/core'
import { useParams } from 'react-router'
import { useProjectImpactsContext } from '@/features/project-impacts/hooks/use-project-impacts-context'
import { useProjectImpactsTab } from '@/features/project-impacts/hooks/use-project-impacts-tab'
import { ProjectImpactsEventView } from '@/features/project-impacts/views/ProjectImpactsEventView'
import { ProjectImpactsIssuesView } from '@/features/project-impacts/views/ProjectImpactsIssuesView'

const PROJECT_IMPACTS_INFO = (
  <Stack gap="xs">
    <Text size="sm">
      Project Impacts surfaces operational conditions that may require user
      attention, organized into Events and Issues.
    </Text>

    <Text size="sm">
      <Text span fw={600}>
        Events
      </Text>{' '}
      represent conditions that directly impact project performance, production,
      or available capacity. These are operational impacts that typically carry
      associated energy or financial loss.
    </Text>

    <Text size="sm">
      <Text span fw={600}>
        Issues
      </Text>{' '}
      represent conditions users may want visibility into, but that do not
      directly reduce project capacity or production. These may include data
      quality concerns, communication problems, configuration anomalies, or
      other informational conditions.
    </Text>
  </Stack>
)

export function ProjectImpactsRoute() {
  const { projectId } = useParams()
  const context = useProjectImpactsContext({ projectId })
  const { activeTab, setActiveTab } = useProjectImpactsTab()

  if (context.isLoading) {
    return <PageLoader />
  }

  if (context.error !== null) {
    return <PageError text="Error loading project impacts data" />
  }

  if (context.project === undefined || context.project === null) {
    return <PageError text="Project not found" />
  }

  return (
    <Stack p="md" h="100%">
      <PageTitle info={PROJECT_IMPACTS_INFO}>Project Impacts</PageTitle>
      <Tabs
        value={activeTab}
        onChange={setActiveTab}
        keepMounted={false}
        h="100%"
        style={{
          display: 'flex',
          flex: 1,
          flexDirection: 'column',
          minHeight: 0,
        }}
      >
        <Tabs.List>
          <Tabs.Tab value="events">Events</Tabs.Tab>
          <Tabs.Tab value="issues">Issues</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="events" style={{ flex: 1, minHeight: 0 }}>
          <ProjectImpactsEventView context={context} />
        </Tabs.Panel>
        <Tabs.Panel value="issues" style={{ flex: 1, minHeight: 0 }}>
          <ProjectImpactsIssuesView context={context} />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  )
}
