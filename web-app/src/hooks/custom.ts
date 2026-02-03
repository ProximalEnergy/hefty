import { Project } from '@/api/v1/operational/projects'
import { ReportInstance } from '@/api/v1/operational/report_instances'
import {
  ProjectFilterCriteria,
  useProjectDropdown,
} from '@/providers/ProjectDropdownContext'
import { useEffect, useMemo } from 'react'

// Custom hook for enabling/disabling the dropdown
export function useProjectDropdownToggle() {
  const { disableProjectDropdown, enableProjectDropdown } = useProjectDropdown()

  useEffect(() => {
    // Disable dropdown when the component using this hook mounts
    disableProjectDropdown()

    // Cleanup function to enable dropdown when the component unmounts
    return () => enableProjectDropdown()
  }, [disableProjectDropdown, enableProjectDropdown])
}

/**
 * Utility function to evaluate if a project matches the given filter criteria
 * If the project matches the criteria, return true
 */
export function evaluateFilterCriteria(
  project: Project,
  reportInstances: ReportInstance[],
  criteria: ProjectFilterCriteria,
): boolean {
  if (
    criteria.projectTypes &&
    !criteria.projectTypes.includes(project.project_type_id)
  ) {
    return false
  }

  if (
    criteria.hasEventIntegration !== undefined &&
    criteria.hasEventIntegration !== project.has_event_integration
  ) {
    return false
  }

  if (
    criteria.hasRealTimeData !== undefined &&
    criteria.hasRealTimeData !== project.has_real_time_data
  ) {
    return false
  }

  if (
    criteria.reportTypeId !== undefined &&
    !reportInstances.some(
      (reportInstance) =>
        reportInstance.project_id === project.project_id &&
        reportInstance.report_type_id === criteria.reportTypeId,
    )
  ) {
    return false
  }

  return true
}

/**
 * Simplified hook for setting project filters with automatic cleanup
 * Usage: useProjectFilter({ startsWith: 'A', endsWith: 'E' })
 * Automatically cleans up when component unmounts
 * Criteria is memoized internally to prevent infinite re-renders
 */
export function useProjectFilter(criteria: ProjectFilterCriteria) {
  const { setFilterCriteria, clearFilterCriteria } = useProjectDropdown()

  // Memoize the criteria to prevent infinite re-renders
  // Use JSON.stringify for deep comparison to avoid re-renders when object reference changes but content is the same
  const jsonCriteria = JSON.stringify(criteria)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const memoizedCriteria = useMemo(() => criteria, [jsonCriteria])

  useEffect(() => {
    setFilterCriteria(memoizedCriteria)

    // Cleanup: re-enable all projects when component unmounts
    return () => {
      clearFilterCriteria()
    }
  }, [memoizedCriteria, setFilterCriteria, clearFilterCriteria])
}
