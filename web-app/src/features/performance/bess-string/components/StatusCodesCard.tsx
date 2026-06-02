import { DeviceTypeEnum, SensorTypeEnum } from '@/api/enumerations'
import { useGetLastKnownStatuses } from '@/api/v1/operational/project/project_status'
import CustomCard from '@/components/CustomCard'
import { useGetDevicesV2 } from '@/hooks/api'
import {
  ActionIcon,
  Group,
  ScrollArea,
  Skeleton,
  Table,
  Text,
} from '@mantine/core'
import { IconArrowLeft } from '@tabler/icons-react'
import { useEffect, useMemo, useRef, useState } from 'react'

const BESS_STRING_STATUS_DEVICE_TYPES = [DeviceTypeEnum.BESS_STRING]
const BESS_STRING_STATUS_SENSOR_TYPES = [
  SensorTypeEnum.BESS_STRING_STATUS,
  SensorTypeEnum.BESS_STRING_ALARM,
]

type StatusCodesCardProps = {
  projectId: string
}

export const StatusCodesCard = ({ projectId }: StatusCodesCardProps) => {
  const [selectedStatusCode, setSelectedStatusCode] = useState<string | null>(
    null,
  )
  const scrollViewportRef = useRef<HTMLDivElement | null>(null)
  const overviewScrollTopRef = useRef(0)
  const shouldRestoreScrollRef = useRef(false)

  const devices = useGetDevicesV2({
    pathParams: { projectId },
    filters: { device_type_ids: BESS_STRING_STATUS_DEVICE_TYPES },
    queryOptions: { enabled: !!projectId, staleTime: Infinity },
  })

  const lastKnownStatuses = useGetLastKnownStatuses({
    pathParams: { project_id: projectId },
    queryParams: {
      device_type_ids: BESS_STRING_STATUS_DEVICE_TYPES,
      sensor_type_ids: BESS_STRING_STATUS_SENSOR_TYPES,
      alert_only: false,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 30000,
      staleTime: 15000,
    },
  })

  const isLoading = devices.isLoading || lastKnownStatuses.isLoading

  const statusSummary = useMemo(() => {
    try {
      if (!Array.isArray(lastKnownStatuses.data) || !devices.data) return []

      const deviceNameMap: Record<number, string> = {}
      ;(devices.data || []).forEach((d) => {
        deviceNameMap[d.device_id] = d.name_long || `String ${d.device_id}`
      })

      const perDeviceStatuses = lastKnownStatuses.data.flatMap((ds) => {
        const deviceId = ds.device_id
        const statuses = ds.statuses || []
        if (deviceId == null || statuses.length === 0) return []

        const uniqueCodes = new Set(
          statuses.map((e) => e?.status).filter((s): s is string => !!s),
        )

        return Array.from(uniqueCodes).map((statusCode) => ({
          statusCode,
          deviceName: deviceNameMap[deviceId] || `String ${deviceId}`,
        }))
      })

      const summaryByStatus: Record<
        string,
        { statusCode: string; count: number; devices: string[] }
      > = {}

      perDeviceStatuses.forEach(({ statusCode, deviceName }) => {
        const entry = summaryByStatus[statusCode] ?? {
          statusCode,
          count: 0,
          devices: [],
        }
        entry.count += 1
        entry.devices.push(deviceName)
        summaryByStatus[statusCode] = entry
      })

      return Object.values(summaryByStatus)
        .map((item) => ({
          ...item,
          devices: item.devices.sort((a, b) => a.localeCompare(b)),
        }))
        .sort(
          (a, b) =>
            b.count - a.count || a.statusCode.localeCompare(b.statusCode),
        )
    } catch {
      return []
    }
  }, [lastKnownStatuses.data, devices.data])

  const selectedStatus = useMemo(
    () =>
      statusSummary.find((item) => item.statusCode === selectedStatusCode) ??
      null,
    [statusSummary, selectedStatusCode],
  )

  useEffect(() => {
    if (
      !selectedStatus &&
      shouldRestoreScrollRef.current &&
      scrollViewportRef.current
    ) {
      scrollViewportRef.current.scrollTop = overviewScrollTopRef.current
      shouldRestoreScrollRef.current = false
    }
  }, [selectedStatus])

  if (!isLoading && statusSummary.length === 0) return null

  const scrollAreaHeight = isLoading
    ? 150
    : Math.min(300, statusSummary.length * 40 + 100)

  return (
    <CustomCard
      title="Status Codes"
      allowMinimize={true}
      storageKey={`bess-string-realtime-status-${projectId}`}
    >
      <ScrollArea
        viewportRef={scrollViewportRef}
        h={scrollAreaHeight}
        type="scroll"
      >
        {isLoading ? (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Status Code</Table.Th>
                <Table.Th ta="right">Strings</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {Array(3)
                .fill(null)
                .map((_, i) => (
                  <Table.Tr key={i}>
                    <Table.Td>
                      <Skeleton height={20} width="60%" />
                    </Table.Td>
                    <Table.Td>
                      <Skeleton height={20} width="30px" />
                    </Table.Td>
                  </Table.Tr>
                ))}
            </Table.Tbody>
          </Table>
        ) : selectedStatus ? (
          <>
            <Group gap="xs" mb="xs">
              <ActionIcon
                variant="subtle"
                size="sm"
                aria-label="Back"
                onClick={() => setSelectedStatusCode(null)}
              >
                <IconArrowLeft size={16} />
              </ActionIcon>
              <Text size="sm" fw={600}>
                Strings with "{selectedStatus.statusCode}"
              </Text>
            </Group>
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>String</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {selectedStatus.devices.map((name) => (
                  <Table.Tr key={name}>
                    <Table.Td>
                      <Text size="sm">{name}</Text>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </>
        ) : (
          <>
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Status Code</Table.Th>
                  <Table.Th ta="right">Strings</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {statusSummary.map((item) => (
                  <Table.Tr
                    key={item.statusCode}
                    style={{ cursor: 'pointer' }}
                    onClick={() => {
                      overviewScrollTopRef.current =
                        scrollViewportRef.current?.scrollTop || 0
                      shouldRestoreScrollRef.current = true
                      setSelectedStatusCode((prev) =>
                        prev === item.statusCode ? null : item.statusCode,
                      )
                    }}
                  >
                    <Table.Td>
                      <Text size="sm" fw={500}>
                        {item.statusCode}
                      </Text>
                    </Table.Td>
                    <Table.Td ta="right">
                      <Text size="sm" fw={600}>
                        {item.count}
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
            <Text size="xs" c="dimmed" mt="md">
              Click a row to view string names.
            </Text>
          </>
        )}
      </ScrollArea>
    </CustomCard>
  )
}
