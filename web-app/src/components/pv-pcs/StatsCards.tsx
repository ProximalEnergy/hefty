import { DeviceTypeEnum, SensorTypeEnum } from '@/api/enumerations'
import { useGetCMMSTickets } from '@/api/v1/operational/project/cmms_tickets'
import { useGetEventsSummary } from '@/api/v1/operational/project/events'
import { useGetMeterPowerAndExpectedPower } from '@/api/v1/protected/pv-expected-energy/plot/plot'
import {
  useGetExpectedPowerByDeviceTypeID,
  useGetRealTimeByDeviceTypeID,
} from '@/api/v1/protected/web-application/projects/real_time'
import { Card, Group, SimpleGrid, Skeleton, Text, Tooltip } from '@mantine/core'
import {
  IconBolt,
  IconDatabaseX,
  IconExclamationCircle,
  IconMoon,
  IconTicket,
} from '@tabler/icons-react'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router'

const PV_PCS_DEVICE_TYPE_ID = DeviceTypeEnum.PV_PCS

interface StatsCardsProps {
  stats: {
    poiPowerMW: string | null
    poiPowerTimestamp: string | null
    expectedPowerMW: string | null
    expectedPowerTimestamp: string | null
    cumulativePCSPowerMW: string
    cumulativePCSPowerTimestamp: string | null
    cumulativeExpectedPCSPowerMW: string | null
    cumulativeExpectedPCSPowerTimestamp: string | null
    totalEventsCount: number
    pcsEventsCount: number
    pvCircuitEventsCount: number
    pvBlockEventsCount: number
    dailyRevenueLoss: string
    openCMMSTickets: number
    staleDevicesCount: number
    staleDeviceNames: string[]
    isNighttime: boolean
  }
}

export const StatsCards = ({ stats }: StatsCardsProps) => {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  // Get expected power at POI - update time range every 30 seconds to match refetch interval
  const [expectedPowerTimeRange, setExpectedPowerTimeRange] = useState(() => {
    const now = dayjs()
    return {
      start: now.subtract(1, 'hour').toISOString(),
      end: now.toISOString(),
    }
  })

  useEffect(() => {
    const interval = setInterval(() => {
      const now = dayjs()
      setExpectedPowerTimeRange({
        start: now.subtract(1, 'hour').toISOString(),
        end: now.toISOString(),
      })
    }, 30000) // Update every 30 seconds

    return () => clearInterval(interval)
  }, [])

  const realtimeData = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: PV_PCS_DEVICE_TYPE_ID,
    },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.PV_PCS_AC_POWER],
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 30000,
      staleTime: 15000,
    },
  })

  const pcsExpectedPower = useGetExpectedPowerByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: PV_PCS_DEVICE_TYPE_ID,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 30000,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 25000,
    },
  })

  const expectedPowerData = useGetMeterPowerAndExpectedPower({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: expectedPowerTimeRange.start,
      end: expectedPowerTimeRange.end,
      include_soiling: true,
      interval: '5min',
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 30000, // Refetch every 30 seconds
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: 25000, // Consider data stale after 25 seconds
    },
  })

  const activeEvents = useGetEventsSummary({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_type_ids: [PV_PCS_DEVICE_TYPE_ID],
      open: true,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 60000,
    },
  })

  const pvCircuitEvents = useGetEventsSummary({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_type_ids: [DeviceTypeEnum.PV_FEEDER],
      open: true,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 60000,
    },
  })

  const pvBlockEvents = useGetEventsSummary({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_type_ids: [DeviceTypeEnum.PV_BLOCK],
      open: true,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 60000,
    },
  })

  const cmmsTickets = useGetCMMSTickets({
    pathParams: { project_id: projectId || '-1' },
    queryParams: {
      device_type_ids: [PV_PCS_DEVICE_TYPE_ID],
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 60000,
    },
  })

  const hasCMMSIntegration = cmmsTickets.data?.integration_configured === true

  return (
    <SimpleGrid cols={{ base: 1, xs: 2, sm: 4, md: 5 }}>
      <Card withBorder p="md" radius="md">
        <Group justify="space-between">
          <Text size="sm" c="dimmed">
            POI Power
          </Text>
          <IconBolt size="1.2rem" stroke={1.5} />
        </Group>
        <Text fz={32} fw={700} mt={15} component="div">
          {expectedPowerData.isLoading && stats.poiPowerMW === null ? (
            <Skeleton height={32} width="60%" />
          ) : stats.poiPowerMW !== null ? (
            <Tooltip
              label={
                stats.poiPowerTimestamp
                  ? `Last updated: ${dayjs(stats.poiPowerTimestamp).format('MMM D, YYYY HH:mm:ss')}`
                  : 'Timestamp not available'
              }
              withArrow
            >
              <Text component="span" fz={32} fw={700}>
                {stats.poiPowerMW} MWac
              </Text>
            </Tooltip>
          ) : (
            'N/A'
          )}
        </Text>
        {stats.poiPowerMW !== null &&
          (stats.isNighttime ? (
            <Group gap="xs" align="center" mt={5}>
              <IconMoon size={16} />
              <Text size="sm" c="dimmed">
                Night
              </Text>
            </Group>
          ) : (
            stats.expectedPowerMW !== null && (
              <Tooltip
                label={
                  stats.expectedPowerTimestamp
                    ? `Last updated: ${dayjs(stats.expectedPowerTimestamp).format('MMM D, YYYY HH:mm:ss')}`
                    : 'Timestamp not available'
                }
                withArrow
              >
                <Text size="sm" c="dimmed" mt={5}>
                  Expected: {stats.expectedPowerMW} MWac
                </Text>
              </Tooltip>
            )
          ))}
      </Card>

      <Card withBorder p="md" radius="md">
        <Group justify="space-between">
          <Text size="sm" c="dimmed">
            Cumulative PCS Power
          </Text>
          <IconBolt size="1.2rem" stroke={1.5} />
        </Group>
        <Text fz={32} fw={700} mt={15} component="div">
          {realtimeData.isLoading || pcsExpectedPower.isLoading ? (
            <Skeleton height={32} width="60%" />
          ) : (
            <Tooltip
              label={
                stats.cumulativePCSPowerTimestamp
                  ? `Last updated: ${dayjs(stats.cumulativePCSPowerTimestamp).format('MMM D, YYYY HH:mm:ss')}`
                  : 'Timestamp not available'
              }
              withArrow
            >
              <Text component="span" fz={32} fw={700}>
                {stats.cumulativePCSPowerMW} MWac
              </Text>
            </Tooltip>
          )}
        </Text>
        {!realtimeData.isLoading &&
          !pcsExpectedPower.isLoading &&
          (stats.isNighttime ? (
            <Group gap="xs" align="center" mt={5}>
              <IconMoon size={16} />
              <Text size="sm" c="dimmed">
                Night
              </Text>
            </Group>
          ) : (
            stats.cumulativeExpectedPCSPowerMW !== null && (
              <Tooltip
                label={
                  stats.cumulativeExpectedPCSPowerTimestamp
                    ? `Last updated: ${dayjs(stats.cumulativeExpectedPCSPowerTimestamp).format('MMM D, YYYY HH:mm:ss')}`
                    : 'Timestamp not available'
                }
                withArrow
              >
                <Text size="sm" c="dimmed" mt={5}>
                  Expected: {stats.cumulativeExpectedPCSPowerMW} MWac
                </Text>
              </Tooltip>
            )
          ))}
      </Card>

      <Card
        withBorder
        p="md"
        radius="md"
        style={{ cursor: 'pointer' }}
        onClick={() => {
          navigate(`/projects/${projectId}/events`)
        }}
      >
        <Group justify="space-between">
          <Text size="sm" c="dimmed">
            Active Events
          </Text>
          <IconExclamationCircle size="1.2rem" stroke={1.5} />
        </Group>
        <Text fz={32} fw={700} mt={15} component="div">
          {activeEvents.isLoading ||
          pvCircuitEvents.isLoading ||
          pvBlockEvents.isLoading ? (
            <Skeleton height={32} width="60%" />
          ) : stats.totalEventsCount === 0 ? (
            <Group gap="xs" align="center">
              <div
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  backgroundColor: 'green',
                }}
              />
              <Text component="span" fz={32} fw={700}>
                0
              </Text>
            </Group>
          ) : (
            <>
              {stats.totalEventsCount}
              {stats.totalEventsCount > 0 && (
                <Text component="span" size="sm" c="dimmed" fw={400}>
                  {' '}
                  {[
                    stats.pcsEventsCount > 0 &&
                      `PV PCS (${stats.pcsEventsCount})`,
                    stats.pvBlockEventsCount > 0 &&
                      `PV Block (${stats.pvBlockEventsCount})`,
                    stats.pvCircuitEventsCount > 0 &&
                      `PV Circuit (${stats.pvCircuitEventsCount})`,
                  ]
                    .filter(Boolean)
                    .join(', ')}
                </Text>
              )}
            </>
          )}
        </Text>
        <Text size="sm" c="dimmed" mt={5} component="div">
          {activeEvents.isLoading ||
          pvCircuitEvents.isLoading ||
          pvBlockEvents.isLoading ? (
            <Skeleton height={16} width="80%" />
          ) : (
            <>${stats.dailyRevenueLoss} daily loss</>
          )}
        </Text>
      </Card>

      <Card
        withBorder
        p="md"
        radius="md"
        style={{ cursor: 'pointer' }}
        onClick={() => {
          navigate(`/projects/${projectId}/cmms/ticket-display`)
        }}
      >
        <Group justify="space-between">
          <Text size="sm" c="dimmed">
            Open CMMS Tickets
          </Text>
          <IconTicket size="1.2rem" stroke={1.5} />
        </Group>
        {cmmsTickets.isLoading ? (
          <Text fz={32} fw={700} mt={15} component="div">
            <Skeleton height={32} width="60%" />
          </Text>
        ) : !hasCMMSIntegration ? (
          <>
            <Text fz={32} fw={700} mt={15} component="div">
              N/A
            </Text>
            <Text size="sm" c="dimmed" mt={5}>
              No integration configured
            </Text>
          </>
        ) : (
          <Text fz={32} fw={700} mt={15} component="div">
            {stats.openCMMSTickets}
          </Text>
        )}
      </Card>

      <Card
        withBorder
        p="md"
        radius="md"
        style={{ cursor: 'pointer' }}
        onClick={() => {
          navigate(`/projects/${projectId}/device-details/data-availability`)
        }}
      >
        <Group justify="space-between">
          <Text size="sm" c="dimmed">
            Data Status
          </Text>
          <IconDatabaseX size="1.2rem" stroke={1.5} />
        </Group>
        <Text fz={32} fw={700} mt={15} component="div">
          {realtimeData.isLoading ? (
            <Skeleton height={32} width="60%" />
          ) : stats.isNighttime ? (
            <Tooltip label="It is currently nighttime at this site." withArrow>
              <Group gap="xs" align="center">
                <div
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    backgroundColor: 'orange',
                  }}
                />
                <Text component="span" fz={32} fw={700}>
                  Night
                </Text>
              </Group>
            </Tooltip>
          ) : (
            <Tooltip
              label={
                stats.staleDevicesCount === 0
                  ? 'All PCSs reported data in the last hour.'
                  : `PCSs ${
                      stats.staleDeviceNames.length > 10
                        ? `${stats.staleDeviceNames.slice(0, 10).join(', ')}, ...`
                        : stats.staleDeviceNames.join(', ')
                    } not reporting data in the last hour.`
              }
              withArrow
            >
              <Group gap="xs" align="center">
                <div
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    backgroundColor:
                      stats.staleDevicesCount === 0 ? 'green' : 'red',
                  }}
                />
                <Text component="span" fz={32} fw={700}>
                  {stats.staleDevicesCount === 0
                    ? 'OK'
                    : stats.staleDevicesCount}
                </Text>
              </Group>
            </Tooltip>
          )}
        </Text>
        {!realtimeData.isLoading &&
          !stats.isNighttime &&
          stats.staleDevicesCount > 0 && (
            <Text size="sm" c="dimmed" mt={5}>
              Not Reporting
            </Text>
          )}
      </Card>
    </SimpleGrid>
  )
}
