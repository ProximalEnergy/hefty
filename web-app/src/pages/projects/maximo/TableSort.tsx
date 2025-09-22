import { PageLoader } from '@/components/Loading'
import { useGetEvents } from '@/hooks/api'
import { Event } from '@/hooks/types'
import {
  Center,
  Group,
  Stack,
  Table,
  Text,
  UnstyledButton,
  rem,
} from '@mantine/core'
import {
  IconCheck,
  IconChevronDown,
  IconChevronUp,
  IconSelector,
} from '@tabler/icons-react'
import { useState } from 'react'
import { useParams } from 'react-router-dom'

import classes from './TableSort.module.css'

interface ThProps {
  children: React.ReactNode
  reversed: boolean
  sorted: boolean
  onSort(): void
}

function Th({ children, reversed, sorted, onSort }: ThProps) {
  const Icon = sorted
    ? reversed
      ? IconChevronUp
      : IconChevronDown
    : IconSelector
  return (
    <Table.Th className={classes.th}>
      <UnstyledButton onClick={onSort} className={classes.control}>
        <Group justify="space-between">
          <Text fw={500} fz="sm">
            {children}
          </Text>
          <Center className={classes.icon}>
            <Icon style={{ width: rem(16), height: rem(16) }} stroke={1.5} />
          </Center>
        </Group>
      </UnstyledButton>
    </Table.Th>
  )
}

function sortData(
  data: Event[],
  payload: { sortBy: keyof Event | null; reversed: boolean },
) {
  const { sortBy } = payload

  if (!sortBy) {
    return data
  }

  return data.sort((a, b) => {
    const aValue = String(a[sortBy])
    const bValue = String(b[sortBy])

    if (payload.reversed) {
      return bValue.localeCompare(aValue)
    }

    return aValue.localeCompare(bValue)
  })
}

export function TableSort() {
  const { projectId } = useParams()
  const [sortBy, setSortBy] = useState<keyof Event | null>(null)
  const [reverseSortDirection, setReverseSortDirection] = useState(false)

  const {
    data: rawData,
    isLoading,
    error,
  } = useGetEvents({ pathParams: { projectId: projectId || '-1' } })
  const sortedData = sortData(rawData || [], {
    sortBy,
    reversed: reverseSortDirection,
  })

  const setSorting = (field: keyof Event) => {
    const reversed = field === sortBy ? !reverseSortDirection : false
    setReverseSortDirection(reversed)
    setSortBy(field)
  }

  if (isLoading) return <PageLoader />
  if (error) return <Text>Error: {error.message}</Text>
  if (!rawData || rawData.length === 0)
    return (
      <div style={{ position: 'relative', height: '100%', width: '100%' }}>
        <Center h="100%" w="100%">
          <Stack align="center">
            <IconCheck size={48} />
            <Text>No active alerts!</Text>
          </Stack>
        </Center>
      </div>
    )

  const rows = sortedData.map((row) => (
    <Table.Tr key={row.event_id}>
      {/* <Table.Td>{row.event_id}</Table.Td> */}
      <Table.Td>{row.event_type_id}</Table.Td>
      <Table.Td>{row.device_id}</Table.Td>
      <Table.Td>{row.device_name_full}</Table.Td>
      <Table.Td>{row.time_start}</Table.Td>
    </Table.Tr>
  ))

  return (
    <Table horizontalSpacing="md" verticalSpacing="xs" miw={700} layout="fixed">
      <Table.Tbody>
        <Table.Tr>
          {/* <Th
            sorted={sortBy === "event_id"}
            reversed={reverseSortDirection}
            onSort={() => setSorting("event_id")}
          >
            ID
          </Th> */}
          <Th
            sorted={sortBy === 'event_type_id'}
            reversed={reverseSortDirection}
            onSort={() => setSorting('event_type_id')}
          >
            Event Type ID
          </Th>
          <Th
            sorted={sortBy === 'device_id'}
            reversed={reverseSortDirection}
            onSort={() => setSorting('device_id')}
          >
            Device ID
          </Th>
          <Th
            sorted={sortBy === 'device_name_full'}
            reversed={reverseSortDirection}
            onSort={() => setSorting('device_name_full')}
          >
            Device Name
          </Th>
          <Th
            sorted={sortBy === 'time_start'}
            reversed={reverseSortDirection}
            onSort={() => setSorting('time_start')}
          >
            Time Start
          </Th>
        </Table.Tr>
      </Table.Tbody>
      <Table.Tbody>{rows}</Table.Tbody>
    </Table>
  )
}
