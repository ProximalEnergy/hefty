import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { Project, useGetProjects } from '@/api/v1/operational/projects'
import CustomCard from '@/components/CustomCard'
import { NoData, PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { useTipsPersonalPortfolio } from '@/components/Tips'
import { Stack, Table, Text } from '@mantine/core'
import { Link } from 'react-router-dom'

const PortfolioList = () => {
  useTipsPersonalPortfolio()

  const { data, isLoading, error } = useGetProjects({
    queryParams: {
      deep: true,
    },
  })

  if (isLoading) {
    return <PageLoader />
  }

  if (error) {
    return <PageError error={error} />
  }

  if (!data) {
    return <NoData />
  }

  // Sort data by data.name_short
  data.sort((a, b) => (a.name_short > b.name_short ? 1 : -1))

  const pvProjects = data.filter(
    (project) => project.project_type_id === ProjectTypeId.PV,
  )
  const bessProjects = data.filter(
    (project) => project.project_type_id === ProjectTypeId.BESS,
  )
  const pvsProjects = data.filter(
    (project) => project.project_type_id === ProjectTypeId.PV_BESS,
  )

  return (
    <Stack p="md">
      <PageTitle
        info={
          <Stack>
            <Text>
              This page provides a sortable list of all projects in the
              portfolio, separated by project type.
            </Text>
            <Text>
              Click on a project name to navigate to its dedicated page.
            </Text>
          </Stack>
        }
      >
        Portfolio
      </PageTitle>
      <PVTable data={pvProjects} />
      <BESSTable data={bessProjects} />
      <PVSTable data={pvsProjects} />
    </Stack>
  )
}

const PVTable = ({ data }: { data: Project[] }) => {
  // If data is empty, return null
  if (data.length === 0) {
    return null
  }

  return (
    <CustomCard title="PV">
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th w="25%">Name</Table.Th>
            <Table.Th w="25%">POI (MW)</Table.Th>
            <Table.Th w="25%">AC (MW)</Table.Th>
            <Table.Th w="25%">DC (MW)</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {data.map((project) => (
            <Table.Tr key={project.project_id}>
              <Table.Td>
                <Link
                  to={`/projects/${project.project_id}`}
                  style={{ color: 'inherit' }}
                >
                  {project.name_long}
                </Link>
              </Table.Td>
              <Table.Td>{Number(project.poi.toFixed(3))}</Table.Td>
              <Table.Td>{Number(project.capacity_ac?.toFixed(3))}</Table.Td>
              <Table.Td>{Number(project.capacity_dc?.toFixed(3))}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </CustomCard>
  )
}

const BESSTable = ({ data }: { data: Project[] }) => {
  // If data is empty, return null
  if (data.length === 0) {
    return null
  }

  return (
    <CustomCard title="BESS">
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th w="33.3%">Name</Table.Th>
            <Table.Th w="33.3%">AC (MW)</Table.Th>
            <Table.Th w="33.3%">DC (MWh)</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {data.map((project) => (
            <Table.Tr key={project.project_id}>
              <Table.Td>
                <Link
                  to={`/projects/${project.project_id}`}
                  style={{ color: 'inherit' }}
                >
                  {project.name_long}
                </Link>
              </Table.Td>
              <Table.Td>
                {Number(project.capacity_bess_power_ac?.toFixed(3))}
              </Table.Td>
              <Table.Td>
                {Number(project.capacity_bess_energy_bol_dc?.toFixed(3))}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </CustomCard>
  )
}

const PVSTable = ({ data }: { data: Project[] }) => {
  // If data is empty, return null
  if (data.length === 0) {
    return null
  }

  return (
    <CustomCard title="PV+BESS">
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th w="16.66%">Name</Table.Th>
            <Table.Th w="16.66%">PV POI (MW)</Table.Th>
            <Table.Th w="16.66%">PV AC (MW)</Table.Th>
            <Table.Th w="16.66%">PV DC (MW)</Table.Th>
            <Table.Th w="16.66%">BESS AC (MW)</Table.Th>
            <Table.Th w="16.66%">BESS DC (MWh)</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {data.map((project) => (
            <Table.Tr key={project.project_id}>
              <Table.Td>
                <Link
                  to={`/projects/${project.project_id}`}
                  style={{ color: 'inherit' }}
                >
                  {project.name_long}
                </Link>
              </Table.Td>
              <Table.Td>{Number(project.poi.toFixed(3))}</Table.Td>
              <Table.Td>{Number(project.capacity_ac?.toFixed(3))}</Table.Td>
              <Table.Td>{Number(project.capacity_dc?.toFixed(3))}</Table.Td>
              <Table.Td>
                {Number(project.capacity_bess_power_ac?.toFixed(3))}
              </Table.Td>
              <Table.Td>
                {project.capacity_bess_energy_bol_dc?.toFixed(1)}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </CustomCard>
  )
}

export default PortfolioList
