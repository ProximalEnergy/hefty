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
import { Annotations, Shape } from 'plotly.js'
import Plotly, {
  Config,
  Data,
  Layout,
  PlotHoverEvent,
  PlotMouseEvent,
  PlotRelayoutEvent,
} from 'plotly.js/dist/plotly-custom.min.js'
import {
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import createPlotlyComponent from 'react-plotly.js/factory'
import { v4 as uuidv4 } from 'uuid'

const Plot = createPlotlyComponent(Plotly)

type ErrorData = {
  detail: string
}

type Annotation = Partial<Annotations> & {
  name: string
}

const PlotlyPlot = ({
  data = [],
  layout = {},
  config = {},
  colorscale,
  isLoading,
  error,
  onClick,
  onHover,
  onRelayout,
  allowPinning,
}: {
  data?: Data[]
  layout?: Partial<Layout>
  config?: Partial<Config>
  colorscale?: string
  isLoading?: boolean
  error?: AxiosError<ErrorData> | null
  onClick?: (event: Readonly<PlotMouseEvent>) => void
  onHover?: (event: Readonly<PlotHoverEvent>) => void
  onRelayout?: (event: Readonly<PlotRelayoutEvent>) => void
  allowPinning?: boolean
}) => {
  //////////////////////////////////////////////////////////////////////////////
  /////// If the plot you're looking for is not working, go check //////////////
  /////// that the plot type exists in the build-plotly-custom.js file /////////
  //////////////////////////////////////////////////////////////////////////////

  const theme = useMantineTheme()
  const computedColorScheme = useComputedColorScheme('dark')
  const context = useContext(GISContext)
  const [annotations, setAnnotations] = useState<Annotation[]>([])
  const [shapes, setShapes] = useState<Partial<Shape>[]>([])
  const [pinModeActive, setPinModeActive] = useState(false)
  const lastHoverEvent = useRef<PlotHoverEvent | null>(null)

  // Ensure that the GISContext is provided
  if (!context) {
    throw new Error('GISContext is not provided')
  }

  const { colorsGoodBad } = context

  let processedData = data

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
    annotations: annotations,
    shapes: shapes,
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
    uirevision: 'true',
  }

  // https://plotly.com/javascript/reference/layout/
  const configTemplate: Partial<Config> = useMemo(
    () => ({
      displaylogo: false,
      // NOTE: ModeBar coloring is defined in index.css
      modeBarButtons: allowPinning
        ? [
            [
              'zoom2d',
              'pan2d',
              'hoverClosestCartesian',
              'hoverCompareCartesian',
              'resetViews',
              'toImage',
              {
                name: 'Toggle pin mode',
                title: 'Toggle pin mode',
                icon: {
                  width: 384,
                  height: 512,
                  path: 'M32 32C32 14.3 46.3 0 64 0H320c17.7 0 32 14.3 32 32s-14.3 32-32 32H290.5l11.4 148.2c36.7 19.9 65.7 53.2 79.5 94.7l1 3c3.3 9.8 1.6 20.5-4.4 28.8s-15.7 13.3-26 13.3H32c-10.3 0-19.9-5-26-13.3s-7.7-19.1-4.4-28.8l1-3c13.8-41.5 42.8-74.8 79.5-94.7L93.5 64H64C46.3 64 32 49.7 32 32zM160 384h64v96c0 17.7-14.3 32-32 32s-32-14.3-32-32V384z',
                  transform: 'matrix(-1 0 0 1 384 0)',
                },
                click: function () {
                  setPinModeActive((prev) => !prev)
                },
              },
            ],
          ]
        : [
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
    }),
    [allowPinning, theme],
  )

  if (colorscale && processedData.length > 0) {
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
      processedData = processedData.map((d) => ({
        ...d,
        colorscale: colorscale,
      }))
    } else if (colorscale === 'good-bad') {
      const colors = chroma
        .scale(colorsGoodBad.map((c) => c.value))
        .mode('rgb')
        .colors(10)
      const colorscale: [number, string][] = colors.map((color, i) => [
        i / (colors.length - 1),
        color,
      ])
      processedData = processedData.map((d) => ({
        ...d,
        colorscale: colorscale,
      }))
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
      processedData = processedData.map((d) => ({
        ...d,
        colorscale: colorscale,
      }))
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
      processedData = processedData.map((d) => ({
        ...d,
        colorscale: colorscale,
      }))
    }
  }

  const onAnnotationClick = useCallback(
    (e: any) => {
      const { index } = e.currentTarget.dataset
      const numericIndex = parseInt(index, 10)
      if (isNaN(numericIndex)) {
        return
      }

      const annotationToRemove = annotations[numericIndex]
      if (annotationToRemove && annotationToRemove.name) {
        const groupId = annotationToRemove.name
        setAnnotations((prev) => prev.filter((ann) => ann.name !== groupId))
        setShapes((prev) => prev.filter((s) => s.name !== groupId))
      }
    },
    [annotations],
  )

  useEffect(() => {
    if (allowPinning) {
      // Find all annotations and add click handlers
      const as = document.getElementsByClassName('annotation-text')
      for (let i = 0; i < as.length; i++) {
        const a = as[i]
        a.setAttribute('data-index', i.toString())
        a.addEventListener('click', onAnnotationClick)
        ;(a as HTMLElement).style.cursor = 'pointer'
      }
      return () => {
        // Find all annotations and remove click handlers
        const as = document.getElementsByClassName('annotation-text')
        for (let i = 0; i < as.length; i++) {
          const a = as[i]
          a.removeEventListener('click', onAnnotationClick)
        }
      }
    }
  }, [annotations, shapes, allowPinning, onAnnotationClick])

  const plotType = processedData.length > 0 ? processedData[0].type : null

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

  const handleClick = (e: Readonly<PlotMouseEvent>) => {
    if (allowPinning && pinModeActive && lastHoverEvent.current) {
      const getVal = (
        val: Plotly.Datum,
      ): number | string | null | undefined => {
        if (val === null || val === undefined) {
          return val
        }
        if (val instanceof Date) {
          return val.getTime()
        }
        if (typeof val === 'string') {
          const d = new Date(val)
          if (!isNaN(d.getTime())) {
            return d.getTime()
          }
        }
        return val
      }

      const groupId = uuidv4()
      const points = lastHoverEvent.current.points

      if (points.length === 0) {
        return
      }

      const xVal = getVal(points[0].x)
      if (xVal === null || xVal === undefined) {
        return // Cannot create annotation without a valid x value
      }
      const annotationText = points
        .map((point) => {
          const trace = point.data as any
          const traceColor =
            trace.line?.color || trace.marker?.color || layoutSettings.fontcolor
          const yVal = getVal(point.y)
          const yDisplay =
            typeof yVal === 'number' ? yVal.toFixed(2) : String(yVal)
          return `<span style="color: ${traceColor}">●</span> ${yDisplay}`
        })
        .join('<br>')

      const topPoint = points.reduce((prev, current) => {
        return (prev.y ?? -Infinity) > (current.y ?? -Infinity) ? prev : current
      })

      const yValTopPoint = getVal(topPoint.y)
      if (yValTopPoint === null || yValTopPoint === undefined) {
        return // Cannot create annotation without a valid y value
      }

      const newAnnotation: Annotation = {
        x: xVal,
        y: yValTopPoint,
        yref: (topPoint.data as any).yaxis || 'y',
        text: annotationText,
        name: groupId,
        showarrow: true,
        arrowhead: 0,
        ax: 0,
        ay: -40,
        yanchor: 'bottom',
        align: 'left',
        bgcolor:
          computedColorScheme === 'dark'
            ? 'rgba(0,0,0,0.8)'
            : 'rgba(255,255,255,0.9)',
        bordercolor: layoutSettings.fontcolor,
        borderwidth: 1,
        borderpad: 4,
        font: {
          color: layoutSettings.fontcolor,
        },
      }

      const newShape: Partial<Shape> = {
        type: 'line',
        x0: xVal,
        x1: xVal,
        y0: 0,
        y1: 1,
        yref: 'paper',
        line: {
          dash: 'dot',
          color: layoutSettings.zerolinecolor,
        },
        name: groupId,
      }

      setAnnotations((prev) => [...prev, newAnnotation])
      setShapes((prev) => [...prev, newShape])
    }
    onClick?.(e)
  }

  const handleHover = (e: Readonly<PlotHoverEvent>) => {
    lastHoverEvent.current = e
    onHover?.(e)
  }

  // Update modebar button active state via CSS
  useEffect(() => {
    if (allowPinning) {
      const pinButton = document.querySelector(
        '[data-title="Toggle pin mode"]',
      ) as HTMLElement
      if (pinButton) {
        if (pinModeActive) {
          pinButton.style.backgroundColor = theme.colors.blue[6]
          pinButton.style.fill = 'white'
        } else {
          pinButton.style.backgroundColor = ''
          pinButton.style.fill = ''
        }
      }
    }
  }, [pinModeActive, allowPinning, theme])

  // Clear pins when pin mode is toggled off
  useEffect(() => {
    if (!pinModeActive) {
      setAnnotations([])
      setShapes([])
    }
  }, [pinModeActive])

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

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <Plot
        data={processedData}
        layout={merge({}, layoutTemplate, conditionalLayout, layout)}
        config={merge({}, configTemplate, config)}
        style={{ width: '100%', height: '100%', overflow: 'hidden' }}
        useResizeHandler={true}
        onClick={handleClick}
        onHover={handleHover}
        onRelayout={onRelayout}
      />
    </div>
  )
}

export default PlotlyPlot
