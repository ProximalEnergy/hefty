import { useGetUserType } from '@/api/admin'
import { ProjectTypeEnum } from '@/api/enumerations'
import { ProjectStatusTypeId } from '@/api/v1/operational/project_status_types'
import { Project } from '@/api/v1/operational/projects'
import { Paper, Stack, Table } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconCircle } from '@tabler/icons-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

interface OnboardingProjectsTabProps {
  projects: Project[]
  searchTerm: string
}

const getProjectTypeName = (typeId: number | null): string => {
  if (!typeId) return 'Unknown'
  const key = Object.keys(ProjectTypeEnum).find(
    (k) => ProjectTypeEnum[k as keyof typeof ProjectTypeEnum] === typeId,
  )
  return key || 'Unknown'
}

export function OnboardingProjectsTab({
  projects,
  searchTerm,
}: OnboardingProjectsTabProps) {
  const navigate = useNavigate()
  const userType = useGetUserType({})
  const [sortConfig, setSortConfig] = useState<{
    key: string
    direction: 'asc' | 'desc'
  } | null>(null)

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

  const getCellText = (project: Project, key: string): string => {
    switch (key) {
      case 'name_long':
        return project.name_long ?? ''
      case 'project_type_id':
        return getProjectTypeName(project.project_type_id)
      default:
        return ''
    }
  }

  const filteredData = onboardingProjects.filter((project) => {
    if (!searchTerm) return true
    const term = searchTerm.toLowerCase()
    return (
      getCellText(project, 'name_long').toLowerCase().includes(term) ||
      getCellText(project, 'project_type_id').toLowerCase().includes(term)
    )
  })

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

  const sortedData = sortConfig
    ? [...filteredData].sort((a, b) => {
        const aVal = getCellText(a, sortConfig.key)
        const bVal = getCellText(b, sortConfig.key)
        const cmp = aVal.localeCompare(bVal, undefined, {
          numeric: true,
        })
        return sortConfig.direction === 'asc' ? cmp : -cmp
      })
    : filteredData

  const sortableColumns = ['name_long', 'project_type_id']

  const columns = [
    { key: 'name_long', header: 'Project Name' },
    { key: 'project_type_id', header: 'Project Type' },
    { key: 'devices', header: 'Devices' },
    {
      key: 'expected_energy_model',
      header: 'Expected Energy Model',
    },
  ]

  return (
    <Paper
      withBorder
      shadow="none"
      radius="md"
      style={{
        display: 'flex',
        flexDirection: 'column',
        flex: 1,
      }}
    >
      <Stack gap={0}>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              {columns.map((col) => {
                const isSortable = sortableColumns.includes(col.key)
                return (
                  <Table.Th
                    key={col.key}
                    style={{
                      cursor: isSortable ? 'pointer' : undefined,
                    }}
                    onClick={isSortable ? () => handleSort(col.key) : undefined}
                  >
                    {col.header}
                    {sortConfig?.key === col.key && (
                      <span>
                        {sortConfig.direction === 'asc' ? ' ↑' : ' ↓'}
                      </span>
                    )}
                  </Table.Th>
                )
              })}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {sortedData.map((project) => (
              <Table.Tr
                key={project.project_id}
                onClick={() =>
                  handleNavigation(`/projects/${project.project_id}`)
                }
                style={{ cursor: 'pointer' }}
              >
                <Table.Td>{project.name_long}</Table.Td>
                <Table.Td>
                  {getProjectTypeName(project.project_type_id)}
                </Table.Td>
                <Table.Td style={{ padding: 0 }}>
                  {project.project_type_id !== ProjectTypeEnum.BESS && (
                    <div
                      onClick={(e) => {
                        e.stopPropagation()
                        handleNavigation(
                          `/onboarding/create-pv-system/${project.project_id}`,
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
                  )}
                </Table.Td>
                <Table.Td>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'center',
                    }}
                  >
                    <IconCircle style={{ fill: 'red' }} />
                  </div>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Stack>
    </Paper>
  )
}
