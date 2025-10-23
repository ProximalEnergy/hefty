import { useGetTrackingAngles } from '@/api/v1/analytics/tracking-angles'
import { useGetTimeSeries } from '@/api/v1/operational/project/project_data'
import { useGetProject } from '@/api/v1/operational/projects'
import CustomCard from '@/components/CustomCard'
import EventGISCard from '@/components/EventGISCard'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import {
  useGetDevicesV2,
  useGetEvents,
  useGetFailureModes,
  useGetGISTrackerByBlock,
} from '@/hooks/api'
import DeviceEventsTimeline from '@/pages/projects/events/DeviceEventsTimeline'
import {
  Alert,
  Button,
  Card,
  Collapse,
  Group,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { Shape } from 'plotly.js'
import React, { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

dayjs.extend(utc)
dayjs.extend(timezone)

const TrackerRowDetail = React.memo(() => {
  const [showSiblings, setShowSiblings] = useState(false)
  const { projectId, deviceId } = useParams()
  const navigate = useNavigate()

  // Get all devices to find parent and siblings
  const { data: devices, isLoading } = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: [28, 29],
    },
    queryOptions: {
      staleTime: Infinity,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
    },
  })
  const failureModes = useGetFailureModes({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: { enabled: !!projectId },
  })

  useEffect(() => {
    if (!deviceId && !isLoading && devices && devices.length > 0) {
      const randomDevice = devices[Math.floor(Math.random() * devices.length)]
      navigate(
        `/projects/${projectId}/device-details/tracker-row/${randomDevice.device_id}${window.location.search}`,
        {
          replace: true,
        },
      )
    }
  }, [devices, isLoading, deviceId, projectId, navigate])

  const device = devices?.find((d) => d.device_id.toString() === deviceId)
  const parentDevice = device?.parent_device_id
    ? devices?.find((d) => d.device_id === device.parent_device_id)
    : undefined
  const siblingDevices = devices
    ?.filter(
      (d) =>
        d.parent_device_id === device?.parent_device_id &&
        d.device_id !== device?.device_id,
    )
    .sort((a, b) => (a.name_short || '').localeCompare(b.name_short || ''))

  // Get project data for timezone
  const { data: project } = useGetProject({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: {
      staleTime: Infinity, // Never expires
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
    },
  })

  const { start: urlStart, end: urlEnd } = useValidateDateRange({
    maxDays: 30, // Limit to 30 days max
  })

  // If no dates in URL, use last 7 days
  const start = urlStart || dayjs().subtract(7, 'days').startOf('day')
  const end = urlEnd || dayjs().endOf('day')

  // Format dates for API
  const startQuery = start.format('YYYY-MM-DD HH:mm:ss')
  const endQuery = end.format('YYYY-MM-DD HH:mm:ss')

  // Fetch time series data for position and setpoint
  const {
    data: timeSeriesData,
    isLoading: isTimeSeriesLoading,
    error: timeSeriesError,
  } = useGetTimeSeries({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_ids: deviceId ? [parseInt(deviceId)] : undefined,
      sensor_type_name_shorts: ['tracker_position', 'tracker_setpoint'],
      start: startQuery,
      end: endQuery,
    },
    queryOptions: {
      staleTime: Infinity, // Never expires
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
    },
  })

  // Fetch true tracking angles
  const { data: trueTrackingData, isLoading: isTrackingLoading } =
    useGetTrackingAngles({
      pathParams: { projectId: projectId || '-1' },
      queryParams: {
        start: startQuery,
        end: endQuery,
      },
      queryOptions: {
        staleTime: Infinity, // Never expires
        refetchOnWindowFocus: false,
        refetchOnMount: false,
        refetchOnReconnect: false,
      },
    })

  // Fetch device events
  const { data: events, isLoading: isEventsLoading } = useGetEvents({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_id: deviceId?.toString(), // Convert deviceId to string
      open: false, // Include both open and closed events
    },
    queryOptions: {
      staleTime: Infinity, // Never expires
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      enabled: !!deviceId, // Only fetch when we have deviceId
    },
  })

  // Add this query to get GIS data for the block
  const { data: gisData } = useGetGISTrackerByBlock({
    pathParams: {
      projectId: projectId || '-1',
      blockId: parentDevice?.device_id.toString() || '-1',
    },
    queryParams: {
      start: start.format('YYYY-MM-DD'),
      end: end.format('YYYY-MM-DD'),
    },
    queryOptions: {
      enabled: !!projectId && !!parentDevice?.device_id && !!start && !!end,
    },
  })

  // Prepare time series plot data
  const plotData = React.useMemo(() => {
    if (!project?.time_zone) return []
    const data = []

    // Handle position and setpoint data
    if (timeSeriesData && timeSeriesData.length >= 2) {
      // Position data
      if (timeSeriesData[0] && timeSeriesData[0].x && timeSeriesData[0].y) {
        data.push({
          x: timeSeriesData[0].x,
          y: timeSeriesData[0].y,
          name: 'Position',
          type: 'scatter' as const,
          mode: 'lines' as const,
          hoverlabel: { namelength: -1 },
        })
      }

      // Setpoint data
      if (timeSeriesData[1] && timeSeriesData[1].x && timeSeriesData[1].y) {
        data.push({
          x: timeSeriesData[1].x,
          y: timeSeriesData[1].y,
          name: 'Setpoint',
          type: 'scatter' as const,
          mode: 'lines' as const,
          hoverlabel: { namelength: -1 },
        })
      }
    }

    // True tracking angle data
    if (
      trueTrackingData &&
      trueTrackingData.times &&
      trueTrackingData.tracker_theta
    ) {
      data.push({
        x: trueTrackingData.times,
        y: trueTrackingData.tracker_theta,
        name: 'Ideal Angle',
        type: 'scatter' as const,
        mode: 'lines' as const,
        line: { dash: 'dash' as const, color: 'green' },
        hoverlabel: { namelength: -1 },
      })
    }
    return data
  }, [timeSeriesData, trueTrackingData, project?.time_zone])

  const plotLayout = React.useMemo(() => {
    const shapes: Partial<Shape>[] =
      events?.map((event) => ({
        type: 'rect' as const, // Add type assertion here
        x0: dayjs
          .utc(event.time_start)
          .tz(project?.time_zone)
          .format('YYYY-MM-DDTHH:mm:ssZ'),
        x1: event.time_end
          ? dayjs
              .utc(event.time_end)
              .tz(project?.time_zone)
              .format('YYYY-MM-DDTHH:mm:ssZ')
          : timeSeriesData?.[0]?.x?.[timeSeriesData[0].x.length - 1]
            ? dayjs
                .utc(timeSeriesData[0].x[timeSeriesData[0].x.length - 1])
                .tz(project?.time_zone)
                .format('YYYY-MM-DDTHH:mm:ssZ')
            : end.format('YYYY-MM-DDTHH:mm:ssZ'),
        y0: 0,
        y1: 1,
        xref: 'x',
        yref: 'paper',
        fillcolor: 'rgba(255, 0, 0, 0.3)',
        line: { width: 0 },
      })) || []

    // Create annotations for events
    const annotations =
      events?.map((event) => ({
        x: dayjs
          .utc(event.time_start)
          .tz(project?.time_zone)
          .format('YYYY-MM-DDTHH:mm:ssZ'),
        y: 0.9,
        text: `Event ${event.event_id}`,
        showarrow: true,
        arrowhead: 2,
        arrowsize: 1,
        arrowwidth: 1,
        ax: 0,
        ay: -40,
        font: { size: 12, color: '#fff' },
        bgcolor: 'rgba(0,0,0,0.7)',
        bordercolor: 'rgba(255,255,255,0.3)',
        borderwidth: 1,
        borderpad: 4,
        captureevents: true,
        xref: 'x' as const,
        yref: 'paper' as const,
      })) || []

    return {
      xaxis: {
        range: [
          start.format('YYYY-MM-DDTHH:mm:ssZ'),
          end.format('YYYY-MM-DDTHH:mm:ssZ'),
        ],
      },
      yaxis: {
        title: { text: 'Angle (degrees)' },
        range: [-90, 90], // Fixed range for tracker angles
      },
      shapes: shapes,
      annotations: annotations,
      // Enable click events on annotations
      hovermode: 'closest' as const,
    }
  }, [start, end, events, timeSeriesData, project?.time_zone])

  return (
    <Stack p="md">
      <Title order={1}>Tracker Row Detail</Title>

      {/* Device Info Header and Map in a 50/50 split */}
      <Group grow align="flex-start">
        <Card padding="sm" radius="md" withBorder>
          <Stack p="md">
            <div>
              <Title order={3}>Tracker Row: {device?.name_long}</Title>
              <Text size="sm" c="dimmed">
                Device ID: {deviceId}
              </Text>
            </div>

            {parentDevice && (
              <div>
                <Text fw={500}>Parent Tracker Zone</Text>
                <Text size="sm" c="blue">
                  {parentDevice.name_long}
                </Text>
              </div>
            )}

            {siblingDevices && siblingDevices.length > 0 && (
              <div>
                <Group align="center">
                  <Text fw={500}>Other Rows in this Zone</Text>
                  <Button
                    variant="subtle"
                    size="xs"
                    onClick={() => setShowSiblings(!showSiblings)}
                  >
                    {showSiblings ? 'Hide' : 'Show'} ({siblingDevices.length})
                  </Button>
                </Group>
                <Collapse in={showSiblings}>
                  <Group gap="xs">
                    {siblingDevices.map((sibling) => (
                      <Link
                        key={sibling.device_id}
                        to={`/projects/${projectId}/device-details/tracker-row/${
                          sibling.device_id
                        }?start=${start.format('YYYY-MM-DD')}&end=${end
                          .subtract(1, 'day')
                          .format('YYYY-MM-DD')}`}
                        style={{ textDecoration: 'none' }}
                      >
                        <Text size="sm" c="blue">
                          {sibling.name_short}
                        </Text>
                      </Link>
                    ))}
                  </Group>
                </Collapse>
              </div>
            )}
          </Stack>
        </Card>

        {/* Location Card */}
        <CustomCard title="Location" fill={true}>
          <div style={{ height: '176px' }}>
            {/* Delay rendering of the map component by using a condition */}
            {timeSeriesData && (
              <EventGISCard
                deviceId={deviceId ? parseInt(deviceId) : '-1'}
                additionalGeoJson={gisData}
                zoom={17}
              />
            )}
          </div>
        </CustomCard>
      </Group>

      {/* Time Series Plot */}
      <CustomCard
        title="Tracker Position Analysis"
        headerChildren={
          <Group>
            <AdvancedDatePicker
              size="xs"
              maxDays={30}
              defaultRange="past-week"
              includeTodayInDateRange={true}
              includeClearButton={false}
            />
          </Group>
        }
        style={{ height: '500px' }}
      >
        {timeSeriesError ? (
          <Alert color="red" title="Error loading time series data">
            {timeSeriesError.message}
          </Alert>
        ) : (
          <PlotlyPlot
            data={plotData}
            layout={plotLayout}
            isLoading={isTimeSeriesLoading || isTrackingLoading}
          />
        )}
      </CustomCard>

      {/* Events Timeline */}
      <CustomCard title="Events">
        {events && events.length > 0 ? (
          <DeviceEventsTimeline
            isLoading={isEventsLoading}
            events={events}
            failureModes={failureModes.data || []}
            projectId={projectId || ''}
            selectedEvent={events[0]}
            tickets={[]}
          />
        ) : (
          <Text c="dimmed">No events found for this device</Text>
        )}
      </CustomCard>
    </Stack>
  )
})

export default TrackerRowDetail
