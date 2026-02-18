import {
  DeviceType,
  useGetDeviceTypes,
} from '@/api/v1/operational/device_types'
import {
  OperationalKPIData,
  useGetOperationalKPIData,
} from '@/api/v1/operational/kpi_data'
import { KPIType, useGetKPITypes } from '@/api/v1/operational/kpi_types'
import { Project, useGetProjects } from '@/api/v1/operational/projects'
import { PageTitle } from '@/components/PageTitle'
import { useTipsPortfolioKPIHome } from '@/components/Tips'
import {
  Group,
  LoadingOverlay,
  Stack,
  Table,
  Text,
  useComputedColorScheme,
} from '@mantine/core'
import { DatePickerInput, DatesProvider } from '@mantine/dates'
import { IconCalendar } from '@tabler/icons-react'
import dayjs from 'dayjs'
import { useMemo, useState } from 'react'
import { Link } from 'react-router'

interface PivotedData {
  [kpiTypeId: string]: string | number | null
  project_id: string
  projectName: string
}

type DeviceTypeKPIGroup = {
  deviceType: DeviceType
  kpis: KPIType[]
}

type SortDirection = 'asc' | 'desc'
type SortState = {
  key: string
  direction: SortDirection
} | null

function buildDeviceTypeKPIGroups({
  kpiTypeIds,
  kpiTypes,
  deviceTypes,
}: {
  kpiTypeIds: number[]
  kpiTypes: KPIType[] | undefined
  deviceTypes: DeviceType[] | undefined
}): DeviceTypeKPIGroup[] {
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

  return Array.from(groupedByDeviceType.entries())
    .sort(([a], [b]) => (a.device_type_id || 0) - (b.device_type_id || 0))
    .map(([deviceType, kpis]) => ({ deviceType, kpis }))
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

function isEmptyKpiValue(value: number | null | undefined) {
  return value === null || value === undefined
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
  const computedColorScheme = useComputedColorScheme('light')
  const headerBg =
    computedColorScheme === 'light' ? 'var(--mantine-color-white)' : undefined
  const [sortState, setSortState] = useState<SortState>(null)

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
  }, [kpiData.data, projects.data])

  const deviceTypeGroups = useMemo(() => {
    return buildDeviceTypeKPIGroups({
      kpiTypeIds,
      kpiTypes: kpiTypes.data,
      deviceTypes: deviceTypes.data,
    })
  }, [kpiTypeIds, kpiTypes.data, deviceTypes.data])

  const kpiColumns = useMemo(
    () =>
      deviceTypeGroups.flatMap(({ deviceType, kpis }) =>
        kpis.map((kpiObj) => ({ deviceType, kpiObj })),
      ),
    [deviceTypeGroups],
  )

  const sortedPivotedData = useMemo(() => {
    if (!sortState) {
      return pivotedData
    }

    const sortedRows = [...pivotedData]
    sortedRows.sort((a, b) => {
      if (sortState.key === 'projectName') {
        const compare = a.projectName.localeCompare(b.projectName)
        return sortState.direction === 'asc' ? compare : -compare
      }

      const aValue = a[sortState.key] as number | null | undefined
      const bValue = b[sortState.key] as number | null | undefined
      const aIsEmpty = isEmptyKpiValue(aValue)
      const bIsEmpty = isEmptyKpiValue(bValue)

      if (aIsEmpty && bIsEmpty) {
        return 0
      }
      if (aIsEmpty) {
        return 1
      }
      if (bIsEmpty) {
        return -1
      }

      const compare = (aValue as number) - (bValue as number)
      return sortState.direction === 'asc' ? compare : -compare
    })

    return sortedRows
  }, [pivotedData, sortState])

  const toggleSort = (key: string) => {
    setSortState((current) => {
      if (!current || current.key !== key) {
        return { key, direction: 'asc' }
      }
      return { key, direction: current.direction === 'asc' ? 'desc' : 'asc' }
    })
  }

  const getSortIndicator = (key: string) => {
    if (!sortState || sortState.key !== key) {
      return '↕'
    }
    return sortState.direction === 'asc' ? '↑' : '↓'
  }

  const isLoading =
    projects.isLoading ||
    kpiData.isLoading ||
    kpiTypes.isLoading ||
    deviceTypes.isLoading

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
        <Table.ScrollContainer
          minWidth={Math.max(900, (kpiTypeIds.length + 1) * 180)}
          maxHeight="100%"
        >
          <Table
            striped="odd"
            withTableBorder
            withColumnBorders
            highlightOnHover
            horizontalSpacing="sm"
            verticalSpacing="xs"
            style={{
              width: 'max-content',
              minWidth: '100%',
              backgroundColor:
                computedColorScheme === 'light'
                  ? 'var(--mantine-color-white)'
                  : undefined,
            }}
          >
            <Table.Thead>
              <Table.Tr>
                <Table.Th
                  rowSpan={2}
                  onClick={() => toggleSort('projectName')}
                  style={{
                    whiteSpace: 'nowrap',
                    cursor: 'pointer',
                    userSelect: 'none',
                    textAlign: 'center',
                    backgroundColor: headerBg,
                  }}
                >
                  <Group gap={4} wrap="nowrap" justify="center">
                    <Text span fw={700}>
                      Project
                    </Text>
                    <Text span size="xs" c="dimmed">
                      {getSortIndicator('projectName')}
                    </Text>
                  </Group>
                </Table.Th>
                {deviceTypeGroups.map(({ deviceType, kpis }) => (
                  <Table.Th
                    key={`group-${deviceType.device_type_id}`}
                    colSpan={kpis.length}
                    style={{
                      whiteSpace: 'nowrap',
                      textAlign: 'center',
                      backgroundColor: headerBg,
                    }}
                  >
                    {deviceType.name_long}
                  </Table.Th>
                ))}
              </Table.Tr>
              <Table.Tr>
                {kpiColumns.map(({ deviceType, kpiObj }) => (
                  <Table.Th
                    key={`kpi-${deviceType.device_type_id}-${kpiObj.kpi_type_id}`}
                    onClick={() => toggleSort(String(kpiObj.kpi_type_id))}
                    style={{
                      whiteSpace: 'nowrap',
                      cursor: 'pointer',
                      userSelect: 'none',
                      textAlign: 'center',
                      backgroundColor: headerBg,
                    }}
                  >
                    <Group gap={4} wrap="nowrap" justify="center">
                      <Text span fw={700}>
                        {kpiObj.name_metric ?? `KPI ${kpiObj.kpi_type_id}`}
                      </Text>
                      <Text span size="xs" c="dimmed">
                        {getSortIndicator(String(kpiObj.kpi_type_id))}
                      </Text>
                    </Group>
                  </Table.Th>
                ))}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {sortedPivotedData.map((row) => (
                <Table.Tr key={row.project_id}>
                  <Table.Td style={{ whiteSpace: 'nowrap' }}>
                    <Link
                      to={`/projects/${row.project_id}`}
                      style={{ color: 'inherit' }}
                    >
                      {row.projectName}
                    </Link>
                  </Table.Td>
                  {kpiColumns.map(({ deviceType, kpiObj }) => (
                    <Table.Td
                      key={`value-${row.project_id}-${deviceType.device_type_id}-${kpiObj.kpi_type_id}`}
                      style={{ whiteSpace: 'nowrap' }}
                    >
                      <Link
                        to={`/projects/${row.project_id}/kpis/type/${kpiObj.kpi_type_id}`}
                        style={{ color: 'inherit' }}
                      >
                        <Text size="sm">
                          {renderKpiCellValue(
                            (row[String(kpiObj.kpi_type_id)] as
                              | number
                              | null) ?? null,
                            kpiObj,
                          )}
                        </Text>
                      </Link>
                    </Table.Td>
                  ))}
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </div>
    </Stack>
  )
}

export default PortfolioKPIHome
