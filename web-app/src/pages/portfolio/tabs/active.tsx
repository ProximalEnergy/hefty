import { useGetUserProjects } from '@/api/v1/admin/user_projects'
import { ProjectDataLastUpdated } from '@/api/v1/operational/project_data_last_updated'
import { ProjectStatusTypeId } from '@/api/v1/operational/project_status_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetUserProjectLabels } from '@/api/v1/operational/user_project_labels'
import { useGetPortfolioHome } from '@/api/v1/protected/web-application/portfolio/home'
import { Box, Center, SimpleGrid, Stack, Text } from '@mantine/core'

import styles from '../PortfolioHome.module.css'
import { PortfolioProjectCard } from '../components/PortfolioProjectCard/PortfolioProjectCard'

interface ActiveProjectsTabProps {
  projects: NonNullable<ReturnType<typeof useSelectProject>['data']>[]
  portfolioHomeData: NonNullable<ReturnType<typeof useGetPortfolioHome>['data']>
  projectDataLastUpdated?: ProjectDataLastUpdated[]
  userProjects: NonNullable<ReturnType<typeof useGetUserProjects>['data']>
  searchTerm: string
  time: '24h' | '30d'
  userProjectLabels: NonNullable<
    ReturnType<typeof useGetUserProjectLabels>['data']
  >
}

export function ActiveProjectsTab({
  projects,
  portfolioHomeData,
  projectDataLastUpdated,
  userProjects,
  searchTerm,
  time,
  userProjectLabels,
}: ActiveProjectsTabProps) {
  const activeProjects = projects
    .filter(
      (project) =>
        project.project_status_type_id === ProjectStatusTypeId.ACTIVE,
    )
    .filter((project) =>
      project.name_long.toLowerCase().includes(searchTerm.toLowerCase()),
    )

  // Create a map for quick lookup of favorited status
  const favoritedMap = new Map<string, boolean>()
  userProjects.forEach((up) => {
    favoritedMap.set(up.operational_project_id, up.is_favorited)
  })

  // Sort projects by favorited status and then by name
  const sortedProjects = [...activeProjects].sort((a, b) => {
    const aIsFavorited = favoritedMap.get(a.project_id) === true
    const bIsFavorited = favoritedMap.get(b.project_id) === true

    if (aIsFavorited && !bIsFavorited) {
      return -1
    }
    if (!aIsFavorited && bIsFavorited) {
      return 1
    }

    return a.name_long.localeCompare(b.name_long)
  })

  const renderProjectGrid = (projectsList: typeof activeProjects) => {
    if (projectsList.length === 0) {
      return (
        <Center h="100px">
          <Text className={styles.emptyState}>No projects found</Text>
        </Center>
      )
    }

    return (
      <SimpleGrid
        cols={{
          base: 1,
          md: 2,
          lg: 3,
          '3xl': 4,
          '5xl': 5,
        }}
      >
        {projectsList.map((project) => (
          <PortfolioProjectCard
            key={project.project_id}
            project={project}
            portfolioHomeProject={portfolioHomeData.find(
              (homeProject) => homeProject.project_id === project.project_id,
            )}
            projectDataLastUpdated={projectDataLastUpdated?.find(
              (data) => data.project_id === project.project_id,
            )}
            isFavorited={favoritedMap.get(project.project_id) === true}
            time={time}
            projectLabels={userProjectLabels.filter((label) =>
              label.project_ids.includes(project.project_id as string),
            )}
          />
        ))}
      </SimpleGrid>
    )
  }

  return (
    <Box pt="md">
      {activeProjects.length > 0 ? (
        <Stack>{renderProjectGrid(sortedProjects)}</Stack>
      ) : (
        <Center h="200px">
          <Text className={styles.emptyState}>No active projects</Text>
        </Center>
      )}
    </Box>
  )
}
