import { ProjectDataLastUpdated } from '@/api/v1/operational/project_data_last_updated'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetPortfolioHome } from '@/api/v1/protected/web-application/portfolio/home'
import styles from '@/pages/portfolio/PortfolioHome.module.css'
import { PortfolioProjectCardHeader } from '@/pages/portfolio/components/PortfolioProjectCard/Header'
import { PortfolioProjectSparkline } from '@/pages/portfolio/components/PortfolioProjectCard/PortfolioProjectSparkline'
import { Stats } from '@/pages/portfolio/components/PortfolioProjectCard/Stats'
import { Box, Card, Group } from '@mantine/core'
import { Link } from 'react-router'

export function PortfolioProjectCard({
  project,
  portfolioHomeProject,
  projectDataLastUpdated,
  isFavorited = false,
  time,
  projectLabels,
}: {
  project: NonNullable<ReturnType<typeof useSelectProject>['data']>
  portfolioHomeProject:
    | NonNullable<ReturnType<typeof useGetPortfolioHome>['data']>[number]
    | undefined
  projectDataLastUpdated?: ProjectDataLastUpdated
  isFavorited?: boolean
  time: '24h' | '30d'
  projectLabels: { name: string; color: string }[]
}) {
  return (
    <Link
      to={`/projects/${project.project_id}`}
      style={{ color: 'inherit', textDecoration: 'none' }}
    >
      <Card
        p="md"
        shadow="md"
        withBorder
        className={styles.root}
        style={{ position: 'relative' }}
      >
        <Card.Section withBorder>
          <PortfolioProjectCardHeader
            project={project}
            projectDataLastUpdated={projectDataLastUpdated}
            isFavorited={isFavorited}
            projectLabels={projectLabels}
          />
        </Card.Section>
        <Group gap="sm" h={210} mt="md">
          <Box h="100%" flex={1}>
            <PortfolioProjectSparkline
              project={project}
              portfolioHomeProject={portfolioHomeProject}
              time={time}
            />
          </Box>
          {time === '24h' && (
            <Stats
              project={project}
              portfolioHomeProject={portfolioHomeProject}
            />
          )}
        </Group>
      </Card>
    </Link>
  )
}
