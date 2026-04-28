import { useGetUserProjectLabelsByProjectId } from '@/api/v1/operational/project/project_user_project_labels'
import { Badge, Group } from '@mantine/core'

export function ProjectLabels({ projectId }: { projectId: string }) {
  const projectLabels = useGetUserProjectLabelsByProjectId({
    pathParams: { project_id: projectId },
  })

  if (!projectLabels.data?.length) {
    return null
  }

  return (
    <Group>
      {projectLabels.data.map((label) => (
        <Badge
          key={label.user_project_label_id}
          color={label.color}
          variant="light"
        >
          {label.name}
        </Badge>
      ))}
    </Group>
  )
}
