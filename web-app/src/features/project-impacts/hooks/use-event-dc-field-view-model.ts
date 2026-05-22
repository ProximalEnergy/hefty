import { DeviceTypeEnum } from '@/api/enumerations'
import { useGetFailureModes } from '@/api/v1/operational/failure_modes'
import { useGetCMMSTickets } from '@/api/v1/operational/project/cmms_tickets'
import { useGetEventLossesSummary } from '@/api/v1/operational/project/events'
import type { Project } from '@/api/v1/operational/projects'
import { useGetRootCauses } from '@/api/v1/operational/root_causes'
import { useGetUtilityExpected } from '@/api/v1/protected/pv-expected-energy/plot/plot'
import { useGetDevicesV2, useGetEvents, useUpdateRootCause } from '@/hooks/api'
import type { Event } from '@/hooks/types'
import { useMantineTheme } from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import type { Layout } from 'plotly.js'
import { useEffect, useMemo, useState } from 'react'
import type { EventLossesData } from '@/features/project-impacts/components/EventLosses'
import type { RootCause } from '@/features/project-impacts/types/project-impacts-types'
import { buildUpdateRootCauseHandler } from '@/features/project-impacts/utils/update-root-cause'
import { calculateMovingAverage } from '@/utils/movingAverage'

dayjs.extend(timezone)
dayjs.extend(utc)

type UseEventDCFieldViewModelProps = {
  event: Event
  eventId: number
  project: Project
  projectId: string
}

export function useEventDCFieldViewModel({
  event,
  eventId,
  project,
  projectId,
}: UseEventDCFieldViewModelProps) {
  const theme = useMantineTheme()
  const [showAllCauses, setShowAllCauses] = useState(false)
  const [selectedRootCause, setSelectedRootCause] = useState<number | null>(
    null,
  )
  const [opened, { close, open }] = useDisclosure(false)
  const projectTz = project.time_zone || 'UTC'
  const eventStartTime = dayjs(event.time_start).tz(projectTz)
  const eventEndTime = dayjs(event.time_end).tz(projectTz)
  const traceEnd = eventStartTime.add(2, 'days').endOf('day')

  const eventLossesSummary = useGetEventLossesSummary({
    pathParams: { projectId },
    queryParams: { event_id: eventId },
    queryOptions: { enabled: eventId > 0 && !!projectId },
  })
  const eventsHistorical = useGetEvents({
    pathParams: { projectId },
    queryParams: {
      device_ids: event.device_id ? [event.device_id] : undefined,
      open: false,
    },
    queryOptions: {
      enabled: !!event.device_id,
    },
  })
  const CMMSTickets = useGetCMMSTickets({
    pathParams: { project_id: projectId },
    queryParams: { device_ids: [event.device_id || -1] },
    queryOptions: { enabled: !!event.device_id },
  })
  const rootCauses = useGetRootCauses({})
  const failureModes = useGetFailureModes({})
  const devices = useGetDevicesV2({
    pathParams: { projectId },
    filters: {
      device_type_ids: [
        DeviceTypeEnum.METER,
        DeviceTypeEnum.PV_INVERTER,
        DeviceTypeEnum.PV_DC_COMBINER,
      ],
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })
  const dcCombinerDevice = devices.data?.find((device) => {
    return device.device_id === event.device?.parent_device_id
  })
  const expectedStart = eventStartTime.startOf('day')
  const expectedEnd = eventStartTime.add(2, 'days').endOf('day')
  const isExpectedPowerEnabled =
    !!dcCombinerDevice && !!expectedStart && !!expectedEnd
  const expectedPower = useGetUtilityExpected({
    pathParams: { projectId },
    queryParams: {
      device_id: dcCombinerDevice?.device_id || -1,
      start: expectedStart.tz(project.time_zone, true).toISOString(),
      end: expectedEnd.tz(project.time_zone, true).toISOString(),
      warranted_degradation: false,
    },
    queryOptions: {
      enabled: isExpectedPowerEnabled,
    },
  })
  const mutation = useUpdateRootCause()
  const updateRootCause = buildUpdateRootCauseHandler({
    eventId,
    projectId,
    mutate: mutation.mutate,
  })

  useEffect(() => {
    queueMicrotask(() => setSelectedRootCause(event.root_cause_id))
  }, [event.root_cause_id])

  const powerDifference =
    expectedPower.data?.expected_soiled?.difference ?? null
  const powerDifferenceMovingAverage = useMemo(() => {
    if (!powerDifference) return []
    return calculateMovingAverage(powerDifference, 20)
  }, [powerDifference])
  const losses: EventLossesData = {
    financial: {
      title: 'Daily Impact',
      value:
        eventLossesSummary.data?.loss_daily_financial != null
          ? eventLossesSummary.data.loss_daily_financial.toFixed(2)
          : 'N/A',
      unit: '$',
    },
    energetic: {
      title: '',
      value:
        eventLossesSummary.data?.loss_daily_energy != null
          ? eventLossesSummary.data.loss_daily_energy.toFixed(2)
          : 'N/A',
      unit: 'MWh',
    },
    capacity: {
      title: 'PV DC Capacity Loss',
      value:
        eventLossesSummary.data?.loss_capacity !== null &&
        eventLossesSummary.data?.loss_capacity !== undefined
          ? eventLossesSummary.data.loss_capacity.toFixed(2)
          : (event.device.capacity_dc || 0).toFixed(2),
      unit: 'kW DC',
    },
  }
  const plotData = [
    { yaxis: 'y' as const },
    ...(expectedPower.data && dcCombinerDevice
      ? [
          {
            x: expectedPower.data.times,
            y: expectedPower.data.actual.power,
            name: 'Actual Power (DC Combiner)',
            type: 'scatter' as const,
            fill: 'tozeroy' as const,
            fillcolor: 'rgba(0, 128, 0, 0.2)',
            line: { color: theme.colors.green[7], width: 2 },
            yaxis: 'y',
          },
          {
            x: expectedPower.data.times,
            y: expectedPower.data.expected_soiled.power,
            name: 'Expected Power (Soiled)',
            type: 'scatter' as const,
            line: { color: theme.colors.orange[6], width: 2 },
            yaxis: 'y',
          },
          {
            x: expectedPower.data.times,
            y: powerDifferenceMovingAverage,
            name: 'Power Difference (Soiled) - 20pt Moving Avg',
            type: 'scatter' as const,
            fill: 'tozeroy' as const,
            fillcolor: 'rgba(255, 0, 0, 0.2)',
            line: { color: theme.colors.red[6], width: 1 },
            yaxis: 'y',
          },
        ]
      : []),
  ]
  const plotLayout: Partial<Layout> = {
    shapes: [
      {
        type: 'rect',
        x0: eventStartTime.format('YYYY-MM-DD HH:mm:ss'),
        x1:
          eventEndTime.isValid() && eventEndTime <= traceEnd
            ? eventEndTime.format('YYYY-MM-DD HH:mm:ss')
            : traceEnd.format('YYYY-MM-DD HH:mm:ss'),
        y0: 0,
        y1: 1,
        xref: 'x',
        yref: 'paper',
        line: {
          width: 0,
        },
      },
    ],
    yaxis: {
      title: {
        text: 'Power (kW)',
      },
      side: 'left',
      showgrid: true,
      zeroline: false,
      automargin: true,
    },
    hoverlabel: {
      namelength: -1,
    },
  }

  return {
    closeRootCauseModal: close,
    failureModes: failureModes.data ?? [],
    historicalEvents: eventsHistorical.data ?? [],
    isTimelineLoading:
      eventsHistorical.isLoading ||
      rootCauses.isLoading ||
      CMMSTickets.isLoading,
    losses,
    openRootCauseModal: open,
    plotData,
    plotLayout,
    rootCauseDeviceTypes: [
      DeviceTypeEnum.DC_FIELD,
      DeviceTypeEnum.PV_INVERTER,
      DeviceTypeEnum.PV_DC_COMBINER,
    ],
    rootCauseModalOpened: opened,
    rootCauses: (rootCauses.data ?? []) as RootCause[],
    selectedRootCause,
    setSelectedRootCause,
    setShowAllCauses,
    showAllCauses,
    tickets: CMMSTickets.data?.data,
    updateRootCause,
    xAxisTimeZone: projectTz,
    isTracesLoading:
      !expectedPower.isError &&
      (!isExpectedPowerEnabled || expectedPower.isLoading),
  }
}
