import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { QUERY_TIME } from '@/utils/queryTiming'
import { useAuth } from '@clerk/react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

export interface EventMessageReaction {
  reaction_id: number
  event_message_id: number
  user_id: string
  reaction_type: string
  created_at: string
}

interface EventMessageReactionCreate {
  event_message_id: number
  reaction_type: string
  project_id: string
  event_id?: number // Optional event_id for batch query invalidation
}

export const useGetEventMessageReactions = ({
  queryParams,
  queryOptions = {},
}: {
  queryParams: {
    event_message_id?: number
    event_id?: number
    project_id: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${queryParams.project_id}/event-message-reactions`,
    method: 'get',
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    refetchInterval: QUERY_TIME.FIVE_SECONDS, // Refetch every 5 seconds (same as messages)
    staleTime: QUERY_TIME.THIRTY_SECONDS, // Consider data fresh for 30 seconds
  }

  // Filter out project_id from queryParams since it's already in the path
  const { project_id: _project_id, ...actualQueryParams } = queryParams

  return useCustomQuery<EventMessageReaction[]>({
    axiosConfig,
    queryName: 'getEventMessageReactions',
    queryParams: actualQueryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useToggleEventMessageReaction = () => {
  const { getToken, userId } = useAuth()
  const queryClient = useQueryClient()

  return useMutation<EventMessageReaction, Error, EventMessageReactionCreate>({
    mutationFn: async (reactionData: EventMessageReactionCreate) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/operational/projects/${reactionData.project_id}/event-message-reactions`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data: {
          event_message_id: reactionData.event_message_id,
          reaction_type: reactionData.reaction_type,
        },
      })
      return response.data
    },
    onMutate: async (reactionData) => {
      if (!userId || !reactionData.event_id) return

      // Cancel any outgoing refetches to avoid overwriting optimistic update
      // Note: project_id is NOT in the query key (it's filtered out in useCustomQuery)
      const batchQueryKey = [
        'getEventMessageReactions',
        {
          event_id: reactionData.event_id,
        },
      ]
      await queryClient.cancelQueries({ queryKey: batchQueryKey })

      // Snapshot the previous value for rollback
      const previousBatchReactions =
        queryClient.getQueryData<EventMessageReaction[]>(batchQueryKey)

      // Optimistically update the batch cache
      if (previousBatchReactions) {
        // Check if user already has this reaction on this message
        const existingReactionIndex = previousBatchReactions.findIndex(
          (r) =>
            r.event_message_id === reactionData.event_message_id &&
            r.user_id === userId &&
            r.reaction_type === reactionData.reaction_type,
        )

        let updatedReactions: EventMessageReaction[]
        if (existingReactionIndex >= 0) {
          // Remove reaction (toggle off)
          updatedReactions = previousBatchReactions.filter(
            (_, index) => index !== existingReactionIndex,
          )
        } else {
          // Add reaction (toggle on) - create optimistic reaction
          const optimisticReaction: EventMessageReaction = {
            reaction_id: Date.now(), // Temporary ID for optimistic update
            event_message_id: reactionData.event_message_id,
            user_id: userId,
            reaction_type: reactionData.reaction_type,
            created_at: new Date().toISOString(),
          }
          updatedReactions = [...previousBatchReactions, optimisticReaction]
        }

        queryClient.setQueryData<EventMessageReaction[]>(
          batchQueryKey,
          updatedReactions,
        )
      } else if (!previousBatchReactions) {
        // If no reactions exist yet, create initial array with optimistic reaction
        const optimisticReaction: EventMessageReaction = {
          reaction_id: Date.now(),
          event_message_id: reactionData.event_message_id,
          user_id: userId,
          reaction_type: reactionData.reaction_type,
          created_at: new Date().toISOString(),
        }
        queryClient.setQueryData<EventMessageReaction[]>(batchQueryKey, [
          optimisticReaction,
        ])
      }

      // Return context with previous value for rollback
      return { previousBatchReactions, batchQueryKey }
    },
    onError: (_err, _variables, context) => {
      // Rollback optimistic update on error
      if (context) {
        const ctx = context as {
          previousBatchReactions: EventMessageReaction[] | undefined
          batchQueryKey: (string | { event_id: number; project_id: string })[]
        }
        if (ctx.previousBatchReactions !== undefined && ctx.batchQueryKey) {
          queryClient.setQueryData(
            ctx.batchQueryKey,
            ctx.previousBatchReactions,
          )
        }
      }
    },
    onSuccess: (data, variables) => {
      // Replace optimistic reaction with real server response in batch cache
      if (!variables.event_id) return

      // Note: project_id is NOT in the query key (it's filtered out in useCustomQuery)
      const batchQueryKey = [
        'getEventMessageReactions',
        {
          event_id: variables.event_id,
        },
      ]

      const currentBatchReactions =
        queryClient.getQueryData<EventMessageReaction[]>(batchQueryKey) || []

      // Find the optimistic reaction (temporary ID from Date.now())
      // Optimistic reactions have IDs that are timestamps (large numbers > 1000000000000)
      const optimisticIndex = currentBatchReactions.findIndex(
        (r) =>
          r.event_message_id === data.event_message_id &&
          r.user_id === data.user_id &&
          r.reaction_type === data.reaction_type &&
          r.reaction_id > 1000000000000, // Timestamp-based temporary ID
      )

      if (optimisticIndex >= 0) {
        // Reaction was added - replace optimistic reaction with real one from server
        const updated = [...currentBatchReactions]
        updated[optimisticIndex] = data
        queryClient.setQueryData(batchQueryKey, updated)
      } else {
        // No optimistic reaction found - this means reaction was removed
        // The optimistic update already removed it, so verify consistency
        const stillExists = currentBatchReactions.some(
          (r) =>
            r.event_message_id === data.event_message_id &&
            r.user_id === data.user_id &&
            r.reaction_type === data.reaction_type,
        )
        if (stillExists) {
          // Reaction still exists but shouldn't - remove it
          const updated = currentBatchReactions.filter(
            (r) =>
              !(
                r.event_message_id === data.event_message_id &&
                r.user_id === data.user_id &&
                r.reaction_type === data.reaction_type
              ),
          )
          queryClient.setQueryData(batchQueryKey, updated)
        }
        // If it doesn't exist, optimistic update already handled it correctly
      }
    },
  })
}
