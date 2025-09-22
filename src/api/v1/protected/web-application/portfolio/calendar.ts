import {
  CalendarEvent,
  CalendarEventCategory,
} from '@/api/v1/operational/calendar'
import { useCustomQuery } from '@/hooks/api'

export const useGetPortfolioCalendarEvents = ({
  projectIds,
}: {
  projectIds: string[]
}) => {
  const axiosConfig = {
    url: '/v1/protected/web-application/portfolio/calendar',
    params: projectIds.length > 0 ? { project_ids: projectIds } : {},
  }

  return useCustomQuery<CalendarEvent[]>({
    axiosConfig,
    queryName: 'getPortfolioCalendarEvents',
    queryOptions: {
      enabled: true, // Always enabled since backend handles empty project_ids
    },
  })
}

export const useGetPortfolioCalendarCategories = () => {
  const axiosConfig = {
    url: '/v1/protected/web-application/portfolio/calendar-categories',
  }

  return useCustomQuery<CalendarEventCategory[]>({
    axiosConfig,
    queryName: 'getPortfolioCalendarCategories',
  })
}
