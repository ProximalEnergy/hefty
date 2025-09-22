import { type MRT_ColumnDef, MantineReactTable } from 'mantine-react-table'
import { useMemo } from 'react'

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

export function DeviceListTable({ data }: DeviceListTableProps) {
  const columns = useMemo<MRT_ColumnDef<DeviceData>[]>(
    () => [
      {
        accessorKey: 'device',
        header: 'Device',
      },
      {
        accessorKey: 'deviceType',
        header: 'Device Type',
      },
      {
        accessorKey: 'parentDevice',
        header: 'Parent Device',
      },
      {
        accessorKey: 'latitude',
        header: 'Latitude',
      },
      {
        accessorKey: 'longitude',
        header: 'Longitude',
      },
    ],
    [],
  )

  return (
    <MantineReactTable
      columns={columns}
      data={data}
      enableRowSelection={false}
      enableColumnOrdering={true}
      enableSorting={true}
      enableFilters={true}
      enablePagination={false}
      enableGlobalFilter={false}
      enableFullScreenToggle={false}
      enableDensityToggle={false}
      enableColumnActions={false}
      enableHiding={false}
      enableColumnFilters={true}
      initialState={{
        density: 'xs',
      }}
      mantineTableProps={{
        highlightOnHover: true,
        striped: true,
      }}
      mantinePaperProps={{
        withBorder: true,
        shadow: 'none',
        radius: 'md',
      }}
    />
  )
}
