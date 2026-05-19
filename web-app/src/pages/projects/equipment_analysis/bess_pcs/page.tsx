import { useGetUserType } from '@/api/admin'
import { ProjectTypeEnum, UserTypeEnum } from '@/api/enumerations'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetEquipmentAnalysisBESSPCS } from '@/api/v1/protected/web-application/projects/equipment-analysis/bess_pcs'
import CustomCard from '@/components/CustomCard'
import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useProjectFilter } from '@/hooks/custom'
import { useResizePlotlyCharts } from '@/hooks/useResizePlotlyCharts'
import { EquipmentHeader } from '@/pages/projects/equipment_analysis/bess_pcs/equipment-header'
import { Realtime } from '@/pages/projects/equipment_analysis/bess_pcs/realtime/realtime'
import { useEquipmentAnalysisTab } from '@/pages/projects/equipment_analysis/useEquipmentAnalysisTab'
import { sortAndColorDevices } from '@/utils/colors'
import { Stack, Tabs, Text } from '@mantine/core'
import { useRef } from 'react'
import { useParams } from 'react-router'

const MAX_DAYS = 7
const PAGE_INFO_BY_TAB = {
  realtime:
    'This tab provides a real-time view of BESS PCS power, voltage, ' +
    'temperature, and alarm data for the selected project.',
  'current-day':
    'This tab shows current-day BESS PCS power trends. Positive values ' +
    'indicate discharging, negative values indicate charging.',
  'long-term':
    'This tab is still under development and will provide long-term ' +
    'BESS PCS performance trends.',
} as const

const EquipmentAnalysisBESSPCSPage = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeEnum.BESS, ProjectTypeEnum.PVS],
  })

  const { projectId } = useParams<{ projectId: string }>()
  const userType = useGetUserType({})
  const isAdmin =
    userType.data?.user_type_id === UserTypeEnum.ADMIN ||
    userType.data?.user_type_id === UserTypeEnum.SUPERADMIN
  const isSuperadmin = userType.data?.user_type_id === UserTypeEnum.SUPERADMIN

  const project = useSelectProject(projectId!)
  const { activeTab, setTab } = useEquipmentAnalysisTab({
    isSuperadmin,
    defaultTab: 'realtime',
  })

  const tabPanelRef = useRef<HTMLDivElement>(null)
  const { start, end } = useValidateDateRange({
    maxDays: MAX_DAYS,
  })

  let startRequest, endRequest
  if (project.data) {
    startRequest = start?.tz(project.data.time_zone, true).toISOString()
    endRequest = end?.tz(project.data.time_zone, true).toISOString()
  }

  const data = useGetEquipmentAnalysisBESSPCS({
    pathParams: { project_id: projectId || '-1' },
    queryParams: {
      start: startRequest || '',
      end: endRequest || '',
    },
    queryOptions: {
      enabled: !!projectId && !!startRequest && !!endRequest,
    },
  })

  useResizePlotlyCharts({
    containerRef: tabPanelRef,
    enabled: activeTab === 'current-day',
  })

  const currentDayInfo =
    'Positive values indicate discharging, negative values indicate charging.'
  const pageInfo = PAGE_INFO_BY_TAB[activeTab]

  const currentDayPlotData =
    data.data &&
    sortAndColorDevices(data.data).map((device) => ({
      x: device.x,
      y: device.y,
      name: device.name,
      line: { color: device.color },
    }))

  if (project.isLoading) {
    return <PageLoader />
  }

  if (project.error) {
    return <PageError error={project.error} />
  }

  return (
    <Stack p="md" h="100%">
      <PageTitle info={pageInfo}>BESS PCS Performance</PageTitle>

      <EquipmentHeader
        projectId={projectId}
        isAdmin={isAdmin}
        placedInServiceDate={project.data?.placed_in_service_date}
        poi={project.data?.poi ?? null}
      />

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
          <Realtime />
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
            <CustomCard
              title="PCS Power"
              info={currentDayInfo}
              style={{ flex: 1 }}
            >
              <PlotlyPlot
                data={currentDayPlotData}
                layout={{
                  yaxis: {
                    title: { text: 'MW' },
                  },
                }}
                isLoading={data.isLoading}
                error={data.error}
              />
            </CustomCard>
          </Stack>
        </Tabs.Panel>

        {isSuperadmin && (
          <Tabs.Panel value="long-term" pt="md">
            <Text c="dimmed">
              This tab and page are still under development and are only visible
              to superadmins. The long-term BESS PCS performance view needs to
              be created.
            </Text>
          </Tabs.Panel>
        )}
      </Tabs>
    </Stack>
  )
}

export default EquipmentAnalysisBESSPCSPage
