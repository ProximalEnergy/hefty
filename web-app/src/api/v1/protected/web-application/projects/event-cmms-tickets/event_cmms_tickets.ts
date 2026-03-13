import { Endpoint } from '@/api/utils'
import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

const URL_GET_EVENT_CMMS_TICKETS =
  '/v1/protected/web-application/projects/{project_id}/event-cmms-tickets'
type GetEventCMMSTickets = Endpoint<typeof URL_GET_EVENT_CMMS_TICKETS, 'get'>
export type EventCMMSTicket =
  GetEventCMMSTickets['Response'] extends (infer Item)[] ? Item : never

export const useGetEventCMMSTickets = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { project_id: GetEventCMMSTickets['PathParams']['project_id'] }
  queryParams?: GetEventCMMSTickets['QueryParams']
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL_GET_EVENT_CMMS_TICKETS,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60,
  }

  return useCustomQuery<GetEventCMMSTickets['Response']>({
    axiosConfig,
    queryName: 'getEventCMMSTickets',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

const URL_GET_SUGGESTED_EVENTS =
  '/v1/protected/web-application/projects/{project_id}/event-cmms-tickets/suggested-events'
type GetSuggestedEvents = Endpoint<typeof URL_GET_SUGGESTED_EVENTS, 'get'>

export const useGetSuggestedEvents = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: {
    project_id: GetSuggestedEvents['PathParams']['project_id']
  }
  queryParams?: GetSuggestedEvents['QueryParams']
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL_GET_SUGGESTED_EVENTS,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60,
  }

  return useCustomQuery<GetSuggestedEvents['Response']>({
    axiosConfig,
    queryName: 'getSuggestedEvents',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

const URL_GET_SUGGESTED_TICKETS =
  '/v1/protected/web-application/projects/{project_id}/event-cmms-tickets/suggested-tickets'
type GetSuggestedTickets = Endpoint<typeof URL_GET_SUGGESTED_TICKETS, 'get'>

export const useGetSuggestedTickets = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: {
    project_id: GetSuggestedTickets['PathParams']['project_id']
  }
  queryParams?: GetSuggestedTickets['QueryParams']
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL_GET_SUGGESTED_TICKETS,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60,
  }

  return useCustomQuery<GetSuggestedTickets['Response']>({
    axiosConfig,
    queryName: 'getSuggestedTickets',
    pathParams,
    queryParams,
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
