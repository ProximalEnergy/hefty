import { useGetUserType } from '@/api/admin'
import { UserTypeEnumEnum } from '@/api/enumerations'
import { useSelectProject } from '@/api/v1/operational/projects'
import CustomCard from '@/components/CustomCard'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import DeviceSunburst from '@/components/plots/DeviceSunburst'
import LossWaterfall from '@/components/plots/LossWaterfall'
import { LossWaterfallCardInfo } from '@/components/plots/LossWaterfallCardInfo'
import POIMeter from '@/components/plots/POIMeter'
import PowerPlantController from '@/components/plots/PowerPlantController'
import {
  ActionIcon,
  Group,
  Popover,
  SegmentedControl,
  Select,
  Stack,
  Switch,
  Tabs,
  Text,
} from '@mantine/core'
import { IconSettings } from '@tabler/icons-react'
import { PlotType } from 'plotly.js'
import Plotly from 'plotly.js/dist/plotly-custom.min.js'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useSearchParams } from 'react-router'

const SystemPerformance = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const [showLevel, setShowLevel] = useState('device_type')
  const [sunburstDepth, setSunburstDepth] = useState<string>('3')
  const [sunburstStyle, setSunburstStyle] = useState<PlotType>('sunburst')
  const [showGridHzV, setShowGridHzV] = useState(false)
  const project = useSelectProject(projectId!)
  const userType = useGetUserType({})
  const isSuperadmin =
    userType.data?.user_type_id === UserTypeEnumEnum.SUPERADMIN
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
  const { start, end } = useValidateDateRange({})

  // Compute showGridHzVSwitch before early return to use in useMemo
  const GRID_HZ_V_SENSOR_TYPE_IDS = [11, 192]
  const showGridHzVSwitch =
    (project.data?.spec.used_sensor_type_ids?.filter((id) =>
      GRID_HZ_V_SENSOR_TYPE_IDS.includes(id),
    ).length ?? 0) === GRID_HZ_V_SENSOR_TYPE_IDS.length || false

  // Reset showGridHzV to false when project doesn't support grid Hz/V
  // This ensures state doesn't persist incorrectly when switching projects
  // Must be called before any early returns (React hooks rules)
  const effectiveShowGridHzV = useMemo(() => {
    if (!showGridHzVSwitch) {
      return false
    }
    return showGridHzV
  }, [showGridHzV, showGridHzVSwitch])

  let startQuery: string | undefined = undefined
  let endQuery: string | undefined = undefined
  if (project.data) {
    if (start) {
      startQuery = start.tz(project.data.time_zone, true).toISOString()
    }
    if (end) {
      endQuery = end.tz(project.data.time_zone, true).toISOString()
    }
  }

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

  if (project.isLoading) return <PageLoader />

  const PPC_SENSOR_TYPE_IDS = [17, 18, 20, 21, 22, 23]
  const showPPCCard =
    project.data?.spec.used_sensor_type_ids?.some((id) =>
      PPC_SENSOR_TYPE_IDS.includes(id),
    ) || false

  const showLossWaterFall =
    project.data?.has_event_integration &&
    project.data?.has_expected_energy_integration

  const showSecondRow = showPPCCard || showLossWaterFall

  return (
    <Stack p="md" h="100%">
      <PageTitle>System Performance</PageTitle>
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
          {isSuperadmin && <Tabs.Tab value="realtime">Real-time</Tabs.Tab>}
          <Tabs.Tab value="current-day">Day View</Tabs.Tab>
          {isSuperadmin && <Tabs.Tab value="long-term">Long Term</Tabs.Tab>}
        </Tabs.List>

        {isSuperadmin && (
          <Tabs.Panel value="realtime" pt="md">
            <Text c="dimmed">
              This tab and page are still under development and are only visible
              to superadmins. The real-time System performance view needs to be
              created.
            </Text>
          </Tabs.Panel>
        )}

        <Tabs.Panel
          value="current-day"
          pt="md"
          ref={tabPanelRef}
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            minHeight: 0,
          }}
        >
          <Group
            flex={1}
            w="100%"
            align="stretch"
            style={{ flex: 1, minHeight: 0 }}
          >
            <CustomCard
              title="POI Meter"
              style={{ height: '100%', flex: 0.6 }}
              headerChildren={
                showGridHzVSwitch && (
                  <Switch
                    label="Grid Hz/V"
                    size="sm"
                    checked={effectiveShowGridHzV}
                    onChange={(event) =>
                      setShowGridHzV(event.currentTarget.checked)
                    }
                  />
                )
              }
              info={
                <>
                  This chart shows power being exported by the project. A lower
                  power factor could be causing a loss of system performance if
                  the grid is asking for reactive power. Power factor is a ratio
                  of real power (the power that does work) to apparent power
                  (the total power flowing in the circuit). When the power
                  factor is low, it means that a larger portion of the power is
                  reactive power, which does not perform useful work but is
                  required by the grid to maintain voltage levels.
                </>
              }
            >
              <POIMeter key={projectId} showGridHzV={effectiveShowGridHzV} />
            </CustomCard>
            <CustomCard
              title="System Device Health"
              style={{ height: '100%', flex: 0.4 }}
              info={
                <>
                  System Device Health is based on the hierarchical
                  relationships between devices.
                  <br />
                  &nbsp;&nbsp;&nbsp;&nbsp;
                  <Text span c="red">
                    Red
                  </Text>
                  : Device has an active Event.
                  <br />
                  &nbsp;&nbsp;&nbsp;&nbsp;
                  <Text span c="yellow">
                    Yellow
                  </Text>
                  : Device has a child with an active Event. This propagates all
                  the way up to the root device from any child.
                  <br />
                  &nbsp;&nbsp;&nbsp;&nbsp;
                  <Text span c="green">
                    Green
                  </Text>
                  : Device has no active Events.
                  <br />
                  Note: A child device can be colored green even when its parent
                  device is red. This is intentional — if a parent device has an
                  active Event causing a child device to go offline, the child
                  won&apos;t always show an active Event.
                </>
              }
              headerChildren={
                <Popover>
                  <Popover.Target>
                    <ActionIcon variant="default">
                      <IconSettings />
                    </ActionIcon>
                  </Popover.Target>
                  <Popover.Dropdown>
                    <Select
                      data={['2', '3', '4']}
                      label={'Plot Depth'}
                      value={sunburstDepth}
                      onChange={(value) => setSunburstDepth(value ?? '3')}
                    />
                    <Text>Plot Style:</Text>
                    <SegmentedControl
                      data={[
                        { label: 'Circular', value: 'sunburst' },
                        { label: 'Rectangular', value: 'icicle' },
                      ]}
                      value={sunburstStyle}
                      onChange={(value) => setSunburstStyle(value as PlotType)}
                    />
                  </Popover.Dropdown>
                </Popover>
              }
            >
              <DeviceSunburst
                depth={parseInt(sunburstDepth)}
                style={sunburstStyle}
              />
            </CustomCard>
          </Group>
          {showSecondRow && (
            <Group flex={1} w="100%" style={{ flex: 1, minHeight: 0 }} mt="md">
              {showPPCCard && (
                <CustomCard
                  title="Power Plant Controller"
                  style={{ height: '100%', flex: 1 }}
                >
                  <PowerPlantController />
                </CustomCard>
              )}
              {showLossWaterFall && (
                <CustomCard
                  headerChildren={
                    <>
                      <AdvancedDatePicker
                        includeClearButton={false}
                        includeTodayInDateRange
                        defaultRange="today"
                      />
                      <SegmentedControl
                        data={[
                          { label: 'Component', value: 'device_type' },
                          { label: 'Failure Mode', value: 'failure_mode' },
                        ]}
                        value={showLevel}
                        onChange={setShowLevel}
                      />
                    </>
                  }
                  title="Loss Waterfall"
                  info={<LossWaterfallCardInfo />}
                  style={{ height: '100%', flex: 1 }}
                >
                  <LossWaterfall
                    level={showLevel}
                    startQuery={startQuery || ''}
                    endQuery={endQuery || ''}
                  />
                </CustomCard>
              )}
            </Group>
          )}
        </Tabs.Panel>

        {isSuperadmin && (
          <Tabs.Panel value="long-term" pt="md">
            <Text c="dimmed">
              This tab and page are still under development and are only visible
              to superadmins. The long-term System performance view needs to be
              created.
            </Text>
          </Tabs.Panel>
        )}
      </Tabs>
    </Stack>
  )
}

export default SystemPerformance
