import { useGetWaterfall } from '@/api/v1/operational/project/waterfall'
import { PageLoader } from '@/components/Loading'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useMantineTheme } from '@mantine/core'
import { useMemo } from 'react'
import { useParams } from 'react-router'

const LOSS_WATERFALL_BAR_BUDGETED = 'Budgeted'
const LOSS_WATERFALL_BAR_WEATHER_ADJ = 'Weather adjustment'
const LOSS_WATERFALL_BAR_PV_EXPECTED = 'PV Expected'
const LOSS_WATERFALL_BAR_CURTAILMENT = 'Curtailment'
const LOSS_WATERFALL_BAR_PV_OUTPUT = 'PV Energy Output'

const LossWaterfall = ({
  level,
  startQuery,
  endQuery,
}: {
  level: string
  startQuery: string
  endQuery: string
}) => {
  const theme = useMantineTheme()
  const { projectId } = useParams<{ projectId: string }>()

  const data = useGetWaterfall({
    pathParams: { projectId: projectId || '-1' },
    queryParams: { level: level, start: startQuery, end: endQuery },
    queryOptions: {
      enabled: !!projectId && !!startQuery && !!endQuery,
    },
  })

  const names = data.data?.name
  const measures = data.data?.measure
  const values = data.data?.value

  const hovertemplate = useMemo(() => {
    if (!names?.length || !measures?.length) return undefined
    if (names.length !== measures.length) return undefined
    return names.map((_, i) => {
      const m = measures[i]
      if (m === 'relative') {
        return '<b>%{x}</b><br>%{delta:.2f} MWh<extra></extra>'
      }
      return '<b>%{x}</b><br>%{final:.2f} MWh<extra></extra>'
    })
  }, [names, measures])

  if (data.isLoading) return <PageLoader />

  const barColors = names?.length
    ? names.map((barName, i) => {
        if (
          barName === LOSS_WATERFALL_BAR_BUDGETED ||
          barName === LOSS_WATERFALL_BAR_PV_EXPECTED ||
          barName === LOSS_WATERFALL_BAR_PV_OUTPUT
        ) {
          return theme.colors.blue[6]
        }
        if (barName === LOSS_WATERFALL_BAR_WEATHER_ADJ) {
          return theme.colors.cyan[6]
        }
        if (barName === LOSS_WATERFALL_BAR_CURTAILMENT) {
          return theme.colors.orange[6]
        }
        const measure = measures?.[i]
        const y = values?.[i]
        if (measure === 'relative' && typeof y === 'number' && y < 0) {
          return theme.colors.red[6]
        }
        return theme.colors.teal[6]
      })
    : undefined

  return (
    <PlotlyPlot
      data={[
        {
          type: 'waterfall',
          name: 'Loss Waterfall',
          measure: data.data?.measure,
          x: data.data?.name,
          y: data.data?.value,
          marker: {
            line: { color: 'black', width: 20 },
            ...(barColors ? { color: barColors } : {}),
          },
          connector: {
            line: {
              color: 'rgb(63, 63, 63)',
            },
          },
          ...(hovertemplate ? { hovertemplate } : {}),
        } as Partial<Plotly.PlotData>,
      ]}
      layout={{
        yaxis: {
          title: { text: 'MWh' },
        },

        margin: { t: 30 },
      }}
      error={data.error}
    />
  )
}

export default LossWaterfall
