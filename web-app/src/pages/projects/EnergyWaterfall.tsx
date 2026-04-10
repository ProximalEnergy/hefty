import { ProjectTypeEnum } from '@/api/enumerations'
import { useGetRoundTripEfficiencyV2 } from '@/api/v1/operational/project/kpi_data'
import {
  useGetBessAuxEnergyDailyAvg,
  useGetProjectBessWaterfall,
} from '@/api/v1/protected/web-application/projects/bess-waterfall'
import CustomCard from '@/components/CustomCard'
import { PageTitle } from '@/components/PageTitle'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useProjectFilter } from '@/hooks/custom'
import {
  Alert,
  Box,
  Card,
  Group,
  SegmentedControl,
  SimpleGrid,
  Skeleton,
  Stack,
  Table,
  Text,
  Tooltip,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { IconAlertCircle, IconBolt } from '@tabler/icons-react'
import dayjs from 'dayjs'
import { useMemo, useState } from 'react'
import { useParams, useSearchParams } from 'react-router'

type TableRow = {
  component: string
  energy: number
  lossPercent: number | null
  expectedLoss: number | null
  isSubtotal: boolean
}

const LOSSES_WATERFALL_CARD_INFO =
  'Visual representation of energy losses at each conversion step. ' +
  'Gray bars show normal losses, blue bars are subtotals, ' +
  'and red labels indicate underperforming components.'

const formatWaterfallPercentCell = (
  value: number | null,
  showEfficiency: boolean,
) => {
  if (value === null) {
    return '-'
  }
  const pct = showEfficiency ? 100 + value : value
  return `${pct.toFixed(1)}%`
}

const EnergyWaterfall = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeEnum.BESS, ProjectTypeEnum.PVS],
  })

  const { projectId } = useParams<{ projectId: string }>()
  const [searchParams] = useSearchParams()
  const start = searchParams.get('start')
  const end = searchParams.get('end')

  /** Backend ranges use exclusive `end`; picker stores inclusive end. */
  const apiEnd = useMemo(() => {
    if (!end) return ''
    const d = dayjs(end)
    if (!d.isValid()) return ''
    return d.add(1, 'day').format('YYYY-MM-DD')
  }, [end])

  const [showEfficiency, setShowEfficiency] = useState(true)

  const lossesTableCardInfo = useMemo(
    () =>
      `Detailed breakdown of energy losses with percentages. Bold rows are subtotals, red italic rows exceed expected losses. ${
        showEfficiency
          ? 'Efficiency % shows remaining efficiency after losses'
          : 'Loss % shows change from previous step'
      }.`,
    [showEfficiency],
  )

  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme()
  const subtotalBackgroundColor =
    colorScheme === 'dark' ? theme.colors.dark[7] : theme.colors.gray[1]
  const plotHoverTextColor =
    colorScheme === 'dark' ? 'white' : theme.colors.dark[6]

  const enabled = !!projectId && !!start && !!end && !!apiEnd

  const { ytdStart, ytdEnd } = useMemo(() => {
    const now = new Date()
    const year = now.getFullYear()
    const today = new Date(year, now.getMonth(), now.getDate())
    const tomorrow = new Date(today)
    tomorrow.setDate(tomorrow.getDate() + 1)
    const toYmd = (d: Date) => d.toISOString().slice(0, 10)
    return {
      ytdStart: `${year}-01-01`,
      ytdEnd: toYmd(tomorrow),
    }
  }, [])

  const enabledYtd = !!projectId

  const rtePoi = useGetRoundTripEfficiencyV2({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: start || '',
      end: apiEnd || '',
      rte_type: 'POI',
    },
    queryOptions: {
      enabled,
    },
  })

  const rtePoiNoAux = useGetRoundTripEfficiencyV2({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: start || '',
      end: apiEnd || '',
      rte_type: 'POI_NO_AUX',
    },
    queryOptions: {
      enabled,
    },
  })

  const rteFeeder = useGetRoundTripEfficiencyV2({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: start || '',
      end: apiEnd || '',
      rte_type: 'FEEDER',
    },
    queryOptions: {
      enabled,
    },
  })

  const rteDc = useGetRoundTripEfficiencyV2({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: start || '',
      end: apiEnd || '',
      rte_type: 'DC',
    },
    queryOptions: {
      enabled,
    },
  })

  const bessWaterfall = useGetProjectBessWaterfall({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: start || '',
      end: apiEnd || '',
    },
    queryOptions: {
      enabled,
    },
  })

  const auxEnergyDailyAvg = useGetBessAuxEnergyDailyAvg({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: start || '',
      end: apiEnd || '',
    },
    queryOptions: {
      enabled,
    },
  })

  const rtePoiYtd = useGetRoundTripEfficiencyV2({
    pathParams: { projectId: projectId || '-1' },
    queryParams: { start: ytdStart, end: ytdEnd, rte_type: 'POI' },
    queryOptions: { enabled: enabledYtd },
  })
  const rtePoiNoAuxYtd = useGetRoundTripEfficiencyV2({
    pathParams: { projectId: projectId || '-1' },
    queryParams: { start: ytdStart, end: ytdEnd, rte_type: 'POI_NO_AUX' },
    queryOptions: { enabled: enabledYtd },
  })
  const rteFeederYtd = useGetRoundTripEfficiencyV2({
    pathParams: { projectId: projectId || '-1' },
    queryParams: { start: ytdStart, end: ytdEnd, rte_type: 'FEEDER' },
    queryOptions: { enabled: enabledYtd },
  })
  const rteDcYtd = useGetRoundTripEfficiencyV2({
    pathParams: { projectId: projectId || '-1' },
    queryParams: { start: ytdStart, end: ytdEnd, rte_type: 'DC' },
    queryOptions: { enabled: enabledYtd },
  })
  const auxEnergyDailyAvgYtd = useGetBessAuxEnergyDailyAvg({
    pathParams: { projectId: projectId || '-1' },
    queryParams: { start: ytdStart, end: ytdEnd },
    queryOptions: { enabled: enabledYtd },
  })

  const formatRteValue = (rte?: number | null) => {
    if (rte === null || rte === undefined) {
      return '--'
    }
    return `${(rte * 100).toFixed(1)}%`
  }

  const formatAuxEnergyValue = (val?: number | null) => {
    if (val === null || val === undefined) return '--'
    return `${val.toFixed(1)} MWh`
  }

  const statsCards = [
    {
      title: 'POI RTE',
      value: formatRteValue(rtePoi.data?.rte),
      ytdValue: formatRteValue(rtePoiYtd.data?.rte),
      icon: IconBolt,
      description:
        'Point of Interconnection Round Trip Efficiency - measures efficiency ' +
        'at the point where the system connects to the electrical grid',
      isLoading: rtePoi.isLoading,
      ytdLoading: rtePoiYtd.isLoading,
    },
    {
      title: 'POI RTE No Aux',
      value: formatRteValue(rtePoiNoAux.data?.rte),
      ytdValue: formatRteValue(rtePoiNoAuxYtd.data?.rte),
      icon: IconBolt,
      description:
        'POI Round Trip Efficiency - measures efficiency at the point of ' +
        'interconnection but without auxiliary loads',
      isLoading: rtePoiNoAux.isLoading,
      ytdLoading: rtePoiNoAuxYtd.isLoading,
    },
    {
      title: 'AC MV RTE',
      value: formatRteValue(rteFeeder.data?.rte),
      ytdValue: formatRteValue(rteFeederYtd.data?.rte),
      icon: IconBolt,
      description:
        'Medium Voltage AC Round Trip Efficiency - the AC round trip efficiency ' +
        'measured at the medium voltage feeders',
      isLoading: rteFeeder.isLoading,
      ytdLoading: rteFeederYtd.isLoading,
    },
    {
      title: 'DC String RTE',
      value: formatRteValue(rteDc.data?.rte),
      ytdValue: formatRteValue(rteDcYtd.data?.rte),
      icon: IconBolt,
      description:
        'DC String Round Trip Efficiency - the DC round trip efficiency measured ' +
        'at the strings',
      isLoading: rteDc.isLoading,
      ytdLoading: rteDcYtd.isLoading,
    },
    {
      title: 'Avg aux energy/day',
      value: formatAuxEnergyValue(
        auxEnergyDailyAvg.data?.average_aux_energy_per_day,
      ),
      ytdValue: formatAuxEnergyValue(
        auxEnergyDailyAvgYtd.data?.average_aux_energy_per_day,
      ),
      icon: IconBolt,
      description:
        'Average auxiliary energy consumed per day over the selected date range',
      isLoading: auxEnergyDailyAvg.isLoading,
      ytdLoading: auxEnergyDailyAvgYtd.isLoading,
    },
  ]

  const tableData: TableRow[] = useMemo(() => {
    const data = bessWaterfall.data
    if (!data) {
      return []
    }

    const makeLossRow = (
      component: string,
      loss:
        | {
            energy_loss: number
            efficiency: number
            expected_efficiency: number
          }
        | undefined,
    ): TableRow | null => {
      if (!loss) {
        return null
      }
      const lossPercent = (loss.efficiency - 1) * 100
      const expectedLoss = (loss.expected_efficiency - 1) * 100

      return {
        component,
        energy: loss.energy_loss,
        lossPercent,
        expectedLoss,
        isSubtotal: false,
      }
    }

    const rows: (TableRow | null)[] = [
      {
        component: 'Charge at POI',
        energy: data.charge_at_poi,
        lossPercent: null,
        expectedLoss: null,
        isSubtotal: true,
      },
      makeLossRow('Gen-tie + GSU Loss (Step Down)', data.gen_tie_gsu_step_down),
      makeLossRow('Aux Energy', data.aux_energy),
      makeLossRow('MVT (Step Down) + PCS Loss', data.mvt_step_down_pcs),
      {
        component: 'Charge at Strings',
        energy: data.charge_at_string,
        lossPercent: null,
        expectedLoss: null,
        isSubtotal: true,
      },
      makeLossRow('RTE Loss', data.rte),
      {
        component: 'Discharge at Strings',
        energy: data.discharge_at_string,
        lossPercent: null,
        expectedLoss: null,
        isSubtotal: true,
      },
      makeLossRow('PCS + MVT Loss (Step Up)', data.pcs_pvt_step_up),
      makeLossRow('GSU Loss (Step Up) + Gen-tie', data.gen_tie_gsu_step_up),
      {
        component: 'Discharge at POI',
        energy: data.discharge_at_poi,
        lossPercent: null,
        expectedLoss: null,
        isSubtotal: true,
      },
    ]

    return rows.filter((row): row is TableRow => row !== null)
  }, [bessWaterfall.data])

  const waterfallData =
    tableData.length === 0
      ? null
      : {
          measure: tableData.map((item, index) => {
            if (index === 0) return 'absolute'
            if (item.isSubtotal) return 'total'
            return 'relative'
          }),
          x: tableData.map((item) => item.component),
          y: tableData.map((item) => item.energy),
          customdata: tableData.map((item) => [
            item.energy,
            item.lossPercent,
            item.expectedLoss,
          ]),
          hovertemplate: tableData.map((item, index) => {
            if (item.isSubtotal) {
              return (
                '<b>%{x}</b><br>' +
                'Energy: %{customdata[0]:.1f} MWh<br>' +
                '<extra></extra>'
              )
            } else if (index === 0) {
              return (
                '<b>%{x}</b><br>' +
                'Energy: %{customdata[0]:.1f} MWh<br>' +
                '<extra></extra>'
              )
            } else {
              const isUnderperforming =
                item.expectedLoss !== null &&
                item.lossPercent !== null &&
                item.lossPercent < item.expectedLoss

              const titleColor = isUnderperforming ? 'red' : plotHoverTextColor

              if (showEfficiency) {
                return (
                  `<b style="color: ${titleColor};">%{x}</b><br>` +
                  `<span style="color: ${plotHoverTextColor};">Energy: %{customdata[0]:.1f} MWh<br>` +
                  'Efficiency: ' +
                  (100 + (item.lossPercent ?? 0)).toFixed(1) +
                  '%<br>' +
                  'Expected Efficiency: ' +
                  (100 + (item.expectedLoss ?? 0)).toFixed(1) +
                  '%</span><br>' +
                  '<extra></extra>'
                )
              } else {
                return (
                  `<b style="color: ${titleColor};">%{x}</b><br>` +
                  `<span style="color: ${plotHoverTextColor};">Energy: %{customdata[0]:.1f} MWh<br>` +
                  'Loss: %{customdata[1]}%<br>' +
                  'Expected Loss: %{customdata[2]}%</span><br>' +
                  '<extra></extra>'
                )
              }
            }
          }),
        }

  const lossesWaterfallPlotLayout = useMemo((): Partial<Plotly.Layout> => {
    if (tableData.length === 0) {
      return {}
    }
    let cumulative = 0
    const barPositions = tableData.map((item, index) => {
      if (index === 0) {
        cumulative = item.energy
        return item.energy
      }
      if (item.isSubtotal) {
        return cumulative
      }
      cumulative += item.energy
      return cumulative
    })

    return {
      yaxis: {
        title: { text: 'Total Energy (MWh)' },
      },
      xaxis: {
        tickmode: 'array',
        tickvals: tableData.map((_, index) => index),
        ticktext: tableData.map((item, index) => {
          const isUnderperforming =
            item.expectedLoss !== null &&
            item.lossPercent !== null &&
            item.lossPercent < item.expectedLoss

          if (isUnderperforming && !item.isSubtotal && index !== 0) {
            return `<b><span style="color: red;">${item.component}</span></b>`
          }
          return item.component
        }),
      },
      margin: { t: 30 },
      annotations: tableData
        .map((item, index) => {
          const isUnderperforming =
            item.expectedLoss !== null &&
            item.lossPercent !== null &&
            item.lossPercent < item.expectedLoss

          if (!isUnderperforming || item.isSubtotal || index === 0) {
            return null
          }

          const priorIndex = index - 1
          return {
            x: index,
            y: barPositions[priorIndex],
            text: '⚠️ ',
            showarrow: false,
            font: { size: 16 },
            xanchor: 'center' as const,
            yanchor: 'bottom' as const,
          }
        })
        .filter(
          (annotation): annotation is NonNullable<typeof annotation> =>
            annotation !== null,
        ),
      showlegend: true,
      legend: {
        x: 0.5,
        y: 0.02,
        xanchor: 'center',
        yanchor: 'bottom',
        bgcolor: 'transparent',
        bordercolor: 'transparent',
        borderwidth: 0,
        orientation: 'h',
      },
    }
  }, [tableData])

  return (
    <Stack p="md">
      <Box style={{ position: 'relative', width: '100%' }}>
        <PageTitle info="This page visualizes energy losses throughout the power conversion process from grid import to export. The waterfall chart shows cumulative energy at each step, while the table provides detailed loss percentages compared to expected values.">
          Energy Waterfall
        </PageTitle>
        <Box
          style={{
            position: 'absolute',
            left: '50%',
            top: 0,
            transform: 'translateX(-50%)',
          }}
        >
          <AdvancedDatePicker
            defaultRange="last-month"
            includeClearButton={false}
          />
        </Box>
      </Box>

      {enabled && bessWaterfall.error && tableData.length === 0 && (
        <Alert
          icon={<IconAlertCircle size={16} />}
          title="BESS Waterfall Unavailable"
          color="red"
          radius="md"
        >
          Unable to load BESS waterfall data for the selected range. This may be
          due to missing KPI data or insufficient cycles.
        </Alert>
      )}

      {/* Key Metrics Cards */}
      <SimpleGrid cols={{ base: 1, xs: 2, md: 5 }}>
        {statsCards.map((stat, index) => {
          const Icon = stat.icon
          return (
            <Tooltip key={index} label={stat.description} withArrow>
              <Card withBorder p="md" radius="md">
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">
                    {stat.title}
                  </Text>
                  <Icon size="1.2rem" stroke={1.5} />
                </Group>
                <Group justify="space-between" align="flex-end" mt={15}>
                  <Box
                    h={40}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                    }}
                  >
                    {stat.isLoading && enabled ? (
                      <Skeleton height={32} width={120} radius="xl" />
                    ) : (
                      <Text fz={32} fw={700}>
                        {stat.value}
                      </Text>
                    )}
                  </Box>
                  <Box style={{ flexShrink: 0 }}>
                    {stat.ytdLoading && enabledYtd ? (
                      <Skeleton height={20} width={70} radius="sm" />
                    ) : (
                      <Text size="xl" c="dimmed" ta="right">
                        YTD: {stat.ytdValue}
                      </Text>
                    )}
                  </Box>
                </Group>
              </Card>
            </Tooltip>
          )
        })}
      </SimpleGrid>

      <div style={{ marginBottom: '2rem' }}>
        <Group align="flex-start" gap="md">
          <div style={{ flex: 3 }}>
            <CustomCard
              title="Losses Waterfall"
              fill={true}
              info={LOSSES_WATERFALL_CARD_INFO}
            >
              <div style={{ height: '550px' }}>
                {bessWaterfall.isLoading && enabled && (
                  <PlotlyPlot data={[]} layout={{}} isLoading />
                )}
                {!bessWaterfall.isLoading &&
                  enabled &&
                  waterfallData &&
                  tableData.length > 0 && (
                    <PlotlyPlot
                      data={[
                        {
                          type: 'waterfall',
                          name: 'Losses Waterfall',
                          measure: waterfallData.measure,
                          x: waterfallData.x,
                          y: waterfallData.y,
                          customdata: waterfallData.customdata,
                          hovertemplate: waterfallData.hovertemplate,
                          base: 0,
                          marker: { line: { color: 'black', width: 2 } },
                          increasing: { marker: { color: '#808080' } },
                          decreasing: { marker: { color: '#808080' } },
                          totals: { marker: { color: '#1e90ff' } },
                          connector: {
                            line: {
                              color: 'rgb(63, 63, 63)',
                            },
                          },
                          showlegend: false,
                        } as Partial<Plotly.PlotData>,
                        {
                          type: 'scatter',
                          mode: 'markers',
                          x: [null],
                          y: [null],
                          name: 'Total Energy',
                          marker: { color: '#1e90ff', size: 12 },
                          showlegend: true,
                        },
                        {
                          type: 'scatter',
                          mode: 'markers',
                          x: [null],
                          y: [null],
                          name: 'Energy Losses',
                          marker: { color: '#808080', size: 12 },
                          showlegend: true,
                        },
                      ]}
                      layout={lossesWaterfallPlotLayout}
                    />
                  )}
              </div>
            </CustomCard>
          </div>

          <div style={{ flex: 2 }}>
            <CustomCard
              title="Losses Table"
              fill={true}
              info={lossesTableCardInfo}
              headerChildren={
                <Group gap="xs">
                  <SegmentedControl
                    value={showEfficiency ? 'efficiency' : 'loss'}
                    onChange={(value) =>
                      setShowEfficiency(value === 'efficiency')
                    }
                    data={[
                      { label: 'Efficiency', value: 'efficiency' },
                      { label: 'Loss', value: 'loss' },
                    ]}
                    size="sm"
                  />
                </Group>
              }
            >
              {bessWaterfall.isLoading && enabled && (
                <Skeleton height={200} mt="sm" />
              )}
              {!bessWaterfall.isLoading && enabled && tableData.length > 0 && (
                <Table highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Component</Table.Th>
                      <Table.Th style={{ textAlign: 'right' }}>
                        Energy (MWh)
                      </Table.Th>
                      <Table.Th style={{ textAlign: 'right' }}>
                        {showEfficiency
                          ? 'Actual Efficiency (%)'
                          : 'Actual Loss (%)'}
                      </Table.Th>
                      <Table.Th style={{ textAlign: 'right' }}>
                        {showEfficiency
                          ? 'Expected Efficiency (%)'
                          : 'Expected Loss (%)'}
                      </Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {tableData.map((item, index) => {
                      const isUnderperforming =
                        item.expectedLoss !== null &&
                        item.lossPercent !== null &&
                        item.lossPercent < item.expectedLoss
                      const isSubtotal = item.isSubtotal
                      const isFirstItem = index === 0
                      const actualPercentLabel = formatWaterfallPercentCell(
                        item.lossPercent,
                        showEfficiency,
                      )
                      const expectedPercentLabel = formatWaterfallPercentCell(
                        item.expectedLoss,
                        showEfficiency,
                      )

                      return (
                        <Table.Tr
                          key={index}
                          style={{
                            fontWeight:
                              isSubtotal || isFirstItem ? 'bold' : 'normal',
                            backgroundColor:
                              isSubtotal || isFirstItem
                                ? subtotalBackgroundColor
                                : 'transparent',
                            color: isUnderperforming
                              ? 'var(--mantine-color-red-6)'
                              : 'inherit',
                            fontStyle: isUnderperforming ? 'italic' : 'normal',
                          }}
                        >
                          <Table.Td>{item.component}</Table.Td>
                          <Table.Td style={{ textAlign: 'right' }}>
                            {item.energy.toFixed(1)}
                          </Table.Td>
                          <Table.Td style={{ textAlign: 'right' }}>
                            {actualPercentLabel}
                          </Table.Td>
                          <Table.Td style={{ textAlign: 'right' }}>
                            {expectedPercentLabel}
                          </Table.Td>
                        </Table.Tr>
                      )
                    })}
                  </Table.Tbody>
                </Table>
              )}
            </CustomCard>
          </div>
        </Group>
      </div>
    </Stack>
  )
}

export default EnergyWaterfall
