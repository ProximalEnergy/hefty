import { SensorTypeEnum } from '@/api/enumerations'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { EnrichedTag } from '@/pages/projects/data_browsing/DataBrowsing'
import { AxiosError } from 'axios'
import { Data, Layout } from 'plotly.js'
import { useMemo } from 'react'

interface PlotWithUnitsProps {
  data?: Data[]
  tags?: EnrichedTag[]
  layout?: Partial<Layout>
  config?: Partial<Plotly.Config>
  colorscale?: string
  isLoading?: boolean
  error?: AxiosError<{ detail: string }> | null
  onClick?: (event: Readonly<Plotly.PlotMouseEvent>) => void
  onHover?: (event: Readonly<Plotly.PlotHoverEvent>) => void
  onRelayout?: (event: Readonly<Plotly.PlotRelayoutEvent>) => void
  allowPinning?: boolean
  tagNameMode?: 'name_full' | 'name_scada'
}

const PlotWithUnits = ({
  data = [],
  tags = [],
  layout = {},
  config,
  colorscale,
  isLoading,
  error,
  onClick,
  onHover,
  onRelayout,
  allowPinning,
  tagNameMode = 'name_full',
}: PlotWithUnitsProps) => {
  // Create a map from tag_id to tag for quick lookup
  const tagMap = useMemo(() => {
    const map = new Map<number, EnrichedTag>()
    tags.forEach((tag) => {
      map.set(tag.tag_id, tag)
    })
    return map
  }, [tags])

  // Create a map from tag_name_scada to tag for lookup by name
  const tagByNameScadaMap = useMemo(() => {
    const map = new Map<string, EnrichedTag>()
    tags.forEach((tag) => {
      map.set(tag.name_scada, tag)
    })
    return map
  }, [tags])

  // Group tags by unit (from sensor_type.unit)
  const unitGroups = useMemo(() => {
    if (!tags || tags.length === 0) return []

    const groups = new Map<string, EnrichedTag[]>()
    const colors = [
      '#1f77b4',
      '#ff7f0e',
      '#2ca02c',
      '#d62728',
      '#9467bd',
      '#8c564b',
      '#e377c2',
      '#7f7f7f',
      '#bcbd22',
      '#17becf',
    ]

    // Group tags by unit
    tags.forEach((tag) => {
      const unit = tag.sensor_type_unit || ''
      if (!groups.has(unit)) {
        groups.set(unit, [])
      }
      groups.get(unit)!.push(tag)
    })

    const uniqueUnits = Array.from(groups.keys())
    return uniqueUnits.map((unit, index) => ({
      unit: unit || '',
      color: uniqueUnits.length > 1 ? colors[index % colors.length] : undefined,
      tags: groups.get(unit) || [],
    }))
  }, [tags])

  // Process data: match traces to tags and assign units/y-axes
  const processedData = useMemo(() => {
    if (!data || data.length === 0) return []

    return data.map((trace) => {
      // Try to find the matching tag
      let matchingTag: EnrichedTag | undefined
      const traceData = trace as unknown as Record<string, unknown>

      // First try to match by tag_id if present in trace metadata
      if (traceData.tag_id && typeof traceData.tag_id === 'number') {
        matchingTag = tagMap.get(traceData.tag_id)
      }
      // Try to match by tag_name_scada from metadata
      else if (
        traceData.tag_name_scada &&
        typeof traceData.tag_name_scada === 'string'
      ) {
        matchingTag = tagByNameScadaMap.get(traceData.tag_name_scada)
      }
      // Otherwise try to match by name (which should be tag_name_scada from endpoint)
      else if (trace.name && typeof trace.name === 'string') {
        matchingTag = tagByNameScadaMap.get(trace.name)
      }

      // Get unit from tag - handle unitless items (no sensor_type or no unit)
      // Unitless items should have an empty string unit
      let unit = ''
      if (matchingTag) {
        unit =
          matchingTag.sensor_type?.unit ?? matchingTag.sensor_type_unit ?? ''
      }

      // Find unit group index - unitless items (empty string) should be grouped together
      const unitIndex = unitGroups.findIndex((g) => g.unit === unit)
      // If unit group not found, default to first group (shouldn't happen, but safety check)
      const safeUnitIndex = unitIndex >= 0 ? unitIndex : 0
      const yAxis = safeUnitIndex === 0 ? 'y' : `y${safeUnitIndex + 1}`

      // Get unit group color (only if multiple units)
      const group = unitGroups[safeUnitIndex]
      const unitColor = group?.color

      // Determine trace name based on tagNameMode
      // Expected power tags (tag_id < 0) don't have name_scada, always use name_full
      let traceName: string
      if (matchingTag) {
        const isExpectedPowerTag = matchingTag.tag_id < 0
        if (isExpectedPowerTag) {
          traceName = matchingTag.name_full || ''
        } else if (tagNameMode === 'name_scada') {
          traceName = matchingTag.name_scada || ''
        } else {
          // name_full mode: Use name_scada fallback for un-mapped tags
          const isUnmappedTag =
            matchingTag.sensor_type_id === SensorTypeEnum.GHOST_UNKNOWN ||
            matchingTag.sensor_type_id === null ||
            matchingTag.device_id === 0
          traceName = isUnmappedTag
            ? matchingTag.name_scada
            : matchingTag.name_full || matchingTag.name_scada
        }
      } else {
        traceName = trace.name || ''
      }

      // Build the processed trace
      const processedTrace: Data = {
        ...trace,
        name: traceName,
        yaxis: yAxis,
        hoverlabel: {
          namelength: -1,
        },
      }

      // If multiple unit groups, apply unit group color to all traces in that group
      // Only override if trace doesn't already have a color
      if (unitColor) {
        const traceRecord = trace as unknown as Record<string, unknown>
        const hasLineColor =
          traceRecord.line &&
          typeof traceRecord.line === 'object' &&
          'color' in traceRecord.line
        const hasMarkerColor =
          traceRecord.marker &&
          typeof traceRecord.marker === 'object' &&
          'color' in traceRecord.marker

        if (!hasLineColor && !hasMarkerColor) {
          return {
            ...processedTrace,
            line: {
              ...(traceRecord.line as Record<string, unknown>),
              color: unitColor,
            },
          } as Data
        }
      }

      return processedTrace
    })
  }, [data, tagMap, tagByNameScadaMap, unitGroups, tagNameMode])

  // Create layout with dynamic y-axes
  const dynamicLayout = useMemo(() => {
    // Calculate how much space we need for axes
    // Each axis needs about 0.08 of space (0.05 for axis + 0.03 buffer)

    const numAxes = unitGroups.length + 1
    const axisSpacing = 0.04
    const leftAxesCount = Math.ceil((numAxes - 1) / 2)
    const rightAxesCount = Math.floor((numAxes - 1) / 2)
    const leftMargin = leftAxesCount * axisSpacing
    const rightMargin = 1 - rightAxesCount * axisSpacing
    const xDomainStart = leftMargin
    const xDomainEnd = rightMargin

    if (unitGroups.length === 0) {
      return {
        xaxis: { domain: [xDomainStart, xDomainEnd] },
        yaxis: { title: { text: '' }, showgrid: false },
        ...layout,
      }
    }

    const baseLayout: Partial<Layout> = {
      xaxis: { domain: [xDomainStart, xDomainEnd] },
      yaxis: {
        title: {
          text: unitGroups[0]?.unit || '',
          ...(unitGroups[0]?.color
            ? { font: { color: unitGroups[0].color } }
            : {}),
        },
        side: 'left',
        linecolor: unitGroups[0]?.color,
        showgrid: false,
        tickfont: unitGroups[0]?.color
          ? { color: unitGroups[0].color }
          : undefined,
      },
    }

    // Add additional y-axes for multiple units
    if (unitGroups.length > 1) {
      const additionalAxes: Record<string, Partial<Layout['yaxis']>> = {}
      unitGroups.slice(1).forEach((group, idx) => {
        // Calculate which side this axis should be on
        // First additional axis (idx=0) goes right, then alternates
        const isRight = idx % 2 === 0
        const side = isRight ? 'right' : 'left'

        // Calculate position offset - move axes OUTSIDE the plot
        // Right side axes (idx=0,2,4...): position = 1.05, 1.10, 1.15, ...
        // Left side axes (idx=1,3,5...): position = -0.05, -0.10, -0.15, ...
        // Position < 0 = outside left, Position > 1 = outside right
        // offsetIndex counts how many axes of this side we've already placed
        const offsetIndex = isRight
          ? Math.floor(idx / 2)
          : Math.floor((idx - 1) / 2)
        const position = isRight
          ? 1 - (offsetIndex + 1) * axisSpacing
          : (offsetIndex + 1) * axisSpacing

        additionalAxes[`yaxis${idx + 2}`] = {
          title: {
            text: group.unit,
            ...(group.color ? { font: { color: group.color } } : {}),
            standoff: 0,
          },
          overlaying: 'y',
          side: side,
          anchor: 'free',
          position: position,
          showgrid: false,
          tickfont: group.color ? { color: group.color } : undefined,
          linecolor: group.color,
        }
      })
      return { ...baseLayout, ...additionalAxes, ...layout }
    }

    return { ...baseLayout, ...layout }
  }, [unitGroups, layout])

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <PlotlyPlot
        data={processedData}
        layout={dynamicLayout}
        config={config}
        colorscale={colorscale}
        isLoading={isLoading}
        error={error}
        onClick={onClick}
        onHover={onHover}
        onRelayout={onRelayout}
        allowPinning={allowPinning}
      />
    </div>
  )
}

export default PlotWithUnits
