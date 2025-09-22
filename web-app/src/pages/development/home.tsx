import CustomCard from '@/components/CustomCard'
import { useGetResources } from '@/hooks/api'
import { Resource } from '@/hooks/types'
import { Stack } from '@mantine/core'
import {
  type MRT_ColumnDef,
  MantineReactTable,
  useMantineReactTable,
} from 'mantine-react-table'
import { useMemo } from 'react'
import { Link } from 'react-router-dom'

const Home = () => {
  const columns = useMemo<MRT_ColumnDef<Resource>[]>(
    () => [
      {
        accessorKey: 'name_long',
        header: 'Name',
        Cell: ({ row }) => (
          <Link
            to={`/development/resources/${row.original.resource_id}`}
            style={{ color: 'inherit' }}
          >
            {row.original.name_long}
          </Link>
        ),
      },
      {
        accessorKey: 'capacity_power',
        header: 'Power Capacity (MW)',
      },
      {
        accessorKey: 'qse.name_long',
        header: 'QSE',
      },
      {
        accessorKey: 'dme.name_long',
        header: 'DME',
      },
      {
        accessorKey: 'settlement_point.name',
        header: 'Settlement Point',
      },
      {
        accessorKey: 'county',
        header: 'County',
      },
    ],
    [],
  )

  const { data } = useGetResources({ queryParams: { deep: true } })

  const fetchedData = data ?? []

  const table = useMantineReactTable({
    columns,
    data: fetchedData,
    enableHiding: false,
    enableRowVirtualization: true,
    enablePagination: false,
    enableBottomToolbar: false,
    enableTopToolbar: false,
    mantinePaperProps: {
      shadow: undefined,
      style: {
        border: 'none',
        borderRadius: 'inherit',
        height: '100%',
      },
    },
  })

  return (
    <Stack h="100%" p="md">
      <CustomCard
        title="ERCOT Energy Storage Resources"
        fill
        style={{ height: '100%' }}
      >
        <MantineReactTable table={table} />
      </CustomCard>
    </Stack>
  )
}

export default Home
