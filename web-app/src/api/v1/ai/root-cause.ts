import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/react'
import { useMutation } from '@tanstack/react-query'
import axios from 'axios'

export const useSuggestRootCauses = () => {
  const { getToken } = useAuth()
  return useMutation({
    mutationFn: async ({
      pairs,
      candidates,
      model,
    }: {
      pairs: Array<{ ir_signal?: string | null; rgb_signal?: string | null }>
      candidates: Array<{
        root_cause_id: number
        name_short?: string | null
        name_long?: string | null
        device_type_id: number
      }>
      model?: string
    }) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/ai/root-cause/suggest`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data: { pairs, candidates, model },
      })
      return response.data as {
        suggestions: Array<{
          index: number
          root_cause_id: number | null
          confidence?: number | null
          rationale?: string | null
        }>
      }
    },
  })
}
