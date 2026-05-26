import { useSearchParamTab } from '@/hooks/useSearchParamTab'
import type { DcAmperageReportTab } from '@/features/projects/reports/dc-amperage-report/types/dc-amperage-report-types'

type UseDcAmperageReportTabReturn = {
  activeTab: DcAmperageReportTab
  setActiveTab: (value: string | null) => void
}

export function useDcAmperageReportTab(): UseDcAmperageReportTabReturn {
  const { activeTab, setTab } = useSearchParamTab({
    tabs: ['clearsky', 'analysis'],
    defaultTab: 'clearsky',
  })

  return { activeTab, setActiveTab: setTab }
}
