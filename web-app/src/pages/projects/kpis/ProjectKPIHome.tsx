import { useGetUserSelf, useGetUserType } from '@/api/admin'
import {
  useGetUserFavoriteKPITypes,
  useUpdateUserKPITypeFavoriteMutation,
} from '@/api/v1/admin/user_kpi_types'
import { useGetOperationalKPIData } from '@/api/v1/operational/kpi_data'
import { useGetProjectKPITypes } from '@/api/v1/operational/kpi_types'
import { PageLoader } from '@/components/Loading'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import {
  ActionIcon,
  Button,
  Group,
  HoverCard,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  ThemeIcon,
  Title,
  rem,
} from '@mantine/core'
import {
  IconBell,
  IconEyeOff,
  IconFilter,
  IconHeart,
  IconHeartFilled,
  IconInfoCircle,
} from '@tabler/icons-react'
import { memo, useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import RequestKPIModal from './RequestKPIModal'

const TrendSparkline = memo(
  ({
    data,
    threshold,
    unit = '',
  }: {
    data: { value: number | null; timestamp: string }[]
    threshold?: number
    unit?: string
  }) => {
    if (!data || data.length === 0) {
      return <div style={{ width: 120, height: 40 }} />
    }

    // Filter out null values and sort by timestamp
    const validData = data
      .filter((point) => point.value !== null)
      .sort(
        (a, b) =>
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
      )

    // Multiply values by 100 if the unit is '%'
    const multiplier = unit === '%' ? 100 : 1
    const adjustedData = validData.map((d) => ({
      ...d,
      value: d.value !== null ? d.value * multiplier : null,
    }))

    // Threshold is already adjusted in categorizedKPIs, so we don't need to multiply it here
    const adjustedThreshold = threshold

    return (
      <div style={{ width: 120, height: 40 }}>
        <PlotlyPlot
          data={[
            {
              type: 'scatter',
              mode: 'lines',
              x: adjustedData.map((d) => d.timestamp),
              y: adjustedData.map((d) => d.value),
              line: {
                color: '#228be6',
                width: 1.5,
                shape: 'spline',
                smoothing: 0.8,
              },
              hovertemplate: `%{y:.1f}${unit ? unit : ''}<br>%{x|%Y-%m-%d}<extra></extra>`,
              hoverlabel: {
                bgcolor: 'white',
                bordercolor: '#228be6',
                font: { size: 12 },
              },
            },
            // @ts-expect-error Manually ignoring type for now
            ...(adjustedThreshold !== undefined
              ? [
                  {
                    type: 'scatter',
                    mode: 'lines',
                    x: [
                      adjustedData[0]?.timestamp,
                      adjustedData[adjustedData.length - 1]?.timestamp,
                    ],
                    y: [adjustedThreshold, adjustedThreshold],
                    line: { color: 'red', width: 1, dash: 'dash' },
                    hovertemplate: `Threshold: ${adjustedThreshold?.toFixed(1)}${
                      unit ? unit : ''
                    }<extra></extra>`,
                    hoverlabel: {
                      bgcolor: 'white',
                      bordercolor: 'red',
                      font: { size: 12 },
                    },
                  },
                ]
              : []),
          ]}
          layout={{
            showlegend: false,
            margin: { l: 0, r: 0, t: 0, b: 0 },
            xaxis: { visible: false },
            yaxis: {
              visible: false,
              autorange: true,
              fixedrange: true,
            },
            plot_bgcolor: 'transparent',
            paper_bgcolor: 'transparent',
            hovermode: 'x unified',
          }}
          config={{
            displayModeBar: false,
            staticPlot: false,
          }}
        />
      </div>
    )
  },
)

// Update the formatNumber helper function to properly handle percentage thresholds
const formatNumber = (
  value: number | null,
  unit: string,
  isThreshold: boolean = false,
) => {
  if (value === null) return 'N/A'

  // For percentage thresholds, multiply by 100 to match the displayed data
  const displayValue = unit === '%' && isThreshold ? value * 100 : value

  // Round to 2 decimal places
  const roundedValue = Number(displayValue.toFixed(2))
  // Only append unit if it exists and isn't "null"
  return `${roundedValue.toLocaleString()}${unit ? ` ${unit}` : ''}`.trim()
}

// Add this helper function
export const getKPIThresholdbyDate = (
  thresholdData: {
    values?: { [key: string]: number }
  } | null,
  date?: Date,
  mode: 'discrete' | 'interpolate' = 'discrete',
): number | null => {
  if (!thresholdData?.values) return null

  const targetDate = date || new Date()
  const targetTime = targetDate.getTime()

  // Convert all dates to timestamps and sort them
  const dates = Object.keys(thresholdData.values)
    .map((dateStr) => new Date(dateStr).getTime())
    .sort((a, b) => a - b)

  if (mode === 'discrete') {
    // Find the most recent date that's before or equal to the target date
    const mostRecentDate = dates
      .filter((timestamp) => timestamp <= targetTime)
      .pop()

    if (mostRecentDate) {
      // Convert back to ISO string format to lookup in thresholdData
      const dateStr = new Date(mostRecentDate).toISOString().split('T')[0]
      return thresholdData.values[dateStr]
    }

    // If no valid date found, use the earliest available threshold
    const earliestDateStr = new Date(dates[0]).toISOString().split('T')[0]
    return thresholdData.values[earliestDateStr] || null
  } else {
    // Interpolation mode
    const beforeDate = dates
      .filter((timestamp) => timestamp <= targetTime)
      .pop()
    const afterDate = dates
      .filter((timestamp) => timestamp > targetTime)
      .shift()

    // If target date is before all threshold dates, return earliest threshold
    if (!beforeDate) {
      const earliestDateStr = new Date(dates[0]).toISOString().split('T')[0]
      return thresholdData.values[earliestDateStr] || null
    }

    // If target date is after all threshold dates, return latest threshold
    if (!afterDate) {
      const latestDateStr = new Date(dates[dates.length - 1])
        .toISOString()
        .split('T')[0]
      return thresholdData.values[latestDateStr] || null
    }

    // Perform linear interpolation
    const beforeDateStr = new Date(beforeDate).toISOString().split('T')[0]
    const afterDateStr = new Date(afterDate).toISOString().split('T')[0]
    const beforeValue = thresholdData.values[beforeDateStr]
    const afterValue = thresholdData.values[afterDateStr]

    const timeFraction = (targetTime - beforeDate) / (afterDate - beforeDate)
    return beforeValue + (afterValue - beforeValue) * timeFraction
  }
}

const KpiTable = ({
  kpis,
  projectId,
  handleFavoriteClick,
  contractsMap,
  type,
  title,
}: {
  kpis: any[]
  projectId: string | undefined
  handleFavoriteClick: (kpi: any) => void
  contractsMap: Map<any, any>
  type: 'benchmark' | 'contractual'
  title: string
}) => {
  if (kpis.length === 0) {
    return null
  }

  return (
    <Stack>
      <Title order={3}>{title}</Title>
      <Table
        striped
        highlightOnHover
        withTableBorder
        styles={{
          td: { padding: '0px 16px' },
          th: { padding: '8px 16px' },
        }}
      >
        <Table.Thead>
          <Table.Tr>
            <Table.Th w={30}></Table.Th>
            <Table.Th>Metric</Table.Th>
            {type === 'contractual' && (
              <>
                <Table.Th>
                  <Group gap={4} wrap="nowrap">
                    Counterparty
                    <HoverCard shadow="md" withArrow>
                      <HoverCard.Target>
                        <IconInfoCircle
                          size={14}
                          stroke={1.5}
                          style={{ display: 'block', cursor: 'help' }}
                        />
                      </HoverCard.Target>
                      <HoverCard.Dropdown>
                        <Text size="xs">
                          The other party named in the relevant contract
                          document.
                        </Text>
                      </HoverCard.Dropdown>
                    </HoverCard>
                  </Group>
                </Table.Th>
                <Table.Th>
                  <Group gap={4} wrap="nowrap">
                    Threshold
                    <HoverCard shadow="md" withArrow>
                      <HoverCard.Target>
                        <IconInfoCircle
                          size={14}
                          stroke={1.5}
                          style={{ display: 'block', cursor: 'help' }}
                        />
                      </HoverCard.Target>
                      <HoverCard.Dropdown>
                        <Text size="xs">
                          The contractual minimum or maximum acceptable value
                          for this KPI on the current date.
                        </Text>
                      </HoverCard.Dropdown>
                    </HoverCard>
                  </Group>
                </Table.Th>
              </>
            )}
            <Table.Th>
              <Group gap={4} wrap="nowrap">
                Yesterday
                <HoverCard shadow="md" withArrow>
                  <HoverCard.Target>
                    <IconInfoCircle
                      size={14}
                      stroke={1.5}
                      style={{ display: 'block', cursor: 'help' }}
                    />
                  </HoverCard.Target>
                  <HoverCard.Dropdown>
                    <Text size="xs">
                      The KPI value calculated for yesterday, and its relative
                      change compared to the day before that.
                    </Text>
                  </HoverCard.Dropdown>
                </HoverCard>
              </Group>
            </Table.Th>
            <Table.Th>
              <Group gap={4} wrap="nowrap">
                Project YTD
                <HoverCard shadow="md" withArrow>
                  <HoverCard.Target>
                    <IconInfoCircle
                      size={14}
                      stroke={1.5}
                      style={{ display: 'block', cursor: 'help' }}
                    />
                  </HoverCard.Target>
                  <HoverCard.Dropdown>
                    <Text size="xs">
                      Average of all daily values from January 1st of the
                      current year to today.
                    </Text>
                  </HoverCard.Dropdown>
                </HoverCard>
              </Group>
            </Table.Th>
            <Table.Th>
              <Group gap={4} wrap="nowrap">
                Trend
                <HoverCard shadow="md" withArrow>
                  <HoverCard.Target>
                    <IconInfoCircle
                      size={14}
                      stroke={1.5}
                      style={{ display: 'block', cursor: 'help' }}
                    />
                  </HoverCard.Target>
                  <HoverCard.Dropdown>
                    <Text size="xs">
                      A sparkline chart showing the daily KPI values from
                      January 1st of the current year to today.
                    </Text>
                  </HoverCard.Dropdown>
                </HoverCard>
              </Group>
            </Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {kpis.map((kpi, index) => {
            const contract =
              type === 'contractual' ? contractsMap.get(kpi.contract_id) : null
            return (
              <Table.Tr key={index}>
                <Table.Td>
                  <ActionIcon
                    variant="transparent"
                    onClick={() => handleFavoriteClick(kpi)}
                    aria-label="Favorite KPI"
                  >
                    {kpi.is_favorited ? (
                      <IconHeartFilled
                        style={{ width: rem(16), height: rem(16) }}
                        color="red"
                      />
                    ) : (
                      <IconHeart style={{ width: rem(16), height: rem(16) }} />
                    )}
                  </ActionIcon>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    {!kpi.is_visible && (
                      <ThemeIcon color="gray" size={20} radius="xl">
                        <IconEyeOff
                          style={{
                            width: rem(16),
                            height: rem(16),
                          }}
                        />
                      </ThemeIcon>
                    )}
                    <Link
                      to={`/projects/${projectId}/kpis/${kpi.link}`}
                      style={{
                        color: 'inherit',
                        textDecoration: 'none',
                      }}
                    >
                      {kpi.title}
                    </Link>
                  </Group>
                </Table.Td>
                {type === 'contractual' && (
                  <>
                    <Table.Td>
                      {contract?.counter_company || 'Unknown'}
                      <Link
                        to={`/projects/${projectId}/contracts/${contract?.contract_id}`}
                        style={{
                          marginLeft: '4px',
                          color: '#228be6',
                          textDecoration: 'none',
                        }}
                      >
                        (contract)
                      </Link>
                    </Table.Td>
                    <Table.Td>
                      {kpi.threshold
                        ? formatNumber(
                            getKPIThresholdbyDate(kpi.threshold),
                            kpi.unit,
                            true,
                          )
                        : 'N/A'}
                    </Table.Td>
                  </>
                )}
                <Table.Td>
                  {kpi.value !== null ? (
                    <>
                      {formatNumber(kpi.value, kpi.unit)}
                      {kpi.change !== null && (
                        <>
                          {' '}
                          ({kpi.change > 0 ? '+' : ''}
                          {kpi.change.toFixed(2)}%)
                        </>
                      )}
                    </>
                  ) : (
                    'N/A'
                  )}
                </Table.Td>
                <Table.Td>
                  {kpi.ytd_value !== null
                    ? formatNumber(kpi.ytd_value, kpi.unit)
                    : 'N/A'}
                </Table.Td>
                <Table.Td>
                  <TrendSparkline
                    data={kpi.trendData}
                    threshold={kpi.thresholdValue}
                    unit={kpi.unit}
                  />
                </Table.Td>
              </Table.Tr>
            )
          })}
        </Table.Tbody>
      </Table>
    </Stack>
  )
}

const ProjectKPIHome = () => {
  const { projectId } = useParams()
  const { data: user } = useGetUserSelf({})
  const { data: favoriteKpis } = useGetUserFavoriteKPITypes({
    userId: user?.user_id,
  })
  const updateUserKPITypeFavorite = useUpdateUserKPITypeFavoriteMutation()
  const [searchParams, setSearchParams] = useSearchParams()
  const userType = useGetUserType({
    queryOptions: {
      enabled: !!projectId,
    },
  })
  const isUserSuperadmin = userType?.data?.user_type_id === 1

  // Parse deviceTypeId from URL params as Number of there
  const deviceTypeId = useMemo(() => {
    const deviceTypeId = searchParams.get('deviceTypeId')
    return deviceTypeId ? Number(deviceTypeId) : undefined
  }, [searchParams])

  const [requestModalOpen, setRequestModalOpen] = useState(false)
  const [showHidden, setShowHidden] = useState(false)

  // Check for URL parameter to automatically open request modal
  useEffect(() => {
    const shouldOpenModal = searchParams.get('openRequestModal')
    if (shouldOpenModal === 'true') {
      setRequestModalOpen(true)
      // Remove the parameter from URL to prevent reopening on refresh
      searchParams.delete('openRequestModal')
      setSearchParams(searchParams)
    }
  }, [searchParams, setSearchParams])

  const { data: kpiTypesWithContracts, isLoading } = useGetProjectKPITypes({
    pathParams: { projectId: projectId || '-1' },
  })

  // Remove the useGetDeviceTypes API call and replace with this memoized calculation
  const deviceTypes = useMemo(() => {
    if (!kpiTypesWithContracts) return { data: [], isLoading: false }

    // Create a Map to store unique device types
    const deviceTypeMap = new Map()

    kpiTypesWithContracts.forEach((kpi) => {
      if (kpi.device_type && kpi.device_type.device_type_id) {
        deviceTypeMap.set(kpi.device_type.device_type_id, {
          device_type_id: kpi.device_type.device_type_id,
          name_long:
            kpi.device_type.name_long ||
            `Device Type ${kpi.device_type.device_type_id}`,
        })
      }
    })

    // Convert Map to array
    const uniqueDeviceTypes = Array.from(deviceTypeMap.values())

    return {
      data: uniqueDeviceTypes,
      isLoading: false,
    }
  }, [kpiTypesWithContracts])

  // Memoize date calculations
  const dates = useMemo(() => {
    const today = new Date()
    const currentYear = today.getFullYear()
    const januaryFirst = new Date(currentYear, 0, 1) // January 1st of current year
    const twoDaysAgo = new Date(today.getTime() - 2 * 24 * 60 * 60 * 1000)

    // Use twoDaysAgo if it's before January 3rd, otherwise use January 1st
    const startDate =
      today.getMonth() === 0 && today.getDate() <= 3 ? twoDaysAgo : januaryFirst

    return {
      startDate: startDate.toISOString().split('T')[0],
      today: today.toISOString().split('T')[0],
    }
  }, [])

  // Add this new query to load all KPI data upfront
  const { data: allKPIData } = useGetOperationalKPIData({
    queryParams: {
      start: dates.startDate,
      end: dates.today,
      project_ids: projectId ? [projectId] : [], // Changed to match backend's array expectation
      include_device_data: false,
    },
  })

  // Memoize filteredDeviceTypes
  const filteredDeviceTypes = useMemo(() => {
    if (!deviceTypes.data) return []
    return deviceTypes.data.filter((dt) => dt.device_type_id !== 0)
  }, [deviceTypes])

  // Update the categorizedKPIs calculation
  const categorizedKPIs = useMemo(() => {
    if (!kpiTypesWithContracts || !allKPIData || !favoriteKpis) {
      return { contractual: [], benchmark: [], favorited: [] }
    }

    const favoriteKpiIds = new Set(favoriteKpis.map((f) => f.kpi_type_id))

    const kpis = kpiTypesWithContracts.reduce(
      (acc, kpiType) => {
        // Skip if filtered by device type and doesn't match
        if (deviceTypeId && kpiType.device_type_id !== deviceTypeId) {
          return acc
        }

        // Find the KPI data for this type
        const kpiData = allKPIData.find(
          (d) => d.kpi_type_id === kpiType.kpi_type_id,
        )

        // Get the last two days of data and dates (if data exists)
        const projectData = kpiData?.data.project_data ?? []
        const dates = kpiData?.data.dates ?? []
        const lastValue = projectData[projectData.length - 1] ?? null
        const previousValue = projectData[projectData.length - 2] ?? null

        // Calculate YTD value (average of all non-null values in the current year)
        const currentYear = new Date().getFullYear()
        const ytdValues = projectData.filter((value, index) => {
          const valueDate = new Date(dates[index])
          return valueDate.getFullYear() === currentYear && value !== null
        })
        const ytdValue =
          ytdValues.length > 0
            ? ytdValues
                .filter((val): val is number => val !== null)
                .reduce((sum, val) => (sum || 0) + val, 0) / ytdValues.length
            : null

        // Calculate change percentage
        const changeValue =
          lastValue !== null && previousValue !== null
            ? ((lastValue - previousValue) / previousValue) * 100
            : null

        // Get threshold from contract KPI if it exists - filter by current project
        const contractKpi = kpiType.contract_kpis.find((ck) =>
          kpiType.contracts.some(
            (contract) =>
              contract.contract_id === ck.contract_id &&
              contract.project_id === projectId,
          ),
        )
        const multiplier = kpiType.unit === '%' ? 100 : 1
        const thresholdValue = contractKpi
          ? (() => {
              const threshold = getKPIThresholdbyDate(
                contractKpi.threshold
                  ? { values: contractKpi.threshold.values }
                  : null,
                new Date(),
              )
              return threshold !== null ? threshold * multiplier : undefined
            })()
          : undefined

        const processedKpi = {
          kpi_type_id: kpiType.kpi_type_id,
          contract_id: contractKpi?.contract_id ?? null,
          title: kpiType.name_long,
          unit: kpiType.unit,
          is_visible: kpiType.is_visible,
          is_favorited: favoriteKpiIds.has(kpiType.kpi_type_id),
          link:
            kpiType.contract_kpis.length > 0
              ? `contractual/${kpiType.name_short.replace(/_/g, '-')}`
              : `type/${kpiType.kpi_type_id}`,
          trendData: dates.map((date, i) => ({
            value: projectData[i],
            timestamp: date,
            threshold: thresholdValue,
          })),
          threshold: contractKpi?.threshold,
          thresholdValue,
          value: lastValue !== null ? lastValue * multiplier : null,
          ytd_value: ytdValue !== null ? ytdValue * multiplier : null,
          change: changeValue,
        }

        acc[
          kpiType.contract_kpis.length > 0 ? 'contractual' : 'benchmark'
        ].push(processedKpi)
        return acc
      },
      { contractual: [], benchmark: [] } as {
        contractual: any[]
        benchmark: any[]
      },
    )

    const favorited = [...kpis.contractual, ...kpis.benchmark].filter(
      (kpi) => kpi.is_favorited,
    )

    const contractual = kpis.contractual.filter((kpi) => !kpi.is_favorited)
    const benchmark = kpis.benchmark.filter((kpi) => !kpi.is_favorited)

    return {
      contractual,
      benchmark,
      favorited,
    }
  }, [kpiTypesWithContracts, allKPIData, deviceTypeId, favoriteKpis])

  // Add this memoized helper to check if there are any hidden KPIs
  const hasHiddenKPIs = useMemo(() => {
    if (!kpiTypesWithContracts) return false
    return kpiTypesWithContracts.some((kpi) => !kpi.is_visible)
  }, [kpiTypesWithContracts])

  const handleFavoriteClick = (kpi: any) => {
    if (user) {
      updateUserKPITypeFavorite.mutate({
        userId: user.user_id,
        kpiTypeId: kpi.kpi_type_id,
        isFavorited: !kpi.is_favorited,
      })
    }
  }

  // Add filtered versions of categorizedKPIs
  const filteredCategorizedKPIs = useMemo(() => {
    const favoritedBenchmark = categorizedKPIs.favorited.filter(
      (kpi) => !kpi.contract_id,
    )
    const favoritedContractual = categorizedKPIs.favorited.filter(
      (kpi) => !!kpi.contract_id,
    )

    if (!showHidden) {
      return {
        contractual: categorizedKPIs.contractual.filter(
          (kpi) => kpi.is_visible,
        ),
        benchmark: categorizedKPIs.benchmark.filter((kpi) => kpi.is_visible),
        favoritedBenchmark: favoritedBenchmark.filter((kpi) => kpi.is_visible),
        favoritedContractual: favoritedContractual.filter(
          (kpi) => kpi.is_visible,
        ),
      }
    }
    return {
      ...categorizedKPIs,
      favoritedBenchmark,
      favoritedContractual,
    }
  }, [categorizedKPIs, showHidden])

  // Create a memoized map of all unique contracts from kpiTypesWithContracts
  const contractsMap = useMemo(() => {
    if (!kpiTypesWithContracts) return new Map()

    const contracts = new Map()

    kpiTypesWithContracts.forEach((kpiType) => {
      kpiType.contracts.forEach((contract) => {
        // Only include contracts for the current project
        if (contract.project_id === projectId) {
          contracts.set(contract.contract_id, contract)
        }
      })
    })

    return contracts
  }, [kpiTypesWithContracts, projectId])

  // Return early if loading
  if (isLoading || deviceTypes.isLoading) {
    return <PageLoader />
  }

  if (!kpiTypesWithContracts) {
    return <Text>No KPI data available.</Text>
  }

  return (
    <>
      <Stack p="md">
        <Title order={1}>Project KPIs</Title>
        <Group align="center" justify="space-between">
          <Group>
            <IconFilter size={24} stroke={1.5} />
            <Select
              placeholder="Select Device Type"
              data={
                filteredDeviceTypes
                  ?.map((deviceType) => ({
                    label: deviceType.name_long ?? 'Unknown',
                    value: deviceType.device_type_id.toString(),
                  }))
                  .sort((a, b) => a.label.localeCompare(b.label)) || []
              }
              value={deviceTypeId?.toString() ?? ''}
              onChange={(value) => {
                if (value === null) {
                  searchParams.delete('deviceTypeId')
                } else {
                  searchParams.set('deviceTypeId', value)
                }
                setSearchParams(searchParams)
              }}
              clearable
            />
            {hasHiddenKPIs && isUserSuperadmin && (
              <Switch
                label="Show Hidden"
                checked={showHidden}
                onChange={(event) => setShowHidden(event.currentTarget.checked)}
              />
            )}
          </Group>
          <Group>
            <Link to={`/projects/${projectId}/kpis/alerts`}>
              <Button variant="light" rightSection={<IconBell size={14} />}>
                Manage Alerts
              </Button>
            </Link>
          </Group>
        </Group>
        {filteredCategorizedKPIs.favoritedBenchmark.length > 0 ||
        filteredCategorizedKPIs.favoritedContractual.length > 0 ? (
          <Stack>
            <Title order={2}>Favorite KPIs</Title>
            <KpiTable
              kpis={filteredCategorizedKPIs.favoritedBenchmark}
              projectId={projectId}
              handleFavoriteClick={handleFavoriteClick}
              contractsMap={contractsMap}
              type="benchmark"
              title="Benchmarking Performance KPIs"
            />
            <KpiTable
              kpis={filteredCategorizedKPIs.favoritedContractual}
              projectId={projectId}
              handleFavoriteClick={handleFavoriteClick}
              contractsMap={contractsMap}
              type="contractual"
              title="Contractual KPIs"
            />
          </Stack>
        ) : null}
        <KpiTable
          kpis={filteredCategorizedKPIs.benchmark}
          projectId={projectId}
          handleFavoriteClick={handleFavoriteClick}
          contractsMap={contractsMap}
          type="benchmark"
          title="Benchmarking Performance KPIs"
        />

        <Stack mt="xl">
          <Group align="center" justify="space-between" pr={4}>
            <Title order={2}>Contractual KPIs</Title>
            <Group>
              <Link to={`/projects/${projectId}/contracts`}>
                <Button variant="light">Contracts</Button>
              </Link>
              <Button variant="light" onClick={() => setRequestModalOpen(true)}>
                Request New KPI
              </Button>
            </Group>
          </Group>
          <KpiTable
            kpis={filteredCategorizedKPIs.contractual}
            projectId={projectId}
            handleFavoriteClick={handleFavoriteClick}
            contractsMap={contractsMap}
            type="contractual"
            title="Performance Obligations"
          />
        </Stack>
      </Stack>

      <RequestKPIModal
        opened={requestModalOpen}
        onClose={() => setRequestModalOpen(false)}
      />
    </>
  )
}

export default memo(ProjectKPIHome)
