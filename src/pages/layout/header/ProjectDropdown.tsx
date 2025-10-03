import { Project, useGetProjects } from '@/api/v1/operational/projects'
import { evaluateFilterCriteria } from '@/hooks/custom'
import {
  ProjectFilterCriteria,
  useProjectDropdown,
} from '@/providers/ProjectDropdownProvider'
import { Select, Tooltip } from '@mantine/core'
import { useDidUpdate, useOs } from '@mantine/hooks'
import { useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

export const isDisabled = (
  projectId: string,
  filterCriteria: ProjectFilterCriteria | null,
  project: Project,
) => {
  // The current project is always disabled
  if (project.project_id === projectId) {
    return true
  }

  // If filter criteria is provided, evaluate if the project passes the filter
  // Disable if the project does not pass the filter
  if (filterCriteria) {
    const passesFilter = evaluateFilterCriteria(project, filterCriteria)
    return !passesFilter
  }

  // If no filter criteria is provided and the project is not the current project, enable the project
  return false
}

const ProjectDropdown = () => {
  // Detect if the user is on macOS
  const isMac = useOs() == 'macos'
  const shortcutText = isMac ? '⌘+O' : 'Ctrl+O'

  const { isProjectDropdownEnabled, filterCriteria } = useProjectDropdown()

  const projects = useGetProjects({
    queryParams: {
      deep: true,
    },
  })
  const { projectId } = useParams()
  const navigate = useNavigate()

  const ref = useRef<HTMLInputElement>(null)
  const blurSelect = () => {
    if (!ref.current) {
      return
    }
    ref.current.blur()
  }

  useDidUpdate(() => {
    blurSelect()
  }, [projectId])

  if (!projectId) {
    return null
  }

  const handleSelectChange = (newProjectId: string | null) => {
    const updatedPath = location.pathname.replace(
      /projects\/[^/]+/,
      `projects/${newProjectId}`,
    )
    navigate(`${updatedPath}${location.search}`)
  }

  return (
    <Tooltip label={shortcutText} position="right" openDelay={1000}>
      <Select
        ref={ref}
        checkIconPosition="right"
        value={String(projectId)}
        onChange={handleSelectChange}
        data={projects.data
          ?.sort((a, b) => a.name_long.localeCompare(b.name_long))
          .map((project) => ({
            value: String(project.project_id),
            label: project.name_long,
            disabled: isDisabled(projectId, filterCriteria, project),
          }))}
        disabled={!isProjectDropdownEnabled || projects.isLoading}
        comboboxProps={{ zIndex: 500 }}
      />
    </Tooltip>
  )
}

export default ProjectDropdown
