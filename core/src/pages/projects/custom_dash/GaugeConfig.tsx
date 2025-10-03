import { Button, Group, Select, Stack, Title, Tooltip } from '@mantine/core'
import { useState } from 'react'

import { GaugeConfig as GaugeConfigType } from './CustomDash'

const GaugeConfig = ({
  stack,
  onAdd,
}: {
  stack: { close: (drawerId: 'gauge-config') => void }
  onAdd: (config: GaugeConfigType) => void
}) => {
  const [measuredVariable, setMeasuredVariable] = useState<string | null>(null)
  const [maximumValue, setMaximumValue] = useState<string | null>(null)

  const addGauge = () => {
    if (!measuredVariable || !maximumValue) {
      // You might want to show an error message here
      return
    }

    const config: GaugeConfigType = {
      measuredVariable,
      maximumValue,
    }

    onAdd(config)
  }
  const allowCreate = !!measuredVariable && !!maximumValue
  return (
    <Stack>
      <Title>Add Gauge</Title>
      <Select
        data={[{ value: 'meter_actual_power', label: 'Meter Energy' }]}
        label="Measured Variable"
        placeholder="Select measured variable..."
        value={measuredVariable}
        onChange={setMeasuredVariable}
      />
      <Select
        data={[
          // { value: 'contract_capacity', label: 'Energy at Contract Capacity' },
          { value: 'expected_energy', label: 'Expected Energy' },
        ]}
        label="Maximum Value"
        placeholder="Select maximum value..."
        value={maximumValue}
        onChange={setMaximumValue}
      />

      <Group justify="flex-end">
        <Button variant="default" onClick={() => stack.close('gauge-config')}>
          Return
        </Button>
        <Tooltip
          label="All fields must be completed to add component."
          disabled={allowCreate}
        >
          <Button onClick={addGauge} disabled={!allowCreate}>
            Add Gauge Component
          </Button>
        </Tooltip>
      </Group>
    </Stack>
  )
}

export default GaugeConfig
