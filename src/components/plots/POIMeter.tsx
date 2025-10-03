import { useGetTimeSeries } from '@/api/v1/operational/project/project_data'
import { DataTimeSeries } from '@/hooks/types'
import { useParams } from 'react-router-dom'

import PlotlyPlot from './PlotlyPlot'

const POIMeter = () => {
  const { projectId } = useParams()

  const { data, isLoading, error } = useGetTimeSeries({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      sensor_type_name_shorts: [
        'meter_active_power',
        'meter_reactive_power',
        'meter_apparent_power',
        'meter_power_factor',
      ],
    },
  })
  const returnedTypes = data?.map((d) => d.sensor_type_name)

  // Calculate apparent power if active and reactive power are available but apparent power is not
  let calculatedApparentPower: DataTimeSeries | null = null
  if (
    returnedTypes?.includes('meter_active_power') &&
    returnedTypes?.includes('meter_reactive_power') &&
    !returnedTypes?.includes('meter_apparent_power')
  ) {
    const activePowerData = data?.find(
      (d) => d.sensor_type_name === 'meter_active_power',
    )
    const reactivePowerData = data?.find(
      (d) => d.sensor_type_name === 'meter_reactive_power',
    )

    if (activePowerData && reactivePowerData) {
      // Calculate apparent power: sqrt(active_power^2 + reactive_power^2)
      const calculatedY = activePowerData.y.map((active, index) => {
        const reactive = reactivePowerData.y[index]
        return Math.sqrt(Math.pow(active, 2) + Math.pow(reactive, 2))
      })

      calculatedApparentPower = {
        x: activePowerData.x, // Use the same X values
        y: calculatedY,
        y_range: calculatedY, // Assuming y_range should match y for calculated values
        yaxis: 'y',
        name: 'Apparent Power (Calculated)',
        sensor_type_name: 'calculated_apparent_power',
        device_name_long: activePowerData.device_name_long,
        tag_name_scada: activePowerData.tag_name_scada,
        tag_name_long: activePowerData.tag_name_long,
        device_id: activePowerData.device_id,
        sensor_type_id: 10,
      }
    }
  }

  // Combine original data with calculated apparent power
  const plotData = data ? [...data] : []
  if (calculatedApparentPower) {
    plotData.push(calculatedApparentPower)
  }

  const nameMapping: { [key: string]: string } = {
    meter_active_power: 'Active Power (MW)',
    meter_reactive_power: 'Reactive Power (MVAR)',
    meter_apparent_power: 'Apparent Power (MVA)',
    meter_power_factor: 'Power Factor',
    calculated_apparent_power: 'Apparent Power (MVA)',
  }

  return (
    <PlotlyPlot
      data={plotData.map((d) => ({
        x: d.x,
        y: d.y,
        name: nameMapping[d.sensor_type_name] || d.name,
        hoverlabel: {
          namelength: -1,
        },
        yaxis: d.sensor_type_name === 'meter_power_factor' ? 'y2' : 'y',
      }))}
      layout={{
        showlegend: true,
        yaxis: {
          title: 'Power (MW, MVAR, MVA)',
          side: 'left',
        },
        yaxis2: {
          title: 'Power Factor',
          overlaying: 'y',
          side: 'right',
          showgrid: false,
          zeroline: false,
          range: [-1.1, 1.1],
        },
      }}
      isLoading={isLoading}
      error={error}
    />
  )
}

export default POIMeter
