import { useCustomQuery } from '@/hooks/api'
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
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<types.EventSummary[]>({
    axiosConfig,
    queryName: 'getEventsTwo',
    pathParams,
    queryParams: queryParams,
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

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<types.EventDeviceInfo>({
    axiosConfig,
    queryName: 'getEventDevices',
    pathParams,
    queryParams: {},
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
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<types.Tag[]>({
    axiosConfig,
    queryName: 'getEventTraceTags',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetCountOpenEvents = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/events/count-open`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<number>({
    axiosConfig,
    queryName: 'getCountOpenEvents',
    pathParams,
    queryParams: {},
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export interface DroneAnomaly {
  anomaly_uuid: string
  inspection_uuid: string
  event_id?: number
  stack_id?: string
  ir_signal?: string
  rgb_signal?: string
  ir_image_url?: string
  rgb_image_url?: string
  subsystem?: string
  remediation_category?: string
  energy_loss_weighting?: number
  power_loss_kw?: number
  location_lat?: number
  location_lon?: number
  client_status_id?: number
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

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<DroneAnomaly[]>({
    axiosConfig,
    queryName: 'getEventAnomalies',
    pathParams,
    queryParams: {},
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
    }: {
      project_id: string
      time_start: string
      time_end?: string | null
      items: {
        device_id: number
        loss: number
        event_loss_type_id?: number
        anomaly_uuids?: string[]
      }[]
      root_cause_id?: number | null
    }) => {
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
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<EventLossesSummary>({
    axiosConfig,
    queryName: 'getEventLossesSummary',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
