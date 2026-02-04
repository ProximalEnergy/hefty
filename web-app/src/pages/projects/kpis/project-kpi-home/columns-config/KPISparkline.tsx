// Sparkline chart component that displays a mini time-series plot of KPI trend data.
// Used in table cells to show historical KPI performance at a glance.
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useComputedColorScheme, useMantineTheme } from '@mantine/core'
import { Data } from 'plotly.js'
import { memo } from 'react'

type KPISparklineProps = {
  trendDates: string[]
  trendData: (number | null)[]
  unit: string | null
  startDate?: string | null
  endDate?: string | null
  thresholds?: {
    critical_low?: number | null
    warning_low?: number | null
    warning_high?: number | null
    critical_high?: number | null
  }
}

const sparklineWidth = 100
const sparklineHeight = 28

const KPISparkline = memo(
  ({
    trendDates,
    trendData,
    unit,
    startDate,
    endDate,
    thresholds,
  }: KPISparklineProps) => {
    const theme = useMantineTheme()
    const computedColorScheme = useComputedColorScheme('light')
    const textColor =
      computedColorScheme === 'dark'
        ? theme.colors.dark[0]
        : theme.colors.gray[9]
    // Return empty div if no data (matching TrendSparkline pattern)
    if (!trendDates.length || !trendData.length) {
      return <div style={{ width: sparklineWidth, height: sparklineHeight }} />
    }

    // Create sorted data points (keep null values for gap display)
    const sortedData = trendDates
      .map((date, index) => ({
        timestamp: date,
        value: trendData[index],
      }))
      .sort(
        (a, b) =>
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
      )

    // Return empty div if all values are null
    if (sortedData.every((point) => point.value === null)) {
      return <div style={{ width: sparklineWidth, height: sparklineHeight }} />
    }

    // Handle percentage units (multiply by 100 to match display format)
    const multiplier = unit === '%' ? 100 : 1
    const adjustedData = sortedData.map((d) => ({
      ...d,
      value: d.value !== null ? d.value * multiplier : null,
    }))

    // Helper function to format threshold hover value
    const formatThresholdHover = (value: number): string => {
      if (unit === '%') {
        return `${value.toFixed(1)}%`
      }
      return `${value.toFixed(1)}${unit ? ` ${unit}` : ''}`
    }

    // Build threshold lines (similar to TrendSparkline)
    const thresholdLines: Data[] = []

    if (thresholds) {
      const adjustedThresholds = {
        critical_low:
          thresholds.critical_low !== undefined &&
          thresholds.critical_low !== null
            ? thresholds.critical_low * multiplier
            : undefined,
        warning_low:
          thresholds.warning_low !== undefined &&
          thresholds.warning_low !== null
            ? thresholds.warning_low * multiplier
            : undefined,
        warning_high:
          thresholds.warning_high !== undefined &&
          thresholds.warning_high !== null
            ? thresholds.warning_high * multiplier
            : undefined,
        critical_high:
          thresholds.critical_high !== undefined &&
          thresholds.critical_high !== null
            ? thresholds.critical_high * multiplier
            : undefined,
      }

      // Use the same x-axis points as the data to enable hover throughout the line
      const thresholdXValues = adjustedData.map((d) => d.timestamp)

      // Add threshold lines if they exist
      if (adjustedThresholds.critical_low !== undefined) {
        const criticalLowValue = adjustedThresholds.critical_low
        thresholdLines.push({
          type: 'scatter',
          mode: 'lines',
          x: thresholdXValues,
          y: thresholdXValues.map(() => criticalLowValue),
          line: { color: '#ff0000', width: 1, dash: 'dot' },
          hovertemplate: `Critical Low: ${formatThresholdHover(criticalLowValue)}<extra></extra>`,
          hoverlabel: {
            namelength: 0,
            bgcolor: 'rgba(0,0,0,0)',
            bordercolor: 'rgba(0,0,0,0)',
            font: { size: 12, color: textColor },
          },
        })
      }
      if (adjustedThresholds.warning_low !== undefined) {
        const warningLowValue = adjustedThresholds.warning_low
        thresholdLines.push({
          type: 'scatter',
          mode: 'lines',
          x: thresholdXValues,
          y: thresholdXValues.map(() => warningLowValue),
          line: { color: '#ffa500', width: 1, dash: 'dot' },
          hovertemplate: `Warning Low: ${formatThresholdHover(warningLowValue)}<extra></extra>`,
          hoverlabel: {
            namelength: 0,
            bgcolor: 'rgba(0,0,0,0)',
            bordercolor: 'rgba(0,0,0,0)',
            font: { size: 12, color: textColor },
          },
        })
      }
      if (adjustedThresholds.warning_high !== undefined) {
        const warningHighValue = adjustedThresholds.warning_high
        thresholdLines.push({
          type: 'scatter',
          mode: 'lines',
          x: thresholdXValues,
          y: thresholdXValues.map(() => warningHighValue),
          line: { color: '#ffa500', width: 1, dash: 'dot' },
          hovertemplate: `Warning High: ${formatThresholdHover(warningHighValue)}<extra></extra>`,
          hoverlabel: {
            namelength: 0,
            bgcolor: 'rgba(0,0,0,0)',
            bordercolor: 'rgba(0,0,0,0)',
            font: { size: 12, color: textColor },
          },
        })
      }
      if (adjustedThresholds.critical_high !== undefined) {
        const criticalHighValue = adjustedThresholds.critical_high
        thresholdLines.push({
          type: 'scatter',
          mode: 'lines',
          x: thresholdXValues,
          y: thresholdXValues.map(() => criticalHighValue),
          line: { color: '#ff0000', width: 1, dash: 'dot' },
          hovertemplate: `Critical High: ${formatThresholdHover(criticalHighValue)}<extra></extra>`,
          hoverlabel: {
            namelength: 0,
            bgcolor: 'rgba(0,0,0,0)',
            bordercolor: 'rgba(0,0,0,0)',
            font: { size: 12, color: textColor },
          },
        })
      }
    }

    return (
      <div
        style={{
          width: sparklineWidth,
          height: sparklineHeight,
        }}
        className="kpi-sparkline-container"
      >
        <style>{`
        .kpi-sparkline-container .hoverlayer .hovertext {
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
        }
        .kpi-sparkline-container .hoverlayer .hovertext > path {
          display: none !important;
        }
        .kpi-sparkline-container .hoverlayer .hovertext > text,
        .kpi-sparkline-container .hoverlayer .hovertext text {
          fill: ${textColor} !important;
          opacity: 1 !important;
          visibility: visible !important;
        }
      `}</style>
        <PlotlyPlot
          data={[
            {
              type: 'scatter',
              mode: 'lines',
              x: adjustedData.map((d) => d.timestamp),
              y: adjustedData.map((d) => d.value),
              connectgaps: false,
              line: {
                color: '#228be6',
                width: 1.5,
                shape: 'spline',
                smoothing: 0.8,
              },
              hovertemplate: `%{y:.1f}${unit ? unit : ''}<br>%{x|%Y-%m-%d}<extra></extra>`,
              hoverlabel: {
                namelength: 0,
                bgcolor: 'rgba(0,0,0,0)',
                bordercolor: 'rgba(0,0,0,0)',
                font: { size: 12, color: textColor },
              },
            },
            ...thresholdLines,
          ]}
          layout={{
            showlegend: false,
            margin: { l: 0, r: 0, t: 0, b: 0 },
            xaxis: {
              visible: false,
              fixedrange: true,
              ...(startDate && endDate ? { range: [startDate, endDate] } : {}),
            },
            yaxis: {
              visible: false,
              autorange: true,
              fixedrange: true,
            },
            plot_bgcolor: 'transparent',
            paper_bgcolor: 'transparent',
            hovermode: 'closest',
          }}
          config={{
            displayModeBar: false,
            staticPlot: false, // Allow hover interactions
            scrollZoom: false,
            doubleClick: false,
          }}
        />
      </div>
    )
  },
)

KPISparkline.displayName = 'KPISparkline'

export { KPISparkline }
