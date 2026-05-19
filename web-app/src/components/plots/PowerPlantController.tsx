import { useGetTimeSeries } from '@/api/v1/operational/project/project_data'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useParams } from 'react-router'

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

  const getTraceColor = (sensorTypeName: string) => {
    switch (sensorTypeName) {
      case 'ppc_active_power':
        return '#69DB7C' // mantine-green-4
      case 'ppc_active_power_setpoint':
        return '#2B8A3E' // mantine-green-9
      case 'ppc_reactive_power':
        return '#4DABF7' // mantine-blue-4
      case 'ppc_reactive_power_setpoint':
        return '#1864AB' // mantine-blue-9
      case 'ppc_power_factor':
        return '#DA77F2' // mantine-grape-4
      case 'ppc_power_factor_setpoint':
        return '#862E9C' // mantine-grape-9
      default:
        return undefined
    }
  }

  return (
    <PlotlyPlot
      data={data?.map((d) => ({
        x: d.x,
        y: d.y,
        name: d.name,
        hoverlabel: {
          namelength: -1,
        },
        line: {
          color: getTraceColor(d.sensor_type_name),
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
