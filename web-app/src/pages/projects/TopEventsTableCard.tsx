import {
  type EnrichedEvent,
  useGetHomepageSummary,
} from '@/api/v1/protected/web-application/projects/events/events'
import CustomCard from '@/components/CustomCard'
import { QUERY_TIME } from '@/utils/queryTiming'
import {
  ActionIcon,
  Box,
  Center,
  Group,
  LoadingOverlay,
  Popover,
  SegmentedControl,
  Table,
  Text,
} from '@mantine/core'
import { IconSettings } from '@tabler/icons-react'
import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router'

import EventFirstModal from './events/components/EventFirstModal'
import {
  EventsCmmsHeaderBadges,
  EventsCmmsTableCell,
  eventToModalEventForCmms,
  useProjectEventsCmms,
} from './events/eventsCmmsShared'

/** Top Events card for project home (PV and BESS), including CMMS link status. */
export function TopEventsTableCard({
  showLosses,
  onEventHover,
}: {
  showLosses: boolean
  onEventHover?: (eventId: number | null) => void
}) {
  const { projectId } = useParams()
  const [sortBy, setSortBy] = useState<'daily' | 'total'>('daily')
  const [linkModalEvent, setLinkModalEvent] = useState<EnrichedEvent | null>(
    null,
  )

  const homepageSummary = useGetHomepageSummary({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      sort_by: sortBy,
    },
    queryOptions: {
      refetchInterval: QUERY_TIME.ONE_MINUTE,
      staleTime: QUERY_TIME.THIRTY_SECONDS,
    },
  })

  const topEventIds = useMemo(
    () => homepageSummary.data?.top_events?.map((e) => e.event_id) ?? [],
    [homepageSummary.data?.top_events],
  )

  const {
    projectId: cmmsProjectId,
    hasCmmsIntegration,
    permissionsLoading,
    linksLoading,
    linksData,
    linkCountByEventId,
    linkedDisplayByEventId,
    linkedTicketDetailsLoading,
  } = useProjectEventsCmms(topEventIds)

  const cardTitle = useMemo(() => {
    if (
      homepageSummary.data &&
      homepageSummary.data?.total_number_of_open_events > 0
    ) {
      if (showLosses) {
        return (
          `Top Events (${homepageSummary.data?.total_number_of_open_events} ` +
          `Open | $${homepageSummary.data?.total_daily_loss.toFixed(2)}/day)`
        )
      }
      return `Top Events (${homepageSummary.data?.total_number_of_open_events} Open)`
    }
    return 'Top Events'
  }, [homepageSummary.data, showLosses])

  const sortPopover = showLosses ? (
    <Popover position="bottom" withArrow shadow="md">
      <Popover.Target>
        <ActionIcon variant="default">
          <IconSettings size={20} stroke={1.5} />
        </ActionIcon>
      </Popover.Target>
      <Popover.Dropdown>
        <Group>
          <Text>Sort by</Text>
          <SegmentedControl
            data={[
              { label: 'Daily Loss', value: 'daily' },
              { label: 'Total Loss', value: 'total' },
            ]}
            value={sortBy}
            onChange={(value) => setSortBy(value as 'daily' | 'total')}
          />
        </Group>
      </Popover.Dropdown>
    </Popover>
  ) : null

  const headerChildren = (
    <Group gap="xs" wrap="nowrap">
      <EventsCmmsHeaderBadges
        hasCmmsIntegration={hasCmmsIntegration}
        permissionsLoading={permissionsLoading}
      />
      {sortPopover}
    </Group>
  )

  const modalLinkedIds =
    linkModalEvent == null
      ? []
      : (linksData
          ?.filter((r) => r.event_id === linkModalEvent.event_id)
          .map((r) => r.cmms_ticket_id) ?? [])

  return (
    <>
      <CustomCard
        title={
          <Link
            to={`/projects/${projectId}/events`}
            style={{ color: 'inherit' }}
          >
            {cardTitle}
          </Link>
        }
        fill
        style={{ flex: 1 }}
        headerChildren={headerChildren}
      >
        <LoadingOverlay visible={homepageSummary.isLoading} />

        {homepageSummary.data &&
        homepageSummary.data.top_events &&
        homepageSummary.data.top_events.length > 0 ? (
          showLosses ? (
            <Table striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Device</Table.Th>
                  <Table.Th>Loss - Daily</Table.Th>
                  <Table.Th>Loss - Total</Table.Th>
                  {hasCmmsIntegration ? <Table.Th>CMMS</Table.Th> : null}
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {homepageSummary.data.top_events.map((event) => (
                  <Table.Tr
                    key={event.event_id}
                    onMouseEnter={() => onEventHover?.(event.event_id)}
                    onMouseLeave={() => onEventHover?.(null)}
                  >
                    <Table.Td>
                      <Link
                        to={`/projects/${projectId}/events/event?eventId=${event.event_id}`}
                        style={{ color: 'inherit' }}
                      >
                        {event.device_name_full}
                      </Link>
                    </Table.Td>
                    <Table.Td>
                      {event.loss_daily_financial
                        ? `$${event.loss_daily_financial.toLocaleString(
                            'en-US',
                            {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 2,
                            },
                          )}`
                        : '-'}
                    </Table.Td>
                    <Table.Td>
                      {event.loss_total_financial
                        ? `$${event.loss_total_financial.toLocaleString(
                            'en-US',
                            {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 2,
                            },
                          )}`
                        : '-'}
                    </Table.Td>
                    {hasCmmsIntegration ? (
                      <Table.Td>
                        <EventsCmmsTableCell
                          projectId={cmmsProjectId}
                          hasCmmsIntegration={hasCmmsIntegration}
                          linksLoading={linksLoading}
                          linkCount={
                            linkCountByEventId.get(event.event_id) ?? 0
                          }
                          linkedTicketDetailsLoading={
                            linkedTicketDetailsLoading
                          }
                          linkedDisplay={
                            linkedDisplayByEventId.get(event.event_id) ?? null
                          }
                          onOpenLinkage={() => setLinkModalEvent(event)}
                        />
                      </Table.Td>
                    ) : null}
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          ) : (
            <Table striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Device</Table.Th>
                  {hasCmmsIntegration ? <Table.Th>CMMS</Table.Th> : null}
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {homepageSummary.data.top_events.map((event) => (
                  <Table.Tr
                    key={event.event_id}
                    onMouseEnter={() => onEventHover?.(event.event_id)}
                    onMouseLeave={() => onEventHover?.(null)}
                  >
                    <Table.Td>
                      <Link
                        to={`/projects/${projectId}/events/event?eventId=${event.event_id}`}
                        style={{ color: 'inherit' }}
                      >
                        {event.device_name_full}
                      </Link>
                    </Table.Td>
                    {hasCmmsIntegration ? (
                      <Table.Td>
                        <EventsCmmsTableCell
                          projectId={cmmsProjectId}
                          hasCmmsIntegration={hasCmmsIntegration}
                          linksLoading={linksLoading}
                          linkCount={
                            linkCountByEventId.get(event.event_id) ?? 0
                          }
                          linkedTicketDetailsLoading={
                            linkedTicketDetailsLoading
                          }
                          linkedDisplay={
                            linkedDisplayByEventId.get(event.event_id) ?? null
                          }
                          onOpenLinkage={() => setLinkModalEvent(event)}
                        />
                      </Table.Td>
                    ) : null}
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )
        ) : homepageSummary.data &&
          homepageSummary.data.top_events &&
          homepageSummary.data.top_events.length === 0 ? (
          <Box h="100%" w="100%">
            <Center h="100%" w="100%">
              <Text size="xl" fw={500}>
                No Open Events
              </Text>
            </Center>
          </Box>
        ) : null}
      </CustomCard>

      {linkModalEvent != null && projectId != null ? (
        <EventFirstModal
          opened
          onClose={() => setLinkModalEvent(null)}
          event={eventToModalEventForCmms(linkModalEvent)}
          linkedTicketIds={modalLinkedIds}
          projectId={projectId}
        />
      ) : null}
    </>
  )
}
