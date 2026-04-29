import { ProjectTypeEnum } from '@/api/enumerations'
import { Project, useGetProjects } from '@/api/v1/operational/projects'
import {
  type PortfolioBessPowerAvailabilityRow,
  usePortfolioBessPowerAvailability,
} from '@/api/v1/protected/web-application/portfolio/bess_power_availability'
import {
  type PortfolioBessRevenueSummaryRow,
  usePortfolioBessRevenueSummary,
} from '@/api/v1/protected/web-application/portfolio/bess_revenue_summary'
import { usePortfolioMarketPerformanceHasAccess } from '@/api/v1/protected/web-application/portfolio/market_performance_has_access'
import CustomCard from '@/components/CustomCard'
import { NoData, PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { useTipsPersonalPortfolio } from '@/components/Tips'
import { RealtimePowerAvailabilityGauge } from '@/pages/projects/components/RealtimePowerAvailabilityGauge'
import SortChevron from '@/pages/projects/kpis/project-kpi-home/table-shell/SortChevron'
import { formatCurrency } from '@/utils/currency'
import {
  HoverCard,
  Progress,
  SegmentedControl,
  Skeleton,
  Stack,
  Table,
  Text,
  TextInput,
  Tooltip,
} from '@mantine/core'
import { useLocalStorage } from '@mantine/hooks'
import { type ReactNode, useMemo, useState } from 'react'
import { Link } from 'react-router'

import {
  type BessPcsAvailabilityPeriod,
  type BessPcsMtdData,
  computeBessPcsMtdAvailability,
  getBessPcsMtdKpiType,
  useBessPcsMtdData,
} from './hooks/useBessPcsMtdAvailability'
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

const POWER_POI_NA_TOOLTIP =
  'POI limit is not set; power availability needs a POI capacity'

const POWER_PCS_NA_TOOLTIP =
  'PCS capacity is not available; power availability needs cumulative PCS' +
  ' power capacity'

type PowerAvailabilityMode = 'poi' | 'pcs'

const PCS_PERIOD_LABEL: Record<BessPcsAvailabilityPeriod, string> = {
  mtd: 'MTD',
  ytd: 'YTD',
  '30d': '30D',
  '7d': '7D',
}

const GROUP_DIVIDER_STYLE = {
  borderLeft: '1px solid var(--mantine-color-gray-3)',
} as const

const fmtPct1 = (v: number | null | undefined) =>
  v != null ? `${v.toFixed(1)}%` : '—'

const pcsColor = (value: number) => {
  if (value >= 90) return 'green'
  if (value >= 75) return 'orange'
  return 'red'
}

const PcsMtdCell = ({
  projectId,
  value,
  isLoading,
  kpiTypeId,
  withDivider = false,
}: {
  projectId: string
  value: number | null | undefined
  isLoading: boolean
  kpiTypeId: number | null
  withDivider?: boolean
}) => {
  const style = withDivider ? GROUP_DIVIDER_STYLE : undefined
  if (isLoading) {
    return (
      <Table.Td px="sm" style={style}>
        <Skeleton height={6} radius="xl" mb={4} />
        <Skeleton height={10} width={36} mx="auto" />
      </Table.Td>
    )
  }
  if (value == null) {
    return (
      <Table.Td ta="center" style={style}>
        <Text size="sm" c="dimmed">
          —
        </Text>
      </Table.Td>
    )
  }

  const color = pcsColor(value)
  const bar = (
    <div style={{ minWidth: 72 }}>
      <Progress
        value={Math.min(value, 100)}
        color={color}
        size={6}
        radius="xl"
      />
      <Text size="xs" ta="center" mt={2} c={color} fw={500}>
        {fmtPct1(value)}
      </Text>
    </div>
  )

  if (kpiTypeId == null) {
    return (
      <Table.Td px="sm" style={style}>
        {bar}
      </Table.Td>
    )
  }

  return (
    <Table.Td px="sm" style={style}>
      <Link
        to={`/projects/${projectId}/kpis/type/${kpiTypeId}`}
        style={{ color: 'inherit', textDecoration: 'none' }}
      >
        {bar}
      </Link>
    </Table.Td>
  )
}

const RealtimePowerCell = ({
  row,
  isLoading,
  mode,
  withDivider = false,
}: {
  row: PortfolioBessPowerAvailabilityRow | undefined
  isLoading: boolean
  mode: PowerAvailabilityMode
  withDivider?: boolean
}) => {
  const style = withDivider ? GROUP_DIVIDER_STYLE : undefined
  const value =
    mode === 'pcs'
      ? (row?.power_availability_pct_pcs ?? null)
      : (row?.power_availability_pct_poi ?? null)
  const ratedCapacityMw =
    mode === 'pcs'
      ? (row?.max_pcs_capacity_mw ?? null)
      : (row?.poi_capacity_mw ?? null)
  const notApplicable = ratedCapacityMw == null || ratedCapacityMw <= 0

  if (!isLoading && notApplicable) {
    const inner = (
      <Text size="sm" c="dimmed" style={{ cursor: 'default' }}>
        —
      </Text>
    )
    return (
      <Table.Td ta="center" style={style}>
        <Tooltip
          label={mode === 'pcs' ? POWER_PCS_NA_TOOLTIP : POWER_POI_NA_TOOLTIP}
          multiline
          w={260}
        >
          {inner}
        </Tooltip>
      </Table.Td>
    )
  }

  return (
    <Table.Td ta="center" style={style}>
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <RealtimePowerAvailabilityGauge
          value={value}
          availablePowerMw={row?.available_power_mw ?? null}
          ratedCapacityMw={ratedCapacityMw}
          numPcsUnits={row?.num_pcs_units ?? null}
          maxPcsCapacityMw={row?.max_pcs_capacity_mw ?? null}
          isLoading={isLoading}
          denominatorLabel={
            mode === 'pcs' ? 'PCS cumulative capacity' : 'POI capacity'
          }
        />
      </div>
    </Table.Td>
  )
}

const PowerAvailabilityToggle = ({
  value,
  onChange,
}: {
  value: PowerAvailabilityMode
  onChange: (value: PowerAvailabilityMode) => void
}) => (
  <SegmentedControl
    size="xs"
    value={value}
    onChange={(next) => onChange(next as PowerAvailabilityMode)}
    data={[
      { label: 'POI', value: 'poi' },
      { label: 'PCS', value: 'pcs' },
    ]}
  />
)

const PcsAvailabilityToggle = ({
  value,
  onChange,
}: {
  value: BessPcsAvailabilityPeriod
  onChange: (value: BessPcsAvailabilityPeriod) => void
}) => (
  <SegmentedControl
    size="xs"
    value={value}
    onChange={(next) => onChange(next as BessPcsAvailabilityPeriod)}
    data={[
      { label: 'MTD', value: 'mtd' },
      { label: 'YTD', value: 'ytd' },
      { label: '30D', value: '30d' },
      { label: '7D', value: '7d' },
    ]}
  />
)

const PowerAvailabilityHeader = ({
  children,
  mode,
  onChange,
  style,
  sortKey,
  sort,
  onSort,
}: {
  children: ReactNode
  mode: PowerAvailabilityMode
  onChange: (value: PowerAvailabilityMode) => void
  style?: React.CSSProperties
  sortKey?: string
  sort?: SortState
  onSort?: (key: string) => void
}) => {
  const explanation =
    mode === 'pcs'
      ? 'Calculated from the latest PCS available charge/discharge power' +
        ' readings. We sum the latest available charge power across PCS' +
        ' units and do the same for discharge, take the larger absolute' +
        ' value, then divide by cumulative PCS AC capacity and cap at 100%.'
      : 'Calculated from the latest PCS available charge/discharge power' +
        ' readings. We sum the latest available charge power across PCS' +
        ' units and do the same for discharge, take the larger absolute' +
        ' value, then divide by POI capacity and cap at 100%.' +
        ' This takes overbuild into account.'
  const switchModeText =
    mode === 'pcs'
      ? 'Switch to POI mode to compare available power against the project' +
        ' interconnection limit, including overbuild.'
      : 'Switch to PCS mode to compare available power against cumulative' +
        ' PCS AC capacity.'
  const modeLabel = mode === 'pcs' ? 'PCS Mode' : 'POI Mode'
  const title = `Real time power availability - ${modeLabel}`

  return (
    <Table.Th ta="center" style={style}>
      <HoverCard width={360} shadow="md" openDelay={150} closeDelay={100}>
        <HoverCard.Target>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '100%',
              cursor: sortKey ? 'pointer' : 'help',
              gap: 4,
              userSelect: 'none',
            }}
            onClick={sortKey && onSort ? () => onSort(sortKey) : undefined}
          >
            <Text span inherit>
              {children}
            </Text>
            {sortKey && sort !== undefined && (
              <SortChevron
                isSorted={sort?.key === sortKey}
                dir={sort?.key === sortKey ? sort?.dir : undefined}
              />
            )}
          </div>
        </HoverCard.Target>
        <HoverCard.Dropdown>
          <Stack gap={8}>
            <Text size="sm" fw={600}>
              {title}
            </Text>
            <Text size="sm">{explanation}</Text>
            <Text size="sm" c="dimmed">
              {switchModeText}
            </Text>
            <div onClick={(e) => e.stopPropagation()}>
              <PowerAvailabilityToggle value={mode} onChange={onChange} />
            </div>
          </Stack>
        </HoverCard.Dropdown>
      </HoverCard>
    </Table.Th>
  )
}

const PcsMtdHeader = ({
  period,
  onChange,
  style,
  sortKey,
  sort,
  onSort,
}: {
  period: BessPcsAvailabilityPeriod
  onChange: (value: BessPcsAvailabilityPeriod) => void
  style?: React.CSSProperties
  sortKey?: string
  sort?: SortState
  onSort?: (key: string) => void
}) => (
  <Table.Th ta="center" style={style}>
    <HoverCard width={360} shadow="md" openDelay={150} closeDelay={100}>
      <HoverCard.Target>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '100%',
            cursor: sortKey ? 'pointer' : 'help',
            gap: 4,
            userSelect: 'none',
          }}
          onClick={sortKey && onSort ? () => onSort(sortKey) : undefined}
        >
          <Text span inherit>
            {`PCS ${PCS_PERIOD_LABEL[period]} %`}
          </Text>
          {sortKey && sort !== undefined && (
            <SortChevron
              isSorted={sort?.key === sortKey}
              dir={sort?.key === sortKey ? sort?.dir : undefined}
            />
          )}
        </div>
      </HoverCard.Target>
      <HoverCard.Dropdown>
        <Stack gap={8}>
          <Text size="sm" fw={600}>
            {`PCS ${PCS_PERIOD_LABEL[period]} %`}
          </Text>
          <Text size="sm">
            Mean daily PCS or PCS-module mechanical availability over the
            selected period, in the project timezone.
          </Text>
          <Text size="sm" c="dimmed">
            This uses KPI data rather than the latest real-time power readings.
          </Text>
          <div onClick={(e) => e.stopPropagation()}>
            <PcsAvailabilityToggle value={period} onChange={onChange} />
          </div>
        </Stack>
      </HoverCard.Dropdown>
    </HoverCard>
  </Table.Th>
)

const REVENUE_LABEL: Record<string, string> = {
  Today: 'Revenue earned today (project local time), in USD.',
  MTD: 'Revenue earned month-to-date (project local time), in USD.',
  YTD: 'Revenue earned year-to-date (project local time), in USD.',
}

const RevenueHeader = ({
  label,
  style,
  sortKey,
  sort,
  onSort,
}: {
  label: 'Today' | 'MTD' | 'YTD'
  style?: React.CSSProperties
  sortKey?: string
  sort?: SortState
  onSort?: (key: string) => void
}) => (
  <Table.Th ta="center" style={style}>
    <HoverCard width={280} shadow="md" openDelay={150} closeDelay={100}>
      <HoverCard.Target>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '100%',
            cursor: sortKey ? 'pointer' : 'help',
            gap: 4,
            userSelect: 'none',
          }}
          onClick={sortKey && onSort ? () => onSort(sortKey) : undefined}
        >
          <Text span inherit>
            {label}
          </Text>
          {sortKey && sort !== undefined && (
            <SortChevron
              isSorted={sort?.key === sortKey}
              dir={sort?.key === sortKey ? sort?.dir : undefined}
            />
          )}
        </div>
      </HoverCard.Target>
      <HoverCard.Dropdown>
        <Stack gap={8}>
          <Text size="sm" fw={600}>
            Revenue — {label}
          </Text>
          <Text size="sm">{REVENUE_LABEL[label]}</Text>
        </Stack>
      </HoverCard.Dropdown>
    </HoverCard>
  </Table.Th>
)

type SortDir = 'asc' | 'desc'
type SortState = { key: string; dir: SortDir } | null

const toggleSort = (current: SortState, key: string): SortState => {
  if (current?.key !== key) return { key, dir: 'asc' }
  if (current.dir === 'asc') return { key, dir: 'desc' }
  return null
}

const sortRows = <T,>(
  rows: T[],
  sort: SortState,
  accessors: Record<string, (row: T) => number | string | null>,
): T[] => {
  if (!sort) return rows
  const fn = accessors[sort.key]
  if (!fn) return rows
  return [...rows].sort((a, b) => {
    const av = fn(a)
    const bv = fn(b)
    if (av === null && bv === null) return 0
    if (av === null) return 1
    if (bv === null) return -1
    if (av < bv) return sort.dir === 'asc' ? -1 : 1
    if (av > bv) return sort.dir === 'asc' ? 1 : -1
    return 0
  })
}

const SortableHeader = ({
  children,
  sortKey,
  sort,
  onSort,
  ...rest
}: {
  children: ReactNode
  sortKey: string
  sort: SortState
  onSort: (k: string) => void
} & React.ComponentProps<typeof Table.Th>) => (
  <Table.Th {...rest}>
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        cursor: 'pointer',
        userSelect: 'none',
      }}
      onClick={() => onSort(sortKey)}
    >
      {children}
      <SortChevron
        isSorted={sort?.key === sortKey}
        dir={sort?.key === sortKey ? sort?.dir : undefined}
      />
    </div>
  </Table.Th>
)

const PortfolioList = () => {
  useTipsPersonalPortfolio()
  const [powerAvailabilityMode, setPowerAvailabilityMode] =
    useLocalStorage<PowerAvailabilityMode>({
      key: 'portfolio-bess-power-availability-mode',
      defaultValue: 'poi',
    })
  const [pcsAvailabilityPeriod, setPcsAvailabilityPeriod] =
    useLocalStorage<BessPcsAvailabilityPeriod>({
      key: 'portfolio-bess-pcs-availability-period',
      defaultValue: 'mtd',
    })

  const { data, isLoading, error } = useGetProjects({
    queryParams: {
      deep: true,
    },
  })

  const { pvProjects, bessProjects, pvsProjects, pvKpiProjectIds, bessKpiIds } =
    useMemo(() => {
      if (!data)
        return {
          pvProjects: [] as Project[],
          bessProjects: [] as Project[],
          pvsProjects: [] as Project[],
          pvKpiProjectIds: [] as string[],
          bessKpiIds: [] as string[],
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
      const bessIds = [...bess, ...pvs].map((p) => p.project_id)
      return {
        pvProjects: pv,
        bessProjects: bess,
        pvsProjects: pvs,
        pvKpiProjectIds: ids,
        bessKpiIds: bessIds,
      }
    }, [data])

  const pvRevenueData = usePVRevenueData({
    projectIds: pvKpiProjectIds,
  })

  const bessPcsMtd = useBessPcsMtdData({ projectIds: bessKpiIds })

  const portfolioPower = usePortfolioBessPowerAvailability({
    projectIds: bessKpiIds,
  })

  const powerAvailabilityByProjectId = useMemo(() => {
    const m = new Map<string, PortfolioBessPowerAvailabilityRow>()
    portfolioPower.data?.forEach((row) => {
      m.set(row.project_id, row)
    })
    return m
  }, [portfolioPower.data])

  const bessQseProjectIds = useMemo(
    () => bessProjects.map((p) => p.project_id),
    [bessProjects],
  )

  const portfolioQseAccess = usePortfolioMarketPerformanceHasAccess({
    projectIds: bessQseProjectIds,
  })

  const qseAccessByProjectId = useMemo(() => {
    const m = new Map<string, boolean>()
    portfolioQseAccess.data?.forEach((row) => {
      m.set(row.project_id, row.has_access)
    })
    return m
  }, [portfolioQseAccess.data])

  const qseAccessChecked =
    !portfolioQseAccess.isLoading &&
    (portfolioQseAccess.data !== undefined || portfolioQseAccess.isError)

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
      <BESSTable
        data={bessProjects}
        bessPcsMtd={bessPcsMtd}
        powerAvailabilityByProjectId={powerAvailabilityByProjectId}
        powerAvailabilityLoading={
          bessKpiIds.length > 0 &&
          portfolioPower.isLoading &&
          !portfolioPower.isError
        }
        powerAvailabilityMode={powerAvailabilityMode}
        onPowerAvailabilityModeChange={setPowerAvailabilityMode}
        pcsAvailabilityPeriod={pcsAvailabilityPeriod}
        onPcsAvailabilityPeriodChange={setPcsAvailabilityPeriod}
        qseAccessByProjectId={qseAccessByProjectId}
        qseAccessChecked={qseAccessChecked}
      />
      <PVSTable
        data={pvsProjects}
        revenueData={pvRevenueData}
        bessPcsMtd={bessPcsMtd}
        powerAvailabilityByProjectId={powerAvailabilityByProjectId}
        powerAvailabilityLoading={
          bessKpiIds.length > 0 &&
          portfolioPower.isLoading &&
          !portfolioPower.isError
        }
        powerAvailabilityMode={powerAvailabilityMode}
        onPowerAvailabilityModeChange={setPowerAvailabilityMode}
        pcsAvailabilityPeriod={pcsAvailabilityPeriod}
        onPcsAvailabilityPeriodChange={setPcsAvailabilityPeriod}
      />
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
  const [nameFilter, setNameFilter] = useState('')
  const [sort, setSort] = useState<SortState>(null)
  const onSort = (key: string) => setSort((s) => toggleSort(s, key))

  const rows = useMemo(() => {
    const lc = nameFilter.toLowerCase()
    let r = data.filter(
      (p) =>
        p.name_long.toLowerCase().includes(lc) ||
        p.name_short.toLowerCase().includes(lc),
    )
    if (sort) {
      r = sortRows(r, sort, {
        name: (p) => p.name_short,
        poi: (p) => p.poi ?? null,
        ac: (p) => p.capacity_ac ?? null,
        dc: (p) => p.capacity_dc ?? null,
        mtd: (p) =>
          computePVRevenue({
            projectId: p.project_id,
            ppaRate: p.ppa?.rate ?? 0,
            tz: p.time_zone,
            kpiData: revenueData.kpiData,
          }).revenueMTD,
        ytd: (p) =>
          computePVRevenue({
            projectId: p.project_id,
            ppaRate: p.ppa?.rate ?? 0,
            tz: p.time_zone,
            kpiData: revenueData.kpiData,
          }).revenueYTD,
      })
    }
    return r
  }, [data, nameFilter, sort, revenueData.kpiData])

  if (data.length === 0) return null

  return (
    <CustomCard title="PV" style={{ overflow: 'unset' }}>
      <TextInput
        placeholder="Filter by name…"
        value={nameFilter}
        onChange={(e) => setNameFilter(e.currentTarget.value)}
        variant="unstyled"
        mb="xs"
        style={{ borderBottom: '1px solid var(--mantine-color-gray-3)' }}
      />
      <Table stickyHeader stickyHeaderOffset={0}>
        <Table.Thead>
          <Table.Tr>
            <SortableHeader
              rowSpan={2}
              sortKey="name"
              sort={sort}
              onSort={onSort}
            >
              Name
            </SortableHeader>
            <Table.Th colSpan={3} ta="center">
              System Size
            </Table.Th>
            <Table.Th colSpan={2} ta="center" style={GROUP_DIVIDER_STYLE}>
              Revenue
            </Table.Th>
          </Table.Tr>
          <Table.Tr>
            <SortableHeader
              ta="center"
              sortKey="poi"
              sort={sort}
              onSort={onSort}
            >
              POI (MW)
            </SortableHeader>
            <SortableHeader
              ta="center"
              sortKey="ac"
              sort={sort}
              onSort={onSort}
            >
              AC (MW)
            </SortableHeader>
            <SortableHeader
              ta="center"
              sortKey="dc"
              sort={sort}
              onSort={onSort}
            >
              DC (MW)
            </SortableHeader>
            <RevenueHeader
              label="MTD"
              style={GROUP_DIVIDER_STYLE}
              sortKey="mtd"
              sort={sort}
              onSort={onSort}
            />
            <RevenueHeader
              label="YTD"
              sortKey="ytd"
              sort={sort}
              onSort={onSort}
            />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((project) => (
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
      <Table.Td ta="center">{fmtNum(project.poi)}</Table.Td>
      <Table.Td ta="center">{fmtNum(project.capacity_ac)}</Table.Td>
      <Table.Td ta="center">{fmtNum(project.capacity_dc)}</Table.Td>
      <RevenueCell
        value={revenueMTD}
        isLoading={isLoading}
        notSetUp={notSetUp}
        tooltipLabel={PPA_TOOLTIP}
        hoverDetail={pvRevenueHover(energyMTD, ppaRate)}
        withDivider
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

const BESSTable = ({
  data,
  bessPcsMtd,
  powerAvailabilityByProjectId,
  powerAvailabilityLoading,
  powerAvailabilityMode,
  onPowerAvailabilityModeChange,
  pcsAvailabilityPeriod,
  onPcsAvailabilityPeriodChange,
  qseAccessByProjectId,
  qseAccessChecked,
}: {
  data: Project[]
  bessPcsMtd: BessPcsMtdData
  powerAvailabilityByProjectId: Map<string, PortfolioBessPowerAvailabilityRow>
  powerAvailabilityLoading: boolean
  powerAvailabilityMode: PowerAvailabilityMode
  onPowerAvailabilityModeChange: (value: PowerAvailabilityMode) => void
  pcsAvailabilityPeriod: BessPcsAvailabilityPeriod
  onPcsAvailabilityPeriodChange: (value: BessPcsAvailabilityPeriod) => void
  qseAccessByProjectId: Map<string, boolean>
  qseAccessChecked: boolean
}) => {
  const accessibleProjectIds = useMemo(
    () =>
      data
        .filter((p) => qseAccessByProjectId.get(p.project_id) === true)
        .map((p) => p.project_id),
    [data, qseAccessByProjectId],
  )

  const bessRevenue = usePortfolioBessRevenueSummary({
    projectIds: accessibleProjectIds,
  })

  const revenueByProjectId = useMemo(() => {
    const m = new Map<string, PortfolioBessRevenueSummaryRow>()
    bessRevenue.data?.forEach((row) => m.set(row.project_id, row))
    return m
  }, [bessRevenue.data])
  const [nameFilter, setNameFilter] = useState('')
  const [sort, setSort] = useState<SortState>(null)
  const onSort = (key: string) => setSort((s) => toggleSort(s, key))

  const rows = useMemo(() => {
    const lc = nameFilter.toLowerCase()
    let r = data.filter(
      (p) =>
        p.name_long.toLowerCase().includes(lc) ||
        p.name_short.toLowerCase().includes(lc),
    )
    if (sort) {
      r = sortRows(r, sort, {
        name: (p) => p.name_short,
        ac: (p) => p.capacity_bess_power_ac ?? null,
        dc: (p) => p.capacity_bess_energy_bol_dc ?? null,
        power: (p) => {
          const row = powerAvailabilityByProjectId.get(p.project_id)
          return powerAvailabilityMode === 'pcs'
            ? (row?.power_availability_pct_pcs ?? null)
            : (row?.power_availability_pct_poi ?? null)
        },
        pcs: (p) =>
          computeBessPcsMtdAvailability({
            projectId: p.project_id,
            tz: p.time_zone,
            kpiData: bessPcsMtd.kpiData,
            preferModule: p.has_pv_pcs_modules,
            period: pcsAvailabilityPeriod,
          }),
      })
    }
    return r
  }, [
    data,
    nameFilter,
    sort,
    powerAvailabilityByProjectId,
    powerAvailabilityMode,
    bessPcsMtd.kpiData,
    pcsAvailabilityPeriod,
  ])

  if (data.length === 0) return null

  return (
    <CustomCard title="BESS" style={{ overflow: 'unset' }}>
      <TextInput
        placeholder="Filter by name…"
        value={nameFilter}
        onChange={(e) => setNameFilter(e.currentTarget.value)}
        variant="unstyled"
        mb="xs"
        style={{ borderBottom: '1px solid var(--mantine-color-gray-3)' }}
      />
      <Table stickyHeader stickyHeaderOffset={0}>
        <Table.Thead>
          <Table.Tr>
            <SortableHeader
              rowSpan={2}
              sortKey="name"
              sort={sort}
              onSort={onSort}
            >
              Name
            </SortableHeader>
            <Table.Th colSpan={2} ta="center">
              System Size
            </Table.Th>
            <Table.Th colSpan={2} ta="center" style={GROUP_DIVIDER_STYLE}>
              Availability
            </Table.Th>
            <Table.Th colSpan={3} ta="center" style={GROUP_DIVIDER_STYLE}>
              Revenue
            </Table.Th>
          </Table.Tr>
          <Table.Tr>
            <SortableHeader
              ta="center"
              sortKey="ac"
              sort={sort}
              onSort={onSort}
            >
              AC (MW)
            </SortableHeader>
            <SortableHeader
              ta="center"
              sortKey="dc"
              sort={sort}
              onSort={onSort}
            >
              DC (MWh)
            </SortableHeader>
            <PowerAvailabilityHeader
              mode={powerAvailabilityMode}
              onChange={onPowerAvailabilityModeChange}
              style={GROUP_DIVIDER_STYLE}
              sortKey="power"
              sort={sort}
              onSort={onSort}
            >
              {`Power (${powerAvailabilityMode.toUpperCase()}) %`}
            </PowerAvailabilityHeader>
            <PcsMtdHeader
              period={pcsAvailabilityPeriod}
              onChange={onPcsAvailabilityPeriodChange}
              sortKey="pcs"
              sort={sort}
              onSort={onSort}
            />
            <RevenueHeader label="Today" style={GROUP_DIVIDER_STYLE} />
            <RevenueHeader label="MTD" />
            <RevenueHeader label="YTD" />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((project) => (
            <BESSProjectRow
              key={project.project_id}
              project={project}
              bessPcsMtd={bessPcsMtd}
              powerAvailabilityByProjectId={powerAvailabilityByProjectId}
              powerAvailabilityLoading={powerAvailabilityLoading}
              powerAvailabilityMode={powerAvailabilityMode}
              pcsAvailabilityPeriod={pcsAvailabilityPeriod}
              qseAccessChecked={qseAccessChecked}
              revenueByProjectId={revenueByProjectId}
              revenueLoading={
                qseAccessChecked &&
                accessibleProjectIds.length > 0 &&
                bessRevenue.isLoading
              }
            />
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
  withDivider = false,
}: {
  value: number | null
  isLoading: boolean
  notSetUp?: boolean
  tooltipLabel?: string
  hoverDetail?: string
  withDivider?: boolean
}) => {
  const style = withDivider ? GROUP_DIVIDER_STYLE : undefined
  if (isLoading) {
    return (
      <Table.Td ta="center" style={style}>
        <Skeleton height={16} width={60} mx="auto" />
      </Table.Td>
    )
  }
  if (notSetUp) {
    return (
      <Table.Td ta="center" style={style}>
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
      <Table.Td ta="center" style={style}>
        <Tooltip label={hoverDetail} multiline>
          <Text size="sm" style={{ cursor: 'default' }}>
            {formatCurrency(value)}
          </Text>
        </Tooltip>
      </Table.Td>
    )
  }
  return (
    <Table.Td ta="center" style={style}>
      {formatCurrency(value)}
    </Table.Td>
  )
}

const BESSProjectRow = ({
  project,
  bessPcsMtd,
  powerAvailabilityByProjectId,
  powerAvailabilityLoading,
  powerAvailabilityMode,
  pcsAvailabilityPeriod,
  qseAccessChecked,
  revenueByProjectId,
  revenueLoading,
}: {
  project: Project
  bessPcsMtd: BessPcsMtdData
  powerAvailabilityByProjectId: Map<string, PortfolioBessPowerAvailabilityRow>
  powerAvailabilityLoading: boolean
  powerAvailabilityMode: PowerAvailabilityMode
  pcsAvailabilityPeriod: BessPcsAvailabilityPeriod
  qseAccessChecked: boolean
  revenueByProjectId: Map<string, PortfolioBessRevenueSummaryRow>
  revenueLoading: boolean
}) => {
  const revenueRow = revenueByProjectId.get(project.project_id)
  const hasAccess = revenueRow !== undefined
  const notSetUp = qseAccessChecked && !hasAccess

  const revenueToday = revenueRow?.revenue_today ?? null
  const revenueMTD = revenueRow?.revenue_mtd ?? null
  const revenueYTD = revenueRow?.revenue_ytd ?? null

  const showLoading = !qseAccessChecked || revenueLoading

  const powerAvailability = powerAvailabilityByProjectId.get(project.project_id)

  const pcsMtdPct = useMemo(
    () =>
      computeBessPcsMtdAvailability({
        projectId: project.project_id,
        tz: project.time_zone,
        kpiData: bessPcsMtd.kpiData,
        preferModule: project.has_pv_pcs_modules,
        period: pcsAvailabilityPeriod,
      }),
    [
      project.project_id,
      project.time_zone,
      project.has_pv_pcs_modules,
      pcsAvailabilityPeriod,
      bessPcsMtd.kpiData,
    ],
  )

  const pcsMtdLoading =
    bessPcsMtd.isLoading && !bessPcsMtd.isError && !bessPcsMtd.kpiData
  const pcsMtdKpiTypeId = useMemo(
    () =>
      getBessPcsMtdKpiType({
        projectId: project.project_id,
        tz: project.time_zone,
        kpiData: bessPcsMtd.kpiData,
        preferModule: project.has_pv_pcs_modules,
        period: pcsAvailabilityPeriod,
      }),
    [
      project.project_id,
      project.time_zone,
      project.has_pv_pcs_modules,
      pcsAvailabilityPeriod,
      bessPcsMtd.kpiData,
    ],
  )

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
      <Table.Td ta="center">{fmtNum(project.capacity_bess_power_ac)}</Table.Td>
      <Table.Td ta="center">
        {fmtNum(project.capacity_bess_energy_bol_dc)}
      </Table.Td>
      <RealtimePowerCell
        row={powerAvailability}
        isLoading={powerAvailabilityLoading}
        mode={powerAvailabilityMode}
        withDivider
      />
      <PcsMtdCell
        projectId={project.project_id}
        value={pcsMtdPct}
        isLoading={pcsMtdLoading}
        kpiTypeId={pcsMtdKpiTypeId}
      />
      <RevenueCell
        value={revenueToday}
        isLoading={showLoading}
        notSetUp={notSetUp}
        tooltipLabel={QSE_TOOLTIP}
        withDivider
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
  bessPcsMtd,
  powerAvailabilityByProjectId,
  powerAvailabilityLoading,
  powerAvailabilityMode,
  onPowerAvailabilityModeChange,
  pcsAvailabilityPeriod,
  onPcsAvailabilityPeriodChange,
}: {
  data: Project[]
  revenueData: PVRevenueData
  bessPcsMtd: BessPcsMtdData
  powerAvailabilityByProjectId: Map<string, PortfolioBessPowerAvailabilityRow>
  powerAvailabilityLoading: boolean
  powerAvailabilityMode: PowerAvailabilityMode
  onPowerAvailabilityModeChange: (value: PowerAvailabilityMode) => void
  pcsAvailabilityPeriod: BessPcsAvailabilityPeriod
  onPcsAvailabilityPeriodChange: (value: BessPcsAvailabilityPeriod) => void
}) => {
  const [nameFilter, setNameFilter] = useState('')
  const [sort, setSort] = useState<SortState>(null)
  const onSort = (key: string) => setSort((s) => toggleSort(s, key))

  const rows = useMemo(() => {
    const lc = nameFilter.toLowerCase()
    let r = data.filter(
      (p) =>
        p.name_long.toLowerCase().includes(lc) ||
        p.name_short.toLowerCase().includes(lc),
    )
    if (sort) {
      r = sortRows(r, sort, {
        name: (p) => p.name_short,
        pvPoi: (p) => p.poi ?? null,
        pvAc: (p) => p.capacity_ac ?? null,
        pvDc: (p) => p.capacity_dc ?? null,
        bessAc: (p) => p.capacity_bess_power_ac ?? null,
        bessDc: (p) => p.capacity_bess_energy_bol_dc ?? null,
        power: (p) => {
          const row = powerAvailabilityByProjectId.get(p.project_id)
          return powerAvailabilityMode === 'pcs'
            ? (row?.power_availability_pct_pcs ?? null)
            : (row?.power_availability_pct_poi ?? null)
        },
        pcs: (p) =>
          computeBessPcsMtdAvailability({
            projectId: p.project_id,
            tz: p.time_zone,
            kpiData: bessPcsMtd.kpiData,
            preferModule: p.has_pv_pcs_modules,
            period: pcsAvailabilityPeriod,
          }),
        mtd: (p) =>
          computePVRevenue({
            projectId: p.project_id,
            ppaRate: p.ppa?.rate ?? 0,
            tz: p.time_zone,
            kpiData: revenueData.kpiData,
          }).revenueMTD,
        ytd: (p) =>
          computePVRevenue({
            projectId: p.project_id,
            ppaRate: p.ppa?.rate ?? 0,
            tz: p.time_zone,
            kpiData: revenueData.kpiData,
          }).revenueYTD,
      })
    }
    return r
  }, [
    data,
    nameFilter,
    sort,
    powerAvailabilityByProjectId,
    powerAvailabilityMode,
    bessPcsMtd.kpiData,
    pcsAvailabilityPeriod,
    revenueData.kpiData,
  ])

  if (data.length === 0) return null

  return (
    <CustomCard title="PV+BESS" style={{ overflow: 'unset' }}>
      <TextInput
        placeholder="Filter by name…"
        value={nameFilter}
        onChange={(e) => setNameFilter(e.currentTarget.value)}
        variant="unstyled"
        mb="xs"
        style={{ borderBottom: '1px solid var(--mantine-color-gray-3)' }}
      />
      <Table stickyHeader stickyHeaderOffset={0}>
        <Table.Thead>
          <Table.Tr>
            <SortableHeader
              rowSpan={2}
              sortKey="name"
              sort={sort}
              onSort={onSort}
            >
              Name
            </SortableHeader>
            <Table.Th colSpan={5} ta="center">
              System Size
            </Table.Th>
            <Table.Th colSpan={2} ta="center" style={GROUP_DIVIDER_STYLE}>
              Availability
            </Table.Th>
            <Table.Th colSpan={2} ta="center" style={GROUP_DIVIDER_STYLE}>
              Revenue
            </Table.Th>
          </Table.Tr>
          <Table.Tr>
            <SortableHeader
              ta="center"
              sortKey="pvPoi"
              sort={sort}
              onSort={onSort}
            >
              PV POI (MW)
            </SortableHeader>
            <SortableHeader
              ta="center"
              sortKey="pvAc"
              sort={sort}
              onSort={onSort}
            >
              PV AC (MW)
            </SortableHeader>
            <SortableHeader
              ta="center"
              sortKey="pvDc"
              sort={sort}
              onSort={onSort}
            >
              PV DC (MW)
            </SortableHeader>
            <SortableHeader
              ta="center"
              sortKey="bessAc"
              sort={sort}
              onSort={onSort}
            >
              BESS AC (MW)
            </SortableHeader>
            <SortableHeader
              ta="center"
              sortKey="bessDc"
              sort={sort}
              onSort={onSort}
            >
              BESS DC (MWh)
            </SortableHeader>
            <PowerAvailabilityHeader
              mode={powerAvailabilityMode}
              onChange={onPowerAvailabilityModeChange}
              style={GROUP_DIVIDER_STYLE}
              sortKey="power"
              sort={sort}
              onSort={onSort}
            >
              {`BESS Power (${powerAvailabilityMode.toUpperCase()}) %`}
            </PowerAvailabilityHeader>
            <PcsMtdHeader
              period={pcsAvailabilityPeriod}
              onChange={onPcsAvailabilityPeriodChange}
              sortKey="pcs"
              sort={sort}
              onSort={onSort}
            />
            <RevenueHeader
              label="MTD"
              style={GROUP_DIVIDER_STYLE}
              sortKey="mtd"
              sort={sort}
              onSort={onSort}
            />
            <RevenueHeader
              label="YTD"
              sortKey="ytd"
              sort={sort}
              onSort={onSort}
            />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((project) => (
            <PVSProjectRow
              key={project.project_id}
              project={project}
              revenueData={revenueData}
              bessPcsMtd={bessPcsMtd}
              powerAvailabilityByProjectId={powerAvailabilityByProjectId}
              powerAvailabilityLoading={powerAvailabilityLoading}
              powerAvailabilityMode={powerAvailabilityMode}
              pcsAvailabilityPeriod={pcsAvailabilityPeriod}
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
  bessPcsMtd,
  powerAvailabilityByProjectId,
  powerAvailabilityLoading,
  powerAvailabilityMode,
  pcsAvailabilityPeriod,
}: {
  project: Project
  revenueData: PVRevenueData
  bessPcsMtd: BessPcsMtdData
  powerAvailabilityByProjectId: Map<string, PortfolioBessPowerAvailabilityRow>
  powerAvailabilityLoading: boolean
  powerAvailabilityMode: PowerAvailabilityMode
  pcsAvailabilityPeriod: BessPcsAvailabilityPeriod
}) => {
  const hasPPA = !!project.ppa?.rate
  const notSetUp = !hasPPA
  const ppaRate = project.ppa?.rate ?? 0

  const powerAvailability = powerAvailabilityByProjectId.get(project.project_id)

  const pcsMtdPct = useMemo(
    () =>
      computeBessPcsMtdAvailability({
        projectId: project.project_id,
        tz: project.time_zone,
        kpiData: bessPcsMtd.kpiData,
        preferModule: project.has_pv_pcs_modules,
        period: pcsAvailabilityPeriod,
      }),
    [
      project.project_id,
      project.time_zone,
      project.has_pv_pcs_modules,
      pcsAvailabilityPeriod,
      bessPcsMtd.kpiData,
    ],
  )

  const pcsMtdLoading =
    bessPcsMtd.isLoading && !bessPcsMtd.isError && !bessPcsMtd.kpiData
  const pcsMtdKpiTypeId = useMemo(
    () =>
      getBessPcsMtdKpiType({
        projectId: project.project_id,
        tz: project.time_zone,
        kpiData: bessPcsMtd.kpiData,
        preferModule: project.has_pv_pcs_modules,
        period: pcsAvailabilityPeriod,
      }),
    [
      project.project_id,
      project.time_zone,
      project.has_pv_pcs_modules,
      pcsAvailabilityPeriod,
      bessPcsMtd.kpiData,
    ],
  )

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
      <Table.Td ta="center">{fmtNum(project.poi)}</Table.Td>
      <Table.Td ta="center">{fmtNum(project.capacity_ac)}</Table.Td>
      <Table.Td ta="center">{fmtNum(project.capacity_dc)}</Table.Td>
      <Table.Td ta="center">{fmtNum(project.capacity_bess_power_ac)}</Table.Td>
      <Table.Td ta="center">
        {fmtNum(project.capacity_bess_energy_bol_dc, 1)}
      </Table.Td>
      <RealtimePowerCell
        row={powerAvailability}
        isLoading={powerAvailabilityLoading}
        mode={powerAvailabilityMode}
        withDivider
      />
      <PcsMtdCell
        projectId={project.project_id}
        value={pcsMtdPct}
        isLoading={pcsMtdLoading}
        kpiTypeId={pcsMtdKpiTypeId}
      />
      <RevenueCell
        value={revenueMTD}
        isLoading={isLoading}
        notSetUp={notSetUp}
        tooltipLabel={PPA_TOOLTIP}
        hoverDetail={pvRevenueHover(energyMTD, ppaRate)}
        withDivider
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
