import {
  DeviceType,
  useGetDeviceTypes,
} from '@/api/v1/operational/device_types'
import { useGetOperationalKPIData } from '@/api/v1/operational/kpi_data'
import { OperationalKPIData } from '@/api/v1/operational/kpi_data'
import { KPIType, useGetKPITypes } from '@/api/v1/operational/kpi_types'
import { Project, useGetProjects } from '@/api/v1/operational/projects'
import { PageTitle } from '@/components/PageTitle'
import { useTipsPortfolioKPIHome } from '@/components/Tips'
import {
  Group,
  LoadingOverlay,
  Stack,
  Text,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { DatePickerInput, DatesProvider } from '@mantine/dates'
import { IconCalendar } from '@tabler/icons-react'
import dayjs from 'dayjs'
import {
  MRT_Cell,
  MRT_ColumnDef,
  MRT_Row,
  MantineReactTable,
  useMantineReactTable,
} from 'mantine-react-table'
import { useMemo, useState } from 'react'
import { Link } from 'react-router'

interface PivotedData {
  [kpiTypeId: string]: string | number | null
  project_id: string
  projectName: string
}

function buildDeviceTypeGroupedColumns({
  kpiTypeIds,
  kpiTypes,
  deviceTypes,
}: {
  kpiTypeIds: number[]
  kpiTypes: KPIType[] | undefined
  deviceTypes: DeviceType[] | undefined
}) {
  if (!kpiTypes || kpiTypes.length === 0) {
    return []
  }

  const groupedByDeviceType = new Map<DeviceType, KPIType[]>()

  for (const kpiTypeObj of kpiTypes) {
    if (!kpiTypeIds.includes(kpiTypeObj.kpi_type_id)) {
      continue
    }

    // If deviceTypes is still undefined or no matching device type is found, skip.
    if (!deviceTypes) {
      continue
    }
    const dt = deviceTypes.find(
      (dt) => dt.device_type_id === kpiTypeObj.device_type_id,
    )
    if (!dt) {
      // skip if you can't find a matching device type
      continue
    }

    if (!groupedByDeviceType.has(dt)) {
      groupedByDeviceType.set(dt, [])
    }
    groupedByDeviceType.get(dt)!.push(kpiTypeObj)
  }

  const deviceTypeGroups = Array.from(groupedByDeviceType.entries())
    .sort(([a], [b]) => (a.device_type_id || 0) - (b.device_type_id || 0))
    .map(([deviceType, kpis]) => {
      const subColumns = kpis.map((kpiObj) => ({
        accessorKey: String(kpiObj.kpi_type_id),
        header: kpiObj.name_metric ?? `KPI ${kpiObj.kpi_type_id}`,
        Cell: ({
          cell,
          row,
        }: {
          cell: MRT_Cell<PivotedData>
          row: MRT_Row<PivotedData>
        }) => (
          <Link
            to={`/projects/${row.original.project_id}/kpis/type/${kpiObj.kpi_type_id}`}
            style={{ color: 'inherit' }}
          >
            <Text size="sm">
              {renderKpiCellValue(cell.getValue<number | null>(), kpiObj)}
            </Text>
          </Link>
        ),
      }))

      return {
        header: deviceType.name_long,
        columns: subColumns,
      }
    })

  return deviceTypeGroups
}

function renderKpiCellValue(value: number | null, kpiType: KPIType) {
  if (value === null || value === 0) {
    return ''
  }
  if (kpiType.unit === '%') {
    return value.toLocaleString('en-US', {
      style: 'percent',
      maximumFractionDigits: 2,
      minimumFractionDigits: 2,
    })
  }
  return `${value.toLocaleString('en-US', {
    style: 'decimal',
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  })} ${kpiType.unit ? kpiType.unit : ''}`
}

function pivotKpiData(rawData: OperationalKPIData[], projects: Project[]) {
  const projectNameMap = new Map(
    projects.map((proj) => [proj.project_id, proj.name_long]),
  )

  const kpiTypeIds = new Set<number>()
  const pivotMap: Record<string, PivotedData> = {}
  for (const project of projects) {
    pivotMap[project.project_id] = {
      project_id: project.project_id,
      projectName: projectNameMap.get(project.project_id) ?? project.project_id,
    }
  }

  for (const item of rawData) {
    const { project_id, kpi_type_id, data } = item
    kpiTypeIds.add(kpi_type_id)

    if (!pivotMap[project_id]) {
      pivotMap[project_id] = {
        project_id,
        projectName: projectNameMap.get(project_id) || project_id,
      }
    }

    // TODO: this will need to be updated when we have multiple days displayed
    pivotMap[project_id][kpi_type_id] = data.project_data[0]
  }

  const pivotedData = Object.values(pivotMap)

  for (const row of pivotedData) {
    for (const kpiId of kpiTypeIds) {
      const key = String(kpiId)
      if (!(key in row)) {
        row[key] = null
      }
    }
  }

  return {
    pivotedData,
    kpiTypeIds: Array.from(kpiTypeIds),
  }
}

const PortfolioKPIHome = () => {
  useTipsPortfolioKPIHome()
  const projects = useGetProjects({ queryParams: { deep: true } })
  const theme = useMantineTheme()
  const computedColorScheme = useComputedColorScheme('dark')
  const color =
    computedColorScheme === 'dark' ? theme.colors.gray[7] : theme.colors.gray[3]

  const [selectedDate, setSelectedDate] = useState<Date | null>(
    dayjs().startOf('day').subtract(1, 'day').toDate(),
  )

  const startDate = selectedDate
    ? dayjs(selectedDate).startOf('day')
    : dayjs().startOf('day').subtract(1, 'day')
  const endDate = startDate.add(1, 'day')

  const kpiData = useGetOperationalKPIData({
    queryParams: {
      project_ids: projects.data?.map((project) => project.project_id),
      start: startDate.format('YYYY-MM-DD'),
      end: endDate.format('YYYY-MM-DD'),
    },
    queryOptions: { enabled: !!projects.data },
  })

  const kpiTypes = useGetKPITypes({
    queryOptions: { enabled: !!projects.data },
  })

  const deviceTypes = useGetDeviceTypes({
    queryParams: {
      device_type_ids: kpiTypes.data?.map((kpiType) => kpiType.device_type_id),
    },
    queryOptions: { enabled: !!projects.data },
  })

  const { pivotedData, kpiTypeIds } = useMemo(() => {
    return pivotKpiData(kpiData?.data ?? [], projects?.data ?? [])
  }, [kpiData?.data, projects?.data])

  const topLevelColumns = useMemo(() => {
    const projectColumn = {
      header: 'Project',
      accessorKey: 'projectName',
      Cell: ({ row }: { row: MRT_Row<PivotedData> }) => {
        return (
          <Link
            to={`/projects/${row.original.project_id}`}
            style={{ color: 'inherit' }}
          >
            {row.original.projectName}
          </Link>
        )
      },
    }

    const deviceTypeColumns = buildDeviceTypeGroupedColumns({
      kpiTypeIds,
      kpiTypes: kpiTypes.data,
      deviceTypes: deviceTypes.data,
    })

    return [projectColumn, ...deviceTypeColumns]
  }, [kpiTypeIds, kpiTypes.data, deviceTypes.data])

  const table = useMantineReactTable({
    columns: topLevelColumns as MRT_ColumnDef<PivotedData>[],
    data: pivotedData,
    enablePagination: false,
    enableBottomToolbar: false,
    enableTopToolbar: false,
    enableColumnActions: false,
    initialState: {
      density: 'xs',
    },
    mantineTableProps: {
      striped: true,
      style: {
        borderCollapse: 'collapse',
        border: `1px solid ${color}`,
      },
    },
    mantineTableHeadCellProps: {
      style: {
        borderLeft: `1px solid ${color}`,
        borderRight: `1px solid ${color}`,
      },
    },
    mantineTableBodyCellProps: {
      style: {
        borderLeft: `1px solid ${color}`,
        borderRight: `1px solid ${color}`,
      },
    },
  })

  const isLoading =
    projects.isLoading || kpiData.isLoading || kpiTypes.isLoading

  return (
    <Stack p="md" flex={1} h="100%">
      <PageTitle
        info={
          <Stack>
            <Text size="sm">
              Portfolio KPIs track the performance of various projects against
              one another.
            </Text>
            <Text size="sm">
              Select a date to view KPIs for that specific day.
            </Text>
          </Stack>
        }
      >
        Portfolio KPIs
      </PageTitle>

      <Group>
        <DatesProvider settings={{ consistentWeeks: true }}>
          <DatePickerInput
            label="Select Date"
            placeholder="Pick a date"
            value={selectedDate}
            onChange={setSelectedDate}
            maxDate={dayjs().subtract(1, 'day').toDate()}
            leftSection={<IconCalendar size={16} />}
            clearable={false}
            valueFormat="MMM DD, YYYY"
          />
        </DatesProvider>
      </Group>

      <div style={{ position: 'relative', height: '100%', width: '100%' }}>
        <LoadingOverlay visible={isLoading} />
        <MantineReactTable table={table} />
      </div>
    </Stack>
  )
}

export default PortfolioKPIHome
