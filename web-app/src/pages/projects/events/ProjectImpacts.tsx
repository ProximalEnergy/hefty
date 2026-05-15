import { PageTitle } from '@/components/PageTitle'
import ProjectEvents from '@/pages/projects/ProjectEvents'
import { Stack, Tabs } from '@mantine/core'

import ProjectIssues from './ProjectIssues'

const ProjectImpacts = () => {
  return (
    <Stack p="md">
      <PageTitle
        info={
          'This page displays active project impacts, including Events and Issues.'
        }
      >
        Impacts
      </PageTitle>
      <Tabs defaultValue="events" keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="events">Events</Tabs.Tab>
          <Tabs.Tab value="issues">Issues</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel pt="md" value="events">
          <ProjectEvents withPageTitle={false} />
        </Tabs.Panel>
        <Tabs.Panel pt="md" value="issues">
          <ProjectIssues />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  )
}

export default ProjectImpacts
