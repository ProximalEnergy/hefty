import { useSearchParamTab } from '@/hooks/useSearchParamTab'
import { ProjectImpactsTab } from '@/features/project-impacts/types/project-impacts-types'

type UseProjectImpactsTabReturn = {
  activeTab: ProjectImpactsTab
  setActiveTab: (value: string | null) => void
}

export function useProjectImpactsTab(): UseProjectImpactsTabReturn {
  const { activeTab, setTab } = useSearchParamTab({
    tabs: ['events', 'issues'],
    defaultTab: 'events',
  })

  return { activeTab, setActiveTab: setTab }
}
