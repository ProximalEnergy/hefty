import { useGetUserType } from '@/api/admin'
import {
  DeviceTypeEnum,
  ProjectTypeEnum,
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
import RealTime from '@/pages/projects/device_details/RealTime'
import { Stack, Tabs, Text } from '@mantine/core'
import Plotly from 'plotly.js/dist/plotly-custom.min.js'
import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router'

const MAX_DAYS = 7

const Page = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeEnum.BESS, ProjectTypeEnum.PVS],
  })

  const { projectId } = useParams<{ projectId: string }>()
  const userType = useGetUserType({})
  const isSuperadmin =
    userType.data?.user_type_id === UserTypeEnumEnum.SUPERADMIN

  const project = useSelectProject(projectId!)
  const [activeTab, setActiveTab] = useState<string>('current-day')
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
            {project.data?.has_bess_enclosures && (
              <CustomCard title="BESS DC Enclosure" style={{ flex: 1 }}>
                <PlotlyPlot
                  data={
                    data.data?.bess_enclosure &&
                    data.data.bess_enclosure.map((d) => ({
                      x: d.x,
                      y: d.y,
                      name: d.name,
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

            {project.data?.has_bess_banks && (
              <CustomCard title="BESS Bank" style={{ flex: 1 }}>
                <PlotlyPlot
                  data={
                    data.data?.bess_bank &&
                    data.data.bess_bank.map((d) => ({
                      x: d.x,
                      y: d.y,
                      name: d.name,
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

            {project.data?.has_bess_strings && (
              <CustomCard title="BESS String" style={{ flex: 1 }}>
                <PlotlyPlot
                  data={
                    data.data?.bess_string &&
                    data.data.bess_string.map((d) => ({
                      x: d.x,
                      y: d.y,
                      name: d.name,
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

export default Page
