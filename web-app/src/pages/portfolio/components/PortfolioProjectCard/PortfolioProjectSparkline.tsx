import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetPortfolioHome } from '@/api/v1/protected/web-application/portfolio/home'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { usePortfolioPlotData } from '@/pages/portfolio/components/PortfolioProjectCard/usePortfolioPlotData'
import { Center, Text } from '@mantine/core'
import { Data } from 'plotly.js'

export function PortfolioProjectSparkline({
  project,
  portfolioHomeProject,
  time,
}: {
  project: NonNullable<ReturnType<typeof useSelectProject>['data']>
  portfolioHomeProject:
    | NonNullable<ReturnType<typeof useGetPortfolioHome>['data']>[number]
    | undefined
  time: '24h' | '30d'
}) {
  const { data, layout, config, hasData } = usePortfolioPlotData({
    project,
    portfolioHomeProject,
    time,
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

  return (
    <PlotlyPlot
      key={time}
      data={data as Data[]}
      layout={layout}
      config={config}
    />
  )
}
