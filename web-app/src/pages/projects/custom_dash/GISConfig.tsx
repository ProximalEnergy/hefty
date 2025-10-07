import { Button, Group, Select, Stack, Text, Title } from '@mantine/core'
import { useState } from 'react'

import { GISConfig as GISConfigType } from './CustomDash'

const GISConfig = ({
  stack,
  onAdd,
}: {
  stack: { close: (drawerId: 'gis-config') => void }
  onAdd: (config: GISConfigType) => void
}) => {
  const [deviceTypeId, setDeviceTypeId] = useState<string | null>(null)
  const [traceSensorTypeId, setTraceSensorTypeId] = useState<string | null>(
    null,
  )

  const addGISChart = () => {
    if (!deviceTypeId) {
      // You might want to show an error message here
      return
    }

    const config: GISConfigType = {
      deviceTypeId,
      traceSensorTypeId,
    }

    onAdd(config)
  }

  return (
    <Stack>
      <Title>Add GIS Map</Title>
      <Text>
        Select a device type to add a GIS map. Once the device type is selected,
        you may select a trace to add color to the devices.
      </Text>
      <Stack gap="md">
        <Select
          data={[
            { value: '1', label: 'PV Inverter' },
            { value: '2', label: 'PCS' },
            { value: '3', label: 'BESS Module' },
          ]}
          label="Device Type"
          placeholder="Select Device Type..."
          value={deviceTypeId}
          onChange={setDeviceTypeId}
          clearable
        />
        <Select
          data={[
            { value: 'none', label: 'No Trace' },
            { value: 'power', label: 'Power' },
            { value: 'voltage', label: 'Voltage' },
            { value: 'current', label: 'Current' },
          ]}
          label="Trace (Optional)"
          placeholder="Select trace for coloring..."
          value={traceSensorTypeId}
          onChange={setTraceSensorTypeId}
          clearable
        />
      </Stack>
      <Group justify="flex-end">
        <Button variant="default" onClick={() => stack.close('gis-config')}>
          Return
        </Button>
        <Button onClick={addGISChart}>Add GIS Map Component</Button>
      </Group>
    </Stack>
  )
}

export default GISConfig
