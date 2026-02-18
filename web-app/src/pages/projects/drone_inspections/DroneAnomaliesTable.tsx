import { DroneAnomaly } from '@/api/v1/operational/drone_integrations'
import {
  Badge,
  Box,
  Group,
  Pagination,
  Portal,
  Select,
  Stack,
  Table,
  Text,
} from '@mantine/core'
import { IconChevronDown, IconChevronRight } from '@tabler/icons-react'
import {
  type ColumnDef,
  type ExpandedState,
  type GroupingState,
  type PaginationState,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getExpandedRowModel,
  getGroupedRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { Fragment, useEffect, useMemo, useRef, useState } from 'react'

interface DroneAnomaliesTableProps {
  anomalies: DroneAnomaly[]
  inspectionId?: string
}

const formatPowerLoss = (value: number | null | undefined): string => {
  const safeValue =
    typeof value === 'number' && Number.isFinite(value) ? value : 0
  return safeValue.toFixed(2)
}

const DroneAnomaliesTable = ({
  anomalies,
  inspectionId,
}: DroneAnomaliesTableProps) => {
  const anomalyColumns = useMemo<ColumnDef<DroneAnomaly>[]>(
    () => [
      {
        header: 'Subsystem',
        accessorKey: 'subsystem',
        cell: ({ getValue }) => getValue<string>() || 'Unknown',
      },
      {
        header: 'DC Power Loss (kW)',
        accessorKey: 'power_loss_kw',
        aggregationFn: 'sum',
        cell: ({ getValue }) => (
          <Text>{formatPowerLoss(getValue<number | null>())}</Text>
        ),
      },
      {
        header: 'IR Signal',
        accessorKey: 'ir_signal',
      },
      {
        header: 'RGB Signal',
        accessorKey: 'rgb_signal',
      },
      {
        header: 'Remediation',
        accessorKey: 'remediation_category',
      },
    ],
    [],
  )

  const [anomalyGrouping] = useState<GroupingState>(['subsystem'])
  const [anomalySorting] = useState<SortingState>([
    { id: 'power_loss_kw', desc: true },
  ])
  const [anomalyExpanded, setAnomalyExpanded] = useState<ExpandedState>({})
  const [anomalyPagination, setAnomalyPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 25,
  })
  const [hoverPreviewSrc, setHoverPreviewSrc] = useState<string | null>(null)
  const hoverPreviewRef = useRef<HTMLDivElement | null>(null)
  const hoverPointerRef = useRef({ x: 0, y: 0 })

  useEffect(() => {
    setAnomalyExpanded({})
    setAnomalyPagination((prev) => ({ ...prev, pageIndex: 0 }))
    setHoverPreviewSrc(null)
  }, [inspectionId])

  const setPreviewPosition = (x: number, y: number) => {
    hoverPointerRef.current = { x, y }
    if (!hoverPreviewRef.current) return

    hoverPreviewRef.current.style.left = `${x + 16}px`
    hoverPreviewRef.current.style.top = `${y + 16}px`
  }

  useEffect(() => {
    if (!hoverPreviewSrc) return
    const { x, y } = hoverPointerRef.current
    setPreviewPosition(x, y)
  }, [hoverPreviewSrc])

  // eslint-disable-next-line react-hooks/incompatible-library
  const anomalyTable = useReactTable({
    data: anomalies,
    columns: anomalyColumns,
    state: {
      grouping: anomalyGrouping,
      sorting: anomalySorting,
      expanded: anomalyExpanded,
      pagination: anomalyPagination,
    },
    onExpandedChange: setAnomalyExpanded,
    onPaginationChange: setAnomalyPagination,
    enableGrouping: true,
    paginateExpandedRows: true,
    getCoreRowModel: getCoreRowModel(),
    getGroupedRowModel: getGroupedRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  })
  const pageCount = anomalyTable.getPageCount()

  useEffect(() => {
    const lastValidPageIndex = Math.max(pageCount - 1, 0)
    if (anomalyPagination.pageIndex <= lastValidPageIndex) return

    setAnomalyPagination((prev) => ({
      ...prev,
      pageIndex: lastValidPageIndex,
    }))
  }, [anomalyPagination.pageIndex, pageCount])

  return (
    <Stack gap="xs">
      {hoverPreviewSrc && (
        <Portal>
          <Box
            ref={hoverPreviewRef}
            style={{
              position: 'fixed',
              pointerEvents: 'none',
              zIndex: 9999,
              left: -9999,
              top: -9999,
              padding: '4px',
              background: 'rgba(0,0,0,0.85)',
              borderRadius: '6px',
            }}
          >
            <img
              src={hoverPreviewSrc}
              alt="Anomaly preview"
              style={{
                maxWidth: '280px',
                maxHeight: '220px',
                borderRadius: '4px',
              }}
            />
          </Box>
        </Portal>
      )}
      <Group>
        <Badge variant="light">Grouped by Subsystem</Badge>
      </Group>
      <Table
        withTableBorder
        withColumnBorders
        highlightOnHover
        style={{
          borderRadius: 'var(--mantine-radius-md)',
          overflow: 'hidden',
        }}
      >
        <Table.Thead>
          {anomalyTable.getHeaderGroups().map((headerGroup) => (
            <Table.Tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <Table.Th key={header.id}>
                  {header.isPlaceholder
                    ? null
                    : flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                </Table.Th>
              ))}
            </Table.Tr>
          ))}
        </Table.Thead>
        <Table.Tbody>
          {(() => {
            const renderedGroupIds = new Set<string>()
            const pageRows = anomalyTable.getRowModel().rows

            return pageRows.map((row) => {
              const isGroupedRow = row.subRows.length > 0

              if (isGroupedRow) {
                renderedGroupIds.add(row.id)
                const subsystemLabel =
                  (row.getValue('subsystem') as string | null) || 'Unknown'
                const groupedPowerLoss =
                  row.getValue<number | null>('power_loss_kw') ?? 0
                const anomalyCount = row.subRows.length

                return (
                  <Table.Tr
                    key={row.id}
                    style={{
                      background: 'var(--mantine-primary-color-light-hover)',
                      cursor: 'pointer',
                    }}
                    onClick={row.getToggleExpandedHandler()}
                  >
                    <Table.Td>
                      <Group gap={6}>
                        {row.getIsExpanded() ? (
                          <IconChevronDown size={14} />
                        ) : (
                          <IconChevronRight size={14} />
                        )}
                        <Text fw={600}>{subsystemLabel}</Text>
                      </Group>
                    </Table.Td>
                    <Table.Td>
                      <Text fw={600}>{formatPowerLoss(groupedPowerLoss)}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" c="dimmed">
                        {anomalyCount}{' '}
                        {anomalyCount === 1 ? 'anomaly' : 'anomalies'}
                      </Text>
                    </Table.Td>
                    <Table.Td />
                    <Table.Td />
                  </Table.Tr>
                )
              }

              const anomaly = row.original
              const imageSrc = anomaly.ir_image_url || anomaly.rgb_image_url
              const parentGroup = row.getParentRow()
              const showContinuedGroup =
                !!parentGroup && !renderedGroupIds.has(parentGroup.id)

              const leafRow = (
                <Table.Tr
                  key={row.id}
                  title={
                    imageSrc ? 'Hover to preview anomaly image' : undefined
                  }
                  onMouseEnter={(e) => {
                    if (!imageSrc) return
                    setPreviewPosition(e.clientX, e.clientY)
                    setHoverPreviewSrc(imageSrc)
                  }}
                  onMouseMove={(e) => {
                    if (!imageSrc) return
                    setPreviewPosition(e.clientX, e.clientY)
                  }}
                  onMouseLeave={() => setHoverPreviewSrc(null)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <Table.Td key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </Table.Td>
                  ))}
                </Table.Tr>
              )

              if (!showContinuedGroup || !parentGroup) {
                return leafRow
              }

              renderedGroupIds.add(parentGroup.id)
              const parentSubsystemLabel =
                (parentGroup.getValue('subsystem') as string | null) ||
                'Unknown'
              const parentPowerLoss =
                parentGroup.getValue<number | null>('power_loss_kw') ?? 0
              const parentAnomalyCount = parentGroup.subRows.length

              return (
                <Fragment key={`${parentGroup.id}-${row.id}`}>
                  <Table.Tr
                    style={{
                      background: 'var(--mantine-primary-color-light-hover)',
                      cursor: 'pointer',
                    }}
                    onClick={parentGroup.getToggleExpandedHandler()}
                  >
                    <Table.Td>
                      <Group gap={6}>
                        <IconChevronDown size={14} />
                        <Text fw={600}>{parentSubsystemLabel} (continued)</Text>
                      </Group>
                    </Table.Td>
                    <Table.Td>
                      <Text fw={600}>{formatPowerLoss(parentPowerLoss)}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" c="dimmed">
                        {parentAnomalyCount}{' '}
                        {parentAnomalyCount === 1 ? 'anomaly' : 'anomalies'}
                      </Text>
                    </Table.Td>
                    <Table.Td />
                    <Table.Td />
                  </Table.Tr>
                  {leafRow}
                </Fragment>
              )
            })
          })()}
        </Table.Tbody>
      </Table>
      <Group justify="space-between" align="center">
        <Group gap="xs">
          <Text size="sm" c="dimmed">
            Rows per page
          </Text>
          <Select
            data={['10', '25', '50', '100']}
            value={String(anomalyPagination.pageSize)}
            onChange={(value) => {
              if (!value) return
              setAnomalyPagination({
                pageIndex: 0,
                pageSize: Number(value),
              })
            }}
            w={80}
            size="xs"
            allowDeselect={false}
          />
        </Group>
        <Group gap="xs" align="center">
          <Text size="sm" c="dimmed">
            {anomalyTable.getRowCount()} total rows
          </Text>
          <Pagination
            size="sm"
            total={Math.max(anomalyTable.getPageCount(), 1)}
            value={anomalyPagination.pageIndex + 1}
            onChange={(page) => anomalyTable.setPageIndex(page - 1)}
          />
        </Group>
      </Group>
    </Stack>
  )
}

export default DroneAnomaliesTable
