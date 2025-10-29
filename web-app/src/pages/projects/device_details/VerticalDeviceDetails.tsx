import { useGetProject } from '@/api/v1/operational/projects'
import {
  useGetDeviceDetailsVertical,
  useGetDeviceDetailsVerticalController,
} from '@/api/v1/protected/web-application/projects/device-details/vertical'
import CustomCard from '@/components/CustomCard'
import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useProjectDropdownToggle } from '@/hooks/custom'
import { ActionIcon, Button, Group, Stack, Tooltip } from '@mantine/core'
import { useViewportSize } from '@mantine/hooks'
import { IconArrowBackUp, IconPlus, IconX } from '@tabler/icons-react'
import type { Layout, PlotMouseEvent, PlotRelayoutEvent } from 'plotly.js'
import React, { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'

const ICON_STROKE = 1.5
const MAX_DAYS = 7
const THRESHOLD_HEIGHT = 300
const FIXED_PAPER_HEIGHT = THRESHOLD_HEIGHT - 50

const simpleLineLayout: Partial<Layout> = {
  margin: { l: 30, r: 10, t: 10, b: 30 },
}

const VerticalDeviceDetails = () => {
  useProjectDropdownToggle()

  // Path and search params
  const { projectId } = useParams()
  const [searchParams] = useSearchParams()

  // Viewport height, to be used for card rendering
  const { height: viewportHeight } = useViewportSize()

  // State
  const [selectedDeviceTypes, setSelectedDeviceTypes] = useState<number[]>([])
  const [sharedXRange, setSharedXRange] = useState<
    [string, string] | undefined
  >(undefined)
  const [controllerData, setControllerData] =
    useState<ReturnType<typeof useGetDeviceDetailsVerticalController>['data']>(
      undefined,
    )

  // --- Start data fetching ---
  // Fetch project data
  const project = useGetProject({
    pathParams: { projectId: projectId || '-1' },
  })

  // Fetch controller data
  const device_id = searchParams.get('device_id')
  const controller = useGetDeviceDetailsVerticalController({
    pathParams: {
      projectId: projectId || '',
      device_id: device_id || '',
    },
    queryParams: {},
  })
  // --- End data fetching ---

  // Validate date range
  const { start, end } = useValidateDateRange({
    maxDays: MAX_DAYS,
  })

  // Convert date range to ISO strings
  let startRequest, endRequest
  if (project.data) {
    startRequest = start && start.tz(project.data.time_zone, true).toISOString()
    endRequest = end && end.tz(project.data.time_zone, true).toISOString()
  }

  // Update state when the controller data is loaded in
  useEffect(() => {
    if (controller.data) {
      // Initialize controllerData to keep track of selected devices
      setControllerData(controller.data)

      // Set selectedDeviceTypes to the initially requested device type
      setSelectedDeviceTypes(
        controller.data.device_tree
          .filter((d) => d.initially_requested)
          .map((d) => d.id),
      )
    }
  }, [controller.data])

  // Helper to add a device type and keep selection ordered
  const addDeviceType = (device_type_id: number) => {
    if (!controllerData) return
    setSelectedDeviceTypes((prev) =>
      [...prev, device_type_id].sort(
        (a, b) =>
          controllerData?.device_tree.findIndex((d) => d.id === Number(a)) -
          controllerData?.device_tree.findIndex((d) => d.id === Number(b)),
      ),
    )
    // Reset the x-axis range to avoid auto range bug
    setSharedXRange(undefined)
  }

  // Helper to remove a device type
  const removeDeviceType = (device_type_id: number) => {
    setSelectedDeviceTypes((prev) => prev.filter((d) => d !== device_type_id))
  }

  // Handler for plot resizing
  const handleRelayout = useCallback((event: Partial<PlotRelayoutEvent>) => {
    if (
      event['xaxis.range[0]'] !== undefined &&
      event['xaxis.range[1]'] !== undefined
    ) {
      setSharedXRange([
        event['xaxis.range[0]'].toString(),
        event['xaxis.range[1]'].toString(),
      ])
    } else if (event['xaxis.autorange']) {
      setSharedXRange(undefined)
    }
  }, [])

  // Determine if the cards should be in fill mode
  // When in fill mode, they will take up the full height of the viewport
  // When not in fill mode, they will be a fixed height
  const isFillMode =
    viewportHeight / selectedDeviceTypes.length > THRESHOLD_HEIGHT

  const AddButton = ({
    device_type_id,
    label,
  }: {
    device_type_id: number
    label: string
  }) => {
    return (
      <Button
        onClick={() => addDeviceType(device_type_id)}
        variant="default"
        size="compact-xs"
        leftSection={<IconPlus size={12} stroke={ICON_STROKE} />}
      >
        {label}
      </Button>
    )
  }

  // Build the UI: for each device, if selected, render; if not, collect add buttons for missing devices in the right spot.
  const elements: React.ReactNode[] = []
  let lastIdx = -1
  if (controllerData) {
    for (let i = 0; i < controllerData?.device_tree.length; i++) {
      const device_type = controllerData?.device_tree[i]

      if (selectedDeviceTypes.includes(device_type.id)) {
        // If there are missing device types between lastIdx and i, group add buttons for them
        const addButtons: React.ReactNode[] = []
        for (let j = lastIdx + 1; j < i; j++) {
          const missingDeviceType = controllerData?.device_tree[j]
          addButtons.push(
            <AddButton
              key={`add-${missingDeviceType.id}`}
              device_type_id={missingDeviceType.id}
              label={missingDeviceType.label}
            />,
          )
        }

        if (addButtons.length > 0) {
          elements.push(
            <Group
              key={`add-group-${lastIdx + 1}-${i - 1}`}
              justify="center"
              w="100%"
            >
              {addButtons}
            </Group>,
          )
        }

        // Render the selected device as a DeviceCard
        elements.push(
          <DeviceTypeCard
            key={device_type.id}
            label={device_type.label}
            onRemove={() => removeDeviceType(device_type.id)}
            layout={simpleLineLayout}
            xaxisRange={sharedXRange}
            onRelayout={handleRelayout}
            isFillMode={isFillMode}
            device_ids={device_type.device_ids}
            start={startRequest || ''}
            end={endRequest || ''}
            selectedCards={selectedDeviceTypes.length}
          />,
        )
        lastIdx = i
      }
    }

    // Add buttons for any device types after the last selected
    const trailingAddButtons: React.ReactNode[] = []
    for (let j = lastIdx + 1; j < controllerData?.device_tree.length; j++) {
      const missingDeviceType = controllerData?.device_tree[j]
      trailingAddButtons.push(
        <AddButton
          key={`add-${missingDeviceType.id}`}
          device_type_id={missingDeviceType.id}
          label={missingDeviceType.label}
        />,
      )
    }

    if (trailingAddButtons.length > 0) {
      elements.push(
        <Group key={`add-group-trailing`} justify="center" w="100%">
          {trailingAddButtons}
        </Group>,
      )
    }
  }

  // If project or controller data is loading, show a loading spinner
  if (project.isLoading || controller.isLoading) {
    return <PageLoader />
  }

  // If there is an error, show an error message
  if (controller.error) {
    return <PageError error={controller.error} />
  }

  return (
    <Stack p="md" h={isFillMode ? '100%' : undefined} gap="md">
      <PageTitle info="View all device details under a single vertical. Add related devices using the + buttons. Click on any device trace to zoom in to its individual device details page.">
        Vertical Device Details
      </PageTitle>
      <Group>
        <AdvancedDatePicker
          defaultRange="past-3-days"
          includeTodayInDateRange
          includeClearButton={false}
          maxDays={MAX_DAYS}
        />
        <Link
          to={`/projects/${projectId}/device-details/horizontal/${controller.data?.device_technology}?${searchParams.toString()}`}
        >
          <Tooltip
            label="To horizontal device details"
            withArrow
            position="bottom"
          >
            <ActionIcon variant="light" size="input-sm">
              <IconArrowBackUp
                style={{ width: '70%', height: '70%' }}
                stroke={1.5}
              />
            </ActionIcon>
          </Tooltip>
        </Link>
      </Group>

      {elements}
    </Stack>
  )
}

function DeviceTypeCard({
  label,
  onRemove,
  layout,
  xaxisRange,
  onRelayout,
  isFillMode,
  device_ids,
  start,
  end,
  selectedCards,
}: {
  label: string
  onRemove: () => void
  layout: Partial<Layout>
  xaxisRange: [string, string] | undefined
  onRelayout: (event: Partial<PlotRelayoutEvent>) => void
  isFillMode: boolean
  device_ids: number[]
  start: string
  end: string
  selectedCards: number
}) {
  const navigate = useNavigate()
  const { projectId } = useParams()
  const [searchParams] = useSearchParams()

  const deviceDetails = useGetDeviceDetailsVertical({
    pathParams: { projectId: projectId || '' },
    queryParams: {
      device_ids: device_ids,
      start: start,
      end: end,
    },
  })

  const handlePlotClick = (event: PlotMouseEvent) => {
    const { points } = event

    if (points.length !== 1) {
      return
    }

    const deviceId = points[0].data.customdata[0]

    navigate(
      `/projects/${projectId}/device-details/single/${deviceId}?${searchParams.toString()}`,
    )
  }

  return (
    <CustomCard
      title={label}
      headerChildren={
        <ActionIcon
          color="red"
          variant="transparent"
          aria-label={`Remove ${label}`}
          onClick={onRemove}
          disabled={selectedCards === 1}
        >
          <IconX size={20} stroke={ICON_STROKE} />
        </ActionIcon>
      }
      style={{
        flex: isFillMode ? 1 : undefined,
        height: isFillMode ? undefined : FIXED_PAPER_HEIGHT,
      }}
    >
      <PlotlyPlot
        data={deviceDetails.data?.data.map((device) => ({
          x: deviceDetails.data?.times,
          y: device.values,
          name: device.name,
          type: 'scatter',
          mode: 'lines',
          customdata: [device.device_id],
        }))}
        layout={{
          ...layout,
          xaxis: {
            range: xaxisRange,
            autorange: xaxisRange === undefined ? true : false,
          },
          yaxis: {
            title: { text: deviceDetails.data?.layout.y_axis_label },
            tickformat:
              deviceDetails.data?.layout.y_axis_label === 'SOC'
                ? ',.0%'
                : undefined,
          },
          showlegend: true,
          hovermode: 'closest',
        }}
        onRelayout={onRelayout}
        isLoading={deviceDetails.isLoading}
        onClick={handlePlotClick}
        error={deviceDetails.error}
      />
    </CustomCard>
  )
}

export default VerticalDeviceDetails
