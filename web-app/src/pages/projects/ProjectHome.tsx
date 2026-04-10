import { ProjectTypeEnum } from '@/api/enumerations'
import { useGetUserFavoriteKPITypes } from '@/api/v1/admin/user_kpi_types'
import { useGetContractKPIs } from '@/api/v1/operational/kpi_data'
import { useGetKPIInstances } from '@/api/v1/operational/kpi_instances'
import { useGetKPISummaryCards } from '@/api/v1/operational/project/kpi_data'
import { useGetUserProjectLabelsByProjectId } from '@/api/v1/operational/project/project_user_project_labels'
import {
  Project,
  useGetProjects,
  useSelectProject,
} from '@/api/v1/operational/projects'
import CustomCard, { iconSize, iconStroke } from '@/components/CustomCard'
import DeviceTypeOverview from '@/components/DeviceTypeOverview'
import { PageError } from '@/components/Error'
import KPICard, { EmptyKPICard } from '@/components/KPICard'
import { PageLoader } from '@/components/Loading'
import WeatherCard from '@/components/WeatherCard'
import ProjectInfoModal from '@/components/modals/ProjectInfoModal'
import PowerPlotPVZoom from '@/components/plots/PowerPlotPVZoom'
import { TopEventsTableCard } from '@/pages/projects/TopEventsTableCard'
import { AdaptiveGisMap } from '@/pages/projects/gis/adaptive-gis'
import { getKPIThresholdbyDate } from '@/pages/projects/kpis/ProjectKPIHome.utils'
import { projectDescription } from '@/utils/projectDescription'
import { QUERY_TIME } from '@/utils/queryTiming'
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Card,
  Group,
  LoadingOverlay,
  Modal,
  ScrollArea,
  SegmentedControl,
  Skeleton,
  Stack,
  Switch,
  Table,
  Text,
  Title,
  Tooltip,
  useMantineTheme,
} from '@mantine/core'
import { useElementSize } from '@mantine/hooks'
import {
  IconChevronDown,
  IconChevronUp,
  IconCursorText,
  IconInfoCircle,
  IconLock,
  IconMouse,
  IconRepeat,
  IconRepeatOff,
  IconSatellite,
  IconZoomIn,
} from '@tabler/icons-react'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router'

// Extend dayjs with timezone support
dayjs.extend(utc)
dayjs.extend(timezone)

const CurrentTime = ({ timezone }: { timezone: string }) => {
  const [currentTime, setCurrentTime] = useState(() =>
    dayjs().tz(timezone).format('MMM D, YYYY HH:mm:ss'),
  )

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(dayjs().tz(timezone).format('MMM D, YYYY HH:mm:ss'))
    }, 1000)

    return () => clearInterval(interval)
  }, [timezone])

  return (
    <Text size="sm" style={{ fontFamily: 'monospace' }}>
      {currentTime}
    </Text>
  )
}

const KPICards = () => {
  const { projectId } = useParams()
  const { ref: containerRef, width: containerWidth } = useElementSize()
  const { ref: contentRef, width: contentWidth } = useElementSize()
  const [rotationOffset, setRotationOffset] = useState(0)
  const [isHovered, setIsHovered] = useState(false)
  const [queryDate, setQueryDate] = useState(dayjs().format('YYYY-MM-DD'))

  const project = useSelectProject(projectId!)
  const projectKPIInstances = useGetKPIInstances({
    queryParams: {
      project_ids: [projectId || '-1'],
      deep: true,
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })
  const projectKPITypeIds = projectKPIInstances.data?.map(
    (kpiInstance) => kpiInstance.kpi_type_id,
  )

  const favoritedKPITypes = useGetUserFavoriteKPITypes({})

  const kpiTypeIds = favoritedKPITypes.data?.map(
    (kpiInstance) => kpiInstance.kpi_type_id,
  )

  const selectedKPITypeIds = (projectKPITypeIds || []).filter((id) =>
    (kpiTypeIds || []).includes(id),
  )

  const data = useGetKPISummaryCards({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      kpi_type_ids: selectedKPITypeIds,
      date: queryDate,
    },
    queryOptions: {
      enabled:
        !!projectId && !!favoritedKPITypes.data && !!projectKPIInstances.data,
      refetchInterval: QUERY_TIME.ONE_MINUTE, // Refetch every 60 seconds
      staleTime: QUERY_TIME.THIRTY_SECONDS, // Consider data stale after 30 seconds
    },
  })

  // Update queryDate when we detect today has no data (defer to avoid cascading renders)
  useEffect(() => {
    const today = dayjs().format('YYYY-MM-DD')
    if (
      data.isSuccess &&
      data.data &&
      data.data.length === 0 &&
      queryDate === today
    ) {
      // Defer state update to avoid cascading renders
      queueMicrotask(() => {
        setQueryDate(dayjs().subtract(1, 'day').format('YYYY-MM-DD'))
      })
    }
  }, [data.isSuccess, data.data, queryDate])

  const contentIsGreaterThanContainer = contentWidth > containerWidth

  const filteredData = data.data?.filter(
    (kpi) => kpi.value !== null && kpi.value !== undefined,
  )

  const items = filteredData?.map((kpi) => kpi)

  // Derive rotation offset: reset to 0 when content fits in container
  const effectiveRotationOffset = contentIsGreaterThanContainer
    ? rotationOffset
    : 0

  const rotatedItems = items
    ?.slice(effectiveRotationOffset)
    .concat(items?.slice(0, effectiveRotationOffset))

  // Rotate items every second when content is greater than container and not hovered
  useEffect(() => {
    if (!contentIsGreaterThanContainer || isHovered || !items?.length) return

    const interval = setInterval(() => {
      setRotationOffset((prev) => (prev + 1) % items.length)
    }, 4000)

    return () => {
      clearInterval(interval)
    }
  }, [contentIsGreaterThanContainer, items?.length, isHovered])

  // Reset rotation offset state when content is no longer greater than container
  useEffect(() => {
    if (!contentIsGreaterThanContainer && rotationOffset !== 0) {
      // Defer state update to avoid cascading renders
      queueMicrotask(() => {
        setRotationOffset(0)
      })
    }
  }, [contentIsGreaterThanContainer, rotationOffset])

  if (
    project.isLoading ||
    favoritedKPITypes.isLoading ||
    data.isLoading ||
    projectKPIInstances.isLoading
  ) {
    return (
      <Skeleton radius="md">
        <EmptyKPICard />
      </Skeleton>
    )
  }

  return (
    <Group
      ref={containerRef}
      style={{ overflow: 'hidden' }}
      w="100%"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <Group wrap="nowrap" ref={contentRef}>
        {rotatedItems?.map((kpi) => (
          <KPICard
            key={kpi.kpi_type_id}
            {...kpi}
            link={`kpis/type/${kpi.kpi_type_id}`}
          />
        ))}
      </Group>
    </Group>
  )
}

function KioskMode({
  enabled,
  setEnabled,
}: {
  enabled: boolean
  setEnabled: (enabled: boolean) => void
}) {
  const INTERVAL = 60

  const { projectId } = useParams()
  const navigate = useNavigate()

  // Query data for all projects
  const projects = useGetProjects({
    queryParams: {
      deep: true,
    },
  })

  // Get an array of all project IDs
  const projectIds = useMemo(
    () => projects.data?.map((project) => project.project_id),
    [projects.data],
  )

  // Effect to handle kiosk mode
  useEffect(() => {
    // If kiosk mode is not enabled, do nothing
    if (!enabled) return

    // If there are no project IDs, do nothing
    if (!projectIds) return

    // Set an interval to rotate to the next project
    const interval = setInterval(() => {
      // Find the current project index in the array
      const currentIndex = projectIds.findIndex((id) => id === projectId)

      // Get the next project ID (wrap around to the beginning if at the end)
      const nextIndex =
        currentIndex === -1 || currentIndex === projectIds.length - 1
          ? 0
          : currentIndex + 1

      // Navigate to the next project
      const nextProjectId = projectIds[nextIndex]
      navigate(`/projects/${nextProjectId}`)
    }, INTERVAL * 1000)

    // Cleanup interval on component unmount
    return () => clearInterval(interval)
  }, [navigate, projectIds, enabled, projectId])

  return (
    <Tooltip
      label={`Kiosk Mode - When enabled, the page will automatically rotate to the next project every ${INTERVAL} seconds.`}
      refProp="rootRef"
    >
      <Switch
        size="md"
        onLabel={<IconRepeat size={16} />}
        offLabel={<IconRepeatOff size={16} />}
        checked={enabled}
        onChange={(event) => setEnabled(event.currentTarget.checked)}
      />
    </Tooltip>
  )
}

const ContractualKPIOverview = ({
  project,
  onExpandedChange,
}: {
  project: Project | null | undefined
  onExpandedChange?: (expanded: boolean) => void
}) => {
  const { projectId } = useParams()
  const theme = useMantineTheme()
  const navigate = useNavigate()
  const [contractModalOpen, setContractModalOpen] = useState(false)
  const [selectedContractUrl, setSelectedContractUrl] = useState<string | null>(
    null,
  )

  // Size values based on project type - BESS projects get larger sizes
  const isBESSProject =
    project?.project_type_id === ProjectTypeEnum.BESS ||
    project?.project_type_id === ProjectTypeEnum.PVS
  const expandedFlex = isBESSProject ? 0.5 : 0.3
  const expandedMinHeight = isBESSProject ? 180 : 80
  const expandedMaxHeight = isBESSProject ? 250 : 150

  // Initialize expanded state from localStorage, default to true (expanded)
  const [isExpanded, setIsExpanded] = useState(() => {
    const saved = localStorage.getItem(`contractRisksExpanded_${projectId}`)
    return saved !== null ? JSON.parse(saved) : true
  })

  // Update expanded state when projectId changes
  useEffect(() => {
    const saved = localStorage.getItem(`contractRisksExpanded_${projectId}`)
    queueMicrotask(() =>
      setIsExpanded(saved !== null ? JSON.parse(saved) : true),
    )
  }, [projectId])

  // Save expanded state to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem(
      `contractRisksExpanded_${projectId}`,
      JSON.stringify(isExpanded),
    )
    // Notify parent component of the change
    onExpandedChange?.(isExpanded)
  }, [isExpanded, onExpandedChange, projectId])

  // Get contract KPI data with thresholds first (lightweight query)
  const contractKPIData = useGetContractKPIs({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.ONE_MINUTE, // Refetch every 60 seconds
      staleTime: QUERY_TIME.THIRTY_SECONDS, // Consider data stale after 30 seconds
    },
  })

  // Extract contractual KPI type IDs from contract data
  const contractualKpiTypeIds = useMemo(() => {
    if (!contractKPIData.data) return []
    return contractKPIData.data.map((ck) => ck.kpi_type_id)
  }, [contractKPIData.data])

  // Only fetch KPI summary cards for contractual KPIs (not all KPIs)
  const kpiData = useGetKPISummaryCards({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      kpi_type_ids:
        contractualKpiTypeIds.length > 0 ? contractualKpiTypeIds : undefined,
    },
    queryOptions: {
      enabled: !!projectId && contractualKpiTypeIds.length > 0,
      refetchInterval: QUERY_TIME.ONE_MINUTE, // Refetch every 60 seconds
      staleTime: QUERY_TIME.THIRTY_SECONDS, // Consider data stale after 30 seconds
    },
  })

  // All fetched KPIs are contractual (no need to filter)
  const contractualKPIs = kpiData.data || []

  // Create a map of KPI type ID to contract KPI data for easy lookup
  const contractKPIMap = useMemo(() => {
    if (!contractKPIData.data) return new Map()
    return new Map(contractKPIData.data.map((ck) => [ck.kpi_type_id, ck]))
  }, [contractKPIData.data])

  // Function to get threshold value for current date
  const getCurrentThreshold = (kpiTypeId: number) => {
    const contractKPI = contractKPIMap.get(kpiTypeId)
    if (!contractKPI?.threshold?.values) return null

    return getKPIThresholdbyDate(contractKPI.threshold, new Date(), 'discrete')
  }

  // Function to determine status color based on value vs threshold
  const getStatusColor = (
    value: number | null | undefined,
    threshold: number | null | undefined,
    unit?: string | null,
  ) => {
    if (
      value === null ||
      value === undefined ||
      threshold === null ||
      threshold === undefined
    ) {
      return theme.colors.gray[4] // Gray for no data
    }

    // For percentage KPIs, convert threshold to match the value format
    const normalizedThreshold = unit === '%' ? threshold * 100 : threshold

    // For KPIs where higher is better (most cases)
    const percentage = (value / normalizedThreshold) * 100

    if (percentage >= 100) {
      return theme.colors.green[6] // Green - above threshold
    } else if (percentage >= 90) {
      return theme.colors.orange[6] // Orange - close to threshold
    } else {
      return theme.colors.red[6] // Red - below threshold
    }
  }

  // Function to format value with unit
  const formatValue = (
    value: number | null | undefined,
    unit?: string | null,
    isThreshold: boolean = false,
  ) => {
    if (value === null || value === undefined) return 'N/A'

    // For percentage thresholds, multiply by 100 to match the displayed data
    const displayValue = unit === '%' && isThreshold ? value * 100 : value

    const formatted = displayValue.toFixed(2)
    return unit ? `${formatted} ${unit}` : formatted
  }

  // Show loading state
  if (kpiData.isLoading || contractKPIData.isLoading) {
    return (
      <CustomCard title="Contract Risks">
        <LoadingOverlay visible={true} />
      </CustomCard>
    )
  }

  // Show placeholder if no contractual KPIs
  if (contractualKPIs.length === 0) {
    // Create placeholder KPIs for demonstration
    const placeholderKPIs = [
      {
        kpi_type_id: 0,
        contract_id: null,
        link: '',
        is_visible: true,
        ytd_value: 97.2,
        title: 'Project Availability',
        info: 'Example contractual KPI',
        value: null,
        prefix: '',
        suffix: '',
        unit: '%',
        change: null,
        icon: null,
        valColor: undefined,
        aggregation_method: undefined,
        threshold: 95.0,
        counterparty: 'Utility Company A',
      },
      {
        kpi_type_id: 1,
        contract_id: null,
        link: '',
        is_visible: true,
        ytd_value: 102.3,
        title: 'Energy Production',
        info: 'Example contractual KPI',
        value: null,
        prefix: '',
        suffix: '',
        unit: 'MWh',
        change: null,
        icon: null,
        valColor: undefined,
        aggregation_method: undefined,
        threshold: 100.0,
        counterparty: 'Utility Company A',
      },
    ]

    return (
      <CustomCard
        title="Contract Risks"
        headerChildren={
          <Group justify="space-between" align="center">
            <Tooltip label="Add new contractual KPI">
              <Button
                variant="light"
                size="sm"
                onClick={() =>
                  navigate(`/projects/${projectId}/kpis?openRequestModal=true`)
                }
              >
                Add New
              </Button>
            </Tooltip>
            <Tooltip label={isExpanded ? 'Collapse' : 'Expand'}>
              <ActionIcon
                variant="subtle"
                onClick={() => setIsExpanded(!isExpanded)}
              >
                {isExpanded ? (
                  <IconChevronDown size={iconSize} stroke={iconStroke} />
                ) : (
                  <IconChevronUp size={iconSize} stroke={iconStroke} />
                )}
              </ActionIcon>
            </Tooltip>
          </Group>
        }
        style={{
          flex: isExpanded ? expandedFlex : '0 0 auto',
          minHeight: isExpanded ? expandedMinHeight : undefined,
        }}
        hideBody={!isExpanded}
      >
        {isExpanded && (
          <>
            <ScrollArea h="100%">
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>KPI</Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>
                      Counterparty
                    </Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>
                      YTD Value
                    </Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>
                      Threshold
                    </Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>Status</Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>
                      Contract
                    </Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {placeholderKPIs.map((kpi, index) => {
                    const statusColor =
                      kpi.ytd_value >= kpi.threshold
                        ? theme.colors.green[6]
                        : theme.colors.red[6]

                    return (
                      <Table.Tr key={index} style={{ opacity: 0.6 }}>
                        <Table.Td>
                          <Text fw={500} c="dimmed">
                            {kpi.title}
                          </Text>
                          <Text size="xs" c="dimmed">
                            Example placeholder
                          </Text>
                        </Table.Td>
                        <Table.Td style={{ textAlign: 'center' }}>
                          <Text size="sm" c="dimmed">
                            {kpi.counterparty}
                          </Text>
                        </Table.Td>
                        <Table.Td style={{ textAlign: 'center' }}>
                          <Text c="dimmed">
                            {kpi.ytd_value} {kpi.unit}
                          </Text>
                        </Table.Td>
                        <Table.Td style={{ textAlign: 'center' }}>
                          <Text c="dimmed">
                            {kpi.threshold} {kpi.unit}
                          </Text>
                        </Table.Td>
                        <Table.Td style={{ textAlign: 'center' }}>
                          <Box
                            w={12}
                            h={12}
                            style={{
                              backgroundColor: statusColor,
                              borderRadius: '50%',
                              display: 'inline-block',
                            }}
                          />
                        </Table.Td>
                        <Table.Td style={{ textAlign: 'center' }}>
                          <Button variant="light" size="xs" disabled c="dimmed">
                            View
                          </Button>
                        </Table.Td>
                      </Table.Tr>
                    )
                  })}
                </Table.Tbody>
              </Table>
            </ScrollArea>
            <Text size="sm" c="dimmed" ta="center" mt="md">
              Click Add New to request a KPI to be added
            </Text>
          </>
        )}
      </CustomCard>
    )
  }

  return (
    <CustomCard
      title="Contract Risks"
      headerChildren={
        <Group justify="space-between" align="center">
          <Tooltip label="Add new contractual KPI">
            <Button
              variant="light"
              size="sm"
              onClick={() =>
                navigate(`/projects/${projectId}/kpis?openRequestModal=true`)
              }
            >
              Add New
            </Button>
          </Tooltip>
          <Tooltip label={isExpanded ? 'Collapse' : 'Expand'}>
            <ActionIcon
              variant="subtle"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? (
                <IconChevronUp size={iconSize} stroke={iconStroke} />
              ) : (
                <IconChevronDown size={iconSize} stroke={iconStroke} />
              )}
            </ActionIcon>
          </Tooltip>
        </Group>
      }
      style={{
        flex: isExpanded ? expandedFlex : 0.1,
        minHeight: isExpanded ? expandedMinHeight : undefined,
      }}
      bodyStyle={{ maxHeight: expandedMaxHeight, overflowY: 'auto' }}
    >
      {isExpanded && (
        <>
          <ScrollArea h="100%">
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>KPI</Table.Th>
                  <Table.Th style={{ textAlign: 'center' }}>
                    Counterparty
                  </Table.Th>
                  <Table.Th style={{ textAlign: 'center' }}>YTD Value</Table.Th>
                  <Table.Th style={{ textAlign: 'center' }}>Threshold</Table.Th>
                  <Table.Th style={{ textAlign: 'center' }}>Status</Table.Th>
                  <Table.Th style={{ textAlign: 'center' }}>Contract</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {contractualKPIs.map((kpi) => {
                  const threshold = getCurrentThreshold(kpi.kpi_type_id)
                  const statusColor = getStatusColor(
                    kpi.ytd_value,
                    threshold,
                    kpi.unit,
                  )

                  // Get counterparty information from contract KPI data
                  const contractKPI = contractKPIMap.get(kpi.kpi_type_id)
                  const counterparty = contractKPI?.counter_company || 'N/A'

                  return (
                    <Table.Tr
                      key={kpi.kpi_type_id}
                      style={{ cursor: 'pointer' }}
                      onClick={() =>
                        navigate(
                          `/projects/${projectId}/kpis/contractual/${kpi.link}`,
                        )
                      }
                    >
                      <Table.Td>
                        <Text fw={500}>{kpi.title}</Text>
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center' }}>
                        <Text size="sm">{counterparty}</Text>
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center' }}>
                        {formatValue(kpi.ytd_value, kpi.unit)}
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center' }}>
                        {formatValue(threshold, kpi.unit, true)}
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center' }}>
                        <Box
                          w={12}
                          h={12}
                          style={{
                            backgroundColor: statusColor,
                            borderRadius: '50%',
                            display: 'inline-block',
                          }}
                        />
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center' }}>
                        <Button
                          variant="light"
                          size="xs"
                          onClick={(e) => {
                            e.stopPropagation()
                            if (
                              contractKPI?.document_url?.startsWith('https://')
                            ) {
                              setSelectedContractUrl(contractKPI.document_url)
                              setContractModalOpen(true)
                            }
                          }}
                          disabled={
                            !contractKPI?.document_url?.startsWith('https://')
                          }
                        >
                          View
                        </Button>
                      </Table.Td>
                    </Table.Tr>
                  )
                })}
              </Table.Tbody>
            </Table>
          </ScrollArea>

          {/* Contract Document Modal */}
          <Modal
            opened={contractModalOpen}
            onClose={() => setContractModalOpen(false)}
            size="90%"
            title="Contract Document"
            styles={{
              title: { fontSize: '1.2rem', fontWeight: 600 },
            }}
          >
            {selectedContractUrl?.startsWith('https://') && (
              <iframe
                src={selectedContractUrl}
                sandbox="allow-popups"
                style={{
                  width: '100%',
                  height: '80vh',
                  border: 'none',
                  borderRadius: '4px',
                }}
                title="Contract Document"
              />
            )}
          </Modal>
        </>
      )}
    </CustomCard>
  )
}

const ProjectHome = () => {
  const { projectId } = useParams()
  const { ref: stackRef } = useElementSize()
  const [projectInfoModalOpen, setProjectInfoModalOpen] = useState(false)
  const [viewMode, setViewMode] = useState<'kpis' | 'devices'>('kpis')

  const project = useSelectProject(projectId!)
  const [kioskModeEnabled, setKioskModeEnabled] = useState(false)

  if (project.isLoading) return <PageLoader />
  if (project.isError) return <PageError error={project.error} />
  if (project.data === undefined) return <PageError error={undefined} />

  const mapComponent = <AdaptiveGisMap />

  return (
    <Stack p="md" h="100%" ref={stackRef}>
      <Group align="start">
        <Group gap="xs" flex={1}>
          <Title order={1} lh={1}>
            {project.data?.name_long}
          </Title>
          <Title order={1} fw="normal" lh={1}>
            {projectDescription(project.data)}
          </Title>
          <ActionIcon
            variant="subtle"
            size="sm"
            onClick={() => setProjectInfoModalOpen(true)}
            title="Project Information"
          >
            <IconInfoCircle size={16} />
          </ActionIcon>
        </Group>
        <Group gap="xs">
          <ProjectLabels projectId={projectId!} />
          <WeatherCard />
          <Card p={5} withBorder>
            <CurrentTime timezone={project.data?.time_zone} />
          </Card>
          <KioskMode
            enabled={kioskModeEnabled}
            setEnabled={setKioskModeEnabled}
          />
          <SegmentedControl
            size="xs"
            value={viewMode}
            onChange={(value) => setViewMode(value as 'kpis' | 'devices')}
            data={[
              { label: 'KPIs', value: 'kpis' },
              { label: 'System', value: 'devices' },
            ]}
          />
        </Group>
      </Group>

      <Box style={{ minHeight: 'fit-content', flexShrink: 0 }}>
        {viewMode === 'kpis' ? <KPICards /> : <DeviceTypeOverview />}
      </Box>
      <Group flex={1} align="start">
        <Stack h="100%" flex={1}>
          <CustomCard
            title="Performance"
            fill
            style={{ flex: 1 }}
            info={
              <Stack gap="xs">
                <Text fw={600}>Understanding Performance Values</Text>
                <Text size="sm">
                  This map shows how well each device is performing compared to
                  expected output.
                </Text>
                <Text size="sm">
                  <Text component="span" fw={500} c="red.7">
                    Red areas:
                  </Text>{' '}
                  Devices performing below 70% of expected output (potential
                  issues)
                </Text>
                <Text size="sm">
                  <Text component="span" fw={500} c="yellow.7">
                    Yellow areas:
                  </Text>{' '}
                  Devices performing at 70-90% of expected output (monitor
                  closely)
                </Text>
                <Text size="sm">
                  <Text component="span" fw={500} c="green.7">
                    Green areas:
                  </Text>{' '}
                  Devices performing at 90%+ of expected output (good
                  performance)
                </Text>
                <Text size="sm" fw={500}>
                  How values are calculated:
                </Text>
                <Text size="sm">
                  •{' '}
                  <Text component="span" fw={500}>
                    PCS & Combiners:
                  </Text>{' '}
                  (Actual Power ÷ Expected Power) × 100%
                </Text>
                <Text size="sm">
                  •{' '}
                  <Text component="span" fw={500}>
                    Fallback:
                  </Text>{' '}
                  (Actual Power ÷ Device Capacity) × 100% when expected data
                  unavailable
                </Text>
                <Text size="sm">
                  •{' '}
                  <Text component="span" fw={500}>
                    Trackers:
                  </Text>{' '}
                  Show angle position (-60° to +60°) with color-coded time of
                  day
                </Text>
                <Text size="sm" fw={500}>
                  Map Controls:
                </Text>
                <Text size="sm">
                  •{' '}
                  <IconZoomIn
                    size={14}
                    style={{ display: 'inline', verticalAlign: 'middle' }}
                  />
                  <Text component="span" fw={500}>
                    {' '}
                    Zoom:
                  </Text>{' '}
                  Changes device detail level (PCS → Combiners → Trackers)
                </Text>
                <Text size="sm">
                  •{' '}
                  <IconMouse
                    size={14}
                    style={{ display: 'inline', verticalAlign: 'middle' }}
                  />
                  <Text component="span" fw={500}>
                    {' '}
                    Hover:
                  </Text>{' '}
                  View device name and performance values
                </Text>
                <Text size="sm">
                  •{' '}
                  <IconLock
                    size={14}
                    style={{ display: 'inline', verticalAlign: 'middle' }}
                  />
                  <Text component="span" fw={500}>
                    {' '}
                    Lock View:
                  </Text>{' '}
                  Pin current zoom level to specific device type
                </Text>
                <Text size="sm">
                  •{' '}
                  <IconCursorText
                    size={14}
                    style={{ display: 'inline', verticalAlign: 'middle' }}
                  />
                  <Text component="span" fw={500}>
                    {' '}
                    Labels:
                  </Text>{' '}
                  Toggle device name labels on/off
                </Text>
                <Text size="sm">
                  •{' '}
                  <IconSatellite
                    size={14}
                    style={{ display: 'inline', verticalAlign: 'middle' }}
                  />
                  <Text component="span" fw={500}>
                    {' '}
                    Satellite:
                  </Text>{' '}
                  Switch between map and satellite view
                </Text>
                <Text size="sm">
                  <Text component="span" fw={500}>
                    Note:
                  </Text>{' '}
                  Values are averaged over the last hour and updated every 5
                  minutes.
                </Text>
              </Stack>
            }
          >
            {mapComponent}
          </CustomCard>
          {/* Contractual KPI Overview for PV-only projects in left pane */}
          {project.data.project_type_id === ProjectTypeEnum.PV && (
            <ContractualKPIOverview project={project.data} />
          )}
        </Stack>
        <Stack h="100%" flex={1}>
          {project.data.has_event_integration && (
            <TopEventsTableCard
              showLosses={project.data.has_expected_energy_integration}
            />
          )}
          {/* Contractual KPI Overview for PV+Storage projects (right pane) */}
          {project.data.project_type_id === ProjectTypeEnum.PVS && (
            <ContractualKPIOverview project={project.data} />
          )}
          <PowerPlotPVZoom />
        </Stack>
      </Group>

      {/* Project Information Modal */}
      <ProjectInfoModal
        opened={projectInfoModalOpen}
        onClose={() => setProjectInfoModalOpen(false)}
        projectData={project.data}
      />
    </Stack>
  )
}

function ProjectLabels({ projectId }: { projectId: string }) {
  const projectLabels = useGetUserProjectLabelsByProjectId({
    pathParams: { project_id: projectId },
  })

  if (!projectLabels.data?.length) {
    return null
  }

  return (
    <Group>
      {projectLabels.data.map((label) => (
        <Badge key={label.name} color={label.color} variant="light">
          {label.name}
        </Badge>
      ))}
    </Group>
  )
}

export default ProjectHome
