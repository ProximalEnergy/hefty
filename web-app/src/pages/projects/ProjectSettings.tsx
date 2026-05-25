import { ProjectTypeEnum } from '@/api/enumerations'
import { useSelectProject } from '@/api/v1/operational/projects'
import { PageTitle } from '@/components/PageTitle'
import OMContractors from '@/pages/projects/settings/OMContractors'
import PVBudgeted from '@/pages/projects/settings/PVBudgeted'
import ProjectInfo from '@/pages/projects/settings/ProjectInfo'
import Documents from '@/pages/projects/settings/documents'
import { Stack, Tabs, Text } from '@mantine/core'
import { useParams, useSearchParams } from 'react-router'

import PVColladaExport from '@/pages/projects/settings/PVColladaExport'

const ProjectSettings = () => {
  const { projectId } = useParams<{ projectId?: string }>()
  const [searchParams] = useSearchParams()
  const project = useSelectProject(projectId || '-1')

  // BESS-only projects have project_type_id = BESS
  const isBESSOnly = project.data?.project_type_id === ProjectTypeEnum.BESS
  const hasPV =
    project.data?.project_type_id === ProjectTypeEnum.PV ||
    project.data?.project_type_id === ProjectTypeEnum.PVS

  // If default tab is pv-budgeted but project is BESS-only, default to project-info
  const rawDefaultTab = searchParams.get('tab') || 'project-info'
  const defaultTab =
    (rawDefaultTab === 'pv-budgeted' && isBESSOnly) ||
    (rawDefaultTab === 'pvcollada-export' && !hasPV)
      ? 'project-info'
      : rawDefaultTab

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
      <Tabs defaultValue={defaultTab} flex={1} keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="project-info">Project Info</Tabs.Tab>
          <Tabs.Tab value="documents">Documents</Tabs.Tab>
          <Tabs.Tab value="om-contractors">O&M Contractors</Tabs.Tab>
          {!isBESSOnly && <Tabs.Tab value="pv-budgeted">PV Budgeted</Tabs.Tab>}
          {hasPV && (
            <Tabs.Tab value="pvcollada-export">PVCollada Export</Tabs.Tab>
          )}
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

        {!isBESSOnly && (
          <Tabs.Panel value="pv-budgeted" flex={1}>
            <PVBudgeted projectId={projectId || '-1'} />
          </Tabs.Panel>
        )}

        {hasPV && (
          <Tabs.Panel value="pvcollada-export" flex={1}>
            <PVColladaExport projectId={projectId || '-1'} />
          </Tabs.Panel>
        )}
      </Tabs>
    </Stack>
  )
}

export default ProjectSettings
