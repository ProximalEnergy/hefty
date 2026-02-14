import { Paper, Table, TextInput } from '@mantine/core'
import { useState } from 'react'

interface DeviceData {
  device: string
  deviceType: string
  parentDevice: string
  latitude: number
  longitude: number
}

interface DeviceListTableProps {
  data: DeviceData[]
}

const columns = [
  { key: 'device', header: 'Device' },
  { key: 'deviceType', header: 'Device Type' },
  { key: 'parentDevice', header: 'Parent Device' },
  { key: 'latitude', header: 'Latitude' },
  { key: 'longitude', header: 'Longitude' },
]

export function DeviceListTable({ data }: DeviceListTableProps) {
  const [sortConfig, setSortConfig] = useState<{
    key: string
    direction: 'asc' | 'desc'
  } | null>(null)
  const [columnFilters, setColumnFilters] = useState<Record<string, string>>({})

  const getCellText = (row: DeviceData, key: string): string =>
    String(row[key as keyof DeviceData] ?? '')

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

  const filtered = data.filter((row) =>
    columns.every((col) => {
      const filter = columnFilters[col.key]
      if (!filter) return true
      const cellText = getCellText(row, col.key)
      return cellText.toLowerCase().includes(filter.toLowerCase())
    }),
  )

  const sortedData = sortConfig
    ? [...filtered].sort((a, b) => {
        const aVal = getCellText(a, sortConfig.key)
        const bVal = getCellText(b, sortConfig.key)
        const aNum = Number(aVal)
        const bNum = Number(bVal)
        const bothNumeric =
          aVal !== '' && bVal !== '' && !isNaN(aNum) && !isNaN(bNum)
        const cmp = bothNumeric
          ? aNum - bNum
          : aVal.localeCompare(bVal, undefined, {
              numeric: true,
            })
        return sortConfig.direction === 'asc' ? cmp : -cmp
      })
    : filtered

  return (
    <Paper withBorder shadow="none" radius="md">
      <Table striped highlightOnHover>
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
                  <span>{sortConfig.direction === 'asc' ? ' ↑' : ' ↓'}</span>
                )}
              </Table.Th>
            ))}
          </Table.Tr>
          <Table.Tr>
            {columns.map((col) => (
              <Table.Th key={`${col.key}-filter`}>
                <TextInput
                  size="xs"
                  placeholder="Filter..."
                  value={columnFilters[col.key] ?? ''}
                  onChange={(e) =>
                    setColumnFilters((prev) => ({
                      ...prev,
                      [col.key]: e.currentTarget.value,
                    }))
                  }
                />
              </Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {sortedData.map((row, index) => (
            <Table.Tr key={index}>
              {columns.map((col) => (
                <Table.Td key={col.key}>{getCellText(row, col.key)}</Table.Td>
              ))}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Paper>
  )
}
