import { useSearchParamTab } from '@/hooks/useSearchParamTab'

const SUPERADMIN_TABS = ['realtime', 'current-day', 'long-term'] as const
const STANDARD_TABS = ['realtime', 'current-day'] as const

type BessStringTab = (typeof SUPERADMIN_TABS)[number]

type UseBessStringTabOptions = {
  defaultTab?: BessStringTab
  isSuperadmin: boolean
}

export function useBessStringTab({
  defaultTab = 'current-day',
  isSuperadmin,
}: UseBessStringTabOptions) {
  const tabs: readonly BessStringTab[] = isSuperadmin
    ? SUPERADMIN_TABS
    : STANDARD_TABS
  const fallbackTab = tabs.find((tab) => tab === defaultTab) ?? tabs[0]

  return useSearchParamTab({
    tabs,
    defaultTab: fallbackTab,
  })
}
