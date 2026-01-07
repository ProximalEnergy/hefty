import { ProjectTypeEnum } from '@/api/enumerations'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetPortfolioHome } from '@/api/v1/protected/web-application/portfolio/home'
import { useComputedColorScheme, useMantineTheme } from '@mantine/core'
import { useMemo } from 'react'

export function usePortfolioPlotData({
  project,
  portfolioHomeProject,
  time,
}: {
  project: NonNullable<ReturnType<typeof useSelectProject>['data']>
  portfolioHomeProject:
    | NonNullable<ReturnType<typeof useGetPortfolioHome>['data']>[number]
    | undefined
  time: '24h' | '30d'
}) {
  const shortTermData = usePortfolioPlotDataShortTerm({
    project,
    portfolioHomeProject,
  })
  const longTermDataBess = usePortfolioPlotDataLongTermBess({
    portfolioHomeProject,
  })
  const longTermDataPV = usePortfolioPlotDataLongTermPV({
    portfolioHomeProject,
  })

  if (time === '24h') {
    return shortTermData
  }

  // Route to BESS version if no energy_production, otherwise use PV version
  const hasEnergyProduction = Boolean(portfolioHomeProject?.energy_production)
  return hasEnergyProduction ? longTermDataPV : longTermDataBess
}

/**
 * Long-term plot data for BESS projects.
 * Shows State of Health and Cycle Count on primary axis.
 */
function usePortfolioPlotDataLongTermBess({
  portfolioHomeProject,
}: {
  portfolioHomeProject:
    | NonNullable<ReturnType<typeof useGetPortfolioHome>['data']>[number]
    | undefined
}) {
  const theme = useMantineTheme()

  return useMemo(() => {
    // For 30d data, use all available times (daily data)
    const x = portfolioHomeProject?.times || null

    const hasCycleCount = Boolean(portfolioHomeProject?.cycle_count_string)

    const data = !x
      ? []
      : [
          // State of Health (primary axis) - dotted line, no fill
          portfolioHomeProject?.state_of_health
            ? {
                x,
                y: portfolioHomeProject.state_of_health,
                type: 'scatter' as const,
                mode: 'lines' as const,
                line: { color: theme.colors.orange[7], dash: 'dot' as const },
                name: 'State of Health',
              }
            : {},
          // Cycle Count (secondary axis) - filled area
          portfolioHomeProject?.cycle_count_string
            ? {
                x,
                y: portfolioHomeProject.cycle_count_string,
                type: 'scatter' as const,
                mode: 'lines' as const,
                line: { color: theme.colors.violet[7] },
                fill: 'tozeroy' as const,
                fillcolor: theme.colors.violet[7] + '20',
                yaxis: 'y2',
                name: 'Cycle Count',
              }
            : {},
        ].filter((trace) => Object.keys(trace).length > 0)

    const layout: Partial<Plotly.Layout> = {
      xaxis: {
        showticklabels: true,
        gridcolor: 'transparent',
        type: 'date',
        tickformat: '%b %d',
      },
      yaxis: {
        title: {
          text: 'State of Health (%)',
          font: { color: theme.colors.orange[7] },
        },
        overlaying: hasCycleCount ? 'y2' : undefined,
        range: [0, 1.1],
        tickformat: ',.0%',
        gridcolor: 'transparent',
      },
      yaxis2: hasCycleCount
        ? {
            title: {
              text: 'Cycle Count',
              font: { color: theme.colors.violet[7] },
            },
            side: 'right',
            showgrid: false,
            zeroline: false,
          }
        : undefined,
      margin: { l: 50, r: hasCycleCount ? 50 : 0, t: 0, b: 0 },
      showlegend: false,
    }

    const config: Partial<Plotly.Config> = {
      displayModeBar: false,
      staticPlot: true,
    }

    return { data, layout, config, hasData: Boolean(x) }
  }, [portfolioHomeProject, theme.colors])
}

/**
 * Long-term plot data for PV and PV+BESS projects.
 * Shows Energy Production on primary axis and PCS Availability on secondary axis.
 */
function usePortfolioPlotDataLongTermPV({
  portfolioHomeProject,
}: {
  portfolioHomeProject:
    | NonNullable<ReturnType<typeof useGetPortfolioHome>['data']>[number]
    | undefined
}) {
  const theme = useMantineTheme()

  return useMemo(() => {
    // For 30d data, use all available times (daily data)
    const x = portfolioHomeProject?.times || null

    const hasPcsAvailability = Boolean(
      portfolioHomeProject?.pcs_mechanical_availability,
    )

    const data = !x
      ? []
      : [
          // Energy Production (primary axis)
          portfolioHomeProject?.energy_production
            ? {
                x,
                y: portfolioHomeProject.energy_production,
                type: 'scatter' as const,
                mode: 'lines' as const,
                line: { color: theme.colors.green[7] },
                fill: 'tozeroy' as const,
                fillcolor: theme.colors.green[7] + 'a0',
                name: 'Energy Production',
              }
            : {},
          // PCS Mechanical Availability (secondary axis)
          portfolioHomeProject?.pcs_mechanical_availability
            ? {
                x,
                y: portfolioHomeProject.pcs_mechanical_availability,
                type: 'scatter' as const,
                mode: 'lines' as const,
                line: { color: theme.colors.blue[7] },
                fill: 'tozeroy' as const,
                fillcolor: theme.colors.blue[7] + '20',
                yaxis: 'y2',
                name: 'PCS Availability',
              }
            : {},
        ].filter((trace) => Object.keys(trace).length > 0)

    const layout: Partial<Plotly.Layout> = {
      xaxis: {
        showticklabels: true,
        gridcolor: 'transparent',
        type: 'date',
        tickformat: '%b %d',
      },
      yaxis: {
        title: {
          text: 'Energy Production (MWh)',
          font: { color: theme.colors.green[7] },
        },
        overlaying: hasPcsAvailability ? 'y2' : undefined,
        gridcolor: 'transparent',
      },
      yaxis2: hasPcsAvailability
        ? {
            title: {
              text: 'PCS Availability (%)',
              font: { color: theme.colors.blue[7] },
            },
            side: 'right',
            showgrid: false,
            zeroline: false,
            tickformat: ',.0%',
          }
        : undefined,
      margin: {
        l: 50,
        r: hasPcsAvailability ? 50 : 0,
        t: 0,
        b: 0,
      },
      showlegend: false,
    }

    const config: Partial<Plotly.Config> = {
      displayModeBar: false,
      staticPlot: true,
    }

    return { data, layout, config, hasData: Boolean(x) }
  }, [portfolioHomeProject, theme.colors])
}

function usePortfolioPlotDataShortTerm({
  project,
  portfolioHomeProject,
}: {
  project: NonNullable<ReturnType<typeof useSelectProject>['data']>
  portfolioHomeProject:
    | NonNullable<ReturnType<typeof useGetPortfolioHome>['data']>[number]
    | undefined
}) {
  const theme = useMantineTheme()
  const scheme = useComputedColorScheme('dark')

  return useMemo(() => {
    const hasRT = project.has_real_time_data
    const x = hasRT
      ? portfolioHomeProject?.times?.slice(-288)
      : portfolioHomeProject?.times?.slice(0, 288)

    const maxPower = Math.max(project.poi, project.capacity_bess_power_ac || 0)
    const maxLineCfg = {
      color: scheme === 'dark' ? theme.colors.dark[0] : 'black',
      dash: 'dot' as const,
      width: 1,
    }

    const data = !x
      ? []
      : [
          {
            x,
            y: Array(x.length).fill(maxPower),
            type: 'scatter',
            mode: 'lines',
            line: maxLineCfg,
          },
          project.project_type_id === ProjectTypeEnum.BESS ||
          project.project_type_id === ProjectTypeEnum.PVS
            ? {
                x,
                y: Array(x.length).fill(-maxPower),
                type: 'scatter',
                mode: 'lines',
                line: maxLineCfg,
              }
            : {},
          portfolioHomeProject?.meter_active_power
            ? {
                x,
                y: hasRT
                  ? portfolioHomeProject.meter_active_power.slice(-288)
                  : portfolioHomeProject.meter_active_power.slice(0, 288),
                type: 'scatter',
                mode: 'lines',
                line: { color: theme.colors.green[7] },
                fill: 'tozeroy',
                fillcolor: theme.colors.green[7] + 'a0',
              }
            : {},
          portfolioHomeProject?.meter_soc_percent
            ? {
                x,
                y: hasRT
                  ? portfolioHomeProject.meter_soc_percent.slice(-288)
                  : portfolioHomeProject.meter_soc_percent.slice(0, 288),
                type: 'scatter',
                mode: 'lines',
                line: { color: theme.colors.blue[7] },
                fill: 'tozeroy',
                fillcolor: theme.colors.blue[7] + '20',
                yaxis: 'y2',
              }
            : {},
          portfolioHomeProject?.max_charge_power
            ? {
                x,
                y: hasRT
                  ? portfolioHomeProject.max_charge_power.slice(-288)
                  : portfolioHomeProject.max_charge_power.slice(0, 288),
                type: 'scatter',
                mode: 'lines',
                line: { color: theme.colors.orange[7], dash: 'dash' },
              }
            : {},
          portfolioHomeProject?.max_discharge_power
            ? {
                x,
                y: hasRT
                  ? portfolioHomeProject.max_discharge_power.slice(-288)
                  : portfolioHomeProject.max_discharge_power.slice(0, 288),
                type: 'scatter',
                mode: 'lines',
                line: { color: theme.colors.orange[7], dash: 'dash' },
              }
            : {},
          portfolioHomeProject?.expected_power
            ? {
                x,
                y: hasRT
                  ? portfolioHomeProject.expected_power.slice(-288)
                  : portfolioHomeProject.expected_power.slice(0, 288),
                type: 'scatter',
                mode: 'lines',
                line: { color: theme.colors.orange[7] },
                fill: 'none',
              }
            : {},
        ]

    const layout: Partial<Plotly.Layout> = {
      xaxis: { showticklabels: false, gridcolor: 'transparent' },
      yaxis: {
        title: {
          text:
            portfolioHomeProject?.max_charge_power ||
            portfolioHomeProject?.max_discharge_power
              ? `Power (MW)<br><sub style="color: ${theme.colors.orange[7]}; font-size: 10px;">Available Power (MW)</sub>`
              : 'Power (MW)',
          font: { color: theme.colors.green[7] },
        },
        overlaying: 'y2',
        range: [
          project.project_type_id === ProjectTypeEnum.PV ? 0 : maxPower * -1.1,
          maxPower * 1.1,
        ],
        gridcolor: 'transparent',
      },
      yaxis2: portfolioHomeProject?.meter_soc_percent
        ? {
            title: { text: 'SOC', font: { color: theme.colors.blue[7] } },
            range: [-0.1, 1.1],
            side: 'right',
            showgrid: false,
            zeroline: false,
            tickformat: ',.0%',
          }
        : undefined,
      margin: { l: 50, r: 0, t: 0, b: 0 },
      showlegend: false,
    }

    const config: Partial<Plotly.Config> = {
      displayModeBar: false,
      staticPlot: true,
    }

    return { data, layout, config, hasData: Boolean(x) }
  }, [project, portfolioHomeProject, scheme, theme.colors])
}
