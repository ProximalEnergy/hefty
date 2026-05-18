import { useSearchParamTab } from '@/hooks/useSearchParamTab'

import type { MetStationTab } from '../types/met-station'

const SUPERADMIN_TABS = ['realtime', 'current-day', 'long-term'] as const
const STANDARD_TABS = ['current-day'] as const

type UseMetStationTabProps = {
  isSuperadmin: boolean
}

type UseMetStationTabReturn = {
  activeTab: MetStationTab
  setActiveTab: (value: string | null) => void
}

export function useMetStationTab({
  isSuperadmin,
}: UseMetStationTabProps): UseMetStationTabReturn {
  const tabs = isSuperadmin ? SUPERADMIN_TABS : STANDARD_TABS
  const { activeTab, setTab } = useSearchParamTab({
    tabs,
    defaultTab: 'current-day',
  })

  return { activeTab, setActiveTab: setTab }
}
