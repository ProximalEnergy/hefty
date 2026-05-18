import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useGetHeatmap } from '@/hooks/api'

type PcsHeatmapProps = {
  projectId: string
  startQuery: string | undefined
  endQuery: string | undefined
}

export function PcsHeatmap({
  projectId,
  startQuery,
  endQuery,
}: PcsHeatmapProps) {
  const { data, isLoading, error } = useGetHeatmap({
    pathParams: {
      projectId: projectId || '-1',
      sensorTypeName: 'pv_inverter_ac_power',
    },
    queryParams: {
      start: startQuery,
      end: endQuery,
    },
  })

  return (
    <PlotlyPlot
      data={[
        {
          z: data?.z,
          x: data?.x,
          y: data?.y,
          type: 'heatmap',
          colorbar: {
            title: {
              text: 'Power (MW)',
            },
            ticksuffix: ' MW',
          },
        },
      ]}
      layout={{
        xaxis: {
          tickangle: -45,
        },
        yaxis: {
          type: 'category',
          dtick: 1,
          tick0: 0,
          title: {
            text: 'Inverter Name',
          },
        },
        height: 450,
      }}
      colorscale="primary"
      isLoading={isLoading}
      error={error}
    />
  )
}
