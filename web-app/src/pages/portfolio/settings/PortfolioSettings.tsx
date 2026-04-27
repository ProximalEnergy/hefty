import { useGetUserType } from '@/api/admin'
import { ProjectTypeEnum, UserTypeEnumEnum } from '@/api/enumerations'
import { useGetProjects } from '@/api/v1/operational/projects'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { Stack, Tabs, Text } from '@mantine/core'
import { useEffect } from 'react'
import { useSearchParams } from 'react-router'

import PVInverterSettings from './PVInverter'
import PVModuleSettings from './PVModule'
import PVRackSettings from './PVRack'
import System from './System'

const PortfolioSettingsPage = () => {
  const [searchParams, setSearchParams] = useSearchParams()

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

  const allowedTabs = isUserSuperadmin
    ? ['PV Inverters', 'PV Rackings', 'PV Modules', 'System']
    : ['PV Inverters', 'PV Rackings']
  const requestedTab = searchParams.get('tab')
  const activeTab =
    requestedTab && allowedTabs.includes(requestedTab)
      ? requestedTab
      : 'PV Inverters'

  useEffect(() => {
    if (searchParams.get('tab') === activeTab) {
      return
    }

    const newParams = new URLSearchParams(searchParams)
    newParams.set('tab', activeTab)
    setSearchParams(newParams, { replace: true })
  }, [activeTab, searchParams, setSearchParams])

  if (projects.isLoading) {
    return (
      <Stack h="100%" p="md">
        <PageTitle>Portfolio Settings</PageTitle>
        <PageLoader />
      </Stack>
    )
  }

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
      <Tabs
        value={activeTab}
        onChange={(value) => {
          if (!value) {
            return
          }
          const newParams = new URLSearchParams(searchParams)
          newParams.set('tab', value)
          setSearchParams(newParams)
        }}
        h="100%"
      >
        <Tabs.List>
          <Tabs.Tab value="PV Inverters">PV Inverters</Tabs.Tab>
          <Tabs.Tab value="PV Rackings">PV Rackings</Tabs.Tab>
          {isUserSuperadmin && (
            <Tabs.Tab value="PV Modules">PV Modules</Tabs.Tab>
          )}
          {isUserSuperadmin && <Tabs.Tab value="System">System</Tabs.Tab>}
        </Tabs.List>

        <Tabs.Panel value="PV Inverters" h="100%">
          <PVInverterSettings />
        </Tabs.Panel>

        <Tabs.Panel value="PV Rackings" h="100%">
          <PVRackSettings />
        </Tabs.Panel>

        {isUserSuperadmin && (
          <Tabs.Panel value="PV Modules" h="100%">
            <PVModuleSettings />
          </Tabs.Panel>
        )}

        {isUserSuperadmin && (
          <Tabs.Panel value="System" h="100%">
            <System />
          </Tabs.Panel>
        )}
      </Tabs>
    </Stack>
  )
}

export default PortfolioSettingsPage
