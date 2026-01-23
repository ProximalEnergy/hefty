import type { components } from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { Tag } from '@/hooks/projectTags'
import * as types from '@/hooks/types'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

interface EventLossesSummary {
  loss_total_energy: number | null
  loss_total_financial: number | null
  loss_daily_energy: number | null
  loss_daily_financial: number | null
  loss_capacity: number | null
}

export interface EventLosses5MinSeries {
  event_loss_type_id: number
  losses: {
    time: string[]
    loss: number[]
  }
}

export interface EventLosses5MinGroup {
  device_id?: number
  device_type_id?: number
  failure_mode_id?: number
  root_cause_id?: number
  data: EventLosses5MinSeries[]
}

export type EventLosses5Min = EventLosses5MinGroup | EventLosses5MinSeries

type BulkCreateEventsPayload = components['schemas']['BulkCreateEventsRequest']
export type DroneAnomaly = components['schemas']['DroneAnomaly']

type EventSummary = components['schemas']['EventSummary']

export const useGetEventsSummary = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    device_ids?: number[]
    device_type_ids?: number[]
    start?: string
    end?: string
    open?: boolean
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/events/get-events-summary`,
  }

  const defaultQueryOptions = {}

  return useCustomQuery<EventSummary[]>({
    axiosConfig,
    queryName: 'getEventsTwo',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetEventDevices = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/events/event-devices`,
  }

  const defaultQueryOptions = {}

  return useCustomQuery<types.EventDeviceInfo>({
    axiosConfig,
    queryName: 'getEventDevices',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetEventTraceTags = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: {
    device_id: number
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/events/event-trace-tags`,
  }

  const defaultQueryOptions = {}

  return useCustomQuery<Tag[]>({
    axiosConfig,
    queryName: 'getEventTraceTags',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetEventAnomalies = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string; eventId: number }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/events/${pathParams.eventId}/anomalies`,
  }

  const defaultQueryOptions = {}

  return useCustomQuery<DroneAnomaly[]>({
    axiosConfig,
    queryName: 'getEventAnomalies',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useBulkCreateEvents = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      project_id,
      time_start,
      time_end,
      items,
      root_cause_id,
    }: { project_id: string } & BulkCreateEventsPayload) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'post',
        url: `${baseURL}/v1/operational/projects/${project_id}/events/bulk-create`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data: {
          time_start,
          time_end: time_end ?? null,
          items,
          root_cause_id: root_cause_id ?? null,
        },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getEvents'] })
      queryClient.invalidateQueries({ queryKey: ['getPaginatedEvents'] })
    },
  })
}

export const useGetEventLossesSummary = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: {
    event_id: number
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/events/event-losses-summary`,
  }

  const defaultQueryOptions = {}

  return useCustomQuery<EventLossesSummary>({
    axiosConfig,
    queryName: 'getEventLossesSummary',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetEventLosses5Min = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: {
    start: string
    end: string
    event_loss_type_ids?: number[]
    device_ids?: number[]
    aggregation_column?:
      | 'device_id'
      | 'device_type_id'
      | 'failure_mode_id'
      | 'root_cause_id'
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/events/5min-event-losses`,
  }

  const defaultQueryOptions = {}

  return useCustomQuery<EventLosses5Min[]>({
    axiosConfig,
    queryName: 'getEventLosses5Min',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetEventLosses5MinSingle = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: {
    start: string
    end: string
    event_loss_type_ids?: number[]
    device_id: number
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/events/5min-event-losses-single`,
  }

  const defaultQueryOptions = {}

  return useCustomQuery<EventLosses5Min[]>({
    axiosConfig,
    queryName: 'getEventLosses5MinSingle',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
