import { ProjectTypeEnum } from '@/api/enumerations'
import { Project, useGetProjects } from '@/api/v1/operational/projects'
import { useGetQSEAccess } from '@/api/v1/protected/web-application/projects/financial/qse_access'
import CustomCard from '@/components/CustomCard'
import { NoData, PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { useTipsPersonalPortfolio } from '@/components/Tips'
import { Skeleton, Stack, Table, Text, Tooltip } from '@mantine/core'
import { useMemo } from 'react'
import { Link } from 'react-router'

import { useBESSRevenueSummary } from './hooks/useBESSRevenueSummary'
import {
  type PVRevenueData,
  computePVRevenue,
  usePVRevenueData,
} from './hooks/usePVRevenueSummary'

const QSE_TOOLTIP =
  'QSE integration and permissions are' + ' not configured for this project'

const PPA_TOOLTIP = 'PPA rate is not configured for this project'

const sortByName = (a: Project, b: Project) =>
  a.name_short > b.name_short ? 1 : -1

const PortfolioList = () => {
  useTipsPersonalPortfolio()

  const { data, isLoading, error } = useGetProjects({
    queryParams: {
      deep: true,
    },
  })

  const { pvProjects, bessProjects, pvsProjects, pvKpiProjectIds } =
    useMemo(() => {
      if (!data)
        return {
          pvProjects: [] as Project[],
          bessProjects: [] as Project[],
          pvsProjects: [] as Project[],
          pvKpiProjectIds: [] as string[],
        }
      const sorted = [...data].sort(sortByName)
      const pv = sorted.filter((p) => p.project_type_id === ProjectTypeEnum.PV)
      const bess = sorted.filter(
        (p) => p.project_type_id === ProjectTypeEnum.BESS,
      )
      const pvs = sorted.filter(
        (p) => p.project_type_id === ProjectTypeEnum.PVS,
      )
      const ids = [...pv, ...pvs]
        .filter((p) => !!p.ppa?.rate)
        .map((p) => p.project_id)
      return {
        pvProjects: pv,
        bessProjects: bess,
        pvsProjects: pvs,
        pvKpiProjectIds: ids,
      }
    }, [data])

  const pvRevenueData = usePVRevenueData({
    projectIds: pvKpiProjectIds,
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
      <PVTable data={pvProjects} revenueData={pvRevenueData} />
      <BESSTable data={bessProjects} />
      <PVSTable data={pvsProjects} revenueData={pvRevenueData} />
    </Stack>
  )
}

const PVTable = ({
  data,
  revenueData,
}: {
  data: Project[]
  revenueData: PVRevenueData
}) => {
  if (data.length === 0) {
    return null
  }

  return (
    <CustomCard title="PV">
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Name</Table.Th>
            <Table.Th>POI (MW)</Table.Th>
            <Table.Th>AC (MW)</Table.Th>
            <Table.Th>DC (MW)</Table.Th>
            <Table.Th ta="right">Rev. MTD</Table.Th>
            <Table.Th ta="right">Rev. YTD</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {data.map((project) => (
            <PVProjectRow
              key={project.project_id}
              project={project}
              revenueData={revenueData}
            />
          ))}
        </Table.Tbody>
      </Table>
    </CustomCard>
  )
}

const fmtNum = (v: number | null | undefined, digits = 3) =>
  v != null ? Number(v.toFixed(digits)) : '—'

const formatMWh = (mwh: number | null) => {
  if (mwh === null) return '—'
  return `${mwh.toLocaleString('en-US', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })} MWh`
}

const pvRevenueHover = (energy: number | null, ppaRate: number) => {
  if (energy === null) return undefined
  return `${formatMWh(energy)}` + ` × $${ppaRate}/MWh`
}

const PVProjectRow = ({
  project,
  revenueData,
}: {
  project: Project
  revenueData: PVRevenueData
}) => {
  const hasPPA = !!project.ppa?.rate
  const notSetUp = !hasPPA
  const ppaRate = project.ppa?.rate ?? 0

  const { energyMTD, energyYTD, revenueMTD, revenueYTD } = useMemo(
    () =>
      computePVRevenue({
        projectId: project.project_id,
        ppaRate,
        tz: project.time_zone,
        kpiData: revenueData.kpiData,
      }),
    [project.project_id, ppaRate, project.time_zone, revenueData.kpiData],
  )

  const isLoading = hasPPA && !revenueData.isError && revenueData.isLoading

  return (
    <Table.Tr>
      <Table.Td>
        <Link
          to={`/projects/${project.project_id}`}
          style={{ color: 'inherit' }}
        >
          {project.name_long}
        </Link>
      </Table.Td>
      <Table.Td>{fmtNum(project.poi)}</Table.Td>
      <Table.Td>{fmtNum(project.capacity_ac)}</Table.Td>
      <Table.Td>{fmtNum(project.capacity_dc)}</Table.Td>
      <RevenueCell
        value={revenueMTD}
        isLoading={isLoading}
        notSetUp={notSetUp}
        tooltipLabel={PPA_TOOLTIP}
        hoverDetail={pvRevenueHover(energyMTD, ppaRate)}
      />
      <RevenueCell
        value={revenueYTD}
        isLoading={isLoading}
        notSetUp={notSetUp}
        tooltipLabel={PPA_TOOLTIP}
        hoverDetail={pvRevenueHover(energyYTD, ppaRate)}
      />
    </Table.Tr>
  )
}

const formatCurrency = (value: number | null) => {
  if (value === null) return '—'
  return value.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })
}

const BESSTable = ({ data }: { data: Project[] }) => {
  if (data.length === 0) {
    return null
  }

  return (
    <CustomCard title="BESS">
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Name</Table.Th>
            <Table.Th>AC (MW)</Table.Th>
            <Table.Th>DC (MWh)</Table.Th>
            <Table.Th ta="right">Rev. Today</Table.Th>
            <Table.Th ta="right">Rev. MTD</Table.Th>
            <Table.Th ta="right">Rev. YTD</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {data.map((project) => (
            <BESSProjectRow key={project.project_id} project={project} />
          ))}
        </Table.Tbody>
      </Table>
    </CustomCard>
  )
}

const RevenueCell = ({
  value,
  isLoading,
  notSetUp,
  tooltipLabel,
  hoverDetail,
}: {
  value: number | null
  isLoading: boolean
  notSetUp?: boolean
  tooltipLabel?: string
  hoverDetail?: string
}) => {
  if (isLoading) {
    return (
      <Table.Td ta="right">
        <Skeleton height={16} width={60} ml="auto" />
      </Table.Td>
    )
  }
  if (notSetUp) {
    return (
      <Table.Td ta="right">
        <Tooltip
          label={tooltipLabel ?? 'Not configured for this project'}
          multiline
          w={220}
        >
          <Text size="sm" c="dimmed" style={{ cursor: 'default' }}>
            Not set up
          </Text>
        </Tooltip>
      </Table.Td>
    )
  }
  if (hoverDetail) {
    return (
      <Table.Td ta="right">
        <Tooltip label={hoverDetail} multiline>
          <Text size="sm" style={{ cursor: 'default' }}>
            {formatCurrency(value)}
          </Text>
        </Tooltip>
      </Table.Td>
    )
  }
  return <Table.Td ta="right">{formatCurrency(value)}</Table.Td>
}

const BESSProjectRow = ({ project }: { project: Project }) => {
  const qseAccess = useGetQSEAccess({
    pathParams: { projectId: project.project_id },
    queryOptions: { enabled: !!project.project_id },
  })
  const hasAccess = qseAccess.data?.has_access === true
  const accessChecked =
    !qseAccess.isLoading && (qseAccess.data !== undefined || qseAccess.isError)
  const notSetUp = accessChecked && !hasAccess

  const {
    revenueToday,
    revenueMTD,
    revenueYTD,
    isLoading: revenueLoading,
  } = useBESSRevenueSummary({
    projectId: project.project_id,
    enabled: hasAccess,
  })

  const showLoading = !accessChecked || (hasAccess && revenueLoading)

  return (
    <Table.Tr>
      <Table.Td>
        <Link
          to={`/projects/${project.project_id}`}
          style={{ color: 'inherit' }}
        >
          {project.name_long}
        </Link>
      </Table.Td>
      <Table.Td>{fmtNum(project.capacity_bess_power_ac)}</Table.Td>
      <Table.Td>{fmtNum(project.capacity_bess_energy_bol_dc)}</Table.Td>
      <RevenueCell
        value={revenueToday}
        isLoading={showLoading}
        notSetUp={notSetUp}
        tooltipLabel={QSE_TOOLTIP}
      />
      <RevenueCell
        value={revenueMTD}
        isLoading={showLoading}
        notSetUp={notSetUp}
        tooltipLabel={QSE_TOOLTIP}
      />
      <RevenueCell
        value={revenueYTD}
        isLoading={showLoading}
        notSetUp={notSetUp}
        tooltipLabel={QSE_TOOLTIP}
      />
    </Table.Tr>
  )
}

const PVSTable = ({
  data,
  revenueData,
}: {
  data: Project[]
  revenueData: PVRevenueData
}) => {
  if (data.length === 0) {
    return null
  }

  return (
    <CustomCard title="PV+BESS">
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Name</Table.Th>
            <Table.Th>PV POI (MW)</Table.Th>
            <Table.Th>PV AC (MW)</Table.Th>
            <Table.Th>PV DC (MW)</Table.Th>
            <Table.Th>BESS AC (MW)</Table.Th>
            <Table.Th>BESS DC (MWh)</Table.Th>
            <Table.Th ta="right">Rev. MTD</Table.Th>
            <Table.Th ta="right">Rev. YTD</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {data.map((project) => (
            <PVSProjectRow
              key={project.project_id}
              project={project}
              revenueData={revenueData}
            />
          ))}
        </Table.Tbody>
      </Table>
    </CustomCard>
  )
}

const PVSProjectRow = ({
  project,
  revenueData,
}: {
  project: Project
  revenueData: PVRevenueData
}) => {
  const hasPPA = !!project.ppa?.rate
  const notSetUp = !hasPPA
  const ppaRate = project.ppa?.rate ?? 0

  const { energyMTD, energyYTD, revenueMTD, revenueYTD } = useMemo(
    () =>
      computePVRevenue({
        projectId: project.project_id,
        ppaRate,
        tz: project.time_zone,
        kpiData: revenueData.kpiData,
      }),
    [project.project_id, ppaRate, project.time_zone, revenueData.kpiData],
  )

  const isLoading = hasPPA && !revenueData.isError && revenueData.isLoading

  return (
    <Table.Tr>
      <Table.Td>
        <Link
          to={`/projects/${project.project_id}`}
          style={{ color: 'inherit' }}
        >
          {project.name_long}
        </Link>
      </Table.Td>
      <Table.Td>{fmtNum(project.poi)}</Table.Td>
      <Table.Td>{fmtNum(project.capacity_ac)}</Table.Td>
      <Table.Td>{fmtNum(project.capacity_dc)}</Table.Td>
      <Table.Td>{fmtNum(project.capacity_bess_power_ac)}</Table.Td>
      <Table.Td>{fmtNum(project.capacity_bess_energy_bol_dc, 1)}</Table.Td>
      <RevenueCell
        value={revenueMTD}
        isLoading={isLoading}
        notSetUp={notSetUp}
        tooltipLabel={PPA_TOOLTIP}
        hoverDetail={pvRevenueHover(energyMTD, ppaRate)}
      />
      <RevenueCell
        value={revenueYTD}
        isLoading={isLoading}
        notSetUp={notSetUp}
        tooltipLabel={PPA_TOOLTIP}
        hoverDetail={pvRevenueHover(energyYTD, ppaRate)}
      />
    </Table.Tr>
  )
}

export default PortfolioList
