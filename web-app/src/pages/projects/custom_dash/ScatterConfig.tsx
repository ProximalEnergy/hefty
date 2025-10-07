import { SensorType } from '@/api/v1/operational/sensor_types'
import {
  Button,
  Group,
  Select,
  Stack,
  Text,
  Title,
  Tooltip,
} from '@mantine/core'
import { UseQueryResult } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { useState } from 'react'

import { ScatterConfig as ScatterConfigType } from './CustomDash'

const ScatterConfig = ({
  stack,
  sensorTypes,
  onAdd,
}: {
  stack: { close: (drawerId: 'scatter-config') => void }
  sensorTypes: UseQueryResult<SensorType[], AxiosError<unknown>>
  onAdd: (config: ScatterConfigType) => void
}) => {
  const [xAxisSensorTypeId, setXAxisSensorTypeId] = useState<string | null>(
    null,
  )
  const [yAxisSensorTypeId, setYAxisSensorTypeId] = useState<string | null>(
    null,
  )

  const addScatterChart = () => {
    if (!xAxisSensorTypeId || !yAxisSensorTypeId) {
      // You might want to show an error message here
      return
    }

    const config: ScatterConfigType = {
      xAxisSensorTypeId,
      yAxisSensorTypeId,
    }

    onAdd(config)
  }
  const sensorTypesData = sensorTypes.data
    ?.sort((a, b) => a.name_long.localeCompare(b.name_long))
    .filter((sensorType) => sensorType.sensor_type_id !== 0)
  const allowCreate = !!xAxisSensorTypeId && !!yAxisSensorTypeId
  return (
    <Stack>
      <Title>Add Scatter Plot</Title>
      <Text>Select two sensor types to add a scatter plot.</Text>
      <Text c="red">
        WARNING: Selecting sensor types with many devices may degrade
        performance, and will be downsampled to 1,000 representative points.
      </Text>
      <Stack gap="md">
        <Select
          data={sensorTypesData?.map((sensorType) => ({
            value: sensorType.sensor_type_id.toString(),
            label: sensorType.name_long,
          }))}
          label="X Axis"
          placeholder="Select Sensor Type..."
          value={xAxisSensorTypeId}
          onChange={setXAxisSensorTypeId}
          searchable
        />
        <Select
          data={sensorTypesData?.map((sensorType) => ({
            value: sensorType.sensor_type_id.toString(),
            label: sensorType.name_long,
          }))}
          label="Y Axis"
          placeholder="Select Sensor Type..."
          value={yAxisSensorTypeId}
          onChange={setYAxisSensorTypeId}
          searchable
        />
      </Stack>
      <Group justify="flex-end">
        <Button variant="default" onClick={() => stack.close('scatter-config')}>
          Return
        </Button>
        <Tooltip
          label="All fields must be completed to add component."
          disabled={allowCreate}
        >
          <Button onClick={addScatterChart} disabled={!allowCreate}>
            Add Scatter Plot Component
          </Button>
        </Tooltip>
      </Group>
    </Stack>
  )
}

export default ScatterConfig
