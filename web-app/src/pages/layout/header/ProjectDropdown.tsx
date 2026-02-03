import { useGetProjects } from '@/api/v1/operational/projects'
import { useGetReportInstances } from '@/api/v1/operational/report_instances'
import { useProjectDropdown } from '@/providers/ProjectDropdownContext'
import { Select, Tooltip } from '@mantine/core'
import { useDidUpdate, useOs } from '@mantine/hooks'
import { useRef } from 'react'
import { useNavigate, useParams } from 'react-router'

import { isDisabled } from './ProjectDropdown.utils'

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

  const reportInstances = useGetReportInstances({})

  const { projectId } = useParams<{ projectId: string }>()
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

  const selectDataLoaded = projects.data && reportInstances.data
  const selectDisabled =
    !isProjectDropdownEnabled || projects.isLoading || reportInstances.isLoading

  return (
    <Tooltip label={shortcutText} position="right" openDelay={1000}>
      <Select
        ref={ref}
        checkIconPosition="right"
        value={String(projectId)}
        onChange={handleSelectChange}
        data={
          selectDataLoaded
            ? projects.data
                .sort((a, b) => a.name_long.localeCompare(b.name_long))
                .map((project) => ({
                  value: String(project.project_id),
                  label: project.name_long,
                  disabled: isDisabled(
                    projectId,
                    filterCriteria,
                    project,
                    reportInstances.data,
                  ),
                }))
            : []
        }
        disabled={selectDisabled}
        comboboxProps={{ zIndex: 500 }}
      />
    </Tooltip>
  )
}

export default ProjectDropdown
