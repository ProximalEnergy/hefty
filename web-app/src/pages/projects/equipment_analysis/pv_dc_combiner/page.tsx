import { useGetUserType } from '@/api/admin'
import {
  DeviceTypeEnum,
  ProjectTypeEnum,
  UserTypeEnumEnum,
} from '@/api/enumerations'
import { useGetBlockDropdown } from '@/api/ui'
import { useSelectProject } from '@/api/v1/operational/projects'
import BlockDropdown from '@/components/BlockDropdown'
import CustomCard from '@/components/CustomCard'
import { PageTitle } from '@/components/PageTitle'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useGetDevicesV2, useGetEquipmentAnalysisCombiner } from '@/hooks/api'
import { useProjectFilter } from '@/hooks/custom'
import { Device } from '@/hooks/types'
import RealTime from '@/pages/projects/device_details/RealTime'
import { Checkbox, Group, HoverCard, Stack, Tabs, Text } from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'
import Plotly from 'plotly.js/dist/plotly-custom.min.js'
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router'

const MAX_DAYS = 1

const Page = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeEnum.PV, ProjectTypeEnum.PVS],
  })

  const navigate = useNavigate()
  const { projectId } = useParams<{ projectId: string }>()
  const userType = useGetUserType({})
  const isSuperadmin =
    userType.data?.user_type_id === UserTypeEnumEnum.SUPERADMIN
  const [searchParams] = useSearchParams()
  const [checked, setChecked] = useState(false)
  const [activeTab, setActiveTab] = useState<string>('current-day')
  const tabPanelRef = useRef<HTMLDivElement>(null)

  // Handle block dropdown change
  const handleBlockDropdownChange = (value: string | null) => {
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
    filters: { device_type_ids: [9, 2, 3] },
  })

  // Helper function to find the parent device recursively
  const findParentDeviceId = (
    deviceId: string,
    devicesMap: Record<string, Device>,
  ) => {
    let currentDevice = devicesMap[deviceId]
    while (
      currentDevice &&
      currentDevice.device_type_id !== DeviceTypeEnum.PV_PCS &&
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
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: startRequest ?? undefined,
      end: endRequest ?? undefined,
    },
    queryOptions: { enabled: !!projectId },
  })

  // Resize Plotly charts when tab becomes active
  // Must be before early return to follow React hooks rules
  useEffect(() => {
    if (!tabPanelRef.current || activeTab !== 'current-day') return

    const resizeCharts = () => {
      // Find all Plotly plot elements within the active tab panel
      const plotElements = tabPanelRef.current?.querySelectorAll(
        '.js-plotly-plot',
      ) as NodeListOf<HTMLElement>

      if (plotElements && plotElements.length > 0) {
        // Resize each plot after a short delay to ensure container has dimensions
        setTimeout(() => {
          plotElements.forEach((plotElement) => {
            const rect = plotElement.getBoundingClientRect()
            // Only resize if the plot element has actual dimensions
            if (rect.width > 0 && rect.height > 0) {
              Plotly.Plots.resize(plotElement)
            }
          })
        }, 150)
      }
    }

    // Initial resize when tab becomes active
    resizeCharts()

    // Also set up an IntersectionObserver to detect when the tab panel becomes visible
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && entry.intersectionRatio > 0) {
            resizeCharts()
          }
        })
      },
      {
        threshold: 0.01,
      },
    )

    if (tabPanelRef.current) {
      observer.observe(tabPanelRef.current)
    }

    return () => {
      observer.disconnect()
    }
  }, [activeTab])

  return (
    <Stack p="md" h="100%">
      <PageTitle>PV DC Combiner Performance</PageTitle>
      <Tabs
        value={activeTab}
        onChange={(value) => setActiveTab(value || 'current-day')}
        defaultValue="current-day"
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
                onChange={handleBlockDropdownChange}
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

export default Page
