import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetPortfolioHome } from '@/api/v1/protected/web-application/portfolio/home'
import { useComputedColorScheme, useMantineTheme } from '@mantine/core'
import { useMemo } from 'react'

export function usePortfolioPlotData({
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
          project.project_type_id === ProjectTypeId.BESS ||
          project.project_type_id === ProjectTypeId.PV_BESS
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
          project.project_type_id === ProjectTypeId.PV ? 0 : maxPower * -1.1,
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
