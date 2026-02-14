import { NumberInput, Paper, Table } from '@mantine/core'
import { useNavigate, useParams } from 'react-router'

interface DeviceTypeSummary {
  deviceType: string
  numberOfDevices: number
}

interface DeviceTypeSummaryTableProps {
  data: DeviceTypeSummary[]
  onDataChange?: (updatedData: DeviceTypeSummary[]) => void
}

const getDeviceTypeRoute = (deviceType: string): string => {
  const routeMap: Record<string, string> = {
    'Met Stations': 'met-stations',
    Transformers: 'transformers',
    Inverters: 'inverters',
    Combiners: 'combiners',
    Trackers: 'trackers',
  }
  return routeMap[deviceType] || deviceType.toLowerCase().replace(/\s+/g, '-')
}

export function DeviceTypeSummaryTable({
  data,
  onDataChange,
}: DeviceTypeSummaryTableProps) {
  const navigate = useNavigate()
  const { projectId } = useParams<{ projectId: string }>()

  const handleRowClick = (row: DeviceTypeSummary) => {
    const route = getDeviceTypeRoute(row.deviceType)
    navigate(`/onboarding/${projectId}/device-types/${route}`)
  }

  const handleDeviceCountChange = (index: number, value: number) => {
    if (!onDataChange) return
    const updatedData = data.map((item, i) => {
      if (i === index) {
        return { ...item, numberOfDevices: value }
      }
      return item
    })
    onDataChange(updatedData)
  }

  return (
    <Paper withBorder shadow="none" radius="md">
      <Table striped>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Device Type</Table.Th>
            <Table.Th>Number of Devices</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {data.map((row, index) => (
            <Table.Tr key={row.deviceType}>
              <Table.Td style={{ padding: 0 }}>
                <div
                  onClick={() => handleRowClick(row)}
                  style={{
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'flex-start',
                    alignItems: 'center',
                    width: '100%',
                    height: '100%',
                    padding: '8px',
                    borderRadius: '4px',
                    transition: 'background-color 0.1s ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor =
                      'var(--mantine-color-proximal-blue-9)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent'
                  }}
                >
                  {row.deviceType}
                </div>
              </Table.Td>
              <Table.Td>
                {onDataChange ? (
                  <NumberInput
                    size="xs"
                    min={0}
                    value={row.numberOfDevices}
                    onChange={(value) =>
                      handleDeviceCountChange(index, Number(value) || 0)
                    }
                  />
                ) : (
                  row.numberOfDevices
                )}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Paper>
  )
}
