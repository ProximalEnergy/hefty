import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import { useMutation } from '@tanstack/react-query'
import axios from 'axios'

export interface VoiceChatSessionRequest {
  model: string
}

export interface VoiceChatSessionResponse {
  client_secret: string
  expires_at: string
}

export interface EnsureVectorStoreRequest {
  openai_file_id: string
  name?: string
}

export interface EnsureVectorStoreResponse {
  vector_store_id: string
}

export const useCreateVoiceChatSession = () => {
  const { getToken } = useAuth()

  return useMutation({
    mutationFn: async (
      request: VoiceChatSessionRequest,
    ): Promise<VoiceChatSessionResponse> => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/ai/voice-chat/session`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: request,
      })
      return response.data
    },
  })
}

export const useEnsureVectorStore = () => {
  const { getToken } = useAuth()

  return useMutation({
    mutationFn: async (
      request: EnsureVectorStoreRequest,
    ): Promise<EnsureVectorStoreResponse> => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/ai/vector-store/ensure`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: request,
      })
      return response.data
    },
  })
}
