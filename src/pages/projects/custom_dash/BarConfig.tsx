import { SensorType } from '@/hooks/types'
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

import { BarConfig as BarConfigType } from './CustomDash'

const BarConfig = ({
  stack,
  sensorTypes,
  onAdd,
}: {
  stack: { close: (drawerId: 'bar-config') => void }
  sensorTypes: UseQueryResult<SensorType[], AxiosError<unknown>>
  onAdd: (config: BarConfigType) => void
}) => {
  const [sensorTypeId, setSensorTypeId] = useState<string | null>(null)
  const [aggregationMethod, setAggregationMethod] = useState<string | null>(
    null,
  )

  const addBarChart = () => {
    if (!sensorTypeId || !aggregationMethod) {
      // You might want to show an error message here
      return
    }

    const config: BarConfigType = {
      sensorTypeId,
      aggregationMethod,
    }

    onAdd(config)
  }
  const sensorTypesData = sensorTypes.data
    ?.sort((a, b) => a.name_long.localeCompare(b.name_long))
    .filter((sensorType) => sensorType.sensor_type_id !== 0)
  const allowCreate = !!sensorTypeId && !!aggregationMethod
  return (
    <Stack>
      <Title>Add Bar Chart</Title>
      <Text>
        Select a sensor type and aggregation method to add a bar chart.
      </Text>
      <Stack gap="md">
        <Select
          data={sensorTypesData?.map((sensorType) => ({
            value: sensorType.sensor_type_id.toString(),
            label: sensorType.name_long,
          }))}
          label="Sensor Type"
          placeholder="Select Sensor Type..."
          value={sensorTypeId}
          onChange={setSensorTypeId}
          searchable
          clearable
        />
        <Select
          data={[
            { value: 'sum', label: 'Sum' },
            { value: 'mean', label: 'Mean' },
            { value: 'median', label: 'Median' },
            { value: 'min', label: 'Minimum' },
            { value: 'max', label: 'Maximum' },
            { value: 'std', label: 'Standard Deviation' },
            { value: 'count', label: 'Count' },
          ]}
          label="Aggregation Method"
          placeholder="Select Aggregation Method..."
          value={aggregationMethod}
          onChange={setAggregationMethod}
          clearable
        />
      </Stack>
      <Group justify="flex-end">
        <Button variant="default" onClick={() => stack.close('bar-config')}>
          Return
        </Button>
        <Tooltip
          label="All fields must be completed to add component."
          disabled={allowCreate}
        >
          <Button onClick={addBarChart} disabled={!allowCreate}>
            Add
          </Button>
        </Tooltip>
      </Group>
    </Stack>
  )
}

export default BarConfig
