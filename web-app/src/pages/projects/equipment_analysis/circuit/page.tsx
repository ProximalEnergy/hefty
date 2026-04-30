import { useGetUserType } from '@/api/admin'
import { ProjectTypeEnum, UserTypeEnumEnum } from '@/api/enumerations'
import { useSelectProject } from '@/api/v1/operational/projects'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { useProjectFilter } from '@/hooks/custom'
import { Stack, Tabs, Text } from '@mantine/core'
import { useParams } from 'react-router'

import { useEquipmentAnalysisTab } from '../useEquipmentAnalysisTab'

const CircuitPage = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeEnum.PV, ProjectTypeEnum.PVS],
  })

  const { projectId } = useParams<{ projectId: string }>()
  const userType = useGetUserType({})
  const isSuperadmin =
    userType.data?.user_type_id === UserTypeEnumEnum.SUPERADMIN
  const { activeTab, setTab } = useEquipmentAnalysisTab({ isSuperadmin })
  const project = useSelectProject(projectId!)

  if (project.isLoading) {
    return <PageLoader />
  }

  return (
    <Stack p="md">
      <PageTitle>PV Circuit Performance</PageTitle>
      <Tabs
        value={activeTab}
        onChange={setTab}
        variant="outline"
        keepMounted={false}
      >
        <Tabs.List>
          <Tabs.Tab value="realtime">Real-time</Tabs.Tab>
          <Tabs.Tab value="current-day">Day View</Tabs.Tab>
          {isSuperadmin && <Tabs.Tab value="long-term">Long Term</Tabs.Tab>}
        </Tabs.List>

        <Tabs.Panel value="realtime" pt="md">
          <Stack gap="md">
            <Text c="dimmed">
              This tab and page are still under development. The real-time view
              for PV Circuit performance needs to be created.
            </Text>
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="current-day" pt="md">
          <Stack gap="md">
            <Text c="dimmed">
              This tab and page are still under development. The day view for PV
              Circuit performance needs to be created.
            </Text>
          </Stack>
        </Tabs.Panel>

        {isSuperadmin && (
          <Tabs.Panel value="long-term" pt="md">
            <Stack gap="md">
              <Text c="dimmed">
                This tab and page are still under development and are only
                visible to superadmins. The long-term PV Circuit performance
                view needs to be created.
              </Text>
            </Stack>
          </Tabs.Panel>
        )}
      </Tabs>
    </Stack>
  )
}

export default CircuitPage
