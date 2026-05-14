import { SensorTypeEnum } from '@/api/enumerations'
import { useGetTimeSeries } from '@/api/v1/operational/project/project_data'
import { DataTimeSeries } from '@/hooks/types'
import { Layout } from 'plotly.js'
import { useParams } from 'react-router'

import PlotlyPlot from './PlotlyPlot'

interface POIMeterProps {
  showGridHzV?: boolean
}

const POIMeter = ({ showGridHzV = false }: POIMeterProps) => {
  const { projectId } = useParams<{ projectId: string }>()

  // Base sensor type IDs: active, reactive, apparent, power factor.
  // Additional when showGridHzV: frequency (11), voltage (192)
  const baseSensorTypeIds = [
    SensorTypeEnum.METER_ACTIVE_POWER,
    SensorTypeEnum.METER_REACTIVE_POWER,
    SensorTypeEnum.METER_APPARENT_POWER,
    SensorTypeEnum.METER_POWER_FACTOR,
  ]
  const gridHzVSensorTypeIds = [
    SensorTypeEnum.METER_FREQUENCY,
    SensorTypeEnum.PROJECT_LINE_TO_LINE_VOLTAGE,
  ]
  const sensorTypeIds = showGridHzV
    ? [...baseSensorTypeIds, ...gridHzVSensorTypeIds]
    : baseSensorTypeIds

  const { data, isLoading, error } = useGetTimeSeries({
    pathParams: { project_id: projectId || '-1' },
    queryParams: {
      sensor_type_ids: sensorTypeIds,
    },
  })

  // Calculate apparent power when active and reactive power are available.
  let calculatedApparentPower: DataTimeSeries | null = null
  const activePowerData = data?.find(
    (d) => d.sensor_type_id === SensorTypeEnum.METER_ACTIVE_POWER,
  )
  const reactivePowerData = data?.find(
    (d) => d.sensor_type_id === SensorTypeEnum.METER_REACTIVE_POWER,
  )
  const apparentPowerData = data?.find(
    (d) => d.sensor_type_id === SensorTypeEnum.METER_APPARENT_POWER,
  )

  if (activePowerData && reactivePowerData && !apparentPowerData) {
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
      sensor_type_id: SensorTypeEnum.METER_APPARENT_POWER,
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
    meter_frequency: 'Frequency (Hz)',
  }

  // Get display name for a data series
  const getDisplayName = (d: DataTimeSeries): string => {
    if (d.sensor_type_id === SensorTypeEnum.PROJECT_LINE_TO_LINE_VOLTAGE) {
      return 'Voltage (kV)'
    }
    return nameMapping[d.sensor_type_name] || d.name
  }

  // Filter data based on showGridHzV
  let filteredPlotData = showGridHzV
    ? plotData
    : plotData.filter(
        (d) =>
          d.sensor_type_id !== SensorTypeEnum.METER_FREQUENCY &&
          d.sensor_type_id !== SensorTypeEnum.PROJECT_LINE_TO_LINE_VOLTAGE,
      )

  // If multiple sensors with ID 192 exist, only keep the first one
  if (showGridHzV) {
    const voltageSensors = filteredPlotData.filter(
      (d) => d.sensor_type_id === SensorTypeEnum.PROJECT_LINE_TO_LINE_VOLTAGE,
    )
    if (voltageSensors.length > 1) {
      // Remove all voltage sensors except the first one
      const firstVoltageIndex = filteredPlotData.findIndex(
        (d) => d.sensor_type_id === SensorTypeEnum.PROJECT_LINE_TO_LINE_VOLTAGE,
      )
      filteredPlotData = filteredPlotData.filter(
        (d, index) =>
          d.sensor_type_id !== SensorTypeEnum.PROJECT_LINE_TO_LINE_VOLTAGE ||
          index === firstVoltageIndex,
      )
    }
  }

  // Separate data into main plot and Hz/V subplot
  const mainPlotData = filteredPlotData.filter(
    (d) =>
      d.sensor_type_id !== SensorTypeEnum.METER_FREQUENCY &&
      d.sensor_type_id !== SensorTypeEnum.PROJECT_LINE_TO_LINE_VOLTAGE,
  )
  const hzVPlotData = filteredPlotData.filter(
    (d) =>
      d.sensor_type_id === SensorTypeEnum.METER_FREQUENCY ||
      d.sensor_type_id === SensorTypeEnum.PROJECT_LINE_TO_LINE_VOLTAGE,
  )

  const traceColors: Record<number, string> = {
    [SensorTypeEnum.METER_ACTIVE_POWER]: '#69DB7C',
    [SensorTypeEnum.METER_REACTIVE_POWER]: '#4DABF7',
    [SensorTypeEnum.METER_APPARENT_POWER]: '#FCC419',
    [SensorTypeEnum.METER_POWER_FACTOR]: '#DA77F2',
    [SensorTypeEnum.METER_FREQUENCY]: '#22B8CF',
    [SensorTypeEnum.PROJECT_LINE_TO_LINE_VOLTAGE]: '#FF922B',
  }

  const getTraceColor = (sensorTypeId: number): string | undefined => {
    return traceColors[sensorTypeId]
  }

  const getAxis = (sensorTypeId: number) => {
    if (sensorTypeId === SensorTypeEnum.METER_POWER_FACTOR) {
      return { yaxis: 'y2', xaxis: 'x' }
    }
    if (sensorTypeId === SensorTypeEnum.METER_FREQUENCY) {
      return { yaxis: 'y3', xaxis: 'x2' }
    }
    if (sensorTypeId === SensorTypeEnum.PROJECT_LINE_TO_LINE_VOLTAGE) {
      return { yaxis: 'y4', xaxis: 'x2' }
    }
    return { yaxis: 'y', xaxis: 'x' }
  }

  // Build data array
  const plotDataArray = [
    ...mainPlotData.map((d) => {
      const axis = getAxis(d.sensor_type_id)
      const color = getTraceColor(d.sensor_type_id)
      return {
        x: d.x,
        y: d.y,
        name: getDisplayName(d),
        hoverlabel: {
          namelength: -1,
        },
        ...(color && { line: { color } }),
        ...axis,
      }
    }),
    ...(showGridHzV
      ? hzVPlotData.map((d) => {
          const axis = getAxis(d.sensor_type_id)
          const color = getTraceColor(d.sensor_type_id)
          return {
            x: d.x,
            y: d.y,
            name: getDisplayName(d),
            hoverlabel: {
              namelength: -1,
            },
            ...(color && { line: { color } }),
            ...axis,
          }
        })
      : []),
  ]

  // Build layout
  const baseLayout: Partial<Layout> = {
    showlegend: true,
    legend: {
      font: {
        size: 10,
      },
    },
    ...(showGridHzV && {
      grid: {
        rows: 2,
        columns: 1,
        pattern: 'independent',
        roworder: 'top to bottom',
      },
      xaxis: {
        domain: [0, 1],
        anchor: 'y',
      },
      xaxis2: {
        domain: [0, 1],
        anchor: 'y3',
        matches: 'x',
        showticklabels: false,
      },
      yaxis: {
        title: { text: 'Power' },
        side: 'left',
        domain: [0, 0.65],
      },
      yaxis2: {
        title: { text: 'Power Factor' },
        overlaying: 'y',
        side: 'right',
        showgrid: false,
        zeroline: false,
        range: [-1.1, 1.1],
        domain: [0, 0.65],
      },
      yaxis3: {
        title: { text: 'Frequency (Hz)', font: { color: '#2196F3' } },
        side: 'left',
        domain: [0.7, 1],
        anchor: 'x2',
        range: [59.9, 60.1],
      },
      yaxis4: {
        title: { text: 'Voltage (kV)', font: { color: '#FF5722' } },
        side: 'right',
        domain: [0.7, 1],
        anchor: 'x2',
        overlaying: 'y3',
        showgrid: false,
        zeroline: false,
      },
    }),
    ...(!showGridHzV && {
      yaxis: {
        title: { text: 'Power' },
        side: 'left',
      },
      yaxis2: {
        title: { text: 'Power Factor' },
        overlaying: 'y',
        side: 'right',
        showgrid: false,
        zeroline: false,
        range: [-1.1, 1.1],
      },
    }),
  }

  // Create a unique key that includes projectId and whether grid layout is used
  // Ensures Plotly re-renders across projects with different grid support.
  const hasGridLayout = !!baseLayout.grid
  const plotKey = `poi-meter-${projectId}-${showGridHzV}-${hasGridLayout}`

  return (
    <PlotlyPlot
      key={plotKey}
      data={plotDataArray}
      layout={baseLayout}
      isLoading={isLoading}
      error={error}
    />
  )
}

export default POIMeter
