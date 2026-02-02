import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  UseQueryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

interface EventMessage {
  event_message_id: number
  event_id: number
  user_id: string
  body: string
  mentions: string | null
  parent_message_id: number | null
  created_at: string
  edited_at: string | null
  deleted_at: string | null
  image_s3_keys: string | null
  private: boolean
}

export interface EventMessageImage {
  event_message_image_id: string
  s3_key: string
  filename: string
  content_type: string
  file_size: number
  presigned_url: string
}

interface EventMessageCreate {
  event_id: number
  body: string
  parent_message_id?: number | null
  project_id: string
  private?: boolean
}

export const useGetEventMessages = ({
  queryParams,
  queryOptions = {},
}: {
  queryParams: { event_id: number; project_id: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${queryParams.project_id}/event-messages`,
    method: 'get',
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    refetchInterval: 5000, // Refetch every 5 seconds
  }

  return useCustomQuery<EventMessage[]>({
    axiosConfig,
    queryName: 'getEventMessages',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

interface EventMessageUpdate {
  event_message_id: number
  body: string
  project_id: string
  image_ids?: string[] | null // List of image IDs to keep, in order matching placeholders
}

export const useCreateEventMessage = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation<EventMessage, Error, EventMessageCreate>({
    mutationFn: async (messageData: EventMessageCreate) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/operational/projects/${messageData.project_id}/event-messages`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data: {
          event_id: messageData.event_id,
          body: messageData.body,
          parent_message_id: messageData.parent_message_id,
          private: messageData.private,
        },
      })
      return response.data
    },
    onSuccess: (_, variables) => {
      // Invalidate and refetch event messages for this event
      // Query key structure matches useCustomQuery: [queryName, queryParams]
      // pathParams is empty so it's not included in the key
      const queryParams: Record<string, unknown> = {
        event_id: variables.event_id,
      }
      if (variables.project_id) {
        queryParams.project_id = variables.project_id
      }
      const queryKey = ['getEventMessages', queryParams]
      queryClient.invalidateQueries({
        queryKey,
      })
      // Also refetch immediately to show the new message right away
      queryClient.refetchQueries({
        queryKey,
      })
    },
  })
}

export const useUpdateEventMessage = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation<EventMessage, Error, EventMessageUpdate>({
    mutationFn: async (messageData: EventMessageUpdate) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'put',
        url: `${baseURL}/v1/operational/projects/${messageData.project_id}/event-messages/${messageData.event_message_id}`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data: {
          body: messageData.body,
          image_ids: messageData.image_ids,
        },
      })
      return response.data
    },
    onSuccess: () => {
      // Invalidate and refetch all event message queries to show updated message
      queryClient.invalidateQueries({
        queryKey: ['getEventMessages'],
      })
      // Also refetch immediately to show the updated message right away
      queryClient.refetchQueries({
        queryKey: ['getEventMessages'],
      })
    },
  })
}

interface EventMessageDelete {
  event_message_id: number
  event_id: number
  project_id: string
}

export const useDeleteEventMessage = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation<EventMessage, Error, EventMessageDelete>({
    mutationFn: async (messageData: EventMessageDelete) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'delete',
        url: `${baseURL}/v1/operational/projects/${messageData.project_id}/event-messages/${messageData.event_message_id}`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
      return response.data
    },
    onSuccess: (_, variables) => {
      // Invalidate and refetch event messages for this event
      const queryParams: Record<string, unknown> = {
        event_id: variables.event_id,
      }
      if (variables.project_id) {
        queryParams.project_id = variables.project_id
      }
      const queryKey = ['getEventMessages', queryParams]
      queryClient.invalidateQueries({
        queryKey,
      })
      // Also refetch immediately to show the deleted message right away
      queryClient.refetchQueries({
        queryKey,
      })
    },
  })
}

export const useToggleEventChatMute = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation<
    { muted: boolean },
    Error,
    { eventId: number; projectId: string }
  >({
    mutationFn: async ({ eventId, projectId }) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/operational/projects/${projectId}/event-messages/${eventId}/mute`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
      return response.data
    },
    onSuccess: (data, variables) => {
      // Update the cache with the new mute status from the response
      queryClient.setQueryData(
        [
          'getEventChatMuteStatus',
          { eventId: variables.eventId, projectId: variables.projectId },
        ],
        data,
      )
      // Refetch to ensure consistency
      queryClient.refetchQueries({
        queryKey: [
          'getEventChatMuteStatus',
          { eventId: variables.eventId, projectId: variables.projectId },
        ],
      })
    },
  })
}

export const useGetEventChatMuteStatus = (
  eventId: number,
  projectId: string,
) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${projectId}/event-messages/${eventId}/mute-status`,
    method: 'get',
  }

  return useCustomQuery<{ muted: boolean }>({
    axiosConfig,
    queryName: 'getEventChatMuteStatus',
    pathParams: { eventId, projectId },
    queryOptions: {
      refetchOnWindowFocus: false,
    },
  })
}

export const useUploadEventMessageImage = () => {
  const { getToken } = useAuth()

  return useMutation<
    EventMessageImage,
    Error,
    { eventId: number; eventMessageId: number; file: File; projectId: string }
  >({
    mutationFn: async ({ eventId, eventMessageId, file, projectId }) => {
      const token = await getToken({ template: 'default' })
      const formData = new FormData()
      formData.append('file', file)

      const url = `${baseURL}/v1/operational/projects/${projectId}/event-messages/${eventId}/images/${eventMessageId}`

      const response = await axios({
        method: 'post',
        url,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
        data: formData,
      })
      return response.data
    },
  })
}

export const useGetEventMessageImageUrl = () => {
  const { getToken } = useAuth()

  return useMutation<
    { presigned_url: string; s3_key: string },
    Error,
    { eventId: number; imageId: string; projectId: string }
  >({
    mutationFn: async ({ eventId, imageId, projectId }) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'get',
        url: `${baseURL}/v1/operational/projects/${projectId}/event-messages/${eventId}/images/${imageId}/url`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      return response.data
    },
  })
}

export const useGetEventMessageImages = ({
  queryParams,
  queryOptions = {},
}: {
  queryParams: { eventId: number; eventMessageId: number; projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const { getToken } = useAuth()

  const queryKey = [
    'getEventMessageImages',
    {
      eventId: queryParams.eventId,
      eventMessageId: queryParams.eventMessageId,
      projectId: queryParams.projectId,
    },
  ]

  const queryFn = async (): Promise<EventMessageImage[]> => {
    const token = await getToken({ template: 'default' })
    const response = await axios({
      method: 'get',
      url: `${baseURL}/v1/operational/projects/${queryParams.projectId}/event-messages/${queryParams.eventId}/messages/${queryParams.eventMessageId}/images`,
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
    return response.data
  }

  return useQuery({
    queryKey,
    queryFn,
    refetchOnWindowFocus: false,
    ...queryOptions,
  })
}
