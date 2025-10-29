import { useGetWaterfall } from '@/api/v1/operational/project/waterfall'
import { useParams } from 'react-router'

import { PageLoader } from '../Loading'
import PlotlyPlot from './PlotlyPlot'

const LossWaterfall = ({
  level,
  startQuery,
  endQuery,
}: {
  level: string
  startQuery: string
  endQuery: string
}) => {
  const { projectId } = useParams()

  const data = useGetWaterfall({
    pathParams: { projectId: projectId || '-1' },
    queryParams: { level: level, start: startQuery, end: endQuery },
  })

  if (data.isLoading) return <PageLoader />

  return (
    <PlotlyPlot
      data={[
        {
          type: 'waterfall',
          name: 'Loss Waterfall',
          measure: data.data?.measure,
          x: data.data?.name,
          y: data.data?.value,
          marker: { line: { color: 'black', width: 20 } },
          connector: {
            line: {
              color: 'rgb(63, 63, 63)',
            },
          },
        } as Partial<Plotly.PlotData>,
      ]}
      layout={{
        title: { text: 'Loss Waterfall' },
        yaxis: {
          title: { text: 'MWh' },
        },

        margin: { t: 30 },
      }}
      error={data.error}
    />
  )
}

export default LossWaterfall
