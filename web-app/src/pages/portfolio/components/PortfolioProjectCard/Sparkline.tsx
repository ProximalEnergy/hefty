import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetPortfolioHome } from '@/api/v1/protected/web-application/portfolio/home'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { Center, Text } from '@mantine/core'

import { usePortfolioPlotData } from './usePortfolioPlotData'

export function Sparkline({
  project,
  portfolioHomeProject,
}: {
  project: NonNullable<ReturnType<typeof useSelectProject>['data']>
  portfolioHomeProject:
    | NonNullable<ReturnType<typeof useGetPortfolioHome>['data']>[number]
    | undefined
}) {
  const { data, layout, config, hasData } = usePortfolioPlotData({
    project,
    portfolioHomeProject,
  })

  if (!hasData) {
    return (
      <Center h="100%" w="100%">
        <Text fw={700} c="red">
          NO DATA FOR PAST 24 HOURS
        </Text>
      </Center>
    )
  }

  return <PlotlyPlot data={data as any} layout={layout} config={config} />
}
