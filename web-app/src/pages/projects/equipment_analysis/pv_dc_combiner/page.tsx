import { useGetBlockDropdown } from '@/api/ui'
import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import BlockDropdown from '@/components/BlockDropdown'
import CustomCard from '@/components/CustomCard'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useGetDevicesV2, useGetEquipmentAnalysisCombiner } from '@/hooks/api'
import { useProjectFilter } from '@/hooks/custom'
import { Device } from '@/hooks/types'
import { Checkbox, Group, HoverCard, Stack, Text } from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'
import { useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router'

const MAX_DAYS = 1

const Page = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeId.PV, ProjectTypeId.PV_BESS],
  })

  const navigate = useNavigate()
  const { projectId } = useParams<{ projectId: string }>()
  const [searchParams] = useSearchParams()
  const [checked, setChecked] = useState(false)

  // Handle block dropdown change
  const handleBlockDropdownChange = (value: string | null) => {
    if (value) {
      const newSearchParams = new URLSearchParams(searchParams)
      newSearchParams.set('deviceId', value)
      newSearchParams.set('tab', 'pv-dc-combiner')
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
    devicesMap: Record<string, any>,
  ) => {
    let currentDevice = devicesMap[deviceId]
    while (currentDevice && currentDevice.device_type_id !== 2) {
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
      deviceMapping[device.name_long] = parentId
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

  return (
    <Stack p="md" h="100%">
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
              title: { text: checked ? 'Current/Power (A/kW)' : 'Current (A)' },
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
              newSearchParams.set('tab', 'pv-dc-combiner')
              navigate(
                `/projects/${projectId}/equipment-analysis/pv-dc-combiner/block?${newSearchParams.toString()}`,
              )
            }
          }}
        />
      </CustomCard>
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
