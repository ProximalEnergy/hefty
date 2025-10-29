import { createContext, useContext } from 'react'

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
export const ProjectDropdownContext = createContext<
  ProjectDropdownContextType | undefined
>(undefined)

export interface ProjectFilterCriteria {
  projectTypes?: number[]
  hasEventIntegration?: boolean
  hasRealTimeData?: boolean
}

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
