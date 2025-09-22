import { ReactNode, createContext, useContext, useState } from 'react'

// Define filter criteria types
export interface ProjectFilterCriteria {
  projectTypes?: number[]
  hasEventIntegration?: boolean
  hasRealTimeData?: boolean
}

// Define the shape of the context
interface ProjectDropdownContextType {
  isProjectDropdownEnabled: boolean
  enableProjectDropdown: () => void
  disableProjectDropdown: () => void
  filterCriteria: ProjectFilterCriteria | null
  setFilterCriteria: (criteria: ProjectFilterCriteria | null) => void
  clearFilterCriteria: () => void
  addFilterCriteria: (criteria: Partial<ProjectFilterCriteria>) => void
  removeFilterCriteria: (key: keyof ProjectFilterCriteria) => void
}

// Create the context with an initial undefined value
const ProjectDropdownContext = createContext<
  ProjectDropdownContextType | undefined
>(undefined)

// Hook for easy use of the context
export function useProjectDropdown() {
  const context = useContext(ProjectDropdownContext)
  if (context === undefined) {
    throw new Error(
      'useProjectDropdown must be used within a ProjectDropdownProvider',
    )
  }
  return context
}

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
