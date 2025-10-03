import {
  useGetContractKPIs,
  useGetProjectContracts,
} from '@/api/v1/operational/project/contracts'
import { useGetKPISummaryCards } from '@/api/v1/operational/project/kpi_data'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { VoiceChatModal } from '@/components/VoiceChat'
import {
  Badge,
  Box,
  Button,
  Card,
  Container,
  Grid,
  Group,
  Paper,
  ScrollArea,
  Skeleton,
  Stack,
  Table,
  Text,
  Title,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import {
  IconFileText,
  IconMail,
  IconMapPin,
  IconPlus,
  IconUser,
} from '@tabler/icons-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import CreateContractModal from './CreateContractModal'

// Placeholder contractual KPIs data
const placeholderKPIs = [
  {
    kpi: 'Availability Guarantee',
    counterparty: 'Utility Company A',
    ytdValue: '98.5%',
    threshold: '95.0%',
    status: 'Good',
    contract: 'Contract #001',
  },
  {
    kpi: 'Performance Ratio',
    counterparty: 'Utility Company A',
    ytdValue: '0.89',
    threshold: '0.85',
    status: 'Good',
    contract: 'Contract #001',
  },
  {
    kpi: 'Response Time',
    counterparty: 'Utility Company A',
    ytdValue: '2.3 min',
    threshold: '5.0 min',
    status: 'Good',
    contract: 'Contract #001',
  },
]

// Example contracts for demo purposes
const exampleContracts = [
  {
    contract_id: 1,
    project_id: 'demo',
    document_id: 'doc_001',
    company_id_provider: 'provider_001',
    company_id_counter: 'counter_001',
    execution_date: '2024-01-15',
    name_short: 'BESS Warranty',
    name_long: 'Tesla Energy Solutions',
    document_url: null,
    s3_key: null,
    contract_summary:
      'This warranty document outlines the Technical Availability Guarantee (TAG) for the BESS project, including reporting responsibilities and liquidated damages. The Supplier guarantees specific availability percentages based on the project site zone. In the case of defects, the Customer must provide detailed reports and grant access for maintenance. The document details the calculation for the Availability Percentage and establishes conditions under which liquidated damages apply if the guaranteed availability is not met. The contract also specifies limits on the Warranty and conditions for extended TAG periods.',
    term_start_date: '2024-01-15',
    term_end_date: '2029-01-15',
    category_name_long: 'Battery Energy Storage System Warranty',
    counter_contact_addressee: 'Sarah Johnson, Customer Success',
    counter_contact_email: 'sarah.johnson@tesla.com',
    counter_contact_address: '123 Energy Plaza, Suite 400\nHouston, TX 77002',
  },
  {
    contract_id: 2,
    project_id: 'demo',
    document_id: 'doc_002',
    company_id_provider: 'provider_002',
    company_id_counter: 'counter_002',
    execution_date: '2024-03-20',
    name_short: 'Service Contract',
    name_long: 'First Solar Operations',
    document_url: null,
    s3_key: null,
    contract_summary:
      'This Operations and Maintenance (O&M) service contract establishes comprehensive maintenance and operational support for the solar photovoltaic system. The contract includes routine inspections, preventive maintenance schedules, performance monitoring, and emergency response protocols. The service provider is responsible for maintaining optimal system performance, conducting regular equipment assessments, and ensuring compliance with manufacturer warranties. The agreement outlines performance guarantees, response time requirements, and detailed reporting procedures for system health and energy production metrics.',
    term_start_date: '2024-03-20',
    term_end_date: '2034-03-20',
    category_name_long: 'Operations and Maintenance Services',
    counter_contact_addressee: 'Michael Chen, Operations Director',
    counter_contact_email: 'mchen@firstsolar.com',
    counter_contact_address: '350 West Washington Street\nTempe, AZ 85281',
  },
]

interface ContractCardProps {
  contract: any
  onContractClick: (contractId: number) => void
  isExample?: boolean
  onVoiceChat: (contract: any) => void
}

const ContractCard = ({
  contract,
  onContractClick,
  isExample = false,
  onVoiceChat,
}: ContractCardProps) => {
  const theme = useMantineTheme()
  const computedColorScheme = useComputedColorScheme('light')
  const isDarkMode = computedColorScheme === 'dark'
  const navigate = useNavigate()

  // Use contract type from data if available, otherwise get random one
  const contractType = contract.category_name_long || 'Unknown'

  // Dates
  const execDate = contract.execution_date
    ? new Date(contract.execution_date)
    : null
  const startDate = contract.term_start_date
    ? new Date(contract.term_start_date)
    : null
  const endDate = contract.term_end_date
    ? new Date(contract.term_end_date)
    : null
  const summaryText = contract.contract_summary || 'Unknown'

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'good':
        return 'green'
      case 'warning':
        return 'yellow'
      case 'critical':
        return 'red'
      default:
        return 'gray'
    }
  }

  const { data: kpis } = useGetContractKPIs({
    pathParams: {
      projectId: contract.project_id,
      contractId: contract.contract_id,
    },
    queryOptions: {
      enabled:
        !isExample && contract.project_id !== 'demo' && !!contract.project_id,
    },
  })

  // Get all KPI summary cards for this project to get the actual KPI values
  const { data: allKpis, isLoading: kpisLoading } = useGetKPISummaryCards({
    pathParams: { projectId: contract.project_id },
    queryOptions: {
      enabled:
        !isExample && contract.project_id !== 'demo' && !!contract.project_id,
    },
  })

  // Filter for only contractual KPIs (those with contract_id) for this specific contract
  const contractualKPIs =
    allKpis?.filter((kpi: any) => kpi.contract_id === contract.contract_id) ||
    []

  // Function to get threshold value for current date (simplified version)
  const getCurrentThreshold = (kpiTypeId: number) => {
    if (!kpis) return null

    const contractKPI = kpis.find((kpi: any) => kpi.kpi_type_id === kpiTypeId)
    if (!contractKPI?.threshold?.values) return null

    // Get the current year's threshold value
    const currentYear = new Date().getFullYear()
    const thresholdValues = contractKPI.threshold.values

    // Look for the current year's threshold
    if (thresholdValues && typeof thresholdValues === 'object') {
      const currentYearKey = `${currentYear}-01-01`
      if (thresholdValues[currentYearKey] !== undefined) {
        return thresholdValues[currentYearKey]
      }

      // Fallback: get the most recent threshold value
      const yearKeys = Object.keys(thresholdValues).filter((key) =>
        key.startsWith(`${currentYear}`),
      )
      if (yearKeys.length > 0) {
        return thresholdValues[yearKeys[0]]
      }

      // Last resort: get any available threshold value
      const availableValues = Object.values(thresholdValues)
      if (availableValues.length > 0) {
        return availableValues[0]
      }
    }

    return null
  }

  // Function to determine status color based on value vs threshold
  const getStatusColorFromValue = (
    value: number | null | undefined,
    threshold: number | null | undefined,
    unit?: string,
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
    unit?: string,
    isThreshold: boolean = false,
  ) => {
    if (value === null || value === undefined) return 'N/A'

    // For percentage thresholds, multiply by 100 to match the displayed data
    const displayValue = unit === '%' && isThreshold ? value * 100 : value

    const formatted = displayValue.toFixed(2)
    return unit ? `${formatted} ${unit}` : formatted
  }

  return (
    <Paper
      shadow="sm"
      p="md"
      radius="md"
      withBorder
      style={{
        minHeight: '20vh',
        cursor: isExample ? 'default' : 'pointer',
        transition: 'all 0.2s ease',
        opacity: isExample ? 0.8 : 1,
      }}
      onClick={
        isExample ? undefined : () => onContractClick(contract.contract_id)
      }
      onMouseEnter={
        isExample
          ? undefined
          : (e) => {
              e.currentTarget.style.transform = 'translateY(-2px)'
              e.currentTarget.style.boxShadow = theme.shadows.md
            }
      }
      onMouseLeave={
        isExample
          ? undefined
          : (e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = theme.shadows.sm
            }
      }
    >
      {/* Header */}
      <Group justify="space-between" mb="md">
        <Title order={3} size="h4" style={{ flex: 1 }}>
          {contractType} - {contract.name_long}
        </Title>
        <Group gap="xs">
          {isExample && (
            <Badge color="orange" variant="light" size="sm">
              Example
            </Badge>
          )}
        </Group>
      </Group>

      <Grid gutter="md">
        {/* PDF Viewer Section (20% width) */}
        <Grid.Col span={2.4}>
          <Stack gap="xs">
            {contract.document_url || contract.s3_key ? (
              <Box
                style={{
                  height: '300px',
                  border: `1px solid ${theme.colors.gray[3]}`,
                  borderRadius: theme.radius.md,
                  overflow: 'hidden',
                }}
              >
                <iframe
                  src={`${
                    contract.document_url ||
                    (contract.s3_key
                      ? `https://proximal-am-documents.s3.amazonaws.com/${contract.s3_key}`
                      : '')
                  }#toolbar=0`}
                  style={{
                    width: '100%',
                    height: '100%',
                    border: 'none',
                  }}
                  title="Contract Preview"
                />
              </Box>
            ) : (
              <Box
                style={{
                  height: '300px',
                  border: `1px solid ${theme.colors.gray[3]}`,
                  borderRadius: theme.radius.md,
                  overflow: 'hidden',
                }}
              >
                <iframe
                  src="/Proximal Solar 1 LLC - OM Agreement Final.pdf#toolbar=0"
                  style={{
                    width: '100%',
                    height: '100%',
                    border: 'none',
                  }}
                  title="Sample Contract Preview"
                />
              </Box>
            )}
            <Button
              variant="light"
              size="xs"
              fullWidth
              onClick={() => {
                const url =
                  contract.document_url ||
                  (contract.s3_key
                    ? `https://proximal-am-documents.s3.amazonaws.com/${contract.s3_key}`
                    : '/Proximal Solar 1 LLC - OM Agreement Final.pdf')
                window.open(url, '_blank')
              }}
            >
              Open Full Document
            </Button>
            <Button
              variant="light"
              size="xs"
              fullWidth
              color="green"
              onClick={(e) => {
                e.stopPropagation()
                onVoiceChat(contract)
              }}
            >
              Aria Document Chat
            </Button>
          </Stack>
        </Grid.Col>

        {/* Contract Details Section (80% width) */}
        <Grid.Col span={9.6}>
          <Grid gutter="md">
            {/* First Row - Contract Details (70%) and Contact Info (30%) */}
            <Grid.Col span={8.4}>
              <Stack gap="sm">
                <Box>
                  <Text size="sm" fw={500} c="dimmed">
                    Term
                  </Text>
                  <Text size="sm">
                    {startDate
                      ? `${startDate.toLocaleDateString('en-CA')} - ${endDate ? endDate.toLocaleDateString('en-CA') : 'N/A'}`
                      : 'Unknown'}
                  </Text>
                </Box>

                <Box>
                  <Text size="sm" fw={500} c="dimmed">
                    Execution Date
                  </Text>
                  <Text size="sm">
                    {execDate
                      ? execDate.toLocaleDateString('en-CA')
                      : 'Unknown'}
                  </Text>
                </Box>

                <Box>
                  <Text size="sm" fw={500} c="dimmed">
                    Summary
                  </Text>
                  <Text size="sm" lineClamp={6}>
                    {summaryText}
                  </Text>
                </Box>
              </Stack>
            </Grid.Col>

            <Grid.Col span={3.6}>
              <Card
                withBorder
                p="sm"
                style={{
                  backgroundColor: isDarkMode
                    ? theme.colors.dark[6]
                    : theme.colors.gray[0],
                }}
              >
                <Stack gap="xs">
                  <Group gap="xs">
                    <IconUser size={16} color={theme.colors.gray[6]} />
                    <Text size="sm" fw={500}>
                      Contact Information
                    </Text>
                  </Group>

                  <Box>
                    <Text size="xs" c="dimmed">
                      Addressee
                    </Text>
                    <Text size="sm">
                      {contract.counter_contact_addressee || 'Unknown'}
                    </Text>
                  </Box>

                  <Box>
                    <Text size="xs" c="dimmed">
                      Email
                    </Text>
                    <Group gap="xs">
                      <IconMail size={14} color={theme.colors.gray[6]} />
                      <Text size="sm">
                        {contract.counter_contact_email || 'Unknown'}
                      </Text>
                    </Group>
                  </Box>

                  <Box>
                    <Text size="xs" c="dimmed">
                      Address
                    </Text>
                    <Group gap="xs" align="flex-start">
                      <IconMapPin
                        size={14}
                        color={theme.colors.gray[6]}
                        style={{ marginTop: 2 }}
                      />
                      <Text size="sm">
                        {contract.counter_contact_address || 'Unknown'}
                      </Text>
                    </Group>
                  </Box>
                </Stack>
              </Card>
            </Grid.Col>

            {/* Second Row - Contractual KPIs Table */}
            <Grid.Col span={12}>
              <Box>
                <Text size="sm" fw={500} c="dimmed" mb="xs">
                  Contractual KPIs
                </Text>

                {!isExample && !kpisLoading && contractualKPIs.length === 0 && (
                  <Text
                    size="xs"
                    c="dimmed"
                    mb="sm"
                    style={{ fontStyle: 'italic' }}
                  >
                    Note: Example KPIs shown.{' '}
                    <Text
                      component="span"
                      c="blue"
                      style={{ cursor: 'pointer', textDecoration: 'underline' }}
                      onClick={(e) => {
                        e.stopPropagation()
                        navigate(
                          `/projects/${contract.project_id}/kpis?openRequestModal=true`,
                        )
                      }}
                    >
                      Request a contractual KPI
                    </Text>{' '}
                    to get added here.
                  </Text>
                )}

                <ScrollArea>
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
                        <Table.Th style={{ textAlign: 'center' }}>
                          Status
                        </Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {kpisLoading
                        ? // Show skeleton loaders while KPIs are loading
                          Array.from({ length: 3 }).map((_, index) => (
                            <Table.Tr key={`skeleton-${index}`}>
                              <Table.Td>
                                <Skeleton height={20} width="80%" />
                              </Table.Td>
                              <Table.Td style={{ textAlign: 'center' }}>
                                <Skeleton height={20} width="70%" />
                              </Table.Td>
                              <Table.Td style={{ textAlign: 'center' }}>
                                <Skeleton height={20} width="60%" />
                              </Table.Td>
                              <Table.Td style={{ textAlign: 'center' }}>
                                <Skeleton height={20} width="60%" />
                              </Table.Td>
                              <Table.Td style={{ textAlign: 'center' }}>
                                <Skeleton
                                  height={12}
                                  width={12}
                                  style={{ borderRadius: '50%' }}
                                />
                              </Table.Td>
                            </Table.Tr>
                          ))
                        : contractualKPIs.length > 0
                          ? contractualKPIs.map((row: any, idx: number) => (
                              <Table.Tr
                                key={`kpi-${idx}`}
                                style={{ cursor: 'pointer' }}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  navigate(
                                    `/projects/${contract.project_id}/kpis/contractual/${row.link}`,
                                  )
                                }}
                                onMouseEnter={(e) => {
                                  e.currentTarget.style.backgroundColor =
                                    theme.colors.gray[1]
                                }}
                                onMouseLeave={(e) => {
                                  e.currentTarget.style.backgroundColor =
                                    'transparent'
                                }}
                              >
                                <Table.Td>
                                  <Text fw={500}>{row.title || 'Unknown'}</Text>
                                </Table.Td>
                                <Table.Td style={{ textAlign: 'center' }}>
                                  <Text size="sm">
                                    {contract.name_long || 'Unknown'}
                                  </Text>
                                </Table.Td>
                                <Table.Td style={{ textAlign: 'center' }}>
                                  {formatValue(row.ytd_value, row.unit)}
                                </Table.Td>
                                <Table.Td style={{ textAlign: 'center' }}>
                                  {formatValue(
                                    getCurrentThreshold(row.kpi_type_id),
                                    row.unit,
                                    true,
                                  )}
                                </Table.Td>
                                <Table.Td style={{ textAlign: 'center' }}>
                                  <Box
                                    w={12}
                                    h={12}
                                    style={{
                                      backgroundColor: getStatusColorFromValue(
                                        row.ytd_value,
                                        getCurrentThreshold(row.kpi_type_id),
                                        row.unit,
                                      ),
                                      borderRadius: '50%',
                                      display: 'inline-block',
                                    }}
                                  />
                                </Table.Td>
                              </Table.Tr>
                            ))
                          : // Show placeholder data only when not loading and no real data
                            placeholderKPIs.map((kpi, index) => (
                              <Table.Tr
                                key={index}
                                style={{
                                  opacity: 0.6,
                                  color: theme.colors.gray[5],
                                }}
                              >
                                <Table.Td>
                                  <Text c="dimmed">{kpi.kpi}</Text>
                                </Table.Td>
                                <Table.Td style={{ textAlign: 'center' }}>
                                  <Text c="dimmed">{kpi.counterparty}</Text>
                                </Table.Td>
                                <Table.Td style={{ textAlign: 'center' }}>
                                  <Text c="dimmed">{kpi.ytdValue}</Text>
                                </Table.Td>
                                <Table.Td style={{ textAlign: 'center' }}>
                                  <Text c="dimmed">{kpi.threshold}</Text>
                                </Table.Td>
                                <Table.Td style={{ textAlign: 'center' }}>
                                  <Badge
                                    color={getStatusColor(kpi.status)}
                                    variant="light"
                                    size="sm"
                                    style={{ opacity: 0.7 }}
                                  >
                                    {kpi.status}
                                  </Badge>
                                </Table.Td>
                              </Table.Tr>
                            ))}
                    </Table.Tbody>
                  </Table>
                </ScrollArea>
              </Box>
            </Grid.Col>
          </Grid>
        </Grid.Col>
      </Grid>
    </Paper>
  )
}

const Page = () => {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const [modalOpen, setModalOpen] = useState(false)
  const [voiceChatModalOpen, setVoiceChatModalOpen] = useState(false)
  const [selectedContract, setSelectedContract] = useState<any>(null)

  if (!projectId) {
    return <Text>Error: Project ID is missing.</Text>
  }
  const {
    data: contracts,
    isLoading,
    error,
  } = useGetProjectContracts({
    pathParams: { projectId: projectId || '-1' },
  })

  if (isLoading) return <PageLoader />
  if (error) return <Text>Error loading contracts: {error.message}</Text>

  const contractList = Array.isArray(contracts) ? contracts : []

  const handleRowClick = (contractId: number) => {
    navigate(`/projects/${projectId}/contracts/${contractId}`)
  }

  const handleVoiceChat = (contract: any) => {
    setSelectedContract(contract)
    setVoiceChatModalOpen(true)
  }

  return (
    <Container fluid pt="md">
      <Stack p="sm" gap="lg">
        <Group justify="space-between" align="center">
          <PageTitle
            order={1}
            info="With Aria, you can summarize and chat with your contracts. You can also create contract-based KPIs that Proximal will monitor for you."
          >
            Contracts
          </PageTitle>
          <Button
            size="sm"
            onClick={() => setModalOpen(true)}
            leftSection={<IconPlus size={16} />}
          >
            Add Contract
          </Button>
        </Group>

        <CreateContractModal
          opened={modalOpen}
          onClose={() => setModalOpen(false)}
        />

        <VoiceChatModal
          opened={voiceChatModalOpen}
          onClose={() => setVoiceChatModalOpen(false)}
          contractData={selectedContract}
        />

        {contractList.length === 0 ? (
          <Stack gap="lg">
            <Paper
              p="md"
              withBorder
              style={{
                textAlign: 'center',
                backgroundColor: 'var(--mantine-color-blue-0)',
                borderColor: 'var(--mantine-color-blue-2)',
              }}
            >
              <Stack align="center" gap="sm">
                <IconFileText size={48} color="var(--mantine-color-blue-6)" />
                <Title order={4} c="blue">
                  No Contracts Found
                </Title>
                <Text c="dimmed" size="sm">
                  No contracts have been added to this project yet. Here are
                  some examples of what contracts will look like:
                </Text>
                <Button
                  variant="light"
                  color="blue"
                  onClick={() => setModalOpen(true)}
                  mt="sm"
                >
                  Add Your First Contract
                </Button>
              </Stack>
            </Paper>

            <Stack gap="lg">
              {exampleContracts.map((contract) => (
                <ContractCard
                  key={contract.contract_id}
                  contract={contract}
                  onContractClick={() => {}} // Disable click for examples
                  isExample={true}
                  onVoiceChat={handleVoiceChat}
                />
              ))}
            </Stack>
          </Stack>
        ) : (
          <Stack gap="lg">
            {contractList.map((contract) => (
              <ContractCard
                key={contract.contract_id}
                contract={contract}
                onContractClick={handleRowClick}
                onVoiceChat={handleVoiceChat}
              />
            ))}
          </Stack>
        )}
      </Stack>
    </Container>
  )
}

export default Page
