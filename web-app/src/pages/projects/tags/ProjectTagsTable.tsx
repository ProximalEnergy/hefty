import { DataTable } from '@/components/DataTable'
import { Tag } from '@/hooks/projectTags'
import { columns } from '@/pages/projects/tags/ProjectTagsColumns'
import {
  ColumnFiltersState,
  getCoreRowModel,
  getExpandedRowModel,
  getFilteredRowModel,
  getGroupedRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'

export function ProjectTagsTable({
  data,
  columnFilters,
  columnVisibility,
}: {
  data: Tag[]
  columnFilters: ColumnFiltersState
  columnVisibility: { [key: string]: boolean }
}) {
  const table = useReactTable({
    data,
    columns,
    initialState: {
      sorting: [
        { id: 'device_id', desc: false },
        { id: 'tag_id', desc: false },
      ],
      grouping: ['device_id'],
      columnVisibility,
    },
    state: {
      columnFilters,
    },
    getCoreRowModel: getCoreRowModel(),
    // Provide sorting row model to enable client side sorting
    getSortedRowModel: getSortedRowModel(),
    // Provide grouped row model to enable row grouping
    getGroupedRowModel: getGroupedRowModel(),
    // Provide expanded row model to enable row expansion
    getExpandedRowModel: getExpandedRowModel(),
    // Provide filtered row model to enable row filtering
    getFilteredRowModel: getFilteredRowModel(),
  })

  return <DataTable table={table} />
}
