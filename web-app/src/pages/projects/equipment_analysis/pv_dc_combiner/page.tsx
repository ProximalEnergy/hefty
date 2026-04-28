import { useGetUserType } from '@/api/admin'
import {
  DeviceTypeEnum,
  ProjectTypeEnum,
  UserTypeEnumEnum,
} from '@/api/enumerations'
import { useGetBlockDropdown } from '@/api/ui'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetEquipmentAnalysisCombiner } from '@/api/v1/protected/web-application/projects/equipment-analysis/combiner'
import BlockDropdown from '@/components/BlockDropdown'
import CustomCard from '@/components/CustomCard'
import { PageTitle } from '@/components/PageTitle'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useGetDevicesV2 } from '@/hooks/api'
import { useProjectFilter } from '@/hooks/custom'
import { Device } from '@/hooks/types'
import { useResizePlotlyCharts } from '@/hooks/useResizePlotlyCharts'
import RealTime from '@/pages/projects/device_details/RealTime'
import { Checkbox, Group, HoverCard, Stack, Tabs, Text } from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'
import { useMemo, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router'

const MAX_DAYS = 1

const EquipmentAnalysisPVDCCombinerPage = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeEnum.PV, ProjectTypeEnum.PVS],
  })

  const navigate = useNavigate()
  const { projectId } = useParams<{ projectId: string }>()
  const userType = useGetUserType({})
  const isSuperadmin =
    userType.data?.user_type_id === UserTypeEnumEnum.SUPERADMIN
  const [searchParams, setSearchParams] = useSearchParams()
  const [checked, setChecked] = useState(false)
  const activeTab = useMemo(() => {
    const tab = searchParams.get('tab')
    if (tab === 'realtime' || tab === 'current-day') {
      return tab
    }
    if (isSuperadmin && tab === 'long-term') {
      return tab
    }
    return 'current-day'
  }, [isSuperadmin, searchParams])
  const setTab = (value: string | null) => {
    const nextTab = value || 'current-day'
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('tab', nextTab)
    setSearchParams(nextParams, { replace: true })
  }
  const tabPanelRef = useRef<HTMLDivElement>(null)

  // Handle block dropdown change
  const handlePvDcCombinerDropdownChange = (value: string | null) => {
    if (value) {
      const newSearchParams = new URLSearchParams(searchParams)
      newSearchParams.set('deviceId', value)
      navigate(
        `/projects/${projectId}/equipment-analysis/pv-dc-combiner/block?${newSearchParams.toString()}`,
      )
    }
  }

  const blockDropdown = useGetBlockDropdown({
    pathParams: { projectId: projectId || '-1' },
  })

  const devices = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: [
        DeviceTypeEnum.PV_DC_COMBINER,
        DeviceTypeEnum.PV_INVERTER,
        DeviceTypeEnum.PV_INVERTER_MODULE,
      ],
    },
  })

  // Helper function to find the parent device recursively
  const findParentDeviceId = (
    deviceId: string,
    devicesMap: Record<string, Device>,
  ) => {
    let currentDevice = devicesMap[deviceId]
    while (
      currentDevice &&
      currentDevice.device_type_id !== DeviceTypeEnum.PV_INVERTER &&
      currentDevice.parent_device_id !== null
    ) {
      currentDevice = devicesMap[currentDevice.parent_device_id]
    }
    return currentDevice ? currentDevice.parent_device_id : null
  }

  const deviceMap: Record<string, Device> = {}

  devices.data?.forEach((device) => {
    deviceMap[device.device_id] = device
  })

  const deviceMapping: Record<string, string> = {}
  devices.data?.forEach((device) => {
    const parentId = findParentDeviceId(String(device.device_id), deviceMap)
    if (parentId && device.name_long) {
      deviceMapping[device.name_long] = String(parentId)
    }
  })

  const project = useSelectProject(projectId!)
  const { start, end } = useValidateDateRange({
    maxDays: MAX_DAYS,
  })
  let startRequest, endRequest
  if (project.data) {
    startRequest = start && start.tz(project.data.time_zone, true).toISOString()
    endRequest =
      end &&
      end.tz(project.data.time_zone, true).subtract(1, 'days').toISOString()
  }

  const data = useGetEquipmentAnalysisCombiner({
    pathParams: { project_id: projectId || '-1' },
    queryParams: {
      start: startRequest ?? undefined,
      end: endRequest ?? undefined,
    },
    queryOptions: { enabled: !!projectId },
  })

  // Must stay before early returns to satisfy hooks rules.
  useResizePlotlyCharts({
    containerRef: tabPanelRef,
    enabled: activeTab === 'current-day',
  })

  return (
    <Stack p="md" h="100%">
      <PageTitle>PV DC Combiner Performance</PageTitle>
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
          {isSuperadmin && <Tabs.Tab value="long-term">Long Term</Tabs.Tab>}
        </Tabs.List>

        <Tabs.Panel
          value="realtime"
          pt="md"
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            minHeight: 0,
            width: '100%',
          }}
        >
          <RealTime
            initialDeviceTypeId={DeviceTypeEnum.PV_DC_COMBINER}
            restrictToDeviceTypeId={DeviceTypeEnum.PV_DC_COMBINER}
          />
        </Tabs.Panel>

        <Tabs.Panel
          value="current-day"
          pt="md"
          ref={tabPanelRef}
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            minHeight: 0,
            width: '100%',
          }}
        >
          <Stack gap="md" style={{ flex: 1, minHeight: 0 }}>
            <Group>
              <BlockDropdown
                data={blockDropdown.data}
                value={null}
                onChange={handlePvDcCombinerDropdownChange}
                includeNextPrevious={false}
                includeFirstLast={false}
              />
              <AdvancedDatePicker
                includeClearButton={false}
                limits={{
                  day: 1,
                  week: 0,
                  month: 0,
                  quarter: 0,
                  year: 0,
                }}
                disableQuickActions={true}
                maxDays={MAX_DAYS}
                defaultRange="today"
              />
              <Info />
            </Group>
            <CustomCard
              title={`Combiner Output Distribution${
                startRequest && endRequest
                  ? ` (${start?.format('MM-DD-YYYY')} 11:30AM - 12:30PM)`
                  : ': Real-Time'
              }`}
              style={{ flex: 1 }}
              headerChildren={
                <Checkbox
                  label="Normalize by Combiner Power"
                  checked={checked}
                  onChange={(event) => setChecked(event.currentTarget.checked)}
                />
              }
            >
              <PlotlyPlot
                key={`combiner-${checked ? 'normalized' : 'raw'}-${startRequest}-${endRequest}`}
                data={
                  data.data && [
                    {
                      x: data.data.x,
                      y: checked ? data.data.y_norm : data.data.y,
                      type: 'bar',
                    },
                  ]
                }
                layout={{
                  yaxis: {
                    title: {
                      text: checked ? 'Current/Power (A/kW)' : 'Current (A)',
                    },
                  },
                }}
                isLoading={data.isLoading}
                error={data.error}
                onClick={(event) => {
                  const xValue = event.points[0]?.x
                  if (xValue) {
                    const deviceId = deviceMapping[xValue as string]
                    const newSearchParams = new URLSearchParams(searchParams)
                    newSearchParams.set('deviceId', deviceId)
                    navigate(
                      `/projects/${projectId}/equipment-analysis/pv-dc-combiner/block?${newSearchParams.toString()}`,
                    )
                  }
                }}
              />
            </CustomCard>
          </Stack>
        </Tabs.Panel>

        {isSuperadmin && (
          <Tabs.Panel value="long-term" pt="md">
            <Text c="dimmed">
              This page is still under development and is only visible to
              superadmins. The long-term PV DC Combiner performance view needs
              to be created.
            </Text>
          </Tabs.Panel>
        )}
      </Tabs>
    </Stack>
  )
}

const Info = () => {
  return (
    <HoverCard width={500}>
      <HoverCard.Target>
        <IconInfoCircle />
      </HoverCard.Target>
      <HoverCard.Dropdown>
        <Text size="sm">
          Select an option from the dropdown to see more details for that block.
        </Text>
        <Text size="sm">
          Select a date to see the combiner output distribution for that period,
          otherwise the real-time data will be shown.
        </Text>
      </HoverCard.Dropdown>
    </HoverCard>
  )
}

export default EquipmentAnalysisPVDCCombinerPage
