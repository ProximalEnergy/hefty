import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetPortfolioHome } from '@/api/v1/protected/web-application/portfolio/home'
import { Stack } from '@mantine/core'

import { RingProgressStat } from './RingProgressStat'

export function Stats({
  project,
  portfolioHomeProject,
}: {
  project: NonNullable<ReturnType<typeof useSelectProject>['data']>
  portfolioHomeProject:
    | NonNullable<ReturnType<typeof useGetPortfolioHome>['data']>[number]
    | undefined
}) {
  if (!project.has_real_time_data) return null
  return (
    <Stack h="100%" justify="center" gap={2}>
      <RingProgressStat
        project={project}
        type="power"
        value={portfolioHomeProject?.power ?? undefined}
      />
      {(project.project_type_id === ProjectTypeId.PV ||
        project.project_type_id === ProjectTypeId.PV_BESS) && (
        <RingProgressStat
          project={project}
          type={
            portfolioHomeProject?.performance_index != null
              ? 'performance_index'
              : 'poa'
          }
          value={
            portfolioHomeProject?.performance_index ??
            portfolioHomeProject?.poa ??
            undefined
          }
        />
      )}
      {(project.project_type_id === ProjectTypeId.BESS ||
        project.project_type_id === ProjectTypeId.PV_BESS) && (
        <RingProgressStat
          project={project}
          type="soc"
          value={portfolioHomeProject?.soc ?? undefined}
        />
      )}
    </Stack>
  )
}
