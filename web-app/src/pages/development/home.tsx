import CustomCard from '@/components/CustomCard'
import { useGetResources } from '@/hooks/api'
import { Resource } from '@/hooks/types'
import { ScrollArea, Stack, Table } from '@mantine/core'
import { useMemo, useState } from 'react'
import { Link } from 'react-router'

const Home = () => {
  const [sortConfig, setSortConfig] = useState<{
    key: string
    direction: 'asc' | 'desc'
  } | null>(null)

  const columns = useMemo(
    () => [
      { key: 'name_long', header: 'Name' },
      { key: 'capacity_power', header: 'Power Capacity (MW)' },
      { key: 'qse.name_long', header: 'QSE' },
      { key: 'dme.name_long', header: 'DME' },
      { key: 'settlement_point.name', header: 'Settlement Point' },
      { key: 'county', header: 'County' },
    ],
    [],
  )

  const { data } = useGetResources({ queryParams: { deep: true } })

  const getNestedValue = (obj: Resource, path: string): string => {
    const keys = path.split('.')
    let value: unknown = obj
    for (const key of keys) {
      if (value && typeof value === 'object' && key in value) {
        value = (value as Record<string, unknown>)[key]
      } else {
        return ''
      }
    }
    return String(value ?? '')
  }

  const sortedData = useMemo(() => {
    const fetchedData = data ?? []
    if (!sortConfig) return fetchedData

    return [...fetchedData].sort((a, b) => {
      const aValue = getNestedValue(a, sortConfig.key)
      const bValue = getNestedValue(b, sortConfig.key)
      const aNum = Number(aValue)
      const bNum = Number(bValue)
      const bothNumeric =
        aValue !== '' && bValue !== '' && !isNaN(aNum) && !isNaN(bNum)
      const cmp = bothNumeric
        ? aNum - bNum
        : aValue.localeCompare(bValue, undefined, { numeric: true })
      return sortConfig.direction === 'asc' ? cmp : -cmp
    })
  }, [data, sortConfig])

  const handleSort = (key: string) => {
    setSortConfig((current) => {
      if (!current || current.key !== key) {
        return { key, direction: 'asc' }
      }
      if (current.direction === 'asc') {
        return { key, direction: 'desc' }
      }
      return null
    })
  }

  const renderCell = (
    resource: Resource,
    columnKey: string,
  ): React.ReactNode => {
    if (columnKey === 'name_long') {
      return (
        <Link
          to={`/development/resources/${resource.resource_id}`}
          style={{ color: 'inherit' }}
        >
          {resource.name_long}
        </Link>
      )
    }
    return getNestedValue(resource, columnKey)
  }

  return (
    <Stack h="100%" p="md">
      <CustomCard
        title="ERCOT Energy Storage Resources"
        fill
        style={{ height: '100%' }}
      >
        <ScrollArea style={{ height: '100%' }}>
          <Table stickyHeader striped>
            <Table.Thead>
              <Table.Tr>
                {columns.map((col) => (
                  <Table.Th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    style={{ cursor: 'pointer' }}
                  >
                    {col.header}
                    {sortConfig?.key === col.key && (
                      <span>
                        {sortConfig.direction === 'asc' ? ' ↑' : ' ↓'}
                      </span>
                    )}
                  </Table.Th>
                ))}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {sortedData.map((resource) => (
                <Table.Tr key={resource.resource_id}>
                  {columns.map((col) => (
                    <Table.Td key={col.key}>
                      {renderCell(resource, col.key)}
                    </Table.Td>
                  ))}
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </ScrollArea>
      </CustomCard>
    </Stack>
  )
}

export default Home
