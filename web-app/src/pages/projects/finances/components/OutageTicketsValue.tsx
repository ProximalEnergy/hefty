import { useGetActiveOutageTickets } from '@/api/v1/protected/web-application/projects/financial/ptp_data'
import {
  ActionIcon,
  Group,
  Modal,
  Popover,
  ScrollArea,
  Stack,
  Table,
  Tabs,
  Text,
  Tooltip,
  useMantineTheme,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { IconCopy, IconInfoCircle, IconStar } from '@tabler/icons-react'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useMemo, useState } from 'react'

dayjs.extend(utc)
dayjs.extend(timezone)

interface OutageTicket {
  identifier: string
  element: string
  outage_status?: string | null
  planned_start_time?: string | null
  planned_end_time?: string | null
  actual_end_time?: string | null
  station?: string | null
  resource_id?: string | null
  data_points?: Record<string, unknown> | null
  go_live_date?: string | null
  expiration_date?: string | null
  parent_identifier?: string | null
  is_active?: boolean
}

interface OutageTicketsValueProps {
  projectId: string
  projectTimeZone?: string | null
}

export const OutageTicketsValue = ({
  projectId,
  projectTimeZone,
}: OutageTicketsValueProps) => {
  const theme = useMantineTheme()
  const [copiedTicketId, setCopiedTicketId] = useState<string | null>(null)
  const [selectedTicket, setSelectedTicket] = useState<OutageTicket | null>(
    null,
  )
  const [modalOpened, { open: openModal, close: closeModal }] =
    useDisclosure(false)

  const { data: outageTicketsData, isLoading: outageTicketsLoading } =
    useGetActiveOutageTickets({
      pathParams: { projectId },
      queryOptions: {
        enabled: !!projectId,
      },
    })

  const handleCopyTicketName = async (text: string, ticketId: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedTicketId(ticketId)
      setTimeout(() => setCopiedTicketId(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const value = useMemo(() => {
    if (outageTicketsLoading) {
      return 'Loading...'
    }

    const count = outageTicketsData?.active_tickets ?? 0
    const tickets = outageTicketsData?.tickets ?? []
    const hasAnyTickets = tickets.length > 0

    // Filter tickets to only those currently active (now() between planned_start and end)
    const now = projectTimeZone ? dayjs().tz(projectTimeZone) : dayjs().utc()
    const currentlyActiveTickets = tickets.filter((ticket) => {
      if (!ticket.planned_start_time) return false

      const startTime = projectTimeZone
        ? dayjs(ticket.planned_start_time).tz(projectTimeZone)
        : dayjs(ticket.planned_start_time).utc()

      // Use actual_end_time if available, otherwise fallback to planned_end_time
      const endTimeStr = ticket.actual_end_time || ticket.planned_end_time
      if (!endTimeStr) return false

      const endTime = projectTimeZone
        ? dayjs(endTimeStr).tz(projectTimeZone)
        : dayjs(endTimeStr).utc()

      // Check if now() is between start and end (inclusive boundaries)
      const nowValue = now.valueOf()
      const startValue = startTime.valueOf()
      const endValue = endTime.valueOf()
      return nowValue >= startValue && nowValue <= endValue
    })

    // Extract HSL and LSL values from currently active tickets only
    const hslValues = currentlyActiveTickets
      .map((t) => t.data_points?.HSL)
      .filter((v) => v !== null && v !== undefined && v !== '')
    const lslValues = currentlyActiveTickets
      .map((t) => t.data_points?.LSL)
      .filter((v) => v !== null && v !== undefined && v !== '')

    // Build subtitle text
    let subtitleText = ''
    if (hslValues.length > 0 || lslValues.length > 0) {
      const hslText =
        hslValues.length > 0 ? `HSL: ${hslValues.join(', ')} MW` : ''
      const lslText =
        lslValues.length > 0 ? `LSL: ${lslValues.join(', ')} MW` : ''
      subtitleText = [hslText, lslText].filter(Boolean).join(' | ')
    }

    // Sort tickets: active first, then by planned_start_time in descending order
    const sortedTickets = hasAnyTickets
      ? [...tickets].sort((a, b) => {
          if (a.is_active && !b.is_active) return -1
          if (!a.is_active && b.is_active) return 1
          const aTime = a.planned_start_time
            ? dayjs(a.planned_start_time).valueOf()
            : 0
          const bTime = b.planned_start_time
            ? dayjs(b.planned_start_time).valueOf()
            : 0
          return bTime - aTime
        })
      : []

    if (!hasAnyTickets) {
      return subtitleText ? (
        <Stack gap={2}>
          <Text fz={32} fw={700}>
            {count}
          </Text>
          <Text size="xs" c="dimmed">
            {subtitleText}
          </Text>
        </Stack>
      ) : (
        String(count)
      )
    }

    return (
      <Stack gap={2}>
        <Group gap="xs" align="center">
          <Text fz={32} fw={700}>
            {count}
          </Text>
          <Popover position="bottom" withArrow shadow="md" width={1200}>
            <Popover.Target>
              <ActionIcon variant="subtle" size="sm" color="gray">
                <IconInfoCircle size={18} />
              </ActionIcon>
            </Popover.Target>
            <Popover.Dropdown>
              <Stack gap="md">
                <Text fw={600} size="sm">
                  Outage Tickets ({tickets.length} total, {count} active)
                </Text>
                <ScrollArea h={400}>
                  <Table striped highlightOnHover>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Ticket Name</Table.Th>
                        <Table.Th>Status</Table.Th>
                        <Table.Th>Planned Start</Table.Th>
                        <Table.Th>Planned End</Table.Th>
                        <Table.Th>Actual End</Table.Th>
                        <Table.Th>Station</Table.Th>
                        <Table.Th>HSL</Table.Th>
                        <Table.Th>LSL</Table.Th>
                        <Table.Th>Supporting Notes</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {sortedTickets.map((ticket) => (
                        <Table.Tr
                          key={ticket.identifier}
                          style={{
                            cursor: 'pointer',
                            opacity: ticket.is_active ? 1 : 0.7,
                          }}
                          onClick={() => {
                            setSelectedTicket(ticket)
                            openModal()
                          }}
                        >
                          <Table.Td>
                            <Group gap="xs" align="center" wrap="nowrap">
                              {ticket.is_active && (
                                <IconStar
                                  size={14}
                                  fill={theme.colors.yellow[6]}
                                  color={theme.colors.yellow[6]}
                                />
                              )}
                              <Text size="xs" fw={ticket.is_active ? 600 : 400}>
                                {ticket.element}
                              </Text>
                              <Tooltip
                                label={
                                  copiedTicketId === ticket.identifier
                                    ? 'Copied!'
                                    : 'Copy ticket name'
                                }
                                withArrow
                              >
                                <ActionIcon
                                  variant="subtle"
                                  size="xs"
                                  color="gray"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleCopyTicketName(
                                      ticket.element,
                                      ticket.identifier,
                                    )
                                  }}
                                >
                                  <IconCopy size={14} />
                                </ActionIcon>
                              </Tooltip>
                            </Group>
                          </Table.Td>
                          <Table.Td>
                            <Text size="xs">
                              {ticket.outage_status || 'N/A'}
                            </Text>
                          </Table.Td>
                          <Table.Td>
                            <Text size="xs">
                              {ticket.planned_start_time
                                ? dayjs(ticket.planned_start_time)
                                    .tz(projectTimeZone || 'UTC')
                                    .format('MMM D, YYYY HH:mm')
                                : 'N/A'}
                            </Text>
                          </Table.Td>
                          <Table.Td>
                            <Text size="xs">
                              {ticket.planned_end_time
                                ? dayjs(ticket.planned_end_time)
                                    .tz(projectTimeZone || 'UTC')
                                    .format('MMM D, YYYY HH:mm')
                                : 'N/A'}
                            </Text>
                          </Table.Td>
                          <Table.Td>
                            <Text size="xs">
                              {ticket.actual_end_time
                                ? dayjs(ticket.actual_end_time)
                                    .tz(projectTimeZone || 'UTC')
                                    .format('MMM D, YYYY HH:mm')
                                : 'N/A'}
                            </Text>
                          </Table.Td>
                          <Table.Td>
                            <Text size="xs">{ticket.station || 'N/A'}</Text>
                          </Table.Td>
                          <Table.Td>
                            <Text size="xs">
                              {ticket.data_points?.HSL !== null &&
                              ticket.data_points?.HSL !== undefined
                                ? `${ticket.data_points.HSL} MW`
                                : 'N/A'}
                            </Text>
                          </Table.Td>
                          <Table.Td>
                            <Text size="xs">
                              {ticket.data_points?.LSL !== null &&
                              ticket.data_points?.LSL !== undefined
                                ? `${ticket.data_points.LSL} MW`
                                : 'N/A'}
                            </Text>
                          </Table.Td>
                          <Table.Td>
                            <Text
                              size="xs"
                              style={{ maxWidth: 200 }}
                              truncate
                              title={
                                ticket.data_points?.SupportingNotesComment
                                  ? String(
                                      ticket.data_points.SupportingNotesComment,
                                    )
                                  : undefined
                              }
                            >
                              {ticket.data_points?.SupportingNotesComment
                                ? String(
                                    ticket.data_points.SupportingNotesComment,
                                  )
                                : 'N/A'}
                            </Text>
                          </Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </ScrollArea>
              </Stack>
            </Popover.Dropdown>
          </Popover>
        </Group>
        {subtitleText && (
          <Text size="xs" c="dimmed">
            {subtitleText}
          </Text>
        )}
        <Modal
          opened={modalOpened}
          onClose={closeModal}
          title="Outage Ticket Details"
          size="xl"
          zIndex={400}
        >
          {selectedTicket && (
            <Stack gap="md">
              <ScrollArea h={800}>
                <Stack gap="md">
                  {/* Basic Information */}
                  <Stack gap="xs">
                    <Text fw={700} size="sm" c="dimmed" tt="uppercase" fz="xs">
                      Basic Information
                    </Text>
                    <Group justify="space-between" align="flex-start">
                      <Text fw={600} size="sm">
                        Ticket Name:
                      </Text>
                      <Text size="sm" style={{ flex: 1 }} ta="right">
                        {selectedTicket.element}
                      </Text>
                    </Group>
                    <Group justify="space-between" align="flex-start">
                      <Text fw={600} size="sm">
                        Identifier:
                      </Text>
                      <Text size="sm" style={{ flex: 1 }} ta="right" c="dimmed">
                        {selectedTicket.identifier}
                      </Text>
                    </Group>
                    <Group justify="space-between" align="flex-start">
                      <Text fw={600} size="sm">
                        Status:
                      </Text>
                      <Text size="sm" style={{ flex: 1 }} ta="right">
                        {selectedTicket.outage_status || 'N/A'}
                      </Text>
                    </Group>
                    {selectedTicket.parent_identifier && (
                      <Group justify="space-between" align="flex-start">
                        <Text fw={600} size="sm">
                          Parent Identifier:
                        </Text>
                        <Text
                          size="sm"
                          style={{ flex: 1 }}
                          ta="right"
                          c="dimmed"
                        >
                          {selectedTicket.parent_identifier}
                        </Text>
                      </Group>
                    )}
                  </Stack>

                  {/* Notes */}
                  {selectedTicket.data_points?.SupportingNotesComment !=
                    null && (
                    <Stack gap="xs">
                      <Text
                        fw={700}
                        size="sm"
                        c="dimmed"
                        tt="uppercase"
                        fz="xs"
                      >
                        Notes
                      </Text>
                      <Group justify="space-between" align="flex-start">
                        <Text fw={600} size="sm">
                          Supporting Notes:
                        </Text>
                        <Text size="sm" style={{ flex: 1 }} ta="right">
                          {String(
                            selectedTicket.data_points.SupportingNotesComment,
                          )}
                        </Text>
                      </Group>
                      {selectedTicket.data_points.SupportingNotesCreatedBy !=
                        null && (
                        <Group justify="space-between" align="flex-start">
                          <Text fw={600} size="sm">
                            Notes Created By:
                          </Text>
                          <Text
                            size="sm"
                            style={{ flex: 1 }}
                            ta="right"
                            c="dimmed"
                          >
                            {String(
                              selectedTicket.data_points
                                .SupportingNotesCreatedBy,
                            )}
                          </Text>
                        </Group>
                      )}
                    </Stack>
                  )}

                  {/* Limits Impact */}
                  {(selectedTicket.data_points?.HSL !== null &&
                    selectedTicket.data_points?.HSL !== undefined) ||
                  (selectedTicket.data_points?.LSL !== null &&
                    selectedTicket.data_points?.LSL !== undefined) ? (
                    <Stack gap="xs">
                      <Text
                        fw={700}
                        size="sm"
                        c="dimmed"
                        tt="uppercase"
                        fz="xs"
                      >
                        Limits Impact
                      </Text>
                      {selectedTicket.data_points?.HSL !== null &&
                        selectedTicket.data_points?.HSL !== undefined && (
                          <Group justify="space-between" align="flex-start">
                            <Text fw={600} size="sm">
                              HSL:
                            </Text>
                            <Text size="sm" style={{ flex: 1 }} ta="right">
                              {String(selectedTicket.data_points.HSL)} MW
                            </Text>
                          </Group>
                        )}
                      {selectedTicket.data_points?.LSL !== null &&
                        selectedTicket.data_points?.LSL !== undefined && (
                          <Group justify="space-between" align="flex-start">
                            <Text fw={600} size="sm">
                              LSL:
                            </Text>
                            <Text size="sm" style={{ flex: 1 }} ta="right">
                              {String(selectedTicket.data_points.LSL)} MW
                            </Text>
                          </Group>
                        )}
                    </Stack>
                  ) : null}

                  {/* Equipment & Resource */}
                  <Stack gap="xs">
                    <Text fw={700} size="sm" c="dimmed" tt="uppercase" fz="xs">
                      Equipment & Resource
                    </Text>
                    <Group justify="space-between" align="flex-start">
                      <Text fw={600} size="sm">
                        Station:
                      </Text>
                      <Text size="sm" style={{ flex: 1 }} ta="right">
                        {selectedTicket.station || 'N/A'}
                      </Text>
                    </Group>
                    <Group justify="space-between" align="flex-start">
                      <Text fw={600} size="sm">
                        Resource ID:
                      </Text>
                      <Text size="sm" style={{ flex: 1 }} ta="right" c="dimmed">
                        {selectedTicket.resource_id || 'N/A'}
                      </Text>
                    </Group>
                    {selectedTicket.data_points?.EquipmentName != null && (
                      <Group justify="space-between" align="flex-start">
                        <Text fw={600} size="sm">
                          Equipment Name:
                        </Text>
                        <Text size="sm" style={{ flex: 1 }} ta="right">
                          {String(selectedTicket.data_points.EquipmentName)}
                        </Text>
                      </Group>
                    )}
                    {selectedTicket.data_points?.EquipmentIdentifier !=
                      null && (
                      <Group justify="space-between" align="flex-start">
                        <Text fw={600} size="sm">
                          Equipment Identifier:
                        </Text>
                        <Text
                          size="sm"
                          style={{ flex: 1 }}
                          ta="right"
                          c="dimmed"
                        >
                          {String(
                            selectedTicket.data_points.EquipmentIdentifier,
                          )}
                        </Text>
                      </Group>
                    )}
                    {selectedTicket.data_points?.ResourceType != null && (
                      <Group justify="space-between" align="flex-start">
                        <Text fw={600} size="sm">
                          Resource Type:
                        </Text>
                        <Text size="sm" style={{ flex: 1 }} ta="right">
                          {String(selectedTicket.data_points.ResourceType)}
                        </Text>
                      </Group>
                    )}
                  </Stack>

                  {/* Tabs for additional information */}
                  <Tabs defaultValue="timeline" mt="md">
                    <Tabs.List>
                      <Tabs.Tab value="timeline">Timeline</Tabs.Tab>
                      <Tabs.Tab value="details">Details</Tabs.Tab>
                      <Tabs.Tab value="contacts">Contacts</Tabs.Tab>
                      <Tabs.Tab value="request">Request</Tabs.Tab>
                      <Tabs.Tab value="market">Market</Tabs.Tab>
                      <Tabs.Tab value="additional">Additional</Tabs.Tab>
                    </Tabs.List>

                    <Tabs.Panel value="timeline" pt="md">
                      <Stack gap="xs">
                        <Text
                          fw={700}
                          size="sm"
                          c="dimmed"
                          tt="uppercase"
                          fz="xs"
                        >
                          Dates & Timeline
                        </Text>
                        <Group justify="space-between" align="flex-start">
                          <Text fw={600} size="sm">
                            Planned Start:
                          </Text>
                          <Text size="sm" style={{ flex: 1 }} ta="right">
                            {selectedTicket.planned_start_time
                              ? dayjs(selectedTicket.planned_start_time)
                                  .tz(projectTimeZone || 'UTC')
                                  .format('MMM D, YYYY HH:mm z')
                              : 'N/A'}
                          </Text>
                        </Group>
                        <Group justify="space-between" align="flex-start">
                          <Text fw={600} size="sm">
                            Planned End:
                          </Text>
                          <Text size="sm" style={{ flex: 1 }} ta="right">
                            {selectedTicket.planned_end_time
                              ? dayjs(selectedTicket.planned_end_time)
                                  .tz(projectTimeZone || 'UTC')
                                  .format('MMM D, YYYY HH:mm z')
                              : 'N/A'}
                          </Text>
                        </Group>
                        <Group justify="space-between" align="flex-start">
                          <Text fw={600} size="sm">
                            Actual End:
                          </Text>
                          <Text size="sm" style={{ flex: 1 }} ta="right">
                            {selectedTicket.actual_end_time
                              ? dayjs(selectedTicket.actual_end_time)
                                  .tz(projectTimeZone || 'UTC')
                                  .format('MMM D, YYYY HH:mm z')
                              : 'N/A'}
                          </Text>
                        </Group>
                        {selectedTicket.go_live_date && (
                          <Group justify="space-between" align="flex-start">
                            <Text fw={600} size="sm">
                              Go Live Date:
                            </Text>
                            <Text size="sm" style={{ flex: 1 }} ta="right">
                              {selectedTicket.go_live_date}
                            </Text>
                          </Group>
                        )}
                        {selectedTicket.expiration_date && (
                          <Group justify="space-between" align="flex-start">
                            <Text fw={600} size="sm">
                              Expiration Date:
                            </Text>
                            <Text size="sm" style={{ flex: 1 }} ta="right">
                              {selectedTicket.expiration_date}
                            </Text>
                          </Group>
                        )}
                      </Stack>
                    </Tabs.Panel>

                    <Tabs.Panel value="details" pt="md">
                      {selectedTicket.data_points &&
                        (selectedTicket.data_points.OutageStatus != null ||
                          selectedTicket.data_points.OutageState != null ||
                          selectedTicket.data_points.OutageType != null ||
                          selectedTicket.data_points.NatureOfWork != null) && (
                          <Stack gap="xs">
                            <Text
                              fw={700}
                              size="sm"
                              c="dimmed"
                              tt="uppercase"
                              fz="xs"
                            >
                              Outage Details
                            </Text>
                            {selectedTicket.data_points.OutageStatus !=
                              null && (
                              <Group justify="space-between" align="flex-start">
                                <Text fw={600} size="sm">
                                  Outage Status:
                                </Text>
                                <Text size="sm" style={{ flex: 1 }} ta="right">
                                  {String(
                                    selectedTicket.data_points.OutageStatus,
                                  )}
                                </Text>
                              </Group>
                            )}
                            {selectedTicket.data_points.OutageState != null && (
                              <Group justify="space-between" align="flex-start">
                                <Text fw={600} size="sm">
                                  Outage State:
                                </Text>
                                <Text size="sm" style={{ flex: 1 }} ta="right">
                                  {String(
                                    selectedTicket.data_points.OutageState,
                                  )}
                                </Text>
                              </Group>
                            )}
                            {selectedTicket.data_points.OutageType != null && (
                              <Group justify="space-between" align="flex-start">
                                <Text fw={600} size="sm">
                                  Outage Type:
                                </Text>
                                <Text size="sm" style={{ flex: 1 }} ta="right">
                                  {String(
                                    selectedTicket.data_points.OutageType,
                                  )}
                                </Text>
                              </Group>
                            )}
                            {selectedTicket.data_points.NatureOfWork !=
                              null && (
                              <Group justify="space-between" align="flex-start">
                                <Text fw={600} size="sm">
                                  Nature of Work:
                                </Text>
                                <Text size="sm" style={{ flex: 1 }} ta="right">
                                  {String(
                                    selectedTicket.data_points.NatureOfWork,
                                  )}
                                </Text>
                              </Group>
                            )}
                            {selectedTicket.data_points.OutageID != null && (
                              <Group justify="space-between" align="flex-start">
                                <Text fw={600} size="sm">
                                  Outage ID:
                                </Text>
                                <Text
                                  size="sm"
                                  style={{ flex: 1 }}
                                  ta="right"
                                  c="dimmed"
                                >
                                  {String(selectedTicket.data_points.OutageID)}
                                </Text>
                              </Group>
                            )}
                            {selectedTicket.data_points.MRID != null && (
                              <Group justify="space-between" align="flex-start">
                                <Text fw={600} size="sm">
                                  MRID:
                                </Text>
                                <Text
                                  size="sm"
                                  style={{ flex: 1 }}
                                  ta="right"
                                  c="dimmed"
                                >
                                  {String(selectedTicket.data_points.MRID)}
                                </Text>
                              </Group>
                            )}
                          </Stack>
                        )}
                    </Tabs.Panel>

                    <Tabs.Panel value="contacts" pt="md">
                      {(selectedTicket.data_points?.PrimaryContact != null ||
                        selectedTicket.data_points?.SecondaryContact != null ||
                        selectedTicket.data_points?.TertiaryContact !=
                          null) && (
                        <Stack gap="xs">
                          <Text
                            fw={700}
                            size="sm"
                            c="dimmed"
                            tt="uppercase"
                            fz="xs"
                          >
                            Contacts
                          </Text>
                          {selectedTicket.data_points.PrimaryContact !=
                            null && (
                            <Group justify="space-between" align="flex-start">
                              <Text fw={600} size="sm">
                                Primary Contact:
                              </Text>
                              <Text size="sm" style={{ flex: 1 }} ta="right">
                                {String(
                                  selectedTicket.data_points.PrimaryContact,
                                )}
                              </Text>
                            </Group>
                          )}
                          {selectedTicket.data_points.SecondaryContact !=
                            null && (
                            <Group justify="space-between" align="flex-start">
                              <Text fw={600} size="sm">
                                Secondary Contact:
                              </Text>
                              <Text size="sm" style={{ flex: 1 }} ta="right">
                                {String(
                                  selectedTicket.data_points.SecondaryContact,
                                )}
                              </Text>
                            </Group>
                          )}
                          {selectedTicket.data_points.TertiaryContact !=
                            null && (
                            <Group justify="space-between" align="flex-start">
                              <Text fw={600} size="sm">
                                Tertiary Contact:
                              </Text>
                              <Text size="sm" style={{ flex: 1 }} ta="right">
                                {String(
                                  selectedTicket.data_points.TertiaryContact,
                                )}
                              </Text>
                            </Group>
                          )}
                        </Stack>
                      )}
                    </Tabs.Panel>

                    <Tabs.Panel value="request" pt="md">
                      {(selectedTicket.data_points?.RequestedBy != null ||
                        selectedTicket.data_points?.RequestedTime != null ||
                        selectedTicket.data_points?.RequestorName != null) && (
                        <Stack gap="xs">
                          <Text
                            fw={700}
                            size="sm"
                            c="dimmed"
                            tt="uppercase"
                            fz="xs"
                          >
                            Request Information
                          </Text>
                          {selectedTicket.data_points.RequestedBy != null && (
                            <Group justify="space-between" align="flex-start">
                              <Text fw={600} size="sm">
                                Requested By:
                              </Text>
                              <Text size="sm" style={{ flex: 1 }} ta="right">
                                {String(selectedTicket.data_points.RequestedBy)}
                              </Text>
                            </Group>
                          )}
                          {selectedTicket.data_points.RequestedTime != null && (
                            <Group justify="space-between" align="flex-start">
                              <Text fw={600} size="sm">
                                Requested Time:
                              </Text>
                              <Text size="sm" style={{ flex: 1 }} ta="right">
                                {(() => {
                                  const value =
                                    selectedTicket.data_points.RequestedTime
                                  if (
                                    typeof value === 'string' &&
                                    /^\d{4}-\d{2}-\d{2}T/.test(value)
                                  ) {
                                    try {
                                      return dayjs(value)
                                        .tz(projectTimeZone || 'UTC')
                                        .format('MMM D, YYYY HH:mm z')
                                    } catch {
                                      return String(value)
                                    }
                                  }
                                  return String(value)
                                })()}
                              </Text>
                            </Group>
                          )}
                          {selectedTicket.data_points.RequestorName != null && (
                            <Group justify="space-between" align="flex-start">
                              <Text fw={600} size="sm">
                                Requestor Name:
                              </Text>
                              <Text size="sm" style={{ flex: 1 }} ta="right">
                                {String(
                                  selectedTicket.data_points.RequestorName,
                                )}
                              </Text>
                            </Group>
                          )}
                          {selectedTicket.data_points.RequestorNotesComment !=
                            null && (
                            <Group justify="space-between" align="flex-start">
                              <Text fw={600} size="sm">
                                Requestor Notes:
                              </Text>
                              <Text size="sm" style={{ flex: 1 }} ta="right">
                                {String(
                                  selectedTicket.data_points
                                    .RequestorNotesComment,
                                )}
                              </Text>
                            </Group>
                          )}
                        </Stack>
                      )}
                    </Tabs.Panel>

                    <Tabs.Panel value="market" pt="md">
                      {(selectedTicket.data_points?.Market != null ||
                        selectedTicket.data_points?.MarketParticipant != null ||
                        selectedTicket.data_points?.OperatingCompany !=
                          null) && (
                        <Stack gap="xs">
                          <Text
                            fw={700}
                            size="sm"
                            c="dimmed"
                            tt="uppercase"
                            fz="xs"
                          >
                            Market & Company
                          </Text>
                          {selectedTicket.data_points.Market != null && (
                            <Group justify="space-between" align="flex-start">
                              <Text fw={600} size="sm">
                                Market:
                              </Text>
                              <Text size="sm" style={{ flex: 1 }} ta="right">
                                {String(selectedTicket.data_points.Market)}
                              </Text>
                            </Group>
                          )}
                          {selectedTicket.data_points.MarketParticipant !=
                            null && (
                            <Group justify="space-between" align="flex-start">
                              <Text fw={600} size="sm">
                                Market Participant:
                              </Text>
                              <Text size="sm" style={{ flex: 1 }} ta="right">
                                {String(
                                  selectedTicket.data_points.MarketParticipant,
                                )}
                              </Text>
                            </Group>
                          )}
                          {selectedTicket.data_points.OperatingCompany !=
                            null && (
                            <Group justify="space-between" align="flex-start">
                              <Text fw={600} size="sm">
                                Operating Company:
                              </Text>
                              <Text size="sm" style={{ flex: 1 }} ta="right">
                                {String(
                                  selectedTicket.data_points.OperatingCompany,
                                )}
                              </Text>
                            </Group>
                          )}
                        </Stack>
                      )}
                    </Tabs.Panel>

                    <Tabs.Panel value="additional" pt="md">
                      {selectedTicket.data_points &&
                        Object.keys(selectedTicket.data_points).length > 0 && (
                          <Stack gap="xs">
                            <Text
                              fw={700}
                              size="sm"
                              c="dimmed"
                              tt="uppercase"
                              fz="xs"
                            >
                              Additional Data Points
                            </Text>
                            {Object.entries(selectedTicket.data_points)
                              .filter(
                                ([key]) =>
                                  ![
                                    'PlannedStartTime',
                                    'PlannedEndTime',
                                    'ActualEndTime',
                                    'ActualStartTime',
                                    'EarliestStartTime',
                                    'LatestEndTime',
                                    'Station',
                                    'ResourceID',
                                    'EquipmentName',
                                    'EquipmentIdentifier',
                                    'ResourceType',
                                    'OutageStatus',
                                    'OutageState',
                                    'OutageStateID',
                                    'OutageType',
                                    'OutageTypeID',
                                    'NatureOfWork',
                                    'NatureOfWorkID',
                                    'OutageID',
                                    'MRID',
                                    'HSL',
                                    'LSL',
                                    'PrimaryContact',
                                    'SecondaryContact',
                                    'TertiaryContact',
                                    'RequestedBy',
                                    'RequestedTime',
                                    'RequestorName',
                                    'RequestorNotesComment',
                                    'RequestorNotesCompany',
                                    'RequestorNotesCreatedBy',
                                    'SupportingNotesComment',
                                    'SupportingNotesCompany',
                                    'SupportingNotesCreatedBy',
                                    'Market',
                                    'MarketParticipant',
                                    'OperatingCompany',
                                    'LastModifiedBy',
                                    'LastModifiedTime',
                                    'VersionID',
                                    'WarningFlag',
                                  ].includes(key),
                              )
                              .sort(([a], [b]) => a.localeCompare(b))
                              .map(([key, value]) => {
                                let displayValue: string
                                if (value === null || value === undefined) {
                                  displayValue = 'N/A'
                                } else if (typeof value === 'boolean') {
                                  displayValue = value.toString()
                                } else if (typeof value === 'number') {
                                  displayValue = value.toString()
                                } else if (
                                  typeof value === 'string' &&
                                  /^\d{4}-\d{2}-\d{2}T/.test(value)
                                ) {
                                  try {
                                    displayValue = dayjs(value)
                                      .tz(projectTimeZone || 'UTC')
                                      .format('MMM D, YYYY HH:mm z')
                                  } catch {
                                    displayValue = value
                                  }
                                } else {
                                  displayValue = String(value)
                                }

                                return (
                                  <Group
                                    key={key}
                                    justify="space-between"
                                    align="flex-start"
                                    wrap="nowrap"
                                  >
                                    <Text
                                      fw={500}
                                      size="sm"
                                      style={{ minWidth: 200 }}
                                    >
                                      {key}:
                                    </Text>
                                    <Text
                                      size="sm"
                                      style={{ flex: 1, textAlign: 'right' }}
                                      c="dimmed"
                                    >
                                      {displayValue}
                                    </Text>
                                  </Group>
                                )
                              })}
                          </Stack>
                        )}
                    </Tabs.Panel>
                  </Tabs>
                </Stack>
              </ScrollArea>
            </Stack>
          )}
        </Modal>
      </Stack>
    )
  }, [
    outageTicketsLoading,
    outageTicketsData,
    projectTimeZone,
    copiedTicketId,
    selectedTicket,
    modalOpened,
    openModal,
    closeModal,
    theme,
  ])

  return value
}
