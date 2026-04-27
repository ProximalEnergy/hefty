import { useGetUserType } from '@/api/admin'
import {
  DeviceTypeEnum,
  ProjectTypeEnum,
  SensorTypeEnum,
  UserTypeEnumEnum,
} from '@/api/enumerations'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetEquipmentAnalysisBESS } from '@/api/v1/protected/web-application/projects/equipment-analysis/bess'
import CustomCard from '@/components/CustomCard'
import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useProjectFilter } from '@/hooks/custom'
import { useResizePlotlyCharts } from '@/hooks/useResizePlotlyCharts'
import RealTime from '@/pages/projects/device_details/RealTime'
import { sortAndColorDevices } from '@/utils/colors'
import { Stack, Tabs, Text } from '@mantine/core'
import { useMemo, useRef } from 'react'
import { useParams, useSearchParams } from 'react-router'

const MAX_DAYS = 7

const EquipmentAnalysisBESSPage = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeEnum.BESS, ProjectTypeEnum.PVS],
  })

  const { projectId } = useParams<{ projectId: string }>()
  const userType = useGetUserType({})
  const isSuperadmin =
    userType.data?.user_type_id === UserTypeEnumEnum.SUPERADMIN

  const project = useSelectProject(projectId!)
  const [searchParams, setSearchParams] = useSearchParams()
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

  const { start, end } = useValidateDateRange({
    maxDays: MAX_DAYS,
  })

  let startRequest, endRequest
  if (project.data) {
    startRequest = start && start.tz(project.data.time_zone, true).toISOString()
    endRequest = end && end.tz(project.data.time_zone, true).toISOString()
  }

  const data = useGetEquipmentAnalysisBESS({
    pathParams: { project_id: projectId || '-1' },
    queryParams: {
      start: startRequest || '',
      end: endRequest || '',
    },
    queryOptions: { enabled: !!projectId && !!startRequest && !!endRequest },
  })

  // Must stay before early returns to satisfy hooks rules.
  useResizePlotlyCharts({
    containerRef: tabPanelRef,
    enabled: activeTab === 'current-day',
  })

  // Project data loading
  if (project.isLoading) {
    return <PageLoader />
  }

  // Project data error
  if (project.error) {
    return <PageError error={project.error} />
  }

  return (
    <Stack p="md" h="100%">
      <PageTitle>BESS Performance</PageTitle>
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
            initialDeviceTypeId={DeviceTypeEnum.BESS_STRING}
            restrictToDeviceTypeId={DeviceTypeEnum.BESS_STRING}
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
            <AdvancedDatePicker
              includeClearButton={false}
              includeTodayInDateRange
              limits={{
                day: 7,
                week: 1,
                month: 0,
                quarter: 0,
                year: 0,
              }}
              maxDays={MAX_DAYS}
              disableQuickActions
              defaultRange="past-3-days"
            />
            {/* {project.data?.has_bess_enclosures && ( */}
            {project.data?.spec?.used_device_type_ids?.includes(
              DeviceTypeEnum.BESS_ENCLOSURE,
            ) &&
              project.data?.spec?.used_sensor_type_ids?.includes(
                SensorTypeEnum.BESS_ENCLOSURE_SOC_PERCENT,
              ) && (
                <CustomCard title="BESS DC Enclosure" style={{ flex: 1 }}>
                  <PlotlyPlot
                    data={
                      data.data?.bess_enclosure &&
                      sortAndColorDevices(data.data.bess_enclosure).map(
                        (d) => ({
                          x: d.x,
                          y: d.y,
                          name: d.name,
                          line: { color: d.color },
                        }),
                      )
                    }
                    layout={{
                      yaxis: {
                        title: { text: 'SOC (%)' },
                        tickformat: ',.0%',
                        range: [0, 1],
                      },
                    }}
                    isLoading={data.isLoading}
                    error={data.error}
                  />
                </CustomCard>
              )}

            {project.data?.spec?.used_device_type_ids?.includes(
              DeviceTypeEnum.BESS_DC_SKID,
            ) &&
              project.data?.spec?.used_sensor_type_ids?.includes(
                SensorTypeEnum.BESS_DC_SKID_SOC_PERCENT,
              ) && (
                <CustomCard title="BESS DC Skid" style={{ flex: 1 }}>
                  <PlotlyPlot
                    data={
                      data.data?.bess_dc_skid &&
                      sortAndColorDevices(data.data.bess_dc_skid).map((d) => ({
                        x: d.x,
                        y: d.y,
                        name: d.name,
                        line: { color: d.color },
                      }))
                    }
                    layout={{
                      yaxis: {
                        title: { text: 'SOC (%)' },
                        tickformat: ',.0%',
                        range: [0, 1],
                      },
                    }}
                    isLoading={data.isLoading}
                    error={data.error}
                  />
                </CustomCard>
              )}

            {project.data?.spec?.used_device_type_ids?.includes(
              DeviceTypeEnum.BESS_BANK,
            ) &&
              project.data?.spec?.used_sensor_type_ids?.includes(
                SensorTypeEnum.BESS_BANK_SOC_PERCENT,
              ) && (
                <CustomCard title="BESS Bank" style={{ flex: 1 }}>
                  <PlotlyPlot
                    data={
                      data.data?.bess_bank &&
                      sortAndColorDevices(data.data.bess_bank).map((d) => ({
                        x: d.x,
                        y: d.y,
                        name: d.name,
                        line: { color: d.color },
                      }))
                    }
                    layout={{
                      yaxis: {
                        title: { text: 'SOC (%)' },
                        tickformat: ',.0%',
                        range: [0, 1],
                      },
                    }}
                    isLoading={data.isLoading}
                    error={data.error}
                  />
                </CustomCard>
              )}

            {project.data?.spec?.used_device_type_ids?.includes(
              DeviceTypeEnum.BESS_STRING,
            ) &&
              project.data?.spec?.used_sensor_type_ids?.includes(
                SensorTypeEnum.BESS_STRING_SOC_PERCENT,
              ) && (
                <CustomCard title="BESS String" style={{ flex: 1 }}>
                  <PlotlyPlot
                    data={
                      data.data?.bess_string &&
                      sortAndColorDevices(data.data.bess_string).map((d) => ({
                        x: d.x,
                        y: d.y,
                        name: d.name,
                        line: { color: d.color },
                      }))
                    }
                    layout={{
                      yaxis: {
                        title: { text: 'SOC (%)' },
                        tickformat: ',.0%',
                        range: [0, 1],
                      },
                    }}
                    isLoading={data.isLoading}
                    error={data.error}
                  />
                </CustomCard>
              )}
          </Stack>
        </Tabs.Panel>

        {isSuperadmin && (
          <Tabs.Panel value="long-term" pt="md">
            <Text c="dimmed">
              This tab and page are still under development and are only visible
              to superadmins. The long-term DC String performance view needs to
              be created.
            </Text>
          </Tabs.Panel>
        )}
      </Tabs>
    </Stack>
  )
}

export default EquipmentAnalysisBESSPage
