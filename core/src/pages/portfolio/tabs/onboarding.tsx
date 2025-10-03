import { useGetUserType } from '@/api/admin'
import { ProjectStatusTypeId } from '@/api/v1/operational/project_status_types'
import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { Project } from '@/api/v1/operational/projects'
import { Paper, Stack } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconCircle } from '@tabler/icons-react'
import {
  type MRT_Cell,
  type MRT_Row,
  MantineReactTable,
} from 'mantine-react-table'
import { useNavigate } from 'react-router-dom'

interface OnboardingProjectsTabProps {
  projects: Project[]
  searchTerm: string
}

export function OnboardingProjectsTab({
  projects,
  searchTerm,
}: OnboardingProjectsTabProps) {
  const navigate = useNavigate()
  const userType = useGetUserType({})

  // Filter for onboarding projects
  const onboardingProjects =
    projects?.filter(
      (project) =>
        project.project_status_type_id === ProjectStatusTypeId.ONBOARDING,
    ) || []

  const handleNavigation = (path: string) => {
    if (userType.data?.name_short === 'superadmin') {
      navigate(path)
    } else {
      notifications.show({
        title: 'Under Construction',
        message:
          'Onboarding features are currently under construction. Please check back later.',
        color: 'orange',
        autoClose: 5000,
      })
    }
  }

  // Define table columns
  const columns = [
    {
      accessorKey: 'name_long',
      header: 'Project Name',
      enableSorting: true,
      enableColumnFilter: true,
    },
    {
      accessorKey: 'project_type_id',
      header: 'Project Type',
      accessorFn: (row: Project) => {
        const typeId = row.project_type_id
        return typeId ? ProjectTypeId[typeId] : 'Unknown'
      },
      enableSorting: true,
      enableColumnFilter: true,
    },
    {
      accessorKey: 'devices',
      header: 'Devices',
      enableSorting: false,
      enableColumnFilter: false,
      Cell: ({ row }: { row: MRT_Row<Project> }) => {
        if (row.original.project_type_id === ProjectTypeId.BESS) {
          return null
        }

        return (
          <div
            onClick={(e) => {
              e.stopPropagation()
              handleNavigation(
                `/onboarding/create-pv-system/${row.original.project_id}`,
              )
            }}
            style={{
              cursor: 'pointer',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              width: '100%',
              height: '100%',
              padding: '12px',
              margin: '-12px',
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
            <IconCircle style={{ fill: 'red' }} />
          </div>
        )
      },
    },
    {
      accessorKey: 'expected_energy_model',
      header: 'Expected Energy Model',
      enableSorting: true,
      enableColumnFilter: true,
      Cell: () => {
        return (
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
            }}
          >
            <IconCircle style={{ fill: 'red' }} />
          </div>
        )
      },
    },
  ]

  return (
    <Paper
      withBorder={false}
      radius="md"
      style={{
        display: 'flex',
        flexDirection: 'column',
        flex: 1,
      }}
    >
      <Stack gap={0}>
        <Paper withBorder={false} radius={0} p={0}>
          <MantineReactTable
            columns={columns}
            data={onboardingProjects}
            enableRowSelection={false}
            enableColumnOrdering={false}
            enableGlobalFilter
            enableFilters={true}
            enablePagination={false}
            state={{
              globalFilter: searchTerm,
            }}
            enableSorting={true}
            enableFullScreenToggle={false}
            enableDensityToggle={false}
            enableColumnActions={false}
            enableHiding={false}
            enableColumnFilters={true}
            mantineTableProps={{
              highlightOnHover: true,
              striped: true,
            }}
            mantineTableBodyRowProps={({ row }) => ({
              onClick: () =>
                handleNavigation(`/projects/${row.original.project_id}`),
            })}
            mantineTableBodyCellProps={({
              cell,
            }: {
              cell: MRT_Cell<Project>
            }) => ({
              style:
                cell.column.id === 'devices'
                  ? {
                      padding: 0,
                    }
                  : {},
            })}
            mantinePaperProps={{
              withBorder: true,
              shadow: 'none',
              radius: 'md',
            }}
          />
        </Paper>
      </Stack>
    </Paper>
  )
}
