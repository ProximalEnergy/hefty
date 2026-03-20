import { ProjectDataLastUpdated } from '@/api/v1/operational/project_data_last_updated'
import { ProjectStatusTypeId } from '@/api/v1/operational/project_status_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetUserProjectLabels } from '@/api/v1/operational/user_project_labels'
import { useGetPortfolioHome } from '@/api/v1/protected/web-application/portfolio/home'
import { Center, Paper, SimpleGrid, Text } from '@mantine/core'

import styles from '../PortfolioHome.module.css'
import { PortfolioProjectCard } from '../components/PortfolioProjectCard/PortfolioProjectCard'

interface ArchivedProjectsTabProps {
  projects: NonNullable<ReturnType<typeof useSelectProject>['data']>[]
  portfolioHomeData: NonNullable<ReturnType<typeof useGetPortfolioHome>['data']>
  projectDataLastUpdated?: ProjectDataLastUpdated[]
  searchTerm: string
  time: '24h' | '30d'
  userProjectLabels: NonNullable<
    ReturnType<typeof useGetUserProjectLabels>['data']
  >
}

export function ArchivedProjectsTab({
  projects,
  portfolioHomeData,
  projectDataLastUpdated,
  searchTerm,
  time,
  userProjectLabels,
}: ArchivedProjectsTabProps) {
  const archivedProjects = projects
    .filter(
      (project) =>
        project.project_status_type_id === ProjectStatusTypeId.ARCHIVED,
    )
    .filter((project) =>
      project.name_long.toLowerCase().includes(searchTerm.toLowerCase()),
    )

  return (
    <Paper p="md" withBorder radius={0} style={{ borderTop: 'none' }}>
      {archivedProjects.length > 0 ? (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
          {archivedProjects
            .sort((a, b) => a.name_long.localeCompare(b.name_long))
            .map((project) => (
              <PortfolioProjectCard
                key={project.project_id}
                project={project}
                portfolioHomeProject={portfolioHomeData.find(
                  (homeProject) =>
                    homeProject.project_id === project.project_id,
                )}
                projectDataLastUpdated={projectDataLastUpdated?.find(
                  (data) => data.project_id === project.project_id,
                )}
                time={time}
                projectLabels={userProjectLabels.filter((label) =>
                  label.project_ids.includes(project.project_id),
                )}
              />
            ))}
        </SimpleGrid>
      ) : (
        <Center h="200px">
          <Text className={styles.emptyState}>
            No projects are currently archived
          </Text>
        </Center>
      )}
    </Paper>
  )
}
