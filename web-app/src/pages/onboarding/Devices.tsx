import { AppShell, Container, Paper, Stack, Text, Title } from '@mantine/core'
import { Dropzone, MIME_TYPES } from '@mantine/dropzone'
import { IconUpload, IconX } from '@tabler/icons-react'
import { useState } from 'react'
import { useParams } from 'react-router'

import {
  DeviceListTable,
  DeviceTypeSummaryTable,
  OnboardingPageHeader,
} from './components'

interface DeviceData {
  device: string
  deviceType: string
  parentDevice: string
  latitude: number
  longitude: number
}

interface DeviceTypeSummary {
  deviceType: string
  numberOfDevices: number
}

function CreatePVsystemDefinition() {
  const { projectId } = useParams<{ projectId: string }>()
  const [data] = useState<DeviceData[]>([])
  const [deviceTypeSummary, setDeviceTypeSummary] = useState<
    DeviceTypeSummary[]
  >([
    { deviceType: 'Met Stations', numberOfDevices: 0 },
    { deviceType: 'Transformers', numberOfDevices: 0 },
    { deviceType: 'Inverters', numberOfDevices: 0 },
    { deviceType: 'Combiners', numberOfDevices: 0 },
    { deviceType: 'Trackers', numberOfDevices: 0 },
  ])

  const handleDeviceTypeSummaryChange = (updatedData: DeviceTypeSummary[]) => {
    setDeviceTypeSummary(updatedData)
  }

  const handleFileDrop = (_files: File[]) => {
    // Handle file upload logic here
  }

  return (
    <AppShell padding={0}>
      <AppShell.Main>
        <Container size="md" py="xl">
          <Stack gap="lg">
            <OnboardingPageHeader
              title="Device Onboarding Overview"
              description="Edit devices"
              projectId={projectId}
            />

            <Paper p="md" withBorder>
              <Stack gap="md">
                <Title order={3}>Upload Device GIS File</Title>
                <Dropzone
                  onDrop={handleFileDrop}
                  accept={[MIME_TYPES.csv, MIME_TYPES.xlsx]}
                  maxSize={5 * 1024 ** 2}
                >
                  <Stack align="center" gap="sm">
                    <Dropzone.Accept>
                      <IconUpload size={50} />
                    </Dropzone.Accept>
                    <Dropzone.Reject>
                      <IconX size={50} />
                    </Dropzone.Reject>
                    <Text size="sm" c="dimmed">
                      Upload Proximal GeoJSON
                    </Text>
                  </Stack>
                </Dropzone>
              </Stack>
            </Paper>

            <Paper p="md" withBorder>
              <Stack gap="md">
                <Title order={3}>Device Type Summary</Title>
                <Text c="dimmed">
                  Click on device type to go to the summary page for that
                  device. Double click on a cell to edit the value.
                </Text>
                <DeviceTypeSummaryTable
                  data={deviceTypeSummary}
                  onDataChange={handleDeviceTypeSummaryChange}
                />
              </Stack>
            </Paper>

            <Paper p="md" withBorder>
              <Stack gap="md">
                <Title order={3}>Device List</Title>
                <DeviceListTable data={data} />
              </Stack>
            </Paper>
          </Stack>
        </Container>
      </AppShell.Main>
    </AppShell>
  )
}

export default CreatePVsystemDefinition
