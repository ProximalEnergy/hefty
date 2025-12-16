import { SensorTypeEnum } from '@/api/enumerations'
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

import { BarConfig as BarConfigType } from './CustomDash'

const BarConfig = ({
  mode,
  stack,
  sensorTypes,
  onAdd,
  initialConfig,
}: {
  mode: 'create' | 'edit'
  stack: { close: (drawerId: 'bar-config') => void }
  sensorTypes: UseQueryResult<SensorType[], AxiosError<unknown>>
  onAdd: (config: BarConfigType) => void
  initialConfig?: BarConfigType
}) => {
  const [sensorTypeId, setSensorTypeId] = useState<string | null>(
    initialConfig?.sensorTypeId ?? null,
  )
  const [aggregationMethod, setAggregationMethod] = useState<string | null>(
    initialConfig?.aggregationMethod ?? null,
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
    .filter(
      (sensorType) =>
        sensorType.sensor_type_id !== SensorTypeEnum.GHOST_UNKNOWN,
    )
  const allowCreate = !!sensorTypeId && !!aggregationMethod
  return (
    <Stack>
      {mode === 'create' && <Title>Add Bar Chart</Title>}
      {mode === 'edit' && <Title>Edit Bar Chart</Title>}
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
        />
        <Select
          data={[
            { value: 'sum', label: 'Sum' },
            { value: 'mean', label: 'Mean' },
            { value: 'median', label: 'Median' },
            { value: 'min', label: 'Minimum' },
            { value: 'max', label: 'Maximum' },
            { value: 'std', label: 'Standard Deviation' },
          ]}
          label="Aggregation Method"
          placeholder="Select Aggregation Method..."
          value={aggregationMethod}
          onChange={setAggregationMethod}
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
            {mode === 'edit'
              ? 'Update Bar Chart Component'
              : 'Add Bar Chart Component'}
          </Button>
        </Tooltip>
      </Group>
    </Stack>
  )
}

export default BarConfig
