import ConstructionBanner from '@/components/ConstructionBanner'
import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { Stack, useMantineTheme } from '@mantine/core'

const ProjectLossWaterfall = () => {
  const theme = useMantineTheme()

  const categories = [
    'Expected DC Energy',
    'DC Collection Loss',
    'Inverter Loss',
    'Inverter Downtime',
    'MVT Loss',
    'MVT Downtime',
    'Measured @ MV Meters',
    'Substation Loss',
    'Station Power Loss',
    'Measured @ HV Meter',
    'Calculated Gen-tie Loss',
    'Settled Energy',
  ]

  return (
    <Stack p="md" h="100%">
      <ConstructionBanner />
      <CustomCard beta title="Loss Waterfall" style={{ height: '100%' }}>
        <PlotlyPlot
          data={[
            {
              type: 'waterfall',
              orientation: 'v',
              // @ts-expect-error TS2353
              measure: [
                'absolute',
                'relative',
                'relative',
                'relative',
                'relative',
                'relative',
                'total',
                'relative',
                'relative',
                'total',
                'relative',
                'total',
              ],
              textposition: 'outside',
              text: categories,
              x: categories,
              y: [100, -5, -5, -5, -5, -5, 0, -5, -5, 0, -5, 0],
              decreasing: { marker: { color: theme.colors.red[7] } },
              totals: { marker: { color: theme.colors.green[7] } },
              hovertemplate: [
                'absolute',
                'relative',
                'relative',
                'relative',
                'relative',
                'relative',
                'total',
                'relative',
                'relative',
                'total',
                'relative',
                'total',
              ].map((m) =>
                m === 'relative'
                  ? '<b>%{x}</b><br>%{delta:.2f} MWh<extra></extra>'
                  : '<b>%{x}</b><br>%{final:.2f} MWh<extra></extra>',
              ),
            },
          ]}
          layout={{
            xaxis: {
              tickvals: [],
            },
            yaxis: {
              title: { text: 'Energy (MWh)' },
            },
          }}
        />
      </CustomCard>
    </Stack>
  )
}

export default ProjectLossWaterfall
