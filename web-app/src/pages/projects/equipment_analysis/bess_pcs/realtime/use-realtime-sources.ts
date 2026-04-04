import { useGetCompanyTeamsWithMembers } from '@/api/admin'
import { DeviceTypeEnum, SensorTypeEnum } from '@/api/enumerations'
import { useGetSelfCompanyUsers } from '@/api/v1/admin/users'
import {
  useGetCalendarEventCategories,
  useGetCalendarEvents,
} from '@/api/v1/operational/calendar'
import { useGetCMMSTickets } from '@/api/v1/operational/project/cmms_tickets'
import { useGetEventsSummary } from '@/api/v1/operational/project/events'
import { useGetEventCMMSTicketsByEventIds } from '@/api/v1/protected/web-application/projects/event-cmms-tickets/event_cmms_tickets'
import {
  useGetDataTimeseriesLast,
  useGetRealTimeByDeviceTypeID,
} from '@/api/v1/protected/web-application/projects/real_time'
import { useMemo } from 'react'

type UseRealtimeSourcesParams = {
  projectId?: string
}

const pcsRealtimeSensorTypeIds = [
  SensorTypeEnum.BESS_PCS_AC_POWER,
  SensorTypeEnum.BESS_PCS_REACTIVE_POWER,
  SensorTypeEnum.BESS_PCS_DC_VOLTAGE,
  SensorTypeEnum.BESS_PCS_AVAILABLE_CHARGE_POWER,
  SensorTypeEnum.BESS_PCS_AVAILABLE_DISCHARGE_POWER,
  SensorTypeEnum.BESS_PCS_AVAILABLE_CAPACITIVE_REACTIVE_POWER,
  SensorTypeEnum.BESS_PCS_AVAILABLE_INDUCTIVE_REACTIVE_POWER,
]

export function useRealtimeSources({ projectId }: UseRealtimeSourcesParams) {
  const enabled = !!projectId

  const pcsRealtime = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DeviceTypeEnum.BESS_PCS,
    },
    queryParams: {
      sensor_type_ids: pcsRealtimeSensorTypeIds,
    },
    queryOptions: {
      enabled,
      refetchInterval: 30_000,
      staleTime: 15_000,
    },
  })

  const activeEvents = useGetEventsSummary({
    pathParams: {
      projectId: projectId || '-1',
    },
    queryParams: {
      device_type_ids: [DeviceTypeEnum.BESS_PCS],
      open: true,
    },
    queryOptions: {
      enabled,
      refetchInterval: 60_000,
    },
  })

  const moduleEvents = useGetEventsSummary({
    pathParams: {
      projectId: projectId || '-1',
    },
    queryParams: {
      device_type_ids: [DeviceTypeEnum.BESS_PCS_MODULE],
      open: true,
    },
    queryOptions: {
      enabled,
      refetchInterval: 60_000,
    },
  })

  const moduleGroupEvents = useGetEventsSummary({
    pathParams: {
      projectId: projectId || '-1',
    },
    queryParams: {
      device_type_ids: [DeviceTypeEnum.BESS_PCS_MODULE_GROUP],
      open: true,
    },
    queryOptions: {
      enabled,
      refetchInterval: 60_000,
    },
  })

  const cmmsTickets = useGetCMMSTickets({
    pathParams: {
      project_id: projectId || '-1',
    },
    queryParams: {
      device_type_ids: [
        DeviceTypeEnum.BESS_PCS,
        DeviceTypeEnum.BESS_PCS_MODULE,
        DeviceTypeEnum.BESS_PCS_MODULE_GROUP,
      ],
    },
    queryOptions: {
      enabled,
      refetchInterval: 60_000,
    },
  })

  const calendarEvents = useGetCalendarEvents({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: {
      enabled,
      staleTime: 60_000,
    },
  })

  const calendarCategories = useGetCalendarEventCategories({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: { enabled },
  })

  const companyUsers = useGetSelfCompanyUsers({
    queryOptions: { enabled },
  })

  const teamsWithMembers = useGetCompanyTeamsWithMembers({
    queryOptions: { enabled },
  })

  const meterLastData = useGetDataTimeseriesLast({
    pathParams: {
      projectId: projectId || '-1',
    },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.METER_ACTIVE_POWER],
    },
    queryOptions: {
      enabled,
      refetchInterval: 30_000,
      staleTime: 15_000,
    },
  })

  const bessMeterLastData = useGetDataTimeseriesLast({
    pathParams: {
      projectId: projectId || '-1',
    },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.BESS_MV_CIRCUIT_METER_ACTIVE_POWER],
    },
    queryOptions: {
      enabled,
      refetchInterval: 30_000,
      staleTime: 15_000,
    },
  })

  const openEventIds = useMemo(() => {
    const eventIds = new Set<number>()

    ;[
      ...(activeEvents.data ?? []),
      ...(moduleEvents.data ?? []),
      ...(moduleGroupEvents.data ?? []),
    ].forEach((event) => {
      if (event.event_id !== null && event.event_id !== undefined) {
        eventIds.add(event.event_id)
      }
    })

    return Array.from(eventIds)
  }, [activeEvents.data, moduleEvents.data, moduleGroupEvents.data])

  const eventCmmsLinks = useGetEventCMMSTicketsByEventIds({
    pathParams: {
      project_id: projectId || '-1',
    },
    eventIds: openEventIds,
    queryOptions: {
      enabled: enabled && openEventIds.length > 0,
      refetchInterval: 60_000,
    },
  })

  const linkedCmmsTicketIds = useMemo(() => {
    const ticketIds = new Set<number>()

    ;(eventCmmsLinks.data ?? []).forEach((link) => {
      if (link.cmms_ticket_id !== null && link.cmms_ticket_id !== undefined) {
        ticketIds.add(link.cmms_ticket_id)
      }
    })

    return Array.from(ticketIds)
  }, [eventCmmsLinks.data])

  const linkedCmmsTickets = useGetCMMSTickets({
    pathParams: {
      project_id: projectId || '-1',
    },
    queryParams: {
      cmms_ticket_ids: linkedCmmsTicketIds,
      include_json_raw: false,
    },
    queryOptions: {
      enabled: enabled && linkedCmmsTicketIds.length > 0,
      refetchInterval: 60_000,
    },
  })

  return {
    pcsRealtime,
    activeEvents,
    moduleEvents,
    moduleGroupEvents,
    cmmsTickets,
    calendarEvents,
    calendarCategories,
    companyUsers,
    teamsWithMembers,
    meterLastData,
    bessMeterLastData,
    eventCmmsLinks,
    linkedCmmsTickets,
  }
}
