// Columns configuration for KPI Instance Viewer
import { Text } from '@mantine/core'
import {
  type ColumnDef,
  type RowData,
  createColumnHelper,
} from '@tanstack/react-table'
import { useMemo } from 'react'

import type { KPIInstanceColumn, RowMetaData } from '../KPIInstanceViewer'
import { keyOf } from '../kpi-instance-state'
import type { KPIInstanceState } from '../kpi-instance-state'
import InstanceStatus from './InstanceStatus'
import ProjectTypeFilter from './ProjectTypeFilter'
import TextFilter from './TextFilter'

declare module '@tanstack/react-table' {
  // eslint-disable-next-line no-unused-vars
  interface ColumnMeta<TData extends RowData, TValue> {
    projectType?: number
  }
}

const columnHelper = createColumnHelper<RowMetaData>()

const getProjectTypeLabel = (projectType?: number | null): string => {
  if (projectType === 1) return 'PV'
  if (projectType === 2) return 'BESS'
  if (projectType === 3) return 'PV+S'
  return '—'
}

export const useCreateColumns = (
  projectList: Record<string, KPIInstanceColumn>,
  kpiInstanceData: KPIInstanceState,
) => {
  return useMemo(() => {
    const columns = [
      columnHelper.accessor(
        (row) =>
          (() => {
            const projectTypeId = (
              row as RowMetaData & { project_type_id?: number | null }
            ).project_type_id
            return projectTypeId != null ? [projectTypeId] : []
          })(),
        {
          id: 'project_type_id',
          header: 'Project Type',
          cell: ({ row }) => {
            const projectTypeId = (
              row.original as RowMetaData & { project_type_id?: number | null }
            ).project_type_id
            return <Text size="sm">{getProjectTypeLabel(projectTypeId)}</Text>
          },
          enableHiding: false,
          enableColumnFilter: true,
          filterFn: 'arrIncludesSome',
          meta: {
            FilterComponent: ProjectTypeFilter,
          },
        },
      ),
      columnHelper.accessor('device_type_name_long', {
        header: 'Device Type',
        cell: ({ getValue }) => <Text size="sm">{getValue()}</Text>,
        enableHiding: false,
        enableColumnFilter: true,
        filterFn: 'includesString',
        meta: {
          FilterComponent: TextFilter,
        },
      }),
      columnHelper.accessor('metric_name', {
        header: 'Metric',
        cell: ({ getValue, row }) => (
          <Text size="sm">
            {getValue()} ({row.original.kpi_type_id})
          </Text>
        ),
        size: 200,
        enableHiding: false,
        enableColumnFilter: true,
        filterFn: 'includesString',
        meta: {
          FilterComponent: TextFilter,
        },
      }),
    ]

    const projectColumns = Object.keys(projectList).map((projectId) =>
      columnHelper.accessor(
        (row) => {
          const kpiTypeId = row.kpi_type_id as number
          const key = keyOf(kpiTypeId, projectId)
          const value = kpiInstanceData[key]
          if (value == null) return -1
          return value ? 1 : 0
        },
        {
          id: `project-${projectId}`,
          header: projectList[projectId].name_long,
          enableSorting: true,
          sortDescFirst: true,
          meta: {
            align: 'center',
            projectType: projectList[projectId].project_type_id,
          },
          cell: ({ row, table }) => {
            const kpiTypeId = row.original.kpi_type_id as number
            const status = kpiInstanceData[keyOf(kpiTypeId, projectId)]
            const cellValue = status ?? null
            const meta = table.options.meta as
              | {
                  setKPIInstanceState: (
                    updater: (prev: KPIInstanceState) => KPIInstanceState,
                  ) => void
                }
              | undefined
            const setKPIInstanceState = meta?.setKPIInstanceState

            if (!setKPIInstanceState) {
              return (
                <Text size="sm">{cellValue === null ? '—' : cellValue}</Text>
              )
            }

            return (
              <InstanceStatus
                status={cellValue}
                kpiTypeId={row.original.kpi_type_id}
                projectId={projectId}
                setKPIInstanceState={setKPIInstanceState}
              />
            )
          },
        },
      ),
    )

    return [...columns, ...projectColumns] as ColumnDef<RowMetaData>[]
  }, [projectList, kpiInstanceData])
}
