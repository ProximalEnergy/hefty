import { KPITypeEnum } from '@/api/enumerations'
import { useGetOperationalKPIData } from '@/api/v1/operational/kpi_data'
import {
  Contract,
  useGetContractKPIs,
} from '@/api/v1/operational/project/contracts'
import { useSelectProject } from '@/api/v1/operational/projects'
import { VoiceChatModal } from '@/components/VoiceChat'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { QUERY_TIME } from '@/utils/queryTiming'
import {
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Container,
  Grid,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  Title,
  useMantineTheme,
} from '@mantine/core'
import { IconBattery3, IconChartBar, IconInfoCircle } from '@tabler/icons-react'
import dayjs from 'dayjs'
import { useState } from 'react'
import { Link, useParams } from 'react-router'

interface BatteryWarrantyContractProps {
  contract: Contract
  onNavigateToContracts: () => void
}

export const BatteryWarrantyContract = ({
  contract,
  onNavigateToContracts,
}: BatteryWarrantyContractProps) => {
  const { projectId } = useParams()
  const theme = useMantineTheme()
  const [voiceChatModalOpen, setVoiceChatModalOpen] = useState(false)
  const primaryTextColor =
    theme.colors[theme.primaryColor]?.[6] || theme.primaryColor || 'blue'

  // Fetch project data
  const { data: projectData } = useSelectProject(projectId || '-1')

  // Fetch cycle count KPI data
  const { data: cycleKPIData } = useGetOperationalKPIData({
    queryParams: {
      project_ids: [projectId || '-1'],
      kpi_type_ids: [KPITypeEnum.PROJECT_CYCLE_COUNT],
      include_device_data: false,
    },
  })

  const { data: contractKpis, isLoading: contractKpisLoading } =
    useGetContractKPIs({
      pathParams: {
        projectId: projectId || '-1',
        contractId: contract.contract_id,
      },
      queryOptions: {
        enabled: Boolean(projectId && contract.contract_id),
        staleTime: QUERY_TIME.THIRTY_SECONDS,
      },
    })

  const documentUrl =
    contract.document_url ||
    (contract.s3_key
      ? `https://proximal-am-documents.s3.amazonaws.com/${contract.s3_key}`
      : null)

  // Calculate cycles per year from KPI data
  const cyclesPerYear = cycleKPIData?.[0]?.data?.project_data?.[0] || 0

  const years = Array.from({ length: 21 }, (_, i) => 2019 + i) // 21-year timeline (2019-2039)
  const xAxisRange: [number, number] = [years[0], years[years.length - 1]]
  // DC enclosure usable energy capacity (MWh) per container
  const uecPerEnclosure = [
    3.87, 3.74, 3.64, 3.56, 3.48, 3.4, 3.34, 3.28, 3.21, 3.16, 3.1, 3.04, 2.99,
    2.94, 2.9, 2.84, 2.8, 2.75, 2.71, 2.66, 2.61,
  ]
  const uecMeasured = uecPerEnclosure.map((value, idx) => {
    if (years[idx] > 2025) return null
    const jitter = ((idx % 4) - 1.5) * 0.02 // deterministic small variation
    const candidate = value + 0.125 + jitter
    const minimumAboveGuarantee = value + 0.05
    return Number(Math.max(minimumAboveGuarantee, candidate).toFixed(2))
  })
  const capacityTestYears = years.filter((y) => y <= 2025)
  const capacityBoxTraces = capacityTestYears.map((year, idx) => ({
    type: 'box' as const,
    name: `Logged Capacity Tests`,
    x: Array(6).fill(year),
    y: Array.from({ length: 6 }, (__, k) =>
      Number((uecPerEnclosure[idx] + 0.05 * (k + 2.5)).toFixed(2)),
    ),
    boxpoints: false as const,
    marker: {
      color: theme.colors[theme.primaryColor]?.[5] || '#4dabf7',
    },
    line: {
      color: theme.colors[theme.primaryColor]?.[6] || '#1f77b4',
    },
    showlegend: idx === 0,
  }))

  const shortYears = years.filter((y) => y <= 2025)
  const annualCyclesData = shortYears.map(
    (_, idx) => 320 + ((idx * 17) % 40) + (idx % 2 === 0 ? 5 : -5),
  )
  const restSocData = shortYears.map(
    (_, idx) => 40 + ((idx * 7) % 12) + (idx % 2 === 0 ? 3 : -2),
  )
  const tempYears = years
  const restTemps = tempYears.map((year, idx) =>
    year <= 2025
      ? Number((21.5 + ((idx % 3) - 1) * 0.6 + ((idx * 0.17) % 0.8)).toFixed(2))
      : null,
  )
  const activeTemps = tempYears.map((year, idx) =>
    year <= 2025
      ? Number((27 + ((idx % 4) - 1.5) * 0.8 + ((idx * 0.23) % 1)).toFixed(2))
      : null,
  )
  const maxModuleTemps = tempYears.map((year, idx) =>
    year <= 2025
      ? Number((40 + ((idx % 5) - 2) * 1.4 + ((idx * 0.31) % 1.4)).toFixed(2))
      : null,
  )

  // Round Trip Efficiency thresholds (%), year 0 corresponds to 2019
  const rteThreshold = [
    93.8, 92.96, 92.57, 92.26, 92.0, 91.76, 91.55, 91.35, 91.16, 90.98, 90.82,
    90.66, 90.5, 90.35, 90.21, 90.07, 89.94, 89.8, 89.68, 89.55, 89.43,
  ]
  const rteActual = rteThreshold.map((value, idx) =>
    years[idx] <= 2025 ? Number((value + 0.15).toFixed(2)) : null,
  )

  const topStats = [
    {
      label: 'Usable Energy @ DC Enclosure',
      value: '3.585 MWh',
      subtitle: (
        <>
          <span style={{ color: 'green', marginRight: 4 }}>✔</span>
          3.6% above warranty
        </>
      ),
    },
    {
      label: 'RTE @ DC Enclosure',
      value: (() => {
        const idx2025 = years.findIndex((y) => y === 2025)
        const base = idx2025 >= 0 ? rteThreshold[idx2025] : rteThreshold[0]
        return `${(base + 0.15).toFixed(2)}%`
      })(),
      subtitle: (() => {
        const idx2025 = years.findIndex((y) => y === 2025)
        const base = idx2025 >= 0 ? rteThreshold[idx2025] : rteThreshold[0]
        const delta = (base + 0.15 - base).toFixed(2)
        return (
          <>
            <span style={{ color: 'green', marginRight: 4 }}>✔</span>
            {`${delta}% above warranty (2025)`}
          </>
        )
      })(),
    },
    {
      label: 'Term progress',
      value: '7 / 20 years',
      subtitle: '2019 – 2038',
    },
    {
      label: 'Cycles',
      value: cyclesPerYear ? `${cyclesPerYear} cycles` : '347 cycles YTD',
      subtitle: 'Projected EOY: 355 - Limit: 365',
    },
    {
      label: 'Average Rest SOC',
      value: '45% YTD',
      subtitle: 'Contract threshold ≤ 60%',
    },
  ]

  return (
    <Container fluid pt="md">
      <VoiceChatModal
        opened={voiceChatModalOpen}
        onClose={() => setVoiceChatModalOpen(false)}
        contractData={contract}
      />
      <Stack p="sm">
        <Group justify="space-between" align="center">
          <Group align="center">
            <IconBattery3 size={32} />
            <Stack gap={2}>
              <Title order={1}>Battery Warranty Contract</Title>
              <Text c="dimmed">
                {contract.name_long
                  ? `Counterparty: ${contract.name_long}`
                  : 'Counterparty'}
              </Text>
            </Stack>
          </Group>
          <Button variant="light" size="sm" onClick={onNavigateToContracts}>
            View all Contracts
          </Button>
        </Group>

        {/* Alert when data is not available */}
        {(!projectData?.capacity_bess_power_ac ||
          !projectData?.capacity_bess_energy_bol_dc ||
          !cyclesPerYear) && (
          <Alert
            variant="light"
            color="blue"
            title="Battery Warranty Data"
            icon={<IconInfoCircle />}
          >
            Example data shown for demonstration purposes.
          </Alert>
        )}

        {/* Top Stats Row */}
        <SimpleGrid cols={5} spacing="md">
          {topStats.map((stat) => (
            <Card key={stat.label} withBorder padding="md">
              <Title order={4} mb="xs">
                {stat.label}
              </Title>
              <Text size="xl" fw={700} c={primaryTextColor}>
                {stat.value}
              </Text>
              {stat.subtitle && (
                <Text size="sm" c="dimmed">
                  {stat.subtitle}
                </Text>
              )}
            </Card>
          ))}
        </SimpleGrid>

        <Grid gutter="md">
          <Grid.Col span={{ base: 12, lg: 8 }}>
            {/* Energy Capacity Metrics */}
            <Paper withBorder p="md" mb="md">
              <Title order={2} mb="md">
                <IconChartBar size={24} style={{ marginRight: 8 }} />
                OEM Warranty Obligations
              </Title>
              {/* Capacity Trend Chart */}
              <Stack gap="xs" mt="md">
                <Text size="sm" c="dimmed">
                  Usable Energy Capacity per DC enclosure
                </Text>
                <PlotlyPlot
                  data={[
                    {
                      x: years,
                      y: uecPerEnclosure,
                      name: 'Usable Energy Capacity Guarantee',
                      mode: 'lines',
                      line: { color: '#fa5252', dash: 'dash' },
                    },
                    {
                      x: years,
                      y: uecMeasured,
                      name: 'Usable Energy Capacity Measured',
                      mode: 'lines+markers',
                      line: { color: '#1f77b4' },
                      marker: { color: '#1f77b4', size: 6 },
                    },
                    ...capacityBoxTraces,
                  ]}
                  layout={{
                    autosize: true,
                    height: 360,
                    margin: { t: 20, r: 20, b: 60, l: 60 },
                    hoverlabel: { namelength: -1 },
                    xaxis: {
                      title: { text: 'Year' },
                      tickvals: years,
                      ticktext: years.map((y) => String(y)),
                      zeroline: false,
                      range: xAxisRange,
                    },
                    yaxis: {
                      title: { text: 'Usable Energy (MWh DC per enclosure)' },
                      range: [2.0, 4.2],
                      zeroline: false,
                    },
                    legend: { orientation: 'h', y: -0.3 },
                  }}
                />
              </Stack>

              {/* Round Trip Efficiency - DC Enclosure */}
              <Stack gap="xs" mt="lg">
                <Text size="sm" c="dimmed">
                  Round Trip Efficiency (DC Enclosure)
                </Text>
                <PlotlyPlot
                  data={[
                    {
                      x: years,
                      y: rteThreshold,
                      name: 'RTE Guarantee',
                      mode: 'lines',
                      line: { color: '#fa5252', dash: 'dash' },
                    },
                    {
                      x: years,
                      y: rteActual,
                      name: 'Measured RTE',
                      mode: 'lines+markers',
                      line: { color: '#2ca02c' },
                      marker: { size: 6, color: '#2ca02c' },
                    },
                  ]}
                  layout={{
                    autosize: true,
                    height: 300,
                    margin: { t: 20, r: 20, b: 60, l: 60 },
                    hoverlabel: { namelength: -1 },
                    xaxis: {
                      title: { text: 'Year' },
                      tickvals: years,
                      ticktext: years.map((y) => String(y)),
                      zeroline: false,
                      range: xAxisRange,
                    },
                    yaxis: {
                      title: { text: 'RTE (%)' },
                      range: [88, 95],
                      zeroline: false,
                    },
                    legend: { orientation: 'h', y: -0.25 },
                  }}
                />
              </Stack>

              <Title order={2} mt="lg" mb="xs">
                Warranty Operating Constraints
              </Title>

              {/* Annual Cycles Chart */}
              <Stack gap="xs" mt="lg">
                <Text size="sm" c="dimmed">
                  Annual Cycles
                </Text>
                <PlotlyPlot
                  data={[
                    {
                      x: shortYears,
                      y: annualCyclesData,
                      name: 'Annual Cycles',
                      mode: 'lines+markers',
                      line: { color: '#ff7f0e' },
                      marker: { size: 6, color: '#ff7f0e' },
                    },
                    {
                      x: years,
                      y: years.map(() => 365),
                      name: 'Threshold (365)',
                      mode: 'lines',
                      line: { color: '#fa5252', dash: 'dash' },
                    },
                  ]}
                  layout={{
                    autosize: true,
                    height: 280,
                    margin: { t: 20, r: 20, b: 60, l: 60 },
                    hoverlabel: { namelength: -1 },
                    xaxis: {
                      title: { text: 'Year' },
                      tickvals: years,
                      ticktext: years.map((y) => String(y)),
                      zeroline: false,
                      range: xAxisRange,
                    },
                    yaxis: {
                      title: { text: 'Cycles' },
                      range: [250, 380],
                      zeroline: false,
                    },
                    legend: { orientation: 'h', y: -0.25 },
                  }}
                />
              </Stack>

              {/* Average Rest SOC Chart */}
              <Stack gap="xs" mt="lg">
                <Text size="sm" c="dimmed">
                  Average Rest SOC
                </Text>
                <PlotlyPlot
                  data={[
                    {
                      x: shortYears,
                      y: restSocData,
                      name: 'Avg Rest SOC',
                      mode: 'lines+markers',
                      line: { color: '#d62728' },
                      marker: { size: 6, color: '#d62728' },
                    },
                    {
                      x: years,
                      y: years.map(() => 60),
                      name: 'Threshold (60%)',
                      mode: 'lines',
                      line: { color: '#fa5252', dash: 'dash' },
                    },
                  ]}
                  layout={{
                    autosize: true,
                    height: 280,
                    margin: { t: 20, r: 20, b: 60, l: 60 },
                    hoverlabel: { namelength: -1 },
                    xaxis: {
                      title: { text: 'Year' },
                      tickvals: years,
                      ticktext: years.map((y) => String(y)),
                      zeroline: false,
                      range: xAxisRange,
                    },
                    yaxis: {
                      title: { text: 'SOC (%)' },
                      range: [30, 70],
                      zeroline: false,
                    },
                    legend: { orientation: 'h', y: -0.25 },
                  }}
                />
              </Stack>

              {/* Module Temperature Limits */}
              <Stack gap="xs" mt="lg">
                <Text size="sm" c="dimmed">
                  BESS Module Temperatures (per DC Enclosure)
                </Text>
                <PlotlyPlot
                  data={[
                    {
                      x: tempYears,
                      y: maxModuleTemps,
                      name: 'Max Temperature',
                      mode: 'lines+markers',
                      line: { color: '#d9480f' },
                      marker: { size: 6, color: '#d9480f' },
                    },
                    {
                      x: tempYears,
                      y: activeTemps,
                      name: 'Active Temp',
                      mode: 'lines+markers',
                      line: { color: '#228be6' },
                      marker: { size: 6, color: '#228be6' },
                    },
                    {
                      x: tempYears,
                      y: restTemps,
                      name: 'Rest Temp',
                      mode: 'lines+markers',
                      line: { color: '#2c7a7b' },
                      marker: { size: 6, color: '#2c7a7b' },
                    },
                    {
                      x: tempYears,
                      y: tempYears.map(() => 50),
                      name: 'Absolute Limit (50°C)',
                      mode: 'lines',
                      line: { color: '#fa5252', dash: 'dash' },
                    },
                    {
                      x: tempYears,
                      y: tempYears.map(() => 30),
                      name: 'Charge/Discharge Limit (30°C)',
                      mode: 'lines',
                      line: { color: '#fab005', dash: 'dot' },
                    },
                    {
                      x: tempYears,
                      y: tempYears.map(() => 23.5),
                      name: 'Rest Limit (23.5°C)',
                      mode: 'lines',
                      line: { color: '#12b886', dash: 'dot' },
                    },
                  ]}
                  layout={{
                    autosize: true,
                    height: 320,
                    margin: { t: 20, r: 20, b: 60, l: 60 },
                    hoverlabel: { namelength: -1 },
                    xaxis: {
                      title: { text: 'Year' },
                      tickvals: tempYears,
                      ticktext: tempYears.map((y) => String(y)),
                      zeroline: false,
                      range: xAxisRange,
                    },
                    yaxis: {
                      title: { text: 'Temperature (°C)' },
                      range: [15, 55],
                      zeroline: false,
                    },
                    legend: { orientation: 'h', y: -0.25 },
                  }}
                />
              </Stack>
            </Paper>

            {/* Contractual KPIs Section */}
            <Paper withBorder p="md">
              <Title order={2} mb="md">
                <IconBattery3 size={24} style={{ marginRight: 8 }} />
                Contractual Warranty Limits
              </Title>
              <SimpleGrid cols={2} spacing="md">
                <Card withBorder padding="md">
                  <Title order={4} mb="xs">
                    Temperature Limits
                  </Title>
                  <Stack gap="xs">
                    <Group justify="space-between">
                      <Text size="sm">Max Instantaneous Cell Temp:</Text>
                      <Badge color="red">50°C</Badge>
                    </Group>
                    <Group justify="space-between">
                      <Text size="sm">Daily Avg Operating Temp:</Text>
                      <Badge color="orange">≤ 30°C</Badge>
                    </Group>
                    <Group justify="space-between">
                      <Text size="sm">Daily Avg Standby Temp:</Text>
                      <Badge color="blue">≤ 23.5°C</Badge>
                    </Group>
                  </Stack>
                </Card>
                <Card withBorder padding="md">
                  <Title order={4} mb="xs">
                    Operational Limits
                  </Title>
                  <Stack gap="xs">
                    <Group justify="space-between">
                      <Text size="sm">Max Cycles per Day:</Text>
                      <Badge color="green">1 cycle</Badge>
                    </Group>
                    <Group justify="space-between">
                      <Text size="sm">SOC Rest Condition:</Text>
                      <Badge color="purple">≤ 60%</Badge>
                    </Group>
                  </Stack>
                </Card>
              </SimpleGrid>
            </Paper>
          </Grid.Col>

          {/* Right column: document + summary */}
          <Grid.Col span={{ base: 12, lg: 4 }}>
            <Paper withBorder p="md" mb="md">
              <Title order={2} mb="md">
                Contract Document
              </Title>
              {documentUrl ? (
                <iframe
                  src={documentUrl}
                  style={{
                    width: '100%',
                    height: '540px',
                    border: 'none',
                  }}
                  title="Battery Warranty Contract PDF Viewer"
                />
              ) : (
                <Text>No document available at this url: {documentUrl}</Text>
              )}
              <Stack gap="sm" mt="md">
                <Button
                  variant="light"
                  size="sm"
                  fullWidth
                  onClick={() => {
                    if (documentUrl) window.open(documentUrl, '_blank')
                  }}
                >
                  Open Fullscreen
                </Button>
                <Button
                  variant="light"
                  color="green"
                  size="sm"
                  fullWidth
                  onClick={() => setVoiceChatModalOpen(true)}
                >
                  Aria Voice Chat
                </Button>
              </Stack>
            </Paper>

            <Card withBorder padding="md">
              <Group justify="space-between" mb="md" align="flex-start">
                <Stack gap="xs">
                  <Text fw={500} size="sm" c="dimmed">
                    Counterparty
                  </Text>
                  <Text>{contract.name_long}</Text>
                </Stack>
                <Stack gap="xs">
                  <Text fw={500} size="sm" c="dimmed">
                    Execution Date
                  </Text>
                  <Text>
                    {dayjs(contract.execution_date).format('MMMM D, YYYY')}
                  </Text>
                </Stack>
              </Group>

              <Title order={4} mb="xs">
                Contract Summary
              </Title>
              <Text size="sm" c="dimmed" mb="xs">
                Key points from the battery warranty agreement.
              </Text>
              <Text>
                {contract.contract_summary ||
                  'Summary not provided. Add a synopsis of the warranty terms, exclusions, and KPI obligations here.'}
              </Text>
            </Card>

            <Card withBorder padding="md" mt="md">
              <Group justify="space-between" align="center" mb="xs">
                <Stack gap={2}>
                  <Title order={4}>Liquidated Damages by Contractual KPI</Title>
                  <Text size="sm" c="dimmed">
                    Liquidated damages linked to this contract.
                  </Text>
                </Stack>
              </Group>

              {contractKpisLoading ? (
                <Text size="sm" c="dimmed">
                  Loading contractual KPIs…
                </Text>
              ) : (
                <Stack gap="sm">
                  {contractKpis
                    ?.filter((kpi) => kpi.provider_responsible === false)
                    .map((kpi) => {
                      const liquidatedDamagesDescription = (
                        kpi.liquidated_damages as {
                          description?: Record<string, unknown>
                        } | null
                      )?.description

                      const descriptionEntries = liquidatedDamagesDescription
                        ? Object.entries(liquidatedDamagesDescription)
                        : []

                      return (
                        <Card
                          key={`${kpi.contract_id}-${kpi.kpi_type_id}`}
                          withBorder
                          padding="sm"
                        >
                          <Stack gap="xs">
                            <Group justify="space-between" align="flex-start">
                              <Stack gap={2}>
                                <Anchor
                                  component={Link}
                                  to={`/projects/${projectId}/kpis/contractual/${kpi.kpi_name_short}`}
                                  fw={600}
                                >
                                  {kpi.kpi_name_long}
                                </Anchor>
                                <Text size="sm" c="dimmed">
                                  {kpi.kpi_name_short}
                                  {kpi.unit ? ` · ${kpi.unit}` : ''}
                                </Text>
                              </Stack>
                            </Group>

                            {descriptionEntries.length ? (
                              <Stack gap={6}>
                                {descriptionEntries.map(([title, content]) => (
                                  <Stack key={title} gap={2}>
                                    <Text fw={500}>{title}</Text>
                                    <Text size="sm">
                                      {typeof content === 'string'
                                        ? content
                                        : JSON.stringify(content)}
                                    </Text>
                                  </Stack>
                                ))}
                              </Stack>
                            ) : (
                              <Text size="sm" c="dimmed">
                                No liquidated damages specified.
                              </Text>
                            )}
                          </Stack>
                        </Card>
                      )
                    })}

                  {!contractKpis?.some(
                    (kpi) => kpi.provider_responsible === false,
                  ) && (
                    <Text size="sm" c="dimmed">
                      No contractual KPIs marked as provider not responsible.
                    </Text>
                  )}
                </Stack>
              )}
            </Card>
          </Grid.Col>
        </Grid>
      </Stack>
    </Container>
  )
}
