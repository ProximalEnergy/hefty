import { useCustomQuery } from '@/hooks/api'
import { Event } from '@/hooks/types'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

export interface EventCMMSTicket {
  event_cmms_ticket_id: number
  event_id: number
  cmms_ticket_id: number
  created_by_user_id: string
  created_at: string
}

interface EventWithScore extends Event {
  score: number
}

export const useGetEventCMMSTickets = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: {
    projectId: string
  }
  queryParams: {
    event_cmms_ticket_ids?: number[]
    event_ids?: number[]
    cmms_ticket_ids?: number[]
    created_by_user_ids?: string[]
    created_at_gte?: string
    created_at_lte?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/event-cmms-tickets`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60,
  }

  return useCustomQuery<EventCMMSTicket[]>({
    axiosConfig,
    queryName: 'getEventCMMSTickets',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetSuggestedEvents = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: {
    projectId: string
  }
  queryParams: {
    cmms_ticket_id: string
    cmms_integration_id: number
    cmms_device_id?: number
    source_created_at?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/event-cmms-tickets/suggested-events`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60,
  }

  return useCustomQuery<EventWithScore[]>({
    axiosConfig,
    queryName: 'getSuggestedEvents',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useAddEventCMMSTicket = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      project_id,
      event_id,
      cmms_ticket_id,
    }: {
      project_id: string
      event_id: number
      cmms_ticket_id: number
    }) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/protected/web-application/projects/${project_id}/event-cmms-tickets`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          event_id,
          cmms_ticket_id,
        },
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getEventCMMSTickets'] })
    },
  })
}

export const useDeleteEventCMMSTicket = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      project_id,
      event_cmms_ticket_id,
    }: {
      project_id: string
      event_cmms_ticket_id: number
    }) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'delete',
        url: `${baseURL}/v1/protected/web-application/projects/${project_id}/event-cmms-tickets/${event_cmms_ticket_id}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getEventCMMSTickets'] })
    },
  })
}
