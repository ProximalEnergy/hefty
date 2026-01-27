import { useGetTimeSeries } from '@/api/v1/operational/project/project_data'
import { useParams } from 'react-router'

import PlotlyPlot from './PlotlyPlot'

const PowerPlantController = () => {
  const { projectId } = useParams<{ projectId: string }>()

  const { data, isLoading, error } = useGetTimeSeries({
    pathParams: { project_id: projectId || '-1' },
    queryParams: {
      sensor_type_name_shorts: [
        'ppc_active_power',
        'ppc_reactive_power',
        'ppc_power_factor',
        'ppc_active_power_setpoint',
        'ppc_reactive_power_setpoint',
        'ppc_power_factor_setpoint',
      ],
    },
  })

  return (
    <PlotlyPlot
      data={data?.map((d) => ({
        x: d.x,
        y: d.y,
        name: d.name,
        hoverlabel: {
          namelength: -1,
        },
        yaxis: d.name.includes('Power Factor') ? 'y2' : 'y',
      }))}
      layout={{
        yaxis: {
          title: { text: 'Power (MW, MVAR, MVA)' },
          side: 'left',
        },
        yaxis2: {
          title: { text: 'Power Factor' },
          side: 'right',
          showgrid: false,
          zeroline: false,
          range: [-1.1, 1.1],
          overlaying: 'y',
        },
      }}
      isLoading={isLoading}
      error={error}
    />
  )
}

export default PowerPlantController
