import { useGetCMMSTickets } from '@/api/v1/operational/project/cmms_tickets'
import { useSelectProject } from '@/api/v1/operational/projects'
import {
  EventCMMSTicket,
  useGetEventCMMSTickets,
} from '@/api/v1/protected/web-application/projects/event-cmms-tickets/event_cmms_tickets'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import {
  Box,
  Button,
  Group,
  MultiSelect,
  ScrollArea,
  Stack,
  Switch,
  Text,
  Tooltip,
} from '@mantine/core'
import { IconPlus } from '@tabler/icons-react'
import { useMemo, useState } from 'react'
import { useParams } from 'react-router'

import CMMSTicketCard from './CMMSTicketCard'
import PlaceholderTicket from './PlaceholderTicket'

const Page = () => {
  const { projectId } = useParams()
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([])
  const [showClosed, setShowClosed] = useState(false)

  const project = useSelectProject(projectId!)

  const tickets = useGetCMMSTickets({
    pathParams: { project_id: projectId || '' },
    queryParams: {},
    queryOptions: { enabled: !!projectId },
  })
  const cmmsTicketIds = useMemo(() => {
    return tickets.data?.data.map((ticket) => ticket.cmms_ticket_id) ?? []
  }, [tickets.data])
  const eventCMMSTickets = useGetEventCMMSTickets({
    pathParams: { project_id: projectId || '' },
    queryParams: { cmms_ticket_ids: cmmsTicketIds },
    queryOptions: { enabled: !!projectId && cmmsTicketIds.length > 0 },
  })
  const availableStatuses = useMemo(() => {
    if (!tickets.data?.data) return []
    const statuses = new Set(
      tickets.data.data.map((ticket) => ticket.status || ''),
    )
    return Array.from(statuses).filter(Boolean)
  }, [tickets.data])

  const sortedAndFilteredTickets = useMemo(() => {
    if (!tickets.data?.data) return []

    const statusOrder: { [key: string]: number } = {
      open: 1,
      'in progress': 2,
      'awaiting triage': 3,
      resolved: 4,
      closed: 5,
    }

    let filteredTickets = tickets.data.data

    if (!showClosed) {
      filteredTickets = filteredTickets.filter(
        (ticket) => ticket.status?.toLowerCase() !== 'closed',
      )
    }

    if (selectedStatuses.length > 0) {
      filteredTickets = filteredTickets.filter((ticket) =>
        selectedStatuses.includes(ticket.status || ''),
      )
    }

    return filteredTickets.sort((a, b) => {
      const statusA = a.status?.toLowerCase() || ''
      const statusB = b.status?.toLowerCase() || ''
      return (statusOrder[statusA] || 99) - (statusOrder[statusB] || 99)
    })
  }, [tickets.data, selectedStatuses, showClosed])

  if (tickets.isLoading || eventCMMSTickets.isLoading || project.isLoading) {
    return <PageLoader />
  }

  const renderContent = () => {
    if (!tickets.data?.integration_configured) {
      return <PlaceholderTicket />
    }

    if (tickets.data?.data.length === 0) {
      return <Text>No tickets created in the last 90 days.</Text>
    }

    return (
      <>
        <Group>
          <MultiSelect
            label="Filter by status"
            placeholder="Select statuses"
            data={availableStatuses}
            value={selectedStatuses}
            onChange={setSelectedStatuses}
            clearable
          />
          <Switch
            label="Show closed tickets"
            checked={showClosed}
            onChange={(event) => setShowClosed(event.currentTarget.checked)}
          />
        </Group>
        <ScrollArea.Autosize flex={1} type="scroll">
          <Stack gap="md">
            {sortedAndFilteredTickets.map((ticket) => (
              <CMMSTicketCard
                key={ticket.cmms_ticket_id}
                ticket={ticket}
                eventCMMSTickets={eventCMMSTickets.data?.filter(
                  (eventCMMSTicket: EventCMMSTicket) =>
                    eventCMMSTicket.cmms_ticket_id === ticket.cmms_ticket_id,
                )}
                project={project.data}
              />
            ))}
          </Stack>
        </ScrollArea.Autosize>
      </>
    )
  }

  const createTicketDisabledHint =
    'The create ticket API connection is not set up. Please visit your ' +
    'CMMS platform to create tickets there.'

  return (
    <Stack h="100%" p="md">
      <Group justify="space-between" align="flex-start" wrap="nowrap" gap="md">
        <PageTitle
          info="CMMS stands for Computerized Maintenance Management System. It's a software
application that helps you manage and track your assets, work orders, and
maintenance activities. You can use it to schedule preventive
maintenance, respond to corrective maintenance requests, and analyze
maintenance data to improve your asset performance."
        >
          CMMS Tickets
        </PageTitle>
        <Tooltip label={createTicketDisabledHint} maw={320} multiline>
          <Box component="span" style={{ display: 'inline-block' }}>
            <Button disabled leftSection={<IconPlus size={16} stroke={1.5} />}>
              Create Ticket
            </Button>
          </Box>
        </Tooltip>
      </Group>
      {renderContent()}
    </Stack>
  )
}

export default Page
