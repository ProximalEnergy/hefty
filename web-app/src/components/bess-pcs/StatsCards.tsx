import {
  Card,
  Group,
  HoverCard,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
} from '@mantine/core'
import {
  IconBolt,
  IconCalendar,
  IconDatabaseX,
  IconExclamationCircle,
  IconTicket,
} from '@tabler/icons-react'
import dayjs from 'dayjs'
import { useNavigate, useParams } from 'react-router'

interface StatsCardsProps {
  stats: {
    poiPowerMW: string | null
    poiPowerTimestamp: string | null
    poiPowerStatus: 'Charging' | 'Discharging' | 'Idling' | null
    cumulativePCSPowerMW: string
    cumulativePCSPowerTimestamp: string | null
    totalEventsCount: number
    pcsEventsCount: number
    moduleEventsCount: number
    moduleGroupEventsCount: number
    dailyRevenueLoss: string
    openCMMSTickets: number
    cmmsHoverTickets: Array<{
      key: string
      summary: string
      status?: string
    }>
    staleDevicesCount: number
    staleDeviceNames: string[]
    isCharging: boolean
    isDischarging: boolean
  }
  activeEventsHoverSections?: Array<{
    label: string
    count: number
    events: Array<{
      eventId: number
      label: string
    }>
    remainingCount: number
  }>
  isLoading: {
    realtime: boolean
    events: boolean
    cmms: boolean
    meter: boolean
  }
  nextPreventativeMaintenance?: {
    formattedDate: string
    calendarItemId: string
    occurrenceDateStr?: string
    hoverContent?: {
      title: string
      description?: string
      assignees?: string
    }
  } | null
  isLoadingCalendar?: boolean
  hasCMMSIntegration?: boolean
}

export const BessPCSStatsCards = ({
  stats,
  isLoading,
  activeEventsHoverSections = [],
  nextPreventativeMaintenance,
  isLoadingCalendar = false,
  hasCMMSIntegration = false,
}: StatsCardsProps) => {
  const { projectId } = useParams<{
    projectId: string
  }>()
  const navigate = useNavigate()

  const powerSubtitle = [
    stats.isCharging
      ? 'Charging'
      : stats.isDischarging
        ? 'Discharging'
        : 'Idle',
    stats.poiPowerMW !== null
      ? `POI Power: ${stats.poiPowerMW} MW`
      : 'POI Power: N/A',
  ].join('. ')
  const hasCmmsHoverContent = stats.cmmsHoverTickets.length > 0
  const cumulativePowerHoverMessage = stats.cumulativePCSPowerTimestamp
    ? `Last updated: ${dayjs(stats.cumulativePCSPowerTimestamp).format(
        'MMM D, YYYY HH:mm:ss',
      )}`
    : 'Timestamp not available'
  const cmmsHoverMessage = !hasCMMSIntegration
    ? 'Use the feedback button (bottom left) to get CMMS integration set up.'
    : hasCmmsHoverContent
      ? null
      : 'No open linked CMMS tickets.'
  const dataStatusHoverMessage =
    stats.staleDevicesCount === 0
      ? 'All PCSs reported data in the last hour.'
      : `PCSs ${
          stats.staleDeviceNames.length > 10
            ? `${stats.staleDeviceNames.slice(0, 10).join(', ')}, ...`
            : stats.staleDeviceNames.join(', ')
        } not reporting data.`
  const hasActiveEventsHoverContent = activeEventsHoverSections.some(
    (section) => section.count > 0,
  )

  return (
    <SimpleGrid cols={{ base: 1, xs: 2, sm: 3, md: 5 }}>
      <HoverCard
        width={320}
        shadow="md"
        openDelay={300}
        closeDelay={100}
        disabled={isLoading.realtime}
      >
        <HoverCard.Target>
          <Card withBorder p="md" radius="md">
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                Cumulative PCS Power
              </Text>
              <IconBolt size="1.2rem" stroke={1.5} />
            </Group>
            <Text fz={32} fw={700} mt={15} component="div">
              {isLoading.realtime ? (
                <Skeleton height={32} width="60%" />
              ) : (
                <Text component="span" fz={32} fw={700}>
                  {stats.cumulativePCSPowerMW} MWac
                </Text>
              )}
            </Text>
            {!isLoading.realtime && (
              <Text size="sm" c="dimmed" mt={5}>
                {powerSubtitle}
              </Text>
            )}
          </Card>
        </HoverCard.Target>
        <HoverCard.Dropdown>
          <Stack gap="xs">
            <Text fw={600} size="sm">
              Cumulative PCS Power
            </Text>
            <Text size="xs" c="dimmed">
              {cumulativePowerHoverMessage}
            </Text>
          </Stack>
        </HoverCard.Dropdown>
      </HoverCard>

      <HoverCard
        width={360}
        shadow="md"
        openDelay={300}
        closeDelay={100}
        disabled={isLoading.events}
      >
        <HoverCard.Target>
          <Card
            withBorder
            p="md"
            radius="md"
            style={{ cursor: 'pointer' }}
            onClick={() => navigate(`/projects/${projectId}/events`)}
          >
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                Active Events
              </Text>
              <IconExclamationCircle size="1.2rem" stroke={1.5} />
            </Group>
            <Text fz={32} fw={700} mt={15} component="div">
              {isLoading.events ? (
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
                          `PCS (${stats.pcsEventsCount})`,
                        stats.moduleGroupEventsCount > 0 &&
                          `Module Group (${stats.moduleGroupEventsCount})`,
                        stats.moduleEventsCount > 0 &&
                          `Module (${stats.moduleEventsCount})`,
                      ]
                        .filter(Boolean)
                        .join(', ')}
                    </Text>
                  )}
                </>
              )}
            </Text>
            <Text size="sm" c="dimmed" mt={5} component="div">
              {isLoading.events ? (
                <Skeleton height={16} width="80%" />
              ) : (
                <>${stats.dailyRevenueLoss} daily loss</>
              )}
            </Text>
          </Card>
        </HoverCard.Target>
        <HoverCard.Dropdown>
          <Stack gap="xs">
            <Text fw={600} size="sm">
              Active Events
            </Text>
            <Text size="xs" c="dimmed">
              Open-event overview by device type. Click to view all events.
            </Text>
            {hasActiveEventsHoverContent
              ? activeEventsHoverSections.map((section) => (
                  <Stack key={section.label} gap={2}>
                    <Text fw={600} size="sm">
                      {section.label} ({section.count})
                    </Text>
                    {section.count > 0 ? (
                      <>
                        {section.events.map((event) => (
                          <Text
                            key={`${section.label}-${event.eventId}`}
                            size="xs"
                            lineClamp={1}
                            style={{ cursor: 'pointer' }}
                            onClick={() =>
                              navigate(
                                `/projects/${projectId}/events/event?eventId=${event.eventId}`,
                              )
                            }
                          >
                            {event.label}
                          </Text>
                        ))}
                        {section.remainingCount > 0 && (
                          <Text
                            size="xs"
                            c="dimmed"
                            style={{ cursor: 'pointer' }}
                            onClick={() =>
                              navigate(`/projects/${projectId}/events`)
                            }
                          >
                            +{section.remainingCount} more (click to view)
                          </Text>
                        )}
                      </>
                    ) : (
                      <Text size="xs" c="dimmed">
                        No open events
                      </Text>
                    )}
                  </Stack>
                ))
              : activeEventsHoverSections.map((section) => (
                  <Text key={section.label} size="xs" c="dimmed">
                    {section.label}: 0
                  </Text>
                ))}
          </Stack>
        </HoverCard.Dropdown>
      </HoverCard>

      <HoverCard width={320} shadow="md" openDelay={300} closeDelay={100}>
        <HoverCard.Target>
          <Card
            withBorder
            p="md"
            radius="md"
            style={{ cursor: 'pointer' }}
            onClick={() => {
              if (nextPreventativeMaintenance?.calendarItemId) {
                const q = new URLSearchParams({
                  event: nextPreventativeMaintenance.calendarItemId,
                })
                if (nextPreventativeMaintenance.occurrenceDateStr) {
                  q.set('date', nextPreventativeMaintenance.occurrenceDateStr)
                }
                navigate(`/projects/${projectId}/calendar?${q.toString()}`)
              } else {
                navigate(`/projects/${projectId}/calendar`)
              }
            }}
          >
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                Maintenance
              </Text>
              <IconCalendar size="1.2rem" stroke={1.5} />
            </Group>
            {isLoading.cmms || isLoadingCalendar ? (
              <Text fz={32} fw={700} mt={15} component="div">
                <Skeleton height={32} width="60%" />
              </Text>
            ) : nextPreventativeMaintenance ? (
              <Text fz={32} fw={700} mt={15} component="div">
                {nextPreventativeMaintenance.formattedDate}
              </Text>
            ) : (
              <Text fz={32} fw={700} mt={15} component="div">
                N/A
              </Text>
            )}
            {!isLoading.cmms && (
              <Text size="sm" c="dimmed" mt={5}>
                Next Preventative Maintenance
              </Text>
            )}
          </Card>
        </HoverCard.Target>
        <HoverCard.Dropdown>
          <Stack gap="xs">
            <Text fw={600} size="sm">
              Next Preventative Maintenance
            </Text>
            <Text size="xs" c="dimmed">
              Click to set the next Preventative Maintenance date. In the
              calendar, click a date and add a new item with category
              &quot;Preventative Maintenance: BESS PCS&quot;.
            </Text>
            {nextPreventativeMaintenance?.hoverContent?.title && (
              <Stack gap={2}>
                <Text fw={600} size="sm">
                  {nextPreventativeMaintenance.hoverContent.title}
                </Text>
                {nextPreventativeMaintenance?.hoverContent?.description && (
                  <Text size="xs" c="dimmed" lineClamp={4}>
                    {nextPreventativeMaintenance.hoverContent.description}
                  </Text>
                )}
                {nextPreventativeMaintenance?.hoverContent?.assignees && (
                  <Text size="xs" c="dimmed" lineClamp={2}>
                    {nextPreventativeMaintenance.hoverContent.assignees}
                  </Text>
                )}
              </Stack>
            )}
          </Stack>
        </HoverCard.Dropdown>
      </HoverCard>

      <HoverCard
        width={320}
        shadow="md"
        openDelay={300}
        closeDelay={100}
        disabled={isLoading.cmms}
      >
        <HoverCard.Target>
          <Card
            withBorder
            p="md"
            radius="md"
            style={{ cursor: 'pointer' }}
            onClick={() =>
              navigate(`/projects/${projectId}/cmms/ticket-display`)
            }
          >
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                CMMS Tickets
              </Text>
              <IconTicket size="1.2rem" stroke={1.5} />
            </Group>
            <Text fz={32} fw={700} mt={15} component="div">
              {isLoading.cmms ? (
                <Skeleton height={32} width="60%" />
              ) : !hasCMMSIntegration ? (
                'N/A'
              ) : (
                stats.openCMMSTickets
              )}
            </Text>
            {!isLoading.cmms && (
              <Text size="sm" c="dimmed" mt={5}>
                {hasCMMSIntegration
                  ? 'Open tickets'
                  : 'No integration configured'}
              </Text>
            )}
          </Card>
        </HoverCard.Target>
        <HoverCard.Dropdown>
          <Stack gap="xs">
            <Text fw={600} size="sm">
              CMMS Tickets
            </Text>
            {cmmsHoverMessage ? (
              <Text size="xs" c="dimmed">
                {cmmsHoverMessage}
              </Text>
            ) : (
              stats.cmmsHoverTickets.map((ticket) => (
                <Stack key={ticket.key} gap={2}>
                  <Text fw={600} size="sm">
                    {ticket.key}
                    {ticket.status ? ` (${ticket.status})` : ''}
                  </Text>
                  <Text size="xs" c="dimmed" lineClamp={3}>
                    {ticket.summary}
                  </Text>
                </Stack>
              ))
            )}
          </Stack>
        </HoverCard.Dropdown>
      </HoverCard>

      <HoverCard
        width={320}
        shadow="md"
        openDelay={300}
        closeDelay={100}
        disabled={isLoading.realtime}
      >
        <HoverCard.Target>
          <Card
            withBorder
            p="md"
            radius="md"
            style={{ cursor: 'pointer' }}
            onClick={() =>
              navigate(
                `/projects/${projectId}/device-details/data-availability`,
              )
            }
          >
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                Data Status
              </Text>
              <IconDatabaseX size="1.2rem" stroke={1.5} />
            </Group>
            <Text fz={32} fw={700} mt={15} component="div">
              {isLoading.realtime ? (
                <Skeleton height={32} width="60%" />
              ) : (
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
              )}
            </Text>
            {!isLoading.realtime && stats.staleDevicesCount > 0 && (
              <Text size="sm" c="dimmed" mt={5}>
                Not Reporting
              </Text>
            )}
          </Card>
        </HoverCard.Target>
        <HoverCard.Dropdown>
          <Stack gap="xs">
            <Text fw={600} size="sm">
              Data Status
            </Text>
            <Text size="xs" c="dimmed">
              {dataStatusHoverMessage}
            </Text>
          </Stack>
        </HoverCard.Dropdown>
      </HoverCard>
    </SimpleGrid>
  )
}
