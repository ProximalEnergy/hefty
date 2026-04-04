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

interface StatusAndAlarmCodesProps {
  projectId: string
}

const DEVICE_TYPES = [
  DeviceTypeEnum.BESS_PCS,
  DeviceTypeEnum.BESS_PCS_MODULE,
  DeviceTypeEnum.BESS_PCS_MODULE_GROUP,
]

const SENSOR_TYPES = [
  SensorTypeEnum.BESS_PCS_STATUS,
  SensorTypeEnum.BESS_PCS_MODULE_STATUS,
  SensorTypeEnum.BESS_BANK_STATUS,
  SensorTypeEnum.BESS_PCS_MODULE_ALARM,
]

const isAbnormalStatus = (statusType?: string | null) =>
  statusType === 'alert' || statusType === 'warning'

export const StatusAndAlarmCodes = ({
  projectId,
}: StatusAndAlarmCodesProps) => {
  const [selectedStatusCode, setSelectedStatusCode] = useState<string | null>(
    null,
  )
  const [isFullscreen, setIsFullscreen] = useState(false)
  const contentRef = useRef<HTMLDivElement | null>(null)
  const scrollViewportRef = useRef<HTMLDivElement | null>(null)
  const overviewScrollTopRef = useRef(0)
  const shouldRestoreScrollRef = useRef(false)

  const devices = useGetDevicesV2({
    pathParams: { projectId },
    filters: {
      device_type_ids: DEVICE_TYPES,
    },
    queryOptions: {
      enabled: !!projectId,
      staleTime: Infinity,
    },
  })

  const lastKnownStatuses = useGetLastKnownStatuses({
    pathParams: { project_id: projectId },
    queryParams: {
      device_type_ids: DEVICE_TYPES,
      sensor_type_ids: SENSOR_TYPES,
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
      if (!Array.isArray(lastKnownStatuses.data) || !devices.data) {
        return []
      }

      const deviceTypeMap: Record<number, number> = {}
      const deviceNameMap: Record<number, string> = {}
      ;(devices.data || []).forEach((d) => {
        deviceTypeMap[d.device_id] = d.device_type_id
        deviceNameMap[d.device_id] = d.name_long || `Device ${d.device_id}`
      })

      const perDeviceStatuses = lastKnownStatuses.data.flatMap(
        (deviceStatus) => {
          const deviceId = deviceStatus.device_id
          const statuses = deviceStatus.statuses || []
          if (
            deviceId === null ||
            deviceId === undefined ||
            statuses.length === 0
          ) {
            return []
          }

          const deviceTypeId = deviceTypeMap[deviceId]
          if (!deviceTypeId) {
            return []
          }

          // One device can have multiple simultaneous active status/fault codes.
          // Count each unique code once per device.
          const uniqueCodes = new Set(
            statuses
              .map((entry) => entry?.status)
              .filter((status): status is string => !!status),
          )

          return Array.from(uniqueCodes).map((statusCode) => ({
            statusCode,
            isAbnormal: statuses.some((entry) => {
              return (
                entry?.status === statusCode &&
                isAbnormalStatus(entry?.status_type)
              )
            }),
            deviceTypeId,
            deviceName: deviceNameMap[deviceId] || `Device ${deviceId}`,
          }))
        },
      )

      const summaryByStatus: Record<
        string,
        {
          statusCode: string
          isAbnormal: boolean
          pcsCount: number
          moduleGroupCount: number
          moduleCount: number
          totalCount: number
          pcsDevices: string[]
          moduleGroupDevices: string[]
          moduleDevices: string[]
        }
      > = {}

      perDeviceStatuses.forEach((row) => {
        const existing = summaryByStatus[row.statusCode] || {
          statusCode: row.statusCode,
          isAbnormal: false,
          pcsCount: 0,
          moduleGroupCount: 0,
          moduleCount: 0,
          totalCount: 0,
          pcsDevices: [],
          moduleGroupDevices: [],
          moduleDevices: [],
        }

        if (row.deviceTypeId === DeviceTypeEnum.BESS_PCS) {
          existing.pcsCount += 1
          existing.pcsDevices.push(row.deviceName)
        } else if (row.deviceTypeId === DeviceTypeEnum.BESS_PCS_MODULE_GROUP) {
          existing.moduleGroupCount += 1
          existing.moduleGroupDevices.push(row.deviceName)
        } else if (row.deviceTypeId === DeviceTypeEnum.BESS_PCS_MODULE) {
          existing.moduleCount += 1
          existing.moduleDevices.push(row.deviceName)
        }
        existing.isAbnormal = existing.isAbnormal || row.isAbnormal
        existing.totalCount += 1
        summaryByStatus[row.statusCode] = existing
      })

      return Object.values(summaryByStatus)
        .map((item) => ({
          ...item,
          pcsDevices: item.pcsDevices.sort((a, b) => a.localeCompare(b)),
          moduleGroupDevices: item.moduleGroupDevices.sort((a, b) =>
            a.localeCompare(b),
          ),
          moduleDevices: item.moduleDevices.sort((a, b) => a.localeCompare(b)),
        }))
        .sort((a, b) => {
          if (a.isAbnormal !== b.isAbnormal) {
            return a.isAbnormal ? -1 : 1
          }
          if (b.totalCount !== a.totalCount) {
            return b.totalCount - a.totalCount
          }
          return a.statusCode.localeCompare(b.statusCode)
        })
    } catch {
      return []
    }
  }, [lastKnownStatuses.data, devices.data])

  const selectedStatus = useMemo(
    () =>
      statusSummary.find((item) => item.statusCode === selectedStatusCode) ||
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

  useEffect(() => {
    const updateFullscreenState = () => {
      const fullscreenElement = document.fullscreenElement
      setIsFullscreen(
        !!fullscreenElement &&
          !!contentRef.current &&
          fullscreenElement.contains(contentRef.current),
      )
    }

    updateFullscreenState()
    document.addEventListener('fullscreenchange', updateFullscreenState)

    return () => {
      document.removeEventListener('fullscreenchange', updateFullscreenState)
    }
  }, [])

  const defaultScrollAreaHeight =
    statusSummary.length > 0
      ? Math.min(300, statusSummary.length * 40 + 100)
      : 150
  const scrollAreaHeight = isFullscreen
    ? 'calc(100vh - 180px)'
    : defaultScrollAreaHeight

  return (
    <CustomCard
      title="Status Codes"
      allowMinimize={true}
      storageKey={`bess-pcs-realtime-status-${projectId}`}
      bodyStyle={{ minHeight: 0 }}
    >
      <div ref={contentRef}>
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
                  <Table.Th ta="right">PCS</Table.Th>
                  <Table.Th ta="right">Module Group</Table.Th>
                  <Table.Th ta="right">Module</Table.Th>
                  <Table.Th ta="right">Total</Table.Th>
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
                        <Skeleton height={20} width="20px" />
                      </Table.Td>
                      <Table.Td>
                        <Skeleton height={20} width="20px" />
                      </Table.Td>
                      <Table.Td>
                        <Skeleton height={20} width="20px" />
                      </Table.Td>
                      <Table.Td>
                        <Skeleton height={20} width="20px" />
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
                  aria-label="Back to status overview"
                  onClick={() => setSelectedStatusCode(null)}
                >
                  <IconArrowLeft size={16} />
                </ActionIcon>
                <Text
                  size="sm"
                  fw={600}
                  c={selectedStatus.isAbnormal ? 'red' : undefined}
                >
                  Devices with "{selectedStatus.statusCode}"
                </Text>
              </Group>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Device Type</Table.Th>
                    <Table.Th>Devices</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  <Table.Tr>
                    <Table.Td>
                      <Text size="sm" fw={500}>
                        PCS ({selectedStatus.pcsCount})
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">
                        {selectedStatus.pcsDevices.length > 0
                          ? selectedStatus.pcsDevices.join(', ')
                          : '—'}
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                  <Table.Tr>
                    <Table.Td>
                      <Text size="sm" fw={500}>
                        Module Group ({selectedStatus.moduleGroupCount})
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">
                        {selectedStatus.moduleGroupDevices.length > 0
                          ? selectedStatus.moduleGroupDevices.join(', ')
                          : '—'}
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                  <Table.Tr>
                    <Table.Td>
                      <Text size="sm" fw={500}>
                        Module ({selectedStatus.moduleCount})
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">
                        {selectedStatus.moduleDevices.length > 0
                          ? selectedStatus.moduleDevices.join(', ')
                          : '—'}
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                </Table.Tbody>
              </Table>
            </>
          ) : statusSummary.length > 0 ? (
            <>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Status Code</Table.Th>
                    <Table.Th ta="right">PCS</Table.Th>
                    <Table.Th ta="right">Module Group</Table.Th>
                    <Table.Th ta="right">Module</Table.Th>
                    <Table.Th ta="right">Total</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {statusSummary.map((item) => (
                    <Table.Tr
                      key={item.statusCode}
                      style={{
                        cursor: 'pointer',
                        backgroundColor:
                          selectedStatusCode === item.statusCode
                            ? 'var(--mantine-color-gray-1)'
                            : undefined,
                      }}
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
                        <Text
                          size="sm"
                          fw={500}
                          c={item.isAbnormal ? 'red' : undefined}
                        >
                          {item.statusCode}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text
                          size="sm"
                          ta="right"
                          c={item.isAbnormal ? 'red' : undefined}
                        >
                          {item.pcsCount}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text
                          size="sm"
                          ta="right"
                          c={item.isAbnormal ? 'red' : undefined}
                        >
                          {item.moduleGroupCount}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text
                          size="sm"
                          ta="right"
                          c={item.isAbnormal ? 'red' : undefined}
                        >
                          {item.moduleCount}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text
                          size="sm"
                          ta="right"
                          fw={600}
                          c={item.isAbnormal ? 'red' : undefined}
                        >
                          {item.totalCount}
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>

              <Text size="xs" c="dimmed" mt="md">
                Click a status row to view device names.
              </Text>
            </>
          ) : (
            <Text size="sm" c="dimmed" ta="center" mt="md">
              No status data available
            </Text>
          )}
        </ScrollArea>
      </div>
    </CustomCard>
  )
}
