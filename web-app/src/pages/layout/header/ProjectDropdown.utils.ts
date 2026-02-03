import { ReportInstance } from '@/api/v1/operational/project/report_instances'
import { Project } from '@/api/v1/operational/projects'
import { evaluateFilterCriteria } from '@/hooks/custom'
import { ProjectFilterCriteria } from '@/providers/ProjectDropdownContext'

export const isDisabled = (
  projectId: string,
  filterCriteria: ProjectFilterCriteria | null,
  project: Project,
  reportInstances: ReportInstance[],
) => {
  // The current project is always disabled
  if (project.project_id === projectId) {
    return true
  }

  // If filter criteria is provided, evaluate if the project passes the filter
  // Disable if the project does not pass the filter
  if (filterCriteria) {
    const passesFilter = evaluateFilterCriteria(
      project,
      reportInstances,
      filterCriteria,
    )
    return !passesFilter
  }

  // If no filter criteria is provided and the project is not the current project, enable the project
  return false
}
