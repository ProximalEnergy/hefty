import { ProjectTypeId } from '@/api/v1/operational/project_types'
import CustomCard from '@/components/CustomCard'
import { PageTitle } from '@/components/PageTitle'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useProjectFilter } from '@/hooks/custom'
import {
  Alert,
  Card,
  Group,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Tooltip,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { IconAlertCircle, IconBolt, IconInfoCircle } from '@tabler/icons-react'
import { useState } from 'react'

const EnergyWaterfall = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeId.BESS, ProjectTypeId.PV_BESS],
  })

  const [showEfficiency, setShowEfficiency] = useState(true)

  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme()
  const subtotalBackgroundColor =
    colorScheme === 'dark' ? theme.colors.dark[7] : theme.colors.gray[1]

  // Stats cards data
  const statsCards = [
    {
      title: 'POI RTE',
      value: '82.0%',
      ytdValue: '83.3%',
      icon: IconBolt,
      description:
        'Point of Interconnection Round Trip Efficiency - measures efficiency at the point where the system connects to the electrical grid',
    },
    {
      title: 'HV Meter RTE',
      value: '82.6%',
      ytdValue: '82.9%',
      icon: IconBolt,
      description:
        'High Voltage Meter Round Trip Efficiency - measures efficiency at the high voltage metering point',
    },
    {
      title: 'MV AC RTE',
      value: '85.7%',
      ytdValue: '86.9%',
      icon: IconBolt,
      description:
        'Medium Voltage AC Round Trip Efficiency - measures the efficiency of medium voltage alternating current conversion',
    },
    {
      title: 'PCS RTE',
      value: '86.3%',
      ytdValue: '87.1%',
      icon: IconBolt,
      description:
        'Power Conversion System Round Trip Efficiency - measures the efficiency of the power conversion system',
    },
    {
      title: 'DC RTE',
      value: '89.0%',
      ytdValue: '89.4%',
      icon: IconBolt,
      description:
        'DC Round Trip Efficiency - measures the efficiency of direct current power conversion and storage',
    },
  ]

  // Hardcoded tabular data
  const tableData = [
    {
      component: 'Charge at POI',
      energy: 581,
      lossPercent: null,
      expectedLoss: null,
      isSubtotal: false,
    },
    {
      component: 'Gen-Tie Loss (In)',
      energy: -2.2,
      lossPercent: -0.4, // 99.6% - 100% = -0.4%
      expectedLoss: -0.5, // 99.5% - 100% = -0.5%
      isSubtotal: false,
    },
    {
      component: 'GSU Loss (Step Down)',
      energy: -2.1,
      lossPercent: -0.4, // 99.6% - 100% = -0.4%
      expectedLoss: -0.5, // 99.5% - 100% = -0.5%
      isSubtotal: false,
    },
    {
      component: 'Aux Energy (In)',
      energy: -8.5,
      lossPercent: -1.5, // 98.5% - 100% = -1.5%
      expectedLoss: -1.0, // 99.0% - 100% = -1.0%
      isSubtotal: false,
    },
    {
      component: 'MV Circuit Loss (In)',
      energy: -1.9,
      lossPercent: -0.3, // 99.7% - 100% = -0.3%
      expectedLoss: -0.5, // 99.5% - 100% = -0.5%
      isSubtotal: false,
    },
    {
      component: 'MVT Loss (Step Down)',
      energy: -1.8,
      lossPercent: -0.3, // 99.7% - 100% = -0.3%
      expectedLoss: -0.5, // 99.5% - 100% = -0.5%
      isSubtotal: false,
    },
    {
      component: 'PCS Loss (AC to DC)',
      energy: -8.3,
      lossPercent: -1.5, // 98.5% - 100% = -1.5%
      expectedLoss: -2.0, // 98.0% - 100% = -2.0%
      isSubtotal: false,
    },
    {
      component: 'Charge at Battery',
      energy: 556.2,
      lossPercent: null,
      expectedLoss: null,
      isSubtotal: true,
    },
    {
      component: 'RTE Loss',
      energy: -61,
      lossPercent: -11.0, // 89.0% - 100% = -11.0%
      expectedLoss: -10.0, // 90.0% - 100% = -10.0%
      isSubtotal: false,
    },
    {
      component: 'Discharge at Battery',
      energy: 495.2,
      lossPercent: null,
      expectedLoss: null,
      isSubtotal: true,
    },
    {
      component: 'PCS Loss (DC to AC)',
      energy: -7.8,
      lossPercent: -1.6, // 98.4% - 100% = -1.6%
      expectedLoss: -2.0, // 98.0% - 100% = -2.0%
      isSubtotal: false,
    },
    {
      component: 'MVT Loss (Step Up)',
      energy: -1.8,
      lossPercent: -0.4, // 99.6% - 100% = -0.4%
      expectedLoss: -0.5, // 99.5% - 100% = -0.5%
      isSubtotal: false,
    },
    {
      component: 'MV Circuit Loss (Out)',
      energy: -1.8,
      lossPercent: -0.4, // 99.6% - 100% = -0.4%
      expectedLoss: -0.5, // 99.5% - 100% = -0.5%
      isSubtotal: false,
    },
    {
      component: 'Aux Energy (Out)',
      energy: -4.1,
      lossPercent: -0.8, // 99.2% - 100% = -0.8%
      expectedLoss: -1.0, // 99.0% - 100% = -1.0%
      isSubtotal: false,
    },
    {
      component: 'GSU Loss (Step Up)',
      energy: -1.7,
      lossPercent: -0.4, // 99.6% - 100% = -0.4%
      expectedLoss: -0.5, // 99.5% - 100% = -0.5%
      isSubtotal: false,
    },
    {
      component: 'Gen-Tie Loss (Out)',
      energy: -1.5,
      lossPercent: -0.3, // 99.7% - 100% = -0.3%
      expectedLoss: -0.5, // 99.5% - 100% = -0.5%
      isSubtotal: false,
    },
    {
      component: 'Discharge at POI',
      energy: 476.5,
      lossPercent: null,
      expectedLoss: null,
      isSubtotal: true,
    },
  ]

  // Hardcoded waterfall data
  const waterfallData = {
    measure: tableData.map((item, index) => {
      if (index === 0) return 'absolute' // First item is always absolute
      if (item.isSubtotal) return 'total' // Subtotal items
      return 'relative' // All other items
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
        // For subtotals, don't show Loss % since it's not relevant
        return (
          '<b>%{x}</b><br>' +
          'Energy: %{customdata[0]} MWh<br>' +
          '<extra></extra>'
        )
      } else if (index === 0) {
        // For the first item (Charge at POI), only show energy since it's the starting point
        return (
          '<b>%{x}</b><br>' +
          'Energy: %{customdata[0]} MWh<br>' +
          '<extra></extra>'
        )
      } else {
        // For regular items, show Loss/Efficiency % and Expected Loss/Efficiency %
        const isUnderperforming =
          item.expectedLoss !== null &&
          item.lossPercent !== null &&
          item.lossPercent < item.expectedLoss

        const titleColor = isUnderperforming ? 'red' : 'white'

        if (showEfficiency) {
          return (
            `<b style="color: ${titleColor};">%{x}</b><br>` +
            '<span style="color: white;">Energy: %{customdata[0]} MWh<br>' +
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
            '<span style="color: white;">Energy: %{customdata[0]} MWh<br>' +
            'Loss: %{customdata[1]}%<br>' +
            'Expected Loss: %{customdata[2]}%</span><br>' +
            '<extra></extra>'
          )
        }
      }
    }),
  }

  return (
    <Stack p="md">
      <PageTitle info="This page visualizes energy losses throughout the power conversion process from grid import to export. The waterfall chart shows cumulative energy at each step, while the table provides detailed loss percentages compared to expected values.">
        Energy Waterfall
      </PageTitle>

      <Alert
        icon={<IconAlertCircle size={16} />}
        title="Placeholder Data"
        color="yellow"
        radius="md"
      >
        Some critical tags are missing from the project SCADA Feed. We're
        working with the SCADA vendor to get the tags. Showing placeholder data
        until the tags are available, including but not limited to: BESS MV
        Circuit Active Power, BESS Meter Energy Charged Total, BESS Meter Energy
        Discharged Total, and BESS Aux Energy Total.
      </Alert>

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
                  <Text fz={32} fw={700}>
                    {stat.value}
                  </Text>
                  <Text size="xl" c="dimmed" ta="right">
                    YTD: {stat.ytdValue}
                  </Text>
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
              headerChildren={
                <Group gap="xs">
                  <AdvancedDatePicker
                    defaultRange="last-month"
                    includeClearButton={false}
                  />
                  <Tooltip
                    label="Visual representation of energy losses at each conversion step. Gray bars show normal losses, blue bars are subtotals, and red labels indicate underperforming components."
                    multiline
                    w={250}
                    withArrow
                  >
                    <IconInfoCircle
                      size={16}
                      style={{
                        cursor: 'help',
                        color: 'var(--mantine-color-dimmed)',
                      }}
                    />
                  </Tooltip>
                </Group>
              }
            >
              <div style={{ height: '550px' }}>
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
                  layout={{
                    // title: 'Losses from Grid Import to Export',
                    yaxis: {
                      title: { text: 'Total Energy (MWh)' },
                      range: [450, 590],
                    },
                    xaxis: {
                      tickmode: 'array',
                      tickvals: tableData.map((_, index) => index),
                      ticktext: tableData.map((item, index) => {
                        const isUnderperforming =
                          item.expectedLoss !== null &&
                          item.lossPercent !== null &&
                          item.lossPercent < item.expectedLoss

                        if (
                          isUnderperforming &&
                          !item.isSubtotal &&
                          index !== 0
                        ) {
                          return `<b><span style="color: red;">${item.component}</span></b>`
                        }
                        return item.component
                      }),
                    },
                    margin: { t: 30 },
                    annotations: (() => {
                      // Calculate the actual y-positions for each bar in the waterfall
                      let cumulative = 0
                      const barPositions = tableData.map((item, index) => {
                        if (index === 0) {
                          // First bar (absolute) - starts at its value
                          cumulative = item.energy
                          return item.energy
                        } else if (item.isSubtotal) {
                          // Subtotal bars show the current cumulative total
                          return cumulative
                        } else {
                          // Relative bars - add to cumulative and return the new total
                          cumulative += item.energy
                          return cumulative
                        }
                      })

                      return tableData
                        .map((item, index) => {
                          const isUnderperforming =
                            item.expectedLoss !== null &&
                            item.lossPercent !== null &&
                            item.lossPercent < item.expectedLoss

                          if (
                            !isUnderperforming ||
                            item.isSubtotal ||
                            index === 0
                          ) {
                            return null
                          }

                          return {
                            x: index, // Use index as x position
                            y: barPositions[index - 1], // Position above the bar
                            text: '⚠️ ',
                            showarrow: false,
                            font: { size: 16 },
                            xanchor: 'center' as const,
                            yanchor: 'bottom' as const,
                          }
                        })
                        .filter(
                          (
                            annotation,
                          ): annotation is NonNullable<typeof annotation> =>
                            annotation !== null,
                        )
                    })(),
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
                  }}
                />
              </div>
            </CustomCard>
          </div>

          <div style={{ flex: 2 }}>
            <CustomCard
              title="Losses Table"
              fill={true}
              headerChildren={
                <Group gap="xs">
                  <Tooltip
                    label={`Detailed breakdown of energy losses with percentages. Bold rows are subtotals, red italic rows exceed expected losses. ${showEfficiency ? 'Efficiency % shows remaining efficiency after losses' : 'Loss % shows change from previous step'}.`}
                    multiline
                    w={280}
                    withArrow
                  >
                    <IconInfoCircle
                      size={16}
                      style={{
                        cursor: 'help',
                        color: 'var(--mantine-color-dimmed)',
                      }}
                    />
                  </Tooltip>
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
                      item.lossPercent < item.expectedLoss
                    const isSubtotal = item.isSubtotal
                    const isFirstItem = index === 0

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
                          {item.energy}
                        </Table.Td>
                        <Table.Td style={{ textAlign: 'right' }}>
                          {item.lossPercent !== null
                            ? showEfficiency
                              ? `${(100 + item.lossPercent).toFixed(1)}%`
                              : `${item.lossPercent}%`
                            : '-'}
                        </Table.Td>
                        <Table.Td style={{ textAlign: 'right' }}>
                          {item.expectedLoss !== null
                            ? showEfficiency
                              ? `${(100 + item.expectedLoss).toFixed(1)}%`
                              : `${item.expectedLoss}%`
                            : '-'}
                        </Table.Td>
                      </Table.Tr>
                    )
                  })}
                </Table.Tbody>
              </Table>
            </CustomCard>
          </div>
        </Group>
      </div>
    </Stack>
  )
}

export default EnergyWaterfall
