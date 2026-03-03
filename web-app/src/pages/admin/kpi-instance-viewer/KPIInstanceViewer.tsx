import {
  KPIInstanceColumn,
  KPITypeInstance,
  useDeleteKPIInstances,
  useGetKPIInstances,
  useUpsertKPIInstances,
} from '@/api/v1/protected/kpi-instances'
import {
  Box,
  Button,
  Checkbox,
  Group,
  Loader,
  Menu,
  Paper,
  Stack,
  Table,
  Title,
} from '@mantine/core'
import { IconColumns } from '@tabler/icons-react'
import {
  type ColumnFiltersState,
  type SortingState,
  type Table as TanStackTable,
  type VisibilityState,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { useEffect, useMemo, useRef, useState } from 'react'

import TableShell from './TableShell'
import { useCreateColumns } from './columns-config/ColumnsConfig'
import { keyOf } from './kpi-instance-state'
import type { KPIInstanceKey, KPIInstanceState } from './kpi-instance-state'

// Re-export types for use in other components
export type { KPIInstanceColumn }

// RowMetaData matches KPITypeInstance structure
export type RowMetaData = KPITypeInstance

const areKPIInstanceDataEqual = (
  a: KPIInstanceState,
  b: KPIInstanceState,
): boolean => {
  const aKeys = Object.keys(a)
  const bKeys = Object.keys(b)
  if (aKeys.length !== bKeys.length) return false

  for (const key of aKeys) {
    const aValue = a[key as KPIInstanceKey]
    const bValue = b[key as KPIInstanceKey]
    if (bValue == null || aValue !== bValue) {
      return false
    }
  }
  return true
}

const diffKPIInstanceState = (
  original: KPIInstanceState,
  current: KPIInstanceState,
): { upserts: KPIInstanceState; deletes: KPIInstanceKey[] } => {
  const upserts: KPIInstanceState = {}
  const deletes: KPIInstanceKey[] = []

  for (const [key, currentValue] of Object.entries(current)) {
    const typedKey = key as KPIInstanceKey
    const originalValue = original[typedKey]
    if (originalValue == null || originalValue !== currentValue) {
      upserts[typedKey] = currentValue
    }
  }

  for (const key of Object.keys(original)) {
    const typedKey = key as KPIInstanceKey
    if (!(typedKey in current)) {
      deletes.push(typedKey)
    }
  }

  return { upserts, deletes }
}

type ColumnVisibilityMenuProps = {
  table: TanStackTable<RowMetaData>
}

const getProjectTypeLabel = (projectType?: number): string | null => {
  if (projectType === 1) return 'PV'
  if (projectType === 2) return 'BESS'
  if (projectType === 3) return 'PV+S'
  return null
}

const ColumnVisibilityMenu = ({ table }: ColumnVisibilityMenuProps) => {
  const hideableColumns = table
    .getAllLeafColumns()
    .filter((column) => column.getCanHide())
  const allVisible = hideableColumns.every((column) => column.getIsVisible())
  const allHidden = hideableColumns.every((column) => !column.getIsVisible())

  const setAllColumnsVisibility = (visible: boolean) => {
    hideableColumns.forEach((column) => column.toggleVisibility(visible))
  }

  return (
    <Menu shadow="md" width={240} closeOnItemClick={false}>
      <Menu.Target>
        <Button variant="light" leftSection={<IconColumns size={16} />}>
          Columns
        </Button>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Label>Toggle Columns</Menu.Label>
        <Menu.Item
          disabled={allVisible}
          onClick={() => setAllColumnsVisibility(true)}
        >
          Select All
        </Menu.Item>
        <Menu.Item
          disabled={allHidden}
          onClick={() => setAllColumnsVisibility(false)}
        >
          Deselect All
        </Menu.Item>
        <Menu.Divider />
        {hideableColumns.map((column) => {
          const header = column.columnDef.header
          const baseLabel = typeof header === 'string' ? header : column.id
          const projectTypeLabel = getProjectTypeLabel(
            column.columnDef.meta?.projectType,
          )
          const label = projectTypeLabel
            ? `${baseLabel} (${projectTypeLabel})`
            : baseLabel
          return (
            <Menu.Item key={column.id}>
              <Checkbox
                label={label}
                checked={column.getIsVisible()}
                onChange={column.getToggleVisibilityHandler()}
              />
            </Menu.Item>
          )
        })}
      </Menu.Dropdown>
    </Menu>
  )
}

type SelectProjectTypeWithInstancesButtonProps = {
  table: TanStackTable<RowMetaData>
  projectList: Record<string, KPIInstanceColumn>
  projectTypeId: number
  label: string
  projectTypeFilterValue?: number[]
}

const SelectProjectTypeWithInstancesButton = ({
  table,
  projectList,
  projectTypeId,
  label,
  projectTypeFilterValue,
}: SelectProjectTypeWithInstancesButtonProps) => {
  const hideableColumns = table
    .getAllLeafColumns()
    .filter((column) => column.getCanHide())

  const matchingProjectColumns = hideableColumns.filter((column) => {
    const projectId = column.id.replace('project-', '')
    const project = projectList[projectId]
    return (
      project != null &&
      project.project_type_id === projectTypeId &&
      project.has_any_kpi_instances
    )
  })

  const handleSelectProjectTypeWithInstances = () => {
    hideableColumns.forEach((column) => {
      const projectId = column.id.replace('project-', '')
      const project = projectList[projectId]
      const shouldBeVisible =
        project != null &&
        project.project_type_id === projectTypeId &&
        project.has_any_kpi_instances
      column.toggleVisibility(shouldBeVisible)
    })
    if (projectTypeFilterValue != null) {
      table.getColumn('project_type_id')?.setFilterValue(projectTypeFilterValue)
    }
  }

  return (
    <Button
      variant="light"
      onClick={handleSelectProjectTypeWithInstances}
      disabled={matchingProjectColumns.length === 0}
    >
      {label}
    </Button>
  )
}

const KPIInstanceViewer = () => {
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})

  // Fetch data from API
  const kpiInstancesQuery = useGetKPIInstances()
  const upsertKPIInstancesMutation = useUpsertKPIInstances()
  const deleteKPIInstancesMutation = useDeleteKPIInstances()

  // Extract data from API response
  const apiData = kpiInstancesQuery.data

  // Convert flat API map "<kpi_type_id>::<project_id>" -> bool into canonical state
  const originalData = useMemo<KPIInstanceState | undefined>(() => {
    if (!apiData) return undefined
    const converted: KPIInstanceState = {}
    for (const [compositeKey, visible] of Object.entries(apiData.data)) {
      const [kpiTypeIdStr, projectId] = compositeKey.split('::')
      const kpiTypeId = Number(kpiTypeIdStr)
      if (Number.isNaN(kpiTypeId) || !projectId) continue
      converted[keyOf(kpiTypeId, projectId)] = Boolean(visible)
    }
    return converted
  }, [apiData])

  // Track if we've initialized state with the latest query data
  const hasInitializedRef = useRef<string>('')

  // Initialize state with original data when available
  const [kpiInstanceState, setKPIInstanceState] = useState<KPIInstanceState>(
    () => {
      // On first render, originalData may be undefined, so initialize with empty object
      return {}
    },
  )

  // Update state when originalData becomes available
  const dataUpdatedKey = `${kpiInstancesQuery.dataUpdatedAt ?? 0}`
  useEffect(() => {
    if (!originalData || hasInitializedRef.current === dataUpdatedKey) return
    hasInitializedRef.current = dataUpdatedKey
    setKPIInstanceState(originalData)
  }, [originalData, dataUpdatedKey])

  const changesDetected = useMemo(
    () =>
      originalData
        ? !areKPIInstanceDataEqual(kpiInstanceState, originalData)
        : false,
    [kpiInstanceState, originalData],
  )

  const handleKPIInstanceStateChange = (
    updater: (prev: KPIInstanceState) => KPIInstanceState,
  ) => {
    setKPIInstanceState(updater)
  }

  const isSaving =
    upsertKPIInstancesMutation.isPending || deleteKPIInstancesMutation.isPending

  const handleSaveChanges = async () => {
    if (!originalData) return

    const { upserts, deletes } = diffKPIInstanceState(
      originalData,
      kpiInstanceState,
    )

    try {
      if (Object.keys(upserts).length > 0) {
        await upsertKPIInstancesMutation.mutateAsync(upserts)
      }
      if (deletes.length > 0) {
        await deleteKPIInstancesMutation.mutateAsync(deletes)
      }
      await kpiInstancesQuery.refetch()
    } catch {
      // Keep local edits in place so the user can retry save.
    }
  }

  // Prepare data for table
  const rows = apiData?.rows ?? []
  const projectList: Record<string, KPIInstanceColumn> = apiData?.columns ?? {}

  const columns = useCreateColumns(projectList, kpiInstanceState)

  const table = useReactTable<RowMetaData>({
    data: rows,
    columns,
    enableSorting: true,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
    },
    meta: {
      projectList,
      kpiInstanceData: kpiInstanceState,
      setKPIInstanceState: handleKPIInstanceStateChange,
    },
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
  })

  const tableReady =
    !kpiInstancesQuery.isLoading && apiData != null && originalData != null

  return (
    <Box p="md">
      <Stack gap="lg">
        <Group justify="space-between" align="center">
          <Group gap="sm">
            <Title order={2}>KPI Instance Viewer</Title>
            <Button
              onClick={() => void handleSaveChanges()}
              disabled={!changesDetected || isSaving}
            >
              Save Changes
            </Button>
          </Group>
          <Group gap="xs">
            <SelectProjectTypeWithInstancesButton
              table={table}
              projectList={projectList}
              projectTypeId={1}
              label="PV Only"
              projectTypeFilterValue={[1, 3]}
            />
            <SelectProjectTypeWithInstancesButton
              table={table}
              projectList={projectList}
              projectTypeId={2}
              label="BESS Only"
              projectTypeFilterValue={[2, 3]}
            />
            <SelectProjectTypeWithInstancesButton
              table={table}
              projectList={projectList}
              projectTypeId={3}
              label="PV+S Only"
              projectTypeFilterValue={[1, 2, 3]}
            />
            <ColumnVisibilityMenu table={table} />
          </Group>
        </Group>
        {tableReady ? (
          <Paper
            withBorder
            shadow="none"
            radius="md"
            style={{ overflow: 'hidden' }}
          >
            <Table.ScrollContainer
              minWidth="100%"
              maxHeight="calc(100vh - 180px)"
            >
              <TableShell table={table} />
            </Table.ScrollContainer>
          </Paper>
        ) : (
          <Box
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: 200,
            }}
          >
            <Loader />
          </Box>
        )}
      </Stack>
    </Box>
  )
}

export default KPIInstanceViewer
