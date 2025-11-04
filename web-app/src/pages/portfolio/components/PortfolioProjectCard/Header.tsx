import { useUpdateProjectFavorite } from '@/api/v1/admin/user_projects'
import { ProjectDataLastUpdated } from '@/api/v1/operational/project_data_last_updated'
import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import { projectDescription } from '@/utils/projectDescription'
import { useUser } from '@clerk/clerk-react'
import {
  ActionIcon,
  Card,
  Group,
  Title,
  Tooltip,
  useMantineTheme,
} from '@mantine/core'
import {
  IconBattery4,
  IconHeart,
  IconHeartFilled,
  IconInfoCircle,
  IconSolarPanel,
} from '@tabler/icons-react'

import DataStatus from '../../../layout/header/DataStatus'

export function Header({
  project,
  projectDataLastUpdated,
  isFavorited,
}: {
  project: NonNullable<ReturnType<typeof useSelectProject>['data']>
  projectDataLastUpdated?: ProjectDataLastUpdated
  isFavorited: boolean
}) {
  const theme = useMantineTheme()
  const { user } = useUser()
  const updateFavoriteMutation = useUpdateProjectFavorite()
  const description = projectDescription(project)

  const handleFavoriteToggle = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!user?.id) return
    updateFavoriteMutation.mutate({
      userId: user.id,
      projectId: project.project_id,
      isFavorited: !isFavorited,
    })
  }

  return (
    <Card.Section withBorder>
      <Group gap="xs" p="md">
        <DataStatus
          data={projectDataLastUpdated}
          data_receive_schedule={project.data_receive_schedule}
          isLoading={false}
          isError={false}
        />
        <Group gap="xs" flex={1}>
          <Title order={5} lh={1}>
            {project.name_long}
          </Title>
          <Tooltip label={description}>
            <Group gap={0}>
              {[ProjectTypeId.PV, ProjectTypeId.PV_BESS].includes(
                project.project_type_id,
              ) && <IconSolarPanel />}
              {[ProjectTypeId.BESS, ProjectTypeId.PV_BESS].includes(
                project.project_type_id,
              ) && <IconBattery4 />}
            </Group>
          </Tooltip>
          {!project.has_real_time_data && (
            <Tooltip label="Real time data is not available for this project. Data shown is from yesterday.">
              <ActionIcon variant="subtle" color="yellow" size="sm">
                <IconInfoCircle size={16} />
              </ActionIcon>
            </Tooltip>
          )}
        </Group>
        <ActionIcon variant="subtle" size="sm" onClick={handleFavoriteToggle}>
          {isFavorited ? (
            <IconHeartFilled size={16} color={theme.colors.red[6]} />
          ) : (
            <IconHeart size={16} />
          )}
        </ActionIcon>
      </Group>
    </Card.Section>
  )
}
