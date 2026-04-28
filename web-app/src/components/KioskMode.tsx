import { useGetProjects } from '@/api/v1/operational/projects'
import { Switch, Tooltip } from '@mantine/core'
import { IconRepeat, IconRepeatOff } from '@tabler/icons-react'
import { useEffect, useMemo } from 'react'
import { useNavigate, useParams } from 'react-router'

interface KioskModeProps {
  enabled: boolean
  setEnabled: (enabled: boolean) => void
}

export function KioskMode({ enabled, setEnabled }: KioskModeProps) {
  const INTERVAL = 60

  const { projectId } = useParams()
  const navigate = useNavigate()

  // Query data for all projects
  const projects = useGetProjects({
    queryParams: {},
  })

  // Get an array of all project IDs
  const projectIds = useMemo(
    () => projects.data?.map((project) => project.project_id),
    [projects.data],
  )

  // Effect to handle kiosk mode
  useEffect(() => {
    // If kiosk mode is not enabled, do nothing
    if (!enabled) return

    // If there are no project IDs, do nothing
    if (!projectIds) return

    // Set an interval to rotate to the next project
    const interval = setInterval(() => {
      // Find the current project index in the array
      const currentIndex = projectIds.findIndex((id) => id === projectId)

      // Get the next project ID (wrap around to the beginning if at the end)
      const nextIndex =
        currentIndex === -1 || currentIndex === projectIds.length - 1
          ? 0
          : currentIndex + 1

      // Navigate to the next project
      const nextProjectId = projectIds[nextIndex]
      navigate(`/projects/${nextProjectId}`)
    }, INTERVAL * 1000)

    // Cleanup interval on component unmount
    return () => clearInterval(interval)
  }, [navigate, projectIds, enabled, projectId])

  return (
    <Tooltip
      label={`Kiosk Mode - When enabled, the page will automatically rotate to the next project every ${INTERVAL} seconds.`}
      refProp="rootRef"
    >
      <Switch
        size="md"
        onLabel={<IconRepeat size={16} />}
        offLabel={<IconRepeatOff size={16} />}
        checked={enabled}
        onChange={(event) => setEnabled(event.currentTarget.checked)}
      />
    </Tooltip>
  )
}
