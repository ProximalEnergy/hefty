import { ProjectTypeEnum } from '@/api/enumerations'
import { useUpdateProjectFavorite } from '@/api/v1/admin/user_projects'
import { ProjectDataLastUpdated } from '@/api/v1/operational/project_data_last_updated'
import { useSelectProject } from '@/api/v1/operational/projects'
import { projectDescription } from '@/utils/projectDescription'
import { useUser } from '@clerk/react'
import {
  ActionIcon,
  Badge,
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
  projectLabels,
}: {
  project: NonNullable<ReturnType<typeof useSelectProject>['data']>
  projectDataLastUpdated?: ProjectDataLastUpdated
  isFavorited: boolean
  projectLabels: { name: string; color: string }[]
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
      <Group gap="xs" p="md" style={{ flexWrap: 'nowrap' }}>
        <DataStatus
          data={projectDataLastUpdated}
          data_receive_schedule={project.data_receive_schedule}
          isLoading={false}
          isError={false}
        />
        <Group gap="xs" flex={1} style={{ flexWrap: 'nowrap' }}>
          <Title order={5} lh={1} textWrap="nowrap">
            {project.name_long}
          </Title>
          <Tooltip label={description}>
            <Group gap={0}>
              {(project.project_type_id === ProjectTypeEnum.PV ||
                project.project_type_id === ProjectTypeEnum.PVS) && (
                <IconSolarPanel />
              )}
              {(project.project_type_id === ProjectTypeEnum.BESS ||
                project.project_type_id === ProjectTypeEnum.PVS) && (
                <IconBattery4 />
              )}
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
        <Group
          gap="xs"
          style={{
            flexWrap: 'nowrap',
            overflowX: 'auto',
            whiteSpace: 'nowrap',
            minWidth: 0,
          }}
        >
          {projectLabels.map((label) => (
            <Badge
              autoContrast={true}
              key={label.name}
              color={label.color}
              variant="light"
            >
              {label.name}
            </Badge>
          ))}
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
