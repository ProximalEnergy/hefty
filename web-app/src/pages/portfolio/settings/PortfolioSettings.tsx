import { useGetUserType } from '@/api/admin'
import { ProjectTypeEnum, UserTypeEnumEnum } from '@/api/enumerations'
import { useGetProjects } from '@/api/v1/operational/projects'
import { PageTitle } from '@/components/PageTitle'
import { Stack, Tabs, Text } from '@mantine/core'

import PVInverter from './PVInverter'
import PVModule from './PVModule'
import PVRack from './PVRack'

const PortfolioSettings = () => {
  // Get all company projects to check if any have PV or PV+S (project_type_id 1 or 3)
  const projects = useGetProjects({ queryParams: { deep: true } })
  const hasPVProjects =
    projects.data?.some(
      (project) =>
        project.project_type_id === ProjectTypeEnum.PV ||
        project.project_type_id === ProjectTypeEnum.PVS,
    ) ?? false

  const userType = useGetUserType({})
  const isUserSuperadmin =
    userType?.data?.user_type_id === UserTypeEnumEnum.SUPERADMIN

  if (!hasPVProjects) {
    return (
      <Stack h="100%" p="md">
        <PageTitle>Portfolio Settings</PageTitle>
        <div>No PV projects found in portfolio.</div>
      </Stack>
    )
  }

  return (
    <Stack h="100%" p="md">
      <PageTitle
        info={
          <Stack>
            <Text>
              This page allows you to manage the settings for your portfolio,
              including the component library for PV inverters, racks, and
              modules.
            </Text>
          </Stack>
        }
      >
        Portfolio Settings
      </PageTitle>
      <Tabs defaultValue="PV Inverters" h="100%">
        <Tabs.List>
          <Tabs.Tab value="PV Inverters">PV Inverters</Tabs.Tab>
          <Tabs.Tab value="PV Rackings">PV Rackings</Tabs.Tab>
          {isUserSuperadmin && (
            <Tabs.Tab value="PV Modules">PV Modules</Tabs.Tab>
          )}
        </Tabs.List>

        <Tabs.Panel value="PV Inverters" h="100%">
          <PVInverter />
        </Tabs.Panel>

        <Tabs.Panel value="PV Rackings" h="100%">
          <PVRack />
        </Tabs.Panel>

        <Tabs.Panel value="PV Modules" h="100%">
          <PVModule />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  )
}

export default PortfolioSettings
