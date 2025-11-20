import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import { useMutation } from '@tanstack/react-query'
import axios from 'axios'

interface KPIBackfillPayload {
  start: string
  end: string
  backfill_days: number
  project_name_short_list: string[]
  kpi_type_ids?: number[]
}

export const useTriggerKPIBackfill = () => {
  const { getToken } = useAuth()

  return useMutation<{ detail: string }, Error, KPIBackfillPayload>({
    mutationFn: async (payload) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/protected/kpi-backfill`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data: payload,
      })

      return response.data
    },
  })
}
