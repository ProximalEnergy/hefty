import { PageTitle } from '@/components/PageTitle'
import { Stack, Tabs, Text } from '@mantine/core'
import { useParams, useSearchParams } from 'react-router-dom'

import OMContractors from './settings/OMContractors'
import PVBudgeted from './settings/PVBudgeted'
import ProjectInfo from './settings/ProjectInfo'
import Documents from './settings/documents'

const ProjectSettings = () => {
  const { projectId } = useParams()
  const [searchParams] = useSearchParams()
  const defaultTab = searchParams.get('tab') || 'project-info'

  return (
    <Stack h="100%" p="md">
      <PageTitle
        info={
          <Text>
            This page contains settings for the project. Use the tabs to
            navigate between different settings pages.
          </Text>
        }
      >
        Project Settings
      </PageTitle>
      <Tabs defaultValue={defaultTab} flex={1}>
        <Tabs.List>
          <Tabs.Tab value="project-info">Project Info</Tabs.Tab>
          <Tabs.Tab value="documents">Documents</Tabs.Tab>
          <Tabs.Tab value="om-contractors">O&M Contractors</Tabs.Tab>
          <Tabs.Tab value="pv-budgeted">PV Budgeted</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="project-info" flex={1}>
          <ProjectInfo projectId={projectId || '-1'} />
        </Tabs.Panel>

        <Tabs.Panel value="documents" flex={1}>
          <Documents projectId={projectId || '-1'} />
        </Tabs.Panel>

        <Tabs.Panel value="om-contractors" flex={1}>
          <OMContractors projectId={projectId || '-1'} />
        </Tabs.Panel>

        <Tabs.Panel value="pv-budgeted" flex={1}>
          <PVBudgeted projectId={projectId || '-1'} />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  )
}

export default ProjectSettings
