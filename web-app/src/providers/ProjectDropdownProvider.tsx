import {
  ProjectDropdownContext,
  ProjectFilterCriteria,
} from '@/providers/ProjectDropdownContext'
import { ReactNode, useState } from 'react'

// Provider component with type for props
interface ProjectDropdownProviderProps {
  children: ReactNode
}

export function ProjectDropdownProvider({
  children,
}: ProjectDropdownProviderProps) {
  const [isProjectDropdownEnabled, setProjectDropdownEnabled] = useState(true)
  const [filterCriteria, setFilterCriteria] =
    useState<ProjectFilterCriteria | null>(null)

  const enableProjectDropdown = () => setProjectDropdownEnabled(true)
  const disableProjectDropdown = () => setProjectDropdownEnabled(false)

  const clearFilterCriteria = () => setFilterCriteria(null)

  const addFilterCriteria = (newCriteria: Partial<ProjectFilterCriteria>) => {
    setFilterCriteria((prev) => ({
      ...prev,
      ...newCriteria,
    }))
  }

  const removeFilterCriteria = (key: keyof ProjectFilterCriteria) => {
    setFilterCriteria((prev) => {
      if (!prev) return null
      const newCriteria = { ...prev }
      delete newCriteria[key]
      return Object.keys(newCriteria).length > 0 ? newCriteria : null
    })
  }

  // The value provided to the context consumers
  const value = {
    isProjectDropdownEnabled,
    enableProjectDropdown,
    disableProjectDropdown,
    filterCriteria,
    setFilterCriteria,
    clearFilterCriteria,
    addFilterCriteria,
    removeFilterCriteria,
  }

  return (
    <ProjectDropdownContext.Provider value={value}>
      {children}
    </ProjectDropdownContext.Provider>
  )
}
