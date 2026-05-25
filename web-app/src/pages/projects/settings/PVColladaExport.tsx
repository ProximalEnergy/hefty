import { useDownloadPVColladaExport } from '@/api/pvcollada'
import {
  Anchor,
  Button,
  Card,
  Group,
  List,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconDownload, IconExternalLink } from '@tabler/icons-react'

const PVCOLLADA_REPO_URL = 'https://github.com/pvlib/pvcollada'
const PVCOLLADA_DOCS_URL = 'https://pvlib.github.io/pvcollada/'

interface PVColladaExportProps {
  projectId: string
}

export default function PVColladaExport({ projectId }: PVColladaExportProps) {
  const downloadPVColladaExport = useDownloadPVColladaExport()

  const handleDownload = () => {
    downloadPVColladaExport.mutate(
      { projectId },
      {
        onError: () => {
          notifications.show({
            title: 'Export failed',
            message: 'Unable to export the PVCollada file.',
            color: 'red',
          })
        },
      },
    )
  }

  return (
    <Stack gap="md" mt="md" h="100%">
      <Title order={3}>PVCollada Export</Title>

      <Group align="start" gap="md" flex={1}>
        <Card withBorder w="500px" h="100%">
          <Stack gap="md">
            <Title order={4}>About PVCollada</Title>
            <Text size="sm" c="dimmed">
              PVCollada 2.0 is a COLLADA 1.5-based open format for exchanging PV
              plant layout, components, and electrical structure between tools.
            </Text>

            <Stack gap="xs">
              <Text size="sm" fw={500}>
                Specification
              </Text>
              <Text size="sm" c="dimmed">
                Schemas, examples, and the developer guide are maintained in the{' '}
                <Anchor
                  href={PVCOLLADA_REPO_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  size="sm"
                >
                  pvlib/pvcollada
                </Anchor>{' '}
                repository, with documentation at{' '}
                <Anchor
                  href={PVCOLLADA_DOCS_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  size="sm"
                >
                  pvlib.github.io/pvcollada
                </Anchor>
                .
              </Text>
              <Anchor
                href={PVCOLLADA_REPO_URL}
                target="_blank"
                rel="noopener noreferrer"
                size="sm"
              >
                <Group gap={4} align="center" wrap="nowrap">
                  <Text inherit>View repository</Text>
                  <IconExternalLink size={14} />
                </Group>
              </Anchor>
            </Stack>

            <Stack gap="xs">
              <Text size="sm" fw={500}>
                Development
              </Text>
              <Text size="sm" c="dimmed">
                PVCollada builds on industry and research collaboration. PVsyst
                and PVCase created the original PV Collada exchange format for
                3D PV scenes. Sandia National Laboratories published early
                PVCollada schema work. The pvlib open-source community maintains
                the PVCollada 2.0 specification today.
              </Text>
            </Stack>

            <Stack gap="xs">
              <Text size="sm" fw={500}>
                This export includes
              </Text>
              <List size="sm" c="dimmed" spacing="xs">
                <List.Item>
                  The project device hierarchy as a COLLADA scene tree
                </List.Item>
                <List.Item>
                  Proximal metadata for every device in the structure
                </List.Item>
                <List.Item>
                  The project geographic origin for coordinate conversion
                </List.Item>
                <List.Item>
                  Rack geometry as metadata when available in Proximal
                </List.Item>
              </List>
            </Stack>
            <Text size="sm" c="dimmed">
              PVCollada uses an East-North-Up coordinate system. Detailed rack
              geometry is included as metadata when available in Proximal.
            </Text>
          </Stack>
        </Card>

        <Card withBorder style={{ flex: 1, height: '100%' }}>
          <Stack gap="md" h="100%">
            <Title order={4}>Export Project File</Title>
            <Text size="sm" c="dimmed">
              Download a PVCollada 2.0 file for this project. The file uses the
              `.pvc2` extension and can be opened in PVCollada-compatible tools.
            </Text>

            <Stack gap="xs">
              <Text size="sm" fw={500}>
                File format
              </Text>
              <Text size="sm" c="dimmed">
                PVCollada 2.0 XML with COLLADA scene data and Proximal device
                extensions.
              </Text>
            </Stack>

            <Group justify="flex-start" gap={6}>
              <Button
                size="xs"
                leftSection={<IconDownload size={14} />}
                loading={downloadPVColladaExport.isPending}
                onClick={handleDownload}
              >
                Export .pvc2
              </Button>
            </Group>
          </Stack>
        </Card>
      </Group>
    </Stack>
  )
}
