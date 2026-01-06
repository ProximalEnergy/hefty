import { SensorTypeEnum } from '@/api/enumerations'
import { useGetRealTimeByDeviceTypeID } from '@/api/v1/protected/web-application/projects/real_time'
import CustomCard from '@/components/CustomCard'
import { Badge, ScrollArea, Skeleton, Table, Text } from '@mantine/core'
import { useMemo } from 'react'

interface StatusAndErrorCodesProps {
  realtimeData: ReturnType<typeof useGetRealTimeByDeviceTypeID>
  projectId: string
}

export const StatusAndErrorCodes = ({
  realtimeData,
  projectId,
}: StatusAndErrorCodesProps) => {
  const statusData = useMemo(() => {
    if (
      !realtimeData.data?.device_names ||
      realtimeData.data.device_names.length === 0
    ) {
      return []
    }

    const deviceNames = realtimeData.data.device_names.filter(
      (n): n is string => n !== null,
    )

    const statusTrace = realtimeData.data.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_PCS_STATUS,
    )

    const statusValues = statusTrace?.values || []

    return deviceNames.map((name, idx) => {
      const deviceName = name || `Device ${idx + 1}`
      const statusValue = statusValues[idx]

      return {
        device: deviceName,
        status:
          statusValue !== null && statusValue !== undefined
            ? String(statusValue)
            : null,
      }
    })
  }, [realtimeData.data])

  return (
    <CustomCard
      title="Status and Error Codes"
      allowMinimize={true}
      storageKey={`pv-pcs-realtime-status-${projectId}`}
    >
      <ScrollArea
        h={
          statusData.length > 0
            ? Math.min(300, statusData.length * 40 + 100)
            : 150
        }
        type="scroll"
      >
        {realtimeData.isLoading ? (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Device</Table.Th>
                <Table.Th>Status</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {Array(3)
                .fill(null)
                .map((_, idx) => (
                  <Table.Tr key={idx}>
                    <Table.Td>
                      <Skeleton height={20} width="60%" />
                    </Table.Td>
                    <Table.Td>
                      <Skeleton height={24} width="80px" />
                    </Table.Td>
                  </Table.Tr>
                ))}
            </Table.Tbody>
          </Table>
        ) : statusData.length > 0 ? (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Device</Table.Th>
                <Table.Th>Status</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {statusData.map((item, idx) => (
                <Table.Tr key={idx}>
                  <Table.Td>
                    <Text size="sm" fw={500}>
                      {item.device || `Device ${idx + 1}`}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge
                      color={item.status === null ? 'gray' : 'blue'}
                      size="sm"
                    >
                      {item.status !== null ? item.status : 'No Data'}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        ) : (
          <Text size="sm" c="dimmed" ta="center" mt="md">
            No status data available. Required sensor type: PV_PCS_STATUS
          </Text>
        )}
      </ScrollArea>
    </CustomCard>
  )
}
