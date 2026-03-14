import type {
  DailyPerformanceStats,
  DailyPerformanceSummaryRequest,
  DailyPerformanceSummaryResponse,
} from '@/api/v1/ai/daily_performance_summary'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/react'
import { useMutation } from '@tanstack/react-query'
import axios from 'axios'

export const useDailyPerformanceSummary = () => {
  const { getToken } = useAuth()

  return useMutation({
    mutationFn: async (
      stats: DailyPerformanceStats,
    ): Promise<DailyPerformanceSummaryResponse> => {
      const token = await getToken({ template: 'default' })

      const response = await axios.post<DailyPerformanceSummaryResponse>(
        `${baseURL}/v1/ai/daily-performance-summary`,
        { stats } as DailyPerformanceSummaryRequest,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        },
      )
      return response.data
    },
  })
}
