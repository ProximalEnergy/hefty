import { useState } from 'react'

type SortConfig = {
  key: string
  direction: 'asc' | 'desc'
}

const getNextSortConfig = (
  current: SortConfig | null,
  key: string,
): SortConfig | null => {
  if (!current || current.key !== key) {
    return { key, direction: 'asc' }
  }

  if (current.direction === 'asc') {
    return { key, direction: 'desc' }
  }

  return null
}

export const useTableSort = (initialSortConfig: SortConfig | null = null) => {
  const [sortConfig, setSortConfig] = useState<SortConfig | null>(
    initialSortConfig,
  )

  const handleSort = (key: string) => {
    setSortConfig((current) => getNextSortConfig(current, key))
  }

  return { sortConfig, handleSort }
}
