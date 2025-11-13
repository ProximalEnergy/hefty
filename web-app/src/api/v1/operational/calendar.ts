import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios, { AxiosResponse } from 'axios'

export interface CalendarEvent {
  calendar_item_id: string
  project_id: string
  title: string
  description?: string
  start_time: string
  end_time: string
  all_day: boolean
  calendar_item_category_id: string
  color: string
  rrule?: string
  timezone: string
  created_at: string
  updated_at: string
  notify_method?: string[]
  notify_offsets?: string[]
  exdates?: string[]
  // Optional assignments returned for display (speculative)
  assignee_user_ids?: string[]
  assignee_team_ids?: string[]
}

// New interface for Calendar Event Category
export interface CalendarEventCategory {
  category_id: string // Changed from uuid.UUID to string for frontend
  short_name: string
  long_name: string
  color_code: string
  created_at: string // Changed from datetime.datetime to string
  updated_at: string // Changed from datetime.datetime to string
}

export const useGetCalendarEvents = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    start?: string
    end?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/calendar-events`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60, // 1 minute
  }

  return useCustomQuery<CalendarEvent[]>({
    axiosConfig,
    queryName: 'getCalendarEvents',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

// New hook for fetching calendar event categories
export const useGetCalendarEventCategories = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string } // projectId is part of the path for endpoint consistency
  queryParams?: Record<string, string | number | boolean | undefined>
  // Generic query params, e.g., for skip/limit if needed later
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/calendar-item-categories`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 5, // 5 minutes, categories are not expected to change often
  }

  return useCustomQuery<CalendarEventCategory[]>({
    // Expecting an array of categories
    axiosConfig,
    queryName: 'getCalendarEventCategories',
    pathParams, // Pass projectId here
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

interface CreateCalendarEventParams {
  projectId: string
  event: Omit<
    CalendarEvent,
    'calendar_item_id' | 'project_id' | 'created_at' | 'updated_at'
  >
}

export const useCreateCalendarEvent = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation<AxiosResponse, Error, CreateCalendarEventParams>({
    mutationFn: async ({ projectId, event }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'post',
        url: `${baseURL}/v1/operational/projects/${projectId}/calendar-events`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: event,
      })
    },
    onSuccess: (_: unknown, variables: CreateCalendarEventParams) => {
      queryClient.invalidateQueries({
        queryKey: ['getCalendarEvents', { projectId: variables.projectId }],
      })
    },
  })
}

export const useUpdateCalendarEvent = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation<
    AxiosResponse,
    Error,
    {
      projectId: string
      calendarItemId: string
      event: Partial<
        Omit<
          CalendarEvent,
          'calendar_item_id' | 'project_id' | 'created_at' | 'updated_at'
        >
      >
    }
  >({
    mutationFn: async ({ projectId, calendarItemId, event }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'put',
        url: `${baseURL}/v1/operational/projects/${projectId}/calendar-events/${calendarItemId}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: event,
      })
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['getCalendarEvents', { projectId: variables.projectId }],
      })
    },
  })
}

interface DeleteCalendarEventParams {
  projectId: string
  eventId: string
}

export const useDeleteCalendarEvent = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation<AxiosResponse, Error, DeleteCalendarEventParams>({
    mutationFn: async ({ projectId, eventId }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'delete',
        url: `${baseURL}/v1/operational/projects/${projectId}/calendar-events/${eventId}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
    },
    onSuccess: (_: unknown, variables: DeleteCalendarEventParams) => {
      queryClient.invalidateQueries({
        queryKey: ['getCalendarEvents', { projectId: variables.projectId }],
      })
    },
  })
}

// Interface for the payload to cancel/modify an occurrence
interface CalendarOccurrenceActionPayload {
  is_cancelled?: boolean
  override_start_time?: string | null // Allow null to clear the time
  override_end_time?: string | null // Allow null to clear the time
}

// Interface for the parameters of the new mutation hook
interface CancelCalendarOccurrenceParams {
  projectId: string
  calendarItemId: string // This is the ID of the main recurring series event
  exceptionDate: string // Format YYYY-MM-DD
  payload: CalendarOccurrenceActionPayload
}

// New hook for cancelling/modifying a single occurrence
export const useCalendarOccurrenceAction = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation<AxiosResponse, Error, CancelCalendarOccurrenceParams>({
    mutationFn: async ({
      projectId,
      calendarItemId,
      exceptionDate,
      payload,
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'post',
        url: `${baseURL}/v1/operational/projects/${projectId}/calendar-events/${calendarItemId}/exceptions/${exceptionDate}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: payload,
      })
    },
    onSuccess: (_: unknown, variables: CancelCalendarOccurrenceParams) => {
      // Invalidate queries for the main calendar events to refresh the view
      queryClient.invalidateQueries({
        queryKey: ['getCalendarEvents', { projectId: variables.projectId }],
      })
      // Potentially invalidate queries for the specific item if you have a separate query for single item details
      // queryClient.invalidateQueries({ queryKey: ['getCalendarEvent', variables.calendarItemId] });
    },
    // onError, onMutate, etc. can be added as needed
  })
}
