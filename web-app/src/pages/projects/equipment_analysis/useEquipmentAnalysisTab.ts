import { useSearchParamTab } from '@/hooks/useSearchParamTab'

const SUPERADMIN_TABS = ['realtime', 'current-day', 'long-term'] as const
const STANDARD_TABS = ['realtime', 'current-day'] as const
const CURRENT_DAY_ONLY_TABS = ['current-day'] as const

type EquipmentAnalysisTab = (typeof SUPERADMIN_TABS)[number]

type UseEquipmentAnalysisTabOptions = {
  defaultTab?: EquipmentAnalysisTab
  isSuperadmin: boolean
  realtimeForStandardUsers?: boolean
}

export function useEquipmentAnalysisTab({
  defaultTab = 'current-day',
  isSuperadmin,
  realtimeForStandardUsers = true,
}: UseEquipmentAnalysisTabOptions) {
  const tabs: readonly EquipmentAnalysisTab[] = isSuperadmin
    ? SUPERADMIN_TABS
    : realtimeForStandardUsers
      ? STANDARD_TABS
      : CURRENT_DAY_ONLY_TABS
  const fallbackTab = tabs.find((tab) => tab === defaultTab) ?? tabs[0]

  return useSearchParamTab({
    tabs,
    defaultTab: fallbackTab,
  })
}
