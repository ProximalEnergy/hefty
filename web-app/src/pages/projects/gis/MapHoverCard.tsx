import type { KPIType } from '@/api/v1/operational/kpi_types'
import type { HoverInfo } from '@/pages/projects/gis/utils'
import { Paper, Text } from '@mantine/core'

interface MapHoverCardProps {
  hoverInfo: HoverInfo
  kpiType: KPIType
  decimalPlaces?: number
  percentDecimalPlaces?: number
}

export function MapHoverCard({
  hoverInfo,
  kpiType,
  decimalPlaces = 2,
  percentDecimalPlaces = 2,
}: MapHoverCardProps) {
  const hoverValue = hoverInfo.feature?.properties?.value

  let hoverValueText = 'No Data'
  if (hoverValue != null) {
    if (kpiType.unit === '%') {
      hoverValueText = `${(hoverValue * 100).toLocaleString('en-US', {
        minimumFractionDigits: percentDecimalPlaces,
        maximumFractionDigits: percentDecimalPlaces,
      })}%`
    } else {
      hoverValueText = `${hoverValue.toLocaleString('en-US', {
        minimumFractionDigits: decimalPlaces,
        maximumFractionDigits: decimalPlaces,
      })} ${kpiType.unit || ''}`.trim()
    }
  }

  return (
    <Paper
      p="xs"
      withBorder
      style={{
        left: hoverInfo.x,
        top: hoverInfo.y,
        position: 'absolute',
        zIndex: 9,
        pointerEvents: 'none',
      }}
    >
      <Text fw={700}>{hoverInfo.feature?.properties?.name}</Text>
      <Text>{hoverValueText}</Text>
    </Paper>
  )
}
