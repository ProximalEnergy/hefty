import type { components } from '@/api/schema'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import { useMutation } from '@tanstack/react-query'
import axios from 'axios'

type KPIBackfillPayload = components['schemas']['KPIBackfillEvent']
type ScheduledKPIBackfillPayload =
  components['schemas']['ScheduledKPIBackfillEvent']

const useKPIBackfillMutation = <TPayload extends KPIBackfillPayload>(
  endpoint: string,
) => {
  const { getToken } = useAuth()

  return useMutation<{ detail: string }, Error, TPayload>({
    mutationFn: async (payload) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        url: `${baseURL}${endpoint}`,
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

export const useTriggerKPIBackfill = () => {
  return useKPIBackfillMutation<KPIBackfillPayload>(
    '/v1/protected/kpi-backfill',
  )
}

export const useScheduleKPIBackfill = () => {
  return useKPIBackfillMutation<ScheduledKPIBackfillPayload>(
    '/v1/protected/kpi-backfill/schedule',
  )
}
