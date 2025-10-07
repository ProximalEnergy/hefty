import { SensorType } from '@/api/v1/operational/sensor_types'
import {
  ActionIcon,
  Box,
  Button,
  Group,
  Select,
  Skeleton,
  Stack,
  Text,
  Title,
  Tooltip,
} from '@mantine/core'
import { IconPlus, IconX } from '@tabler/icons-react'
import { UseQueryResult } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { useState } from 'react'

import { LineConfig as LineConfigType } from './CustomDash'

interface Trace {
  id: string
  sensorTypeId: string | null
  aggregationMethod: string | null
}

const LineConfig = ({
  stack,
  sensorTypes,
  onAdd,
}: {
  stack: { close: (drawerId: 'line-config') => void }
  sensorTypes: UseQueryResult<SensorType[], AxiosError<unknown>>
  onAdd: (config: LineConfigType) => void
}) => {
  const [traces, setTraces] = useState<Trace[]>([
    { id: '1', sensorTypeId: null, aggregationMethod: 'none' },
  ])
  const allowCreate = traces.every(
    (trace) => trace.sensorTypeId && trace.aggregationMethod,
  )
  const addTrace = () => {
    const newTrace: Trace = {
      id: Date.now().toString(),
      sensorTypeId: null,
      aggregationMethod: 'none',
    }
    setTraces([...traces, newTrace])
  }

  const removeTrace = (traceId: string) => {
    if (traces.length > 1) {
      setTraces(traces.filter((trace) => trace.id !== traceId))
    }
  }

  const updateTrace = (
    traceId: string,
    field: keyof Trace,
    value: string | null,
  ) => {
    setTraces(
      traces.map((trace) =>
        trace.id === traceId ? { ...trace, [field]: value } : trace,
      ),
    )
  }

  const addLineChart = () => {
    // Validate that all traces have required fields
    const validTraces = traces.filter(
      (trace) => trace.sensorTypeId && trace.aggregationMethod,
    )

    if (validTraces.length === 0) {
      // You might want to show an error message here
      return
    }

    const config: LineConfigType = {
      traces: validTraces,
    }

    onAdd(config)
  }
  const sensorTypesData = sensorTypes.data
    ?.sort((a, b) => a.name_long.localeCompare(b.name_long))
    .filter((sensorType) => sensorType.sensor_type_id !== 0)
  return (
    <Stack>
      <Title>Add Line Chart</Title>
      <Text>
        Select a sensor type and an aggregation method to add a line chart. You
        may add multiple traces to the chart by pressing the green plus button.
      </Text>

      {sensorTypes.isLoading ? (
        <Skeleton height={90} />
      ) : (
        <Stack gap="md">
          {traces.map((trace) => (
            <Box
              key={trace.id}
              p="md"
              style={{ border: '1px solid #e9ecef', borderRadius: '8px' }}
            >
              <Group>
                <ActionIcon
                  variant="light"
                  color="green"
                  onClick={addTrace}
                  title="Add another trace"
                >
                  <IconPlus size={16} />
                </ActionIcon>

                {traces.length > 1 && (
                  <ActionIcon
                    variant="light"
                    color="red"
                    onClick={() => removeTrace(trace.id)}
                    title="Remove this trace"
                  >
                    <IconX size={16} />
                  </ActionIcon>
                )}

                <Select
                  data={
                    sensorTypesData?.map((sensorType) => ({
                      value: sensorType.sensor_type_id.toString(),
                      label: sensorType.name_long,
                    })) || []
                  }
                  label="Sensor Type"
                  placeholder="Select Sensor Type..."
                  value={trace.sensorTypeId}
                  onChange={(value) =>
                    updateTrace(trace.id, 'sensorTypeId', value)
                  }
                  flex={1}
                  searchable
                  clearable
                />

                <Select
                  data={[
                    { value: 'none', label: 'None' },
                    { value: 'sum', label: 'Sum' },
                    { value: 'avg', label: 'Mean' },
                    { value: 'median', label: 'Median' },
                    { value: 'min', label: 'Minimum' },
                    { value: 'max', label: 'Maximum' },
                    { value: 'std', label: 'Standard Deviation' },
                    { value: 'count', label: 'Count' },
                  ]}
                  label="Aggregation Method"
                  placeholder="Select Aggregation Method..."
                  value={trace.aggregationMethod}
                  onChange={(value) =>
                    updateTrace(trace.id, 'aggregationMethod', value)
                  }
                  flex={1}
                  clearable
                />
              </Group>
            </Box>
          ))}
        </Stack>
      )}

      <Group justify="flex-end">
        <Button variant="default" onClick={() => stack.close('line-config')}>
          Return
        </Button>
        <Tooltip
          label="At least one trace must be selected."
          disabled={allowCreate}
        >
          <Button onClick={addLineChart} disabled={!allowCreate}>
            Add Line Chart Component
          </Button>
        </Tooltip>
      </Group>
    </Stack>
  )
}

export default LineConfig
