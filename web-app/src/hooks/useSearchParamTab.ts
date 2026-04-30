import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router'

type UseSearchParamTabOptions<Tab extends string> = {
  tabs: readonly Tab[]
  defaultTab: Tab
  paramName?: string
}

export function useSearchParamTab<Tab extends string>({
  tabs,
  defaultTab,
  paramName = 'tab',
}: UseSearchParamTabOptions<Tab>) {
  const [searchParams, setSearchParams] = useSearchParams()

  const activeTab = useMemo(() => {
    const currentTab = searchParams.get(paramName)

    return tabs.find((tab) => tab === currentTab) ?? defaultTab
  }, [defaultTab, paramName, searchParams, tabs])

  const setTab = useCallback(
    (value: string | null) => {
      const nextTab = tabs.find((tab) => tab === value) ?? defaultTab
      const nextParams = new URLSearchParams(searchParams)

      nextParams.set(paramName, nextTab)
      setSearchParams(nextParams, { replace: true })
    },
    [defaultTab, paramName, searchParams, setSearchParams, tabs],
  )

  return { activeTab, searchParams, setTab }
}
