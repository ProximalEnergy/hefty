import { traceColors } from '@/components/plots/PlotlyPlotUtils'
import { GISContext } from '@/contexts/GISContext'
import {
  Center,
  LoadingOverlay,
  Stack,
  Text,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { IconAlertTriangle } from '@tabler/icons-react'
import { AxiosError } from 'axios'
import chroma from 'chroma-js'
import { merge } from 'lodash'
import Plotly, {
  Config,
  Data,
  Layout,
  PlotMouseEvent,
  PlotRelayoutEvent,
} from 'plotly.js/dist/plotly-custom.min.js'
import { useContext } from 'react'
import createPlotlyComponent from 'react-plotly.js/factory'

const Plot = createPlotlyComponent(Plotly)

type ErrorData = {
  detail: string
}

const PlotlyPlot = ({
  data = [],
  layout = {},
  config = {},
  colorscale,
  isLoading,
  error,
  onClick,
  onRelayout,
}: {
  data?: Data[]
  layout?: Partial<Layout>
  config?: Partial<Config>
  colorscale?: string
  isLoading?: boolean
  error?: AxiosError<ErrorData> | null
  onClick?: (event: Readonly<PlotMouseEvent>) => void
  onRelayout?: (event: Readonly<PlotRelayoutEvent>) => void
}) => {
  //////////////////////////////////////////////////////////////////////////////
  /////// If the plot you're looking for is not working, go check //////////////
  /////// that the plot type exists in the build-plotly-custom.js file /////////
  //////////////////////////////////////////////////////////////////////////////

  const theme = useMantineTheme()
  const computedColorScheme = useComputedColorScheme('dark')
  const context = useContext(GISContext)

  // Ensure that the GISContext is provided
  if (!context) {
    throw new Error('GISContext is not provided')
  }

  const { colorsGoodBad } = context

  if (isLoading) {
    return <LoadingOverlay visible />
  }

  if (error) {
    return (
      <Center h={'100%'} w={'100%'}>
        <Stack align="center">
          <IconAlertTriangle size={48} />
          <Text>{error.response?.data.detail}</Text>
        </Stack>
      </Center>
    )
  }

  const gridAlpha = 0.25
  const zeroAlpha = 0.75

  const layoutSettings = {
    fontcolor: computedColorScheme === 'dark' ? theme.colors.dark[0] : 'black',
    gridcolor:
      computedColorScheme === 'dark'
        ? chroma(theme.colors.dark[0]).alpha(gridAlpha).hex()
        : chroma(theme.black).alpha(gridAlpha).hex(),
    zerolinecolor:
      computedColorScheme === 'dark'
        ? chroma(theme.colors.dark[0]).alpha(zeroAlpha).hex()
        : chroma(theme.black).alpha(zeroAlpha).hex(),
  }

  const yaxisTemplate = {
    gridcolor: layoutSettings.gridcolor,
    zerolinecolor: layoutSettings.zerolinecolor,
    automargin: true,
    showspikes: false,
  }

  const layoutTemplate: Partial<Layout> = {
    autosize: true,
    margin: {
      b: 50,
      t: 20,
      pad: 0,
    },
    legend: {
      yref: 'container',
      yanchor: 'bottom',
      xanchor: 'center',
      x: 0.5,
      y: 0,
      orientation: 'h',
    },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: {
      color: layoutSettings.fontcolor,
      family: theme.fontFamily,
    },
    xaxis: {
      gridcolor: layoutSettings.gridcolor,
      automargin: true,
      spikemode: 'across',
      spikethickness: -2, // https://github.com/plotly/plotly.js/issues/3042
      spikecolor: layoutSettings.fontcolor,
    },
    yaxis: yaxisTemplate,
    yaxis2: yaxisTemplate,
    yaxis3: yaxisTemplate,
    colorway: traceColors(theme),
    hovermode: 'x',
    modebar: {
      bgcolor:
        computedColorScheme === 'dark'
          ? theme.colors.dark[7]
          : theme.colors.gray[1],
    },
  }

  // https://plotly.com/javascript/reference/layout/
  const configTemplate: Partial<Config> = {
    displaylogo: false,
    // NOTE: ModeBar coloring is defined in index.css
    modeBarButtons: [
      [
        'zoom2d',
        'pan2d',
        'hoverClosestCartesian',
        'hoverCompareCartesian',
        'resetViews',
        'toImage',
      ],
    ],
    responsive: true,
    doubleClick: false,
    showTips: false,
  }

  if (colorscale && data) {
    if (colorscale === 'primary') {
      const primary =
        theme.colors[theme.primaryColor][computedColorScheme === 'dark' ? 7 : 7]
      const low =
        computedColorScheme === 'dark'
          ? theme.colors.dark[7]
          : theme.colors.gray[0]
      const colors = chroma.scale([low, primary]).mode('rgb').colors(10)
      const colorscale: [number, string][] = colors.map((color, i) => [
        i / (colors.length - 1),
        color,
      ])
      data = data.map((d) => ({ ...d, colorscale: colorscale }))
    } else if (colorscale === 'good-bad') {
      const colors = chroma
        .scale(colorsGoodBad.map((c) => c.value))
        .mode('rgb')
        .colors(10)
      const colorscale: [number, string][] = colors.map((color, i) => [
        i / (colors.length - 1),
        color,
      ])
      data = data.map((d) => ({ ...d, colorscale: colorscale }))
    } else if (colorscale === 'good-bad-reversed') {
      const reversedColors = [...colorsGoodBad].reverse()
      const colors = chroma
        .scale(reversedColors.map((c) => c.value))
        .mode('rgb')
        .colors(10)
      const colorscale: [number, string][] = colors.map((color, i) => [
        i / (colors.length - 1),
        color,
      ])
      data = data.map((d) => ({ ...d, colorscale: colorscale }))
    } else if (colorscale === 'tracker') {
      const trackerColors = [
        { id: 0, value: '#b5d6e0' }, // Sunrise (-60)
        { id: 1, value: '#ffef7a' }, // Mid-morning (-30)
        { id: 2, value: '#f7c16a' }, // Noon (0)
        { id: 3, value: '#ff6b3e' }, // Mid-afternoon (30)
        { id: 4, value: '#27214e' }, // Sunset (60)
      ]
      const colors = chroma
        .scale(trackerColors.map((c) => c.value))
        .mode('rgb')
        .colors(10)
      const colorscale: [number, string][] = colors.map((color, i) => [
        i / (colors.length - 1),
        color,
      ])
      data = data.map((d) => ({ ...d, colorscale: colorscale }))
    }
  }

  const plotType = data.length > 0 ? data[0].type : null

  let conditionalLayout: Partial<Layout> = {}
  if (plotType === 'heatmap') {
    conditionalLayout = {
      plot_bgcolor: '#1C7ED6',
    }
  } else if (plotType === 'bar') {
    conditionalLayout = {
      xaxis: {
        type: 'category',
      },
    }
  }

  return (
    <Plot
      data={data}
      layout={merge({}, layoutTemplate, conditionalLayout, layout)}
      config={merge({}, configTemplate, config)}
      style={{ width: '100%', height: '100%', overflow: 'hidden' }}
      useResizeHandler={true}
      onClick={onClick}
      onRelayout={onRelayout}
    />
  )
}

export default PlotlyPlot
