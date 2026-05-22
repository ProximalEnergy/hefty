import {
  DeviceTypeEnum,
  ProjectTypeEnum,
  SensorTypeEnum,
} from '@/api/enumerations'
import { useGetTrackingAngles } from '@/api/v1/analytics/tracking-angles'
import { useGetFailureModes } from '@/api/v1/operational/failure_modes'
import { useGetCMMSTickets } from '@/api/v1/operational/project/cmms_tickets'
import {
  useGetEventLossesSummary,
  useGetEventTraceTags,
} from '@/api/v1/operational/project/events'
import { useGetTimeSeries } from '@/api/v1/operational/project/project_data'
import { useGetStatusTimeSeries } from '@/api/v1/operational/project/project_status'
import type { Project } from '@/api/v1/operational/projects'
import { useGetRootCauses } from '@/api/v1/operational/root_causes'
import { traceColors } from '@/components/plots/PlotlyPlotUtils'
import { useGetEvents, useUpdateRootCause } from '@/hooks/api'
import type { Event } from '@/hooks/types'
import { QUERY_TIME } from '@/utils/queryTiming'
import { useDisclosure } from '@mantine/hooks'
import { useMantineTheme } from '@mantine/core'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import type { Dash, Layout } from 'plotly.js'
import { useEffect, useMemo, useState } from 'react'
import type {
  RootCause,
  StatusTimeSeriesTrace,
} from '@/features/project-impacts/types/project-impacts-types'
import { buildUpdateRootCauseHandler } from '@/features/project-impacts/utils/update-root-cause'
import type { EventLossesData } from '@/features/project-impacts/components/EventLosses'

dayjs.extend(timezone)
dayjs.extend(utc)

type UseEventGeneralViewModelProps = {
  event: Event
  eventId: number
  project: Project
  projectId: string
}

type EventPlotTrace = {
  x: string[]
  y: number[]
  name: string
  type: 'scatter'
  line: { color: string; dash: Dash }
  yaxis: string
  hoverlabel: {
    namelength: -1
  }
}

type EventPlotYAxis = {
  title: { text: string; font: { color: string } }
  side: 'left' | 'right'
  overlaying: string
  showgrid: boolean
  zeroline: boolean
  position: number
  anchor: 'free'
  autoshift: boolean
  tickformat?: string
}

const stringToInt = (str: string) => {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i)
    hash |= 0
  }
  return hash
}

const getRootCauseDeviceTypes = (event: Event, project: Project) => {
  const rootCauseDeviceTypes: number[] = [event.device.device_type_id || -1]
  if (
    project.has_pv_dc_combiners &&
    event.device.device_type_id === DeviceTypeEnum.PV_DC_COMBINER
  ) {
    rootCauseDeviceTypes.push(DeviceTypeEnum.DC_FIELD)
  } else if (
    !project.has_pv_dc_combiners &&
    event.device.device_type_id === DeviceTypeEnum.PV_INVERTER
  ) {
    rootCauseDeviceTypes.push(DeviceTypeEnum.DC_FIELD)
  }
  if (event.device.device_type_id === DeviceTypeEnum.PV_INVERTER_MODULE) {
    rootCauseDeviceTypes.push(DeviceTypeEnum.PV_INVERTER)
  }
  if (event.device.device_type_id === DeviceTypeEnum.TRACKER_ROW) {
    rootCauseDeviceTypes.push(DeviceTypeEnum.TRACKER_ROW)
  }
  if (event.device.device_type_id === DeviceTypeEnum.TRACKER_ZONE) {
    rootCauseDeviceTypes.push(DeviceTypeEnum.TRACKER_ZONE)
  }
  return rootCauseDeviceTypes
}

export function useEventGeneralViewModel({
  event,
  eventId,
  project,
  projectId,
}: UseEventGeneralViewModelProps) {
  const theme = useMantineTheme()
  const [showAllCauses, setShowAllCauses] = useState(false)
  const [selectedRootCause, setSelectedRootCause] = useState<number | null>(
    null,
  )
  const [opened, { close, open }] = useDisclosure(false)
  const projectTz = project.time_zone || 'UTC'
  const eventStartTime = dayjs(event.time_start).tz(projectTz)
  const eventEndTime = dayjs(event.time_end).tz(projectTz)

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
  const mutation = useUpdateRootCause()
  const updateRootCause = buildUpdateRootCauseHandler({
    eventId,
    projectId,
    mutate: mutation.mutate,
  })

  useEffect(() => {
    queueMicrotask(() => setSelectedRootCause(event.root_cause_id))
  }, [event.root_cause_id])

  const eventTraceTags = useGetEventTraceTags({
    pathParams: { projectId },
    queryParams: {
      device_id: event.device_id || -1,
    },
    queryOptions: { enabled: !!event.device_id },
  })

  const traceStart = dayjs(event.time_start)
    .tz(projectTz)
    .subtract(1, 'day')
    .startOf('day')
  const traceEnd = useMemo(() => {
    let end = dayjs(event.time_end).isValid()
      ? dayjs(event.time_end).tz(projectTz).endOf('day')
      : dayjs().tz(projectTz).endOf('day')
    if (end.diff(traceStart, 'days') > 3) {
      end = traceStart.add(3, 'days').endOf('day')
    }
    return end
  }, [event.time_end, projectTz, traceStart])

  const eventTraces = useGetTimeSeries({
    pathParams: { project_id: projectId },
    queryParams: {
      tag_ids: eventTraceTags.data?.map((tag) => tag.tag_id) || [],
      start: traceStart.toISOString(),
      end: traceEnd.toISOString(),
    },
    queryOptions: { enabled: !!eventTraceTags.data?.length },
  })
  const deviceIds = eventTraceTags.data?.map((tag) => tag.device_id ?? -1) ?? []
  const uniqueDeviceIds = Array.from(new Set(deviceIds))
  const statusTimeSeries = useGetStatusTimeSeries({
    pathParams: { project_id: projectId },
    queryParams: {
      device_ids: uniqueDeviceIds,
      start: traceStart.toISOString(),
      end: traceEnd.toISOString(),
    },
    queryOptions: { enabled: !!eventTraceTags.data?.length },
  })
  const trueTrackingData = useGetTrackingAngles({
    pathParams: { projectId },
    queryParams: {
      start: traceStart.format('YYYY-MM-DD HH:mm:ss'),
      end: traceEnd.format('YYYY-MM-DD HH:mm:ss'),
    },
    queryOptions: {
      staleTime: QUERY_TIME.NEVER,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      enabled:
        event.device.device_type_id === DeviceTypeEnum.TRACKER_ROW ||
        event.device.device_type_id === DeviceTypeEnum.TRACKER_ZONE,
    },
  })

  const processedEventTraces = useMemo(() => {
    if (
      event.device.device_type_id !== DeviceTypeEnum.TRACKER_ZONE ||
      !eventTraces.data
    ) {
      return eventTraces.data
    }
    const tracesByName = eventTraces.data.reduce<
      Record<string, typeof eventTraces.data>
    >((acc, trace) => {
      if (!acc[trace.name]) {
        acc[trace.name] = []
      }
      acc[trace.name].push(trace)
      return acc
    }, {})
    return Object.entries(tracesByName).flatMap(([name, traces]) => {
      if ((name !== 'Position' && name !== 'Setpoint') || traces.length <= 1) {
        return traces
      }
      const firstTrace = traces[0]
      return [
        {
          ...firstTrace,
          x: firstTrace.x.filter((_, timeIndex) => {
            return traces.some((trace) => trace.y[timeIndex] !== null)
          }),
          y: firstTrace.x
            .map((_, timeIndex) => {
              const values = traces
                .map((trace) => trace.y[timeIndex])
                .filter((value): value is number => value !== null)
              if (values.length === 0) return null
              return values.reduce((sum, val) => sum + val, 0) / values.length
            })
            .filter((value): value is number => value !== null),
          device_name_long: event.device.name_long || '',
        },
      ]
    })
  }, [event.device.device_type_id, event.device.name_long, eventTraces.data])

  const eventDeviceTypeId = event.device.device_type?.device_type_id
  const currentType =
    eventDeviceTypeId === DeviceTypeEnum.PV_INVERTER ||
    eventDeviceTypeId === DeviceTypeEnum.PV_INVERTER_MODULE
      ? 'ac'
      : 'dc'
  const losses: EventLossesData = {
    financial: {
      title: 'Daily Impact',
      value:
        (eventLossesSummary.data?.loss_daily_financial || 0)?.toFixed(2) ||
        ' N/A',
      unit: '$',
      info:
        'Daily financial loss is calculated by dividing the total financial ' +
        'loss by the number of days in the event. This calculation is ' +
        'sensitive to nuances such as other impacts to the project ' +
        '(including other Events) and daily expected production. Financial ' +
        'loss is calculated as energy lost multiplied by the PPA price, as ' +
        'provided.',
    },
    energetic: {
      title: '',
      value:
        (eventLossesSummary.data?.loss_daily_energy || 0)?.toFixed(2) || ' N/A',
      unit: 'MWh',
    },
    capacity: {
      title: 'Capacity Loss',
      value:
        eventLossesSummary.data?.loss_capacity !== null &&
        eventLossesSummary.data?.loss_capacity !== undefined
          ? eventLossesSummary.data.loss_capacity
          : currentType === 'ac'
            ? event.device.capacity_ac || 0
            : event.device.capacity_dc || 0,
      unit:
        eventLossesSummary.data?.loss_capacity !== null &&
        eventLossesSummary.data?.loss_capacity !== undefined
          ? 'kW DC'
          : currentType === 'ac'
            ? 'kW AC'
            : 'kW DC',
    },
  }
  const statusTraces = (statusTimeSeries.data ?? []) as StatusTimeSeriesTrace[]
  const validTraces = statusTraces.filter((trace) =>
    trace.y.some((value) => value !== null && value !== '{}'),
  )
  const hasStatus = validTraces.length > 0
  const flatZ: number[] = []
  const flatCustomData: [string][] = []
  const flatX: string[] = []
  const flatY: string[] = []
  validTraces.forEach((trace) => {
    ;(trace.alert ?? []).forEach((isAlert, colIdx) => {
      flatZ.push(isAlert ? 1 : 0)
      const yValue = trace.y[colIdx] ?? null
      flatCustomData.push([
        typeof yValue === 'string'
          ? yValue.replace(/,/g, '<br>')
          : yValue || 'Unknown',
      ])
      flatX.push(trace.x[colIdx])
      flatY.push(trace.name ?? 'Unknown')
    })
  })
  const traceTagsWithoutStatus =
    eventTraceTags.data?.filter((tag) => !tag.name_scada.includes('status')) ??
    []
  const traceUnits = Array.from(
    new Set(traceTagsWithoutStatus.map((tag) => tag.sensor_type_unit ?? '')),
  ).filter((unit) => unit !== '')
  const traceYAxisTitle = traceUnits.length === 1 ? traceUnits[0] : 'Value'
  const traceYAxisTickFormat =
    traceUnits.length === 1 && traceUnits[0] === '%' ? ',.0%' : undefined
  const uniqueUnits = Array.from(
    new Set(traceTagsWithoutStatus.map((tag) => tag.sensor_type_unit ?? '')),
  ).sort((a, b) => {
    if (a === '') return 1
    if (b === '') return -1
    return a.localeCompare(b)
  })
  const traceColorsArray = traceColors(theme)
  const unitColorMap = uniqueUnits.reduce<Record<string, string>>(
    (acc, unit, index) => {
      acc[unit] = traceColorsArray[index]
      return acc
    },
    {},
  )
  const tracesBySensorType = processedEventTraces?.reduce<
    Record<number, EventPlotTrace[]>
  >((acc, trace) => {
    const tag = eventTraceTags.data?.find(
      (traceTag) => traceTag.name_scada === trace.tag_name_scada,
    )
    if (
      trace.sensor_type_name.includes('status') ||
      trace.sensor_type_name.includes('alarm')
    ) {
      return acc
    }
    const unit = tag?.sensor_type_unit ?? ''
    const unitIndex = stringToInt(unit)
    const traceName =
      event.device.device_type_id === DeviceTypeEnum.TRACKER_ZONE
        ? `Average ${tag?.sensor_type_name_long} ${event.device.name_long}`
        : `${tag?.sensor_type_name_long} ${tag?.device_name_long}`

    if (!acc[unitIndex]) {
      acc[unitIndex] = []
    }
    acc[unitIndex].push({
      x: trace.x.filter((_, index) => trace.y[index] !== null),
      y: trace.y.filter((value): value is number => value !== null),
      name: traceName,
      type: 'scatter',
      line: {
        color: unitColorMap[unit] || traceColorsArray[0],
        dash:
          tag?.sensor_type_id === SensorTypeEnum.TRACKER_ROW_SETPOINT
            ? 'dash'
            : 'solid',
      },
      yaxis: unitIndex === 0 ? 'y' : `y${unitIndex + 1}`,
      hoverlabel: {
        namelength: -1,
      },
    })
    return acc
  }, {})
  const sensorTraces = Object.entries(tracesBySensorType ?? {}).flatMap(
    ([, traces]) => traces,
  )
  const statusHeatmapTraces = hasStatus
    ? [
        {
          x: flatX,
          y: flatY,
          z: flatZ,
          type: 'heatmap' as const,
          yaxis: 'y2',
          showscale: false,
          zmin: 0,
          zmax: 1,
          colorscale: [
            [0, theme.colors.green[7]],
            [1, theme.colors.red[7]],
          ] as [number, string][],
          customdata: flatCustomData,
          hovertemplate:
            'Time: %{x}<br>Status: %{customdata[0]}<extra></extra>',
          hoverlabel: {
            namelength: -1,
          },
        },
      ]
    : []
  const trueTrackingTraces = trueTrackingData.data
    ? [
        {
          x: trueTrackingData.data.times,
          y: trueTrackingData.data.tracker_theta,
          name: 'Ideal Tracking Angle',
          type: 'scatter' as const,
          line: {
            color: theme.colors.green[7],
            dash: 'dot' as const,
          },
          yaxis: 'y',
          hoverlabel: {
            namelength: -1,
          },
        },
      ]
    : []
  const plotData = [
    { yaxis: 'y' as const },
    ...sensorTraces,
    ...statusHeatmapTraces,
    ...trueTrackingTraces,
  ]
  const extraYAxes = traceUnits.reduce<Record<string, EventPlotYAxis>>(
    (acc, unit, index) => {
      const unitIndex = stringToInt(unit)
      const axisName = `yaxis${unitIndex + 1}`
      const color = unitColorMap[unit] || traceColorsArray[0]
      const placeOnLeft = index % 2 === 0
      acc[axisName] = {
        title: { text: unit || 'Unitless', font: { color } },
        side: placeOnLeft ? 'left' : 'right',
        overlaying: 'y',
        showgrid: false,
        zeroline: false,
        position: placeOnLeft ? 0 : 1,
        anchor: 'free',
        autoshift: true,
        tickformat: unit === '%' ? ',.0%' : undefined,
      }
      return acc
    },
    {},
  )
  const plotLayout: Partial<Layout> = {
    shapes: [
      {
        type: 'rect',
        x0: eventStartTime.format('YYYY-MM-DD HH:mm:ss'),
        x1:
          eventEndTime.isValid() && eventEndTime <= traceEnd
            ? eventEndTime.format('YYYY-MM-DD HH:mm:ss')
            : traceEnd.format('YYYY-MM-DD HH:mm:ss'),
        y0: hasStatus ? 0.575 : 0,
        y1: 1,
        xref: 'x',
        yref: 'paper',
        fillcolor: 'rgba(255, 0, 0, 0.3)',
        line: { width: 0 },
      },
    ],
    grid: {
      rows: hasStatus ? 2 : 1,
      columns: 1,
      pattern: 'independent',
    },
    xaxis: { type: 'date', automargin: true },
    yaxis: {
      title: {
        text: traceYAxisTitle,
        font: { color: theme.colors.blue[6] },
      },
      side: 'left',
      domain: hasStatus ? [0.62, 1] : [0, 1],
      showgrid: false,
      zeroline: false,
      automargin: true,
      visible: false,
      tickformat: traceYAxisTickFormat,
    },
    yaxis2: {
      domain: hasStatus ? [0, 0.34] : [0, 1],
      range: [
        traceStart.format('YYYY-MM-DD HH:mm:ss'),
        traceEnd.format('YYYY-MM-DD HH:mm:ss'),
      ],
      title: {
        text: 'Status',
        font: { color: theme.colors.gray[6] },
      },
      showgrid: false,
      zeroline: false,
    },
    ...extraYAxes,
  }
  const capacityOnly =
    !project.has_expected_energy_integration &&
    project.project_type_id !== ProjectTypeEnum.BESS

  return {
    capacityOnly,
    closeRootCauseModal: close,
    eventTraceError: eventTraceTags.error,
    failureModes: failureModes.data ?? [],
    historicalEvents: eventsHistorical.data ?? [],
    isTimelineLoading:
      eventsHistorical.isLoading ||
      rootCauses.isLoading ||
      CMMSTickets.isLoading,
    isTracesLoading:
      eventTraces.isLoading ||
      !eventTraceTags.data ||
      statusTimeSeries.isLoading,
    losses,
    openRootCauseModal: open,
    rootCauseDeviceTypes: getRootCauseDeviceTypes(event, project),
    rootCauseModalOpened: opened,
    rootCauses: (rootCauses.data ?? []) as RootCause[],
    selectedRootCause,
    setSelectedRootCause,
    setShowAllCauses,
    showAllCauses,
    tickets: CMMSTickets.data?.data,
    updateRootCause,
    xAxisTimeZone: projectTz,
    plotData,
    plotLayout,
  }
}
