import { type MRT_ColumnDef, MantineReactTable } from 'mantine-react-table'
import { useMemo } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

interface DeviceTypeSummary {
  deviceType: string
  numberOfDevices: number
}

interface DeviceTypeSummaryTableProps {
  data: DeviceTypeSummary[]
  onDataChange?: (updatedData: DeviceTypeSummary[]) => void
}

export function DeviceTypeSummaryTable({
  data,
  onDataChange,
}: DeviceTypeSummaryTableProps) {
  const navigate = useNavigate()
  const { projectId } = useParams<{ projectId: string }>()

  const getDeviceTypeRoute = (deviceType: string): string => {
    const routeMap: Record<string, string> = {
      'Met Stations': 'met-stations',
      Transformers: 'transformers',
      Inverters: 'inverters',
      Combiners: 'combiners',
      Trackers: 'trackers',
    }
    return routeMap[deviceType] || deviceType.toLowerCase().replace(/\s+/g, '-')
  }

  const handleRowClick = (row: DeviceTypeSummary) => {
    const route = getDeviceTypeRoute(row.deviceType)
    navigate(`/onboarding/${projectId}/device-types/${route}`)
  }

  const columns = useMemo<MRT_ColumnDef<DeviceTypeSummary>[]>(
    () => [
      {
        accessorKey: 'deviceType',
        header: 'Device Type',
        enableEditing: false,
        Cell: ({ row }) => (
          <div
            onClick={() => handleRowClick(row.original)}
            style={{
              cursor: 'pointer',
              display: 'flex',
              justifyContent: 'flex-start',
              alignItems: 'center',
              width: '100%',
              height: '100%',
              padding: '8px 8px 8px 8px',
              margin: '0px 0px 0px 0px',
              borderRadius: '4px',
              transition: 'background-color 0.1s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor =
                'var(--mantine-color-proximal-blue-9)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent'
            }}
          >
            {row.original.deviceType}
          </div>
        ),
      },
      {
        accessorKey: 'numberOfDevices',
        header: 'Number of Devices',
        enableEditing: true,
        muiEditTextFieldProps: ({ row }: { row: any }) => ({
          type: 'number',
          inputProps: { min: 0 },
          onBlur: (event: React.FocusEvent<HTMLInputElement>) => {
            const newValue = parseInt(event.target.value) || 0
            if (onDataChange) {
              const updatedData = data.map((item, index) => {
                if (index === row.index) {
                  return {
                    ...item,
                    numberOfDevices: newValue,
                  }
                }
                return item
              })
              onDataChange(updatedData)
            }
          },
        }),
      },
    ],
    [],
  )

  return (
    <MantineReactTable
      columns={columns}
      data={data}
      enableRowSelection={false}
      enableColumnOrdering={false}
      enableSorting={false}
      enableFilters={false}
      enablePagination={false}
      enableGlobalFilter={false}
      enableFullScreenToggle={false}
      enableDensityToggle={false}
      enableColumnActions={false}
      enableHiding={false}
      enableColumnFilters={false}
      enableEditing={!!onDataChange}
      editDisplayMode="cell"
      initialState={{
        density: 'xs',
      }}
      mantineTableProps={{
        highlightOnHover: false,
        striped: true,
      }}
      mantineTableBodyCellProps={({ cell }) => ({
        style:
          cell.column.id === 'deviceType'
            ? {
                paddingTop: 0,
                paddingRight: 0,
                paddingBottom: 0,
                paddingLeft: 0,
              }
            : {},
      })}
      mantinePaperProps={{
        withBorder: true,
        shadow: 'none',
        radius: 'md',
      }}
    />
  )
}
