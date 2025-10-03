import { useGetOperationalKPIData } from '@/api/v1/operational/kpi_data'
import { useGetKPITypeByName } from '@/api/v1/operational/kpi_types'
import CustomCard from '@/components/CustomCard'
import { PageLoader } from '@/components/Loading'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useProjectDropdownToggle } from '@/hooks/custom'
import { getKPIThresholdbyDate } from '@/pages/projects/kpis/ProjectKPIHome'
import {
  Box,
  Button,
  Card,
  Container,
  Grid,
  Group,
  List,
  Paper,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  Title,
} from '@mantine/core'
import dayjs from 'dayjs'
import { Data } from 'plotly.js'
import { useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'

interface Threshold {
  values: { [key: string]: number }
  mode?: 'discrete' | 'interpolate'
}

const BarAndHeatmapCard = ({
  parsedData,
  isLoading,
  kpiTypeData,
  selectedYear,
  setSelectedYear,
  yearOptions,
}: {
  parsedData: Data[] | undefined
  isLoading: boolean
  kpiTypeData: any
  selectedYear: string
  setSelectedYear: (value: string) => void
  yearOptions: { value: string; label: string }[]
}) => {
  const isCumulative = kpiTypeData?.aggregation_method === 'sum'

  return (
    <CustomCard
      title="Performance Data"
      style={{ height: '50vh' }}
      headerChildren={
        <Select
          size="xs"
          value={selectedYear}
          onChange={(value) =>
            setSelectedYear(value || dayjs().year().toString())
          }
          data={yearOptions}
          style={{ width: '120px' }}
        />
      }
    >
      <PlotlyPlot
        data={parsedData}
        layout={{
          xaxis: {
            type: kpiTypeData?.device_type_id === 1 ? 'date' : 'category',
            title: kpiTypeData?.device_type_id === 1 ? 'Date' : undefined,
          },
          yaxis: {
            tickformat: kpiTypeData?.unit === '%' ? ',.0%' : ',.0f',
            title: isCumulative
              ? `Cumulative Total (${kpiTypeData.unit || ''})`
              : kpiTypeData?.unit
                ? `Value (${kpiTypeData.unit})`
                : 'Value',
          },
          showlegend: true,
          legend: {
            orientation: 'h',
            yanchor: 'bottom',
            y: 1.02,
            xanchor: 'right',
            x: 1,
          },
          annotations: !parsedData
            ? [
                {
                  text: 'No data. Adjust the date range.',
                  xref: 'paper',
                  yref: 'paper',
                  x: 0.5,
                  y: 0.5,
                  showarrow: false,
                  font: {
                    size: 16,
                    color: 'gray',
                  },
                },
              ]
            : undefined,
        }}
        config={{ displayModeBar: false }}
        colorscale="primary"
        isLoading={isLoading}
      />
    </CustomCard>
  )
}

const AnnualAveragesCard = ({
  parsedData,
  isLoading,
  kpiTypeData,
}: {
  parsedData: { data: Data[]; layout: any } | undefined
  isLoading: boolean
  kpiTypeData: any
}) => {
  // Determine y-axis label based on aggregation method and unit
  const yAxisTitle = kpiTypeData?.unit
    ? `${
        kpiTypeData.aggregation_method === 'sum' ? 'Total' : 'Average'
      } Value (${kpiTypeData.unit})`
    : `${kpiTypeData.aggregation_method === 'sum' ? 'Total' : 'Average'} Value`

  return (
    <CustomCard title="Annual Performance" style={{ height: '30vh' }}>
      <PlotlyPlot
        data={parsedData?.data}
        layout={{
          ...parsedData?.layout,
          yaxis: {
            ...parsedData?.layout?.yaxis,
            title: yAxisTitle,
          },
        }}
        config={{ displayModeBar: false }}
        colorscale="primary"
        isLoading={isLoading}
      />
    </CustomCard>
  )
}

const ProjectKPIContractual = () => {
  const { projectId, nameShort } = useParams()
  const [selectedYear, setSelectedYear] = useState(dayjs().year().toString())
  // const [searchParams] = useSearchParams();

  useProjectDropdownToggle()
  const { data: kpiTypeData, isLoading: kpiLoading } = useGetKPITypeByName({
    pathParams: { nameShort: nameShort || '' },
  })

  // Single query to fetch all KPI data
  const { data: allKPIData, isLoading: kpiDataLoading } =
    useGetOperationalKPIData({
      queryParams: {
        start: dayjs()
          .subtract(20, 'years')
          .startOf('year')
          .format('YYYY-MM-DD'),
        end: dayjs().format('YYYY-MM-DD'),
        project_ids: projectId ? [projectId] : [],
        kpi_type_ids: kpiTypeData?.kpi_type_id ? [kpiTypeData.kpi_type_id] : [],
        include_device_data: false,
      },
      queryOptions: {
        enabled: !!kpiTypeData?.kpi_type_id,
        staleTime: Infinity,
      },
    })

  // Generate year options from the data
  const yearOptions = useMemo(() => {
    if (!allKPIData?.length || !allKPIData[0]?.data?.dates) return []

    const years = new Set(
      allKPIData[0].data.dates.map((date: string) =>
        dayjs(date).year().toString(),
      ),
    )

    return Array.from(years)
      .sort()
      .reverse()
      .map((year) => ({
        value: year,
        label: year === dayjs().year().toString() ? `${year} (Current)` : year,
      }))
  }, [allKPIData])

  // Filter data for the selected year
  const getFilteredYearData = () => {
    if (!allKPIData?.length || !allKPIData[0]?.data) {
      return undefined
    }

    const kpiData = allKPIData[0].data
    const yearStart = dayjs(`${selectedYear}-01-01`)

    // Filter data points within the selected year
    const filteredIndices = kpiData.dates.reduce(
      (acc: number[], date: string, index: number) => {
        const currentDate = dayjs(date)
        if (currentDate.isSame(yearStart, 'year')) {
          acc.push(index)
        }
        return acc
      },
      [],
    )

    return {
      ...kpiData,
      dates: filteredIndices.map((i) => kpiData.dates[i]),
      project_data: filteredIndices.map((i) => kpiData.project_data[i]),
      device_data_obj: kpiData.device_data_obj
        ? {
            device_values: Object.fromEntries(
              Object.entries(kpiData.device_data_obj.device_values).map(
                ([key, values]) => [key, filteredIndices.map((i) => values[i])],
              ),
            ),
          }
        : undefined,
    }
  }

  // Use filtered data for performance chart
  const filteredData = useMemo(() => {
    if (!allKPIData) return undefined
    return [
      {
        ...allKPIData[0],
        data: getFilteredYearData(),
      },
    ]
  }, [allKPIData, selectedYear])

  const parseData = (data: any, kpiTypeData: any) => {
    if (!data?.length || !data[0]?.data) {
      return []
    }

    const kpiData = data[0].data
    const isPercentage = kpiTypeData?.unit === '%'

    // For device_type_id = 1, show daily data with time on x-axis
    if (kpiTypeData?.device_type_id === 1) {
      const isCumulative = kpiTypeData?.aggregation_method === 'sum'
      const hovertemplate = isPercentage
        ? '%{y:.2%}<extra></extra>'
        : `%{y:.2f}${kpiTypeData.unit || ''}<extra></extra>`

      const thresholdHovertemplate = isPercentage
        ? '%{y:.2%}<extra>Threshold</extra>'
        : `%{y:.2f}${kpiTypeData.unit || ''}<extra>Threshold</extra>`

      // Get threshold values for each date point
      const thresholdValues = kpiData.dates.map((date: string) => {
        if (!kpiTypeData?.contracts) return null
        for (const contract of kpiTypeData.contracts) {
          const contractKpi = kpiTypeData.contract_kpis?.find(
            (ck: any) => ck.contract_id === contract.contract_id,
          )
          if (contractKpi?.threshold) {
            const threshold = getKPIThresholdbyDate(
              contractKpi.threshold,
              new Date(date),
            )
            if (threshold !== null) {
              return isPercentage ? threshold : threshold
            }
          }
        }
        return null
      })

      // Calculate cumulative sum if aggregation method is sum
      let yValues = [...kpiData.project_data]
      if (isCumulative) {
        let sum = 0
        yValues = yValues.map((value: number) => {
          sum += value
          return sum
        })
      }

      const traces = [
        {
          x: kpiData.dates.map((date: string) =>
            dayjs(date).format('YYYY-MM-DD'),
          ),
          y: yValues,
          type: 'scatter',
          mode: 'lines+markers',
          name: isCumulative ? 'Cumulative Total' : 'Performance',
          hovertemplate,
          line: { color: '#228BE6' },
        },
        {
          x: kpiData.dates.map((date: string) =>
            dayjs(date).format('YYYY-MM-DD'),
          ),
          y: thresholdValues,
          type: 'scatter',
          mode: 'lines',
          line: {
            dash: 'dash',
            color: 'red',
            width: 2,
          },
          name: 'Threshold',
          hovertemplate: thresholdHovertemplate,
        },
      ] as Data[]

      // For non-cumulative KPIs, calculate and add YTD average trace
      if (!isCumulative) {
        const ytdAverages = kpiData.project_data.map(
          (_: any, index: number) => {
            const valuesUpToIndex = kpiData.project_data.slice(0, index + 1)
            // Filter out null/undefined values before calculating average
            const validValues = valuesUpToIndex.filter(
              (val: number) => val != null,
            )
            if (validValues.length === 0) return null
            const average =
              validValues.reduce((sum: number, val: number) => sum + val, 0) /
              validValues.length
            return isPercentage ? average : average
          },
        )

        traces.push({
          x: kpiData.dates.map((date: string) =>
            dayjs(date).format('YYYY-MM-DD'),
          ),
          y: ytdAverages,
          type: 'scatter',
          mode: 'lines',
          line: {
            color: 'green',
            width: 2,
          },
          name: 'YTD Average',
          hovertemplate: isPercentage
            ? '%{y:.2%}<extra>YTD Average</extra>'
            : `%{y:.2f}${kpiTypeData.unit || ''}<extra>YTD Average</extra>`,
        })
      }

      return traces
    }

    // Bar chart logic (removed heatmap condition since it's always bar now)
    const hovertemplate =
      kpiTypeData.unit === '%'
        ? '%{y:.2%}<extra></extra>'
        : `%{y:.2f}${kpiTypeData.unit || ''}<extra></extra>`

    const thresholdValues = kpiData.dates.map((date: string) => {
      if (!kpiTypeData?.contracts) return null
      for (const contract of kpiTypeData.contracts) {
        const contractKpi = kpiTypeData.contract_kpis?.find(
          (ck: any) => ck.contract_id === contract.contract_id,
        )
        if (contractKpi?.threshold) {
          const threshold = getKPIThresholdbyDate(
            contractKpi.threshold,
            new Date(date),
          )
          if (threshold !== null) {
            return isPercentage ? threshold : threshold
          }
        }
      }
      return null
    })

    // For non-cumulative KPIs, calculate YTD average
    const ytdAverages = kpiData.project_data.map((_: any, index: number) => {
      const valuesUpToIndex = kpiData.project_data.slice(0, index + 1)
      // Filter out null/undefined values before calculating average
      const validValues = valuesUpToIndex.filter((val: number) => val != null)
      if (validValues.length === 0) return null
      const average =
        validValues.reduce((sum: number, val: number) => sum + val, 0) /
        validValues.length
      return isPercentage ? average : average
    })

    return [
      {
        x: kpiData.dates.map((date: string) =>
          dayjs(date).format('YYYY-MM-DD'),
        ),
        y: kpiData.project_data,
        type: 'bar',
        name: 'Performance',
        hovertemplate,
        marker: {
          color: 'rgba(34, 139, 230, 0.4)', // #228BE6 with 40% opacity
        },
      },
      {
        x: kpiData.dates.map((date: string) =>
          dayjs(date).format('YYYY-MM-DD'),
        ),
        y: thresholdValues,
        type: 'scatter',
        mode: 'lines',
        line: {
          dash: 'dash',
          color: 'red',
          width: 2,
        },
        name: 'Threshold',
        hovertemplate: hovertemplate,
      },
      {
        x: kpiData.dates.map((date: string) =>
          dayjs(date).format('YYYY-MM-DD'),
        ),
        y: ytdAverages,
        type: 'scatter',
        mode: 'lines',
        line: {
          color: '#228BE6', // Same blue as bars but fully opaque
          width: 2,
        },
        name: 'YTD Average',
        hovertemplate: isPercentage
          ? '%{y:.2%}<extra>YTD Average</extra>'
          : `%{y:.2f}${kpiTypeData.unit || ''}<extra>YTD Average</extra>`,
      },
    ] as Data[]
  }

  const parseAnnualData = (data: any, kpiTypeData: any) => {
    if (!data?.length || !data[0]?.data) {
      return { data: [], layout: {} }
    }

    const kpiData = data[0].data
    const isPercentage = kpiTypeData?.unit === '%'
    const isCumulative = kpiTypeData?.aggregation_method === 'sum'

    // Group data by year and calculate totals/averages
    const yearlyData: { [key: string]: { sum: number; count: number } } = {}

    kpiData.dates.forEach((date: string, idx: number) => {
      const year = dayjs(date).year().toString()
      if (!yearlyData[year]) {
        yearlyData[year] = { sum: 0, count: 0 }
      }
      // Only include non-null values
      if (kpiData.project_data[idx] != null) {
        yearlyData[year].sum += kpiData.project_data[idx]
        yearlyData[year].count += 1
      }
    })

    // Calculate values for each year (total for sum, average for others)
    const years = Object.keys(yearlyData).sort()
    const values = years.map((year) => {
      const { sum, count } = yearlyData[year]
      return isCumulative ? sum : count > 0 ? sum / count : 0
    })

    // Get threshold values for each year
    const thresholds = years.map((year) => {
      if (!kpiTypeData?.contracts) return null
      const yearStart = new Date(parseInt(year), 0, 1)

      for (const contract of kpiTypeData.contracts) {
        const contractKpi = kpiTypeData.contract_kpis?.find(
          (ck: any) => ck.contract_id === contract.contract_id,
        )
        if (contractKpi?.threshold) {
          const threshold = getKPIThresholdbyDate(
            contractKpi.threshold,
            yearStart,
          )
          if (threshold !== null) {
            return threshold
          }
        }
      }
      return null
    })

    const hovertemplate = isPercentage
      ? '%{y:.2%}<extra></extra>'
      : `%{y:.2f}${kpiTypeData.unit || ''}<extra></extra>`

    const thresholdHovertemplate = isPercentage
      ? '%{y:.2%}<extra>Threshold</extra>'
      : `%{y:.2f}${kpiTypeData.unit || ''}<extra>Threshold</extra>`

    return {
      data: [
        {
          x: years,
          y: values,
          type: 'bar' as const,
          name: isCumulative ? 'Annual Total' : 'Annual Average',
          hovertemplate,
        },
        {
          x: years,
          y: thresholds,
          type: 'scatter' as const,
          mode: 'lines+markers',
          line: { dash: 'dash', color: 'red', width: 2 },
          marker: { color: 'red', size: 8, symbol: 'circle' },
          name: 'Threshold',
          hovertemplate: thresholdHovertemplate,
        },
      ],
      layout: {
        xaxis: {
          type: 'category',
        },
        yaxis: {
          tickformat: isPercentage ? ',.0%' : ',.0f',
          autorange: true,
          title: kpiTypeData.unit
            ? `${isCumulative ? 'Annual Total' : 'Annual Average'} (${
                kpiTypeData.unit
              })`
            : isCumulative
              ? 'Annual Total'
              : 'Annual Average',
        },
        margin: { t: 10, r: 10, b: 30, l: 50 },
        showlegend: true,
        legend: {
          orientation: 'h',
          yanchor: 'bottom',
          y: 1.02,
          xanchor: 'right',
          x: 1,
        },
      },
    }
  }

  if (kpiLoading) return <PageLoader />

  if (!kpiTypeData) {
    return (
      <Container fluid pt="md">
        <Text>KPI type not found.</Text>
      </Container>
    )
  }

  return (
    <Container fluid pt="md">
      <Stack p="sm">
        <Title order={1}>{kpiTypeData.name_long}</Title>
        <Text>{kpiTypeData.description || ''}</Text>

        <Grid>
          <Grid.Col span={8}>
            <BarAndHeatmapCard
              parsedData={
                filteredData ? parseData(filteredData, kpiTypeData) : undefined
              }
              isLoading={kpiDataLoading}
              kpiTypeData={kpiTypeData}
              selectedYear={selectedYear}
              setSelectedYear={setSelectedYear}
              yearOptions={yearOptions}
            />

            <Box mt="md">
              <AnnualAveragesCard
                // @ts-expect-error manually ignoring for now
                parsedData={parseAnnualData(allKPIData, kpiTypeData)}
                isLoading={kpiDataLoading}
                kpiTypeData={kpiTypeData}
              />
            </Box>
          </Grid.Col>

          {/* Right side - Contract Information */}
          <Grid.Col span={4}>
            {kpiTypeData.contracts.map((contract) => (
              <Paper key={contract.contract_id} withBorder p="md" mb="md">
                <Stack>
                  {/* Contract Header */}
                  <Stack gap="xs" mb="md">
                    <Group justify="space-between">
                      <Text fw={500}>Contract Counterparty:</Text>
                      <Text>{contract.name_long}</Text>
                    </Group>
                    <Group justify="space-between">
                      <Text fw={500}>Executed:</Text>
                      <Text>
                        {dayjs(contract.execution_date).format('M/D/YYYY')}
                      </Text>
                    </Group>
                  </Stack>

                  {/* Contract Document Preview */}
                  <Stack gap="xs" mb="md">
                    {contract.document_url || contract.s3_key ? (
                      <Stack>
                        <iframe
                          src={`${
                            contract.document_url ||
                            (contract.s3_key
                              ? `https://proximal-am-documents.s3.amazonaws.com/${contract.s3_key}`
                              : '')
                          }#toolbar=0`}
                          style={{
                            width: '100%',
                            height: '300px',
                            border: '1px solid #eee',
                            borderRadius: '4px',
                          }}
                          title="Contract Preview"
                        />
                        <Button
                          variant="light"
                          size="sm"
                          onClick={() => {
                            const url =
                              contract.document_url ||
                              (contract.s3_key
                                ? `https://proximal-am-documents.s3.amazonaws.com/${contract.s3_key}`
                                : null)
                            if (url) window.open(url, '_blank')
                          }}
                        >
                          Open Full Document
                        </Button>
                      </Stack>
                    ) : (
                      <Text color="dimmed">No document available</Text>
                    )}
                  </Stack>

                  {/* Contract Details Tabs */}
                  <Tabs defaultValue="threshold">
                    <Tabs.List grow>
                      <Tabs.Tab value="threshold">Threshold</Tabs.Tab>
                      <Tabs.Tab value="remedies">Remedies</Tabs.Tab>
                      <Tabs.Tab value="recordKeeping">Claim</Tabs.Tab>
                    </Tabs.List>

                    <Tabs.Panel value="threshold" pt="md">
                      {kpiTypeData.contract_kpis
                        .filter((ck) => ck.contract_id === contract.contract_id)
                        .map((contractKpi) => (
                          <Stack
                            key={`${contractKpi.contract_id}-thresholds`}
                            gap="xs"
                          >
                            <Title order={3}>Performance Thresholds</Title>

                            {/* Add mode information */}
                            {(contractKpi.threshold as Threshold)?.mode && (
                              <Text>
                                <Text span fw={500}>
                                  Mode:{' '}
                                </Text>
                                {(contractKpi.threshold as Threshold).mode}
                              </Text>
                            )}

                            <Table striped highlightOnHover>
                              <Table.Thead>
                                <Table.Tr>
                                  <Table.Th>Year</Table.Th>
                                  <Table.Th>
                                    Target{' '}
                                    {kpiTypeData.unit
                                      ? `(${kpiTypeData.unit})`
                                      : ''}
                                  </Table.Th>
                                </Table.Tr>
                              </Table.Thead>
                              <Table.Tbody>
                                {Object.entries(
                                  contractKpi.threshold?.values || {},
                                ).map(([date, value]) => (
                                  <Table.Tr key={date}>
                                    <Table.Td>
                                      {dayjs(date).format('YYYY')}
                                    </Table.Td>
                                    <Table.Td>
                                      {kpiTypeData.unit === '%'
                                        ? value * 100
                                        : value}
                                    </Table.Td>
                                  </Table.Tr>
                                ))}
                              </Table.Tbody>
                            </Table>
                          </Stack>
                        ))}
                    </Tabs.Panel>

                    <Tabs.Panel value="remedies" pt="md">
                      <Stack>
                        <Title order={3}>Liquidated Damages</Title>
                        {kpiTypeData.contract_kpis
                          .filter(
                            (ck) => ck.contract_id === contract.contract_id,
                          )
                          .map((contractKpi) => {
                            if (!contractKpi.liquidated_damages?.description) {
                              return (
                                <Text>No liquidated damages specified</Text>
                              )
                            }

                            return Object.entries(
                              contractKpi.liquidated_damages.description,
                            ).map(([title, content]) => (
                              <Paper key={title} withBorder p="md" mb="xs">
                                <Stack gap="xs">
                                  <Text fw={500} size="lg">
                                    {title}
                                  </Text>
                                  <Text>{content as string}</Text>
                                </Stack>
                              </Paper>
                            ))
                          })}
                      </Stack>
                    </Tabs.Panel>

                    <Tabs.Panel value="recordKeeping" pt="md">
                      <Stack>
                        <Title order={3}>Claims</Title>
                        {kpiTypeData.contract_kpis
                          .filter(
                            (ck) => ck.contract_id === contract.contract_id,
                          )
                          .map((contractKpi) => {
                            if (!contractKpi.claim_howto?.description) {
                              return <Text>No Description Provided</Text>
                            }

                            const { method, timeframe, data_contents } =
                              contractKpi.claim_howto.description

                            return (
                              <Stack key={`${contractKpi.contract_id}-claims`}>
                                {/* Method Section */}
                                <Card withBorder shadow="xs">
                                  <Stack gap="xs">
                                    <Text fw={500} size="lg">
                                      Submission Method
                                    </Text>
                                    <Text>
                                      {method?.type || 'Not specified'}
                                    </Text>
                                    <Text>
                                      {method?.details || 'No details provided'}
                                    </Text>
                                  </Stack>
                                </Card>

                                {/* Timeframe Section */}
                                <Card withBorder shadow="xs">
                                  <Stack gap="xs">
                                    <Text fw={500} size="lg">
                                      Timeframe
                                    </Text>
                                    <Text>{timeframe || 'Not specified'}</Text>
                                  </Stack>
                                </Card>

                                {/* Required Data Section */}
                                <Card withBorder shadow="xs">
                                  <Stack gap="xs">
                                    <Text fw={500} size="lg">
                                      Required Information
                                    </Text>
                                    {data_contents ? (
                                      <List>
                                        {Object.entries(data_contents).map(
                                          ([title, content]) => (
                                            <List.Item key={title}>
                                              <Text fw={500}>{title}:</Text>{' '}
                                              {content as string}
                                            </List.Item>
                                          ),
                                        )}
                                      </List>
                                    ) : (
                                      <Text>
                                        No required information specified
                                      </Text>
                                    )}
                                  </Stack>
                                </Card>
                              </Stack>
                            )
                          })}
                      </Stack>
                    </Tabs.Panel>
                  </Tabs>
                </Stack>
              </Paper>
            ))}
          </Grid.Col>
        </Grid>
      </Stack>
    </Container>
  )
}

export default ProjectKPIContractual
