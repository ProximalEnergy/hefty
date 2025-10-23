import ConstructionBanner from '@/components/ConstructionBanner'
import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { Stack, useMantineTheme } from '@mantine/core'

const ProjectAvailabilityAnalysis = () => {
  const theme = useMantineTheme()

  return (
    <Stack p="md" h="100%">
      <ConstructionBanner />
      <CustomCard beta title="Availability Analysis" style={{ height: '100%' }}>
        <PlotlyPlot
          data={[
            {
              x: [
                'Inverter Trip',
                'Inverter Failure',
                'MVT overheating',
                'Ground Fault',
                'MV Collector Fault',
                'GSU Fault',
                'Tracker Malfunction',
                'PV String Faults',
                'DC Fuse Faults',
                'Other Faults',
              ],
              y: [2, 15, 3, 9, 1, 1, 3, 2, 5, 4],
              name: 'Number of Faults',
              type: 'bar',
              hoverlabel: { namelength: -1 },
            },
            {
              x: [
                'Inverter Trip',
                'Inverter Failure',
                'MVT overheating',
                'Ground Fault',
                'MV Collector Fault',
                'GSU Fault',
                'Tracker Malfunction',
                'PV String Faults',
                'DC Fuse Faults',
                'Other Faults',
              ],
              y: [
                0.07, 0.1, 0.03, 0.03, 0.001, 0.001, 0.005, 0.002, 0.006, 0.04,
              ],
              text: [
                '0.07%',
                '0.10%',
                '0.03%',
                '0.03%',
                '0.001%',
                '0.001%',
                '0.005%',
                '0.002%',
                '0.006%',
                '0.04%',
              ],
              textposition: 'top center',
              mode: 'text+lines+markers',
              name: 'Total Unavailability Contribution',
              yaxis: 'y2',
              type: 'scatter',
              line: { color: theme.colors.blue[7] },
              hoverlabel: { namelength: -1 },
            },
          ]}
          layout={{
            yaxis: { title: { text: 'Number of Faults' } },
            yaxis2: {
              title: { text: 'Total Unavailability Contribution' },
              overlaying: 'y',
              side: 'right',
              showgrid: false,
            },
            showlegend: false,
          }}
        />
      </CustomCard>
    </Stack>
  )
}

export default ProjectAvailabilityAnalysis
