import { RealtimeGaugeValue } from '@/pages/projects/components/RealtimeGaugeValue'
import { getRealtimeGaugeColor } from '@/pages/projects/components/realtimeGaugeUtils'
import { RingProgress, Tooltip } from '@mantine/core'

const DASH = 8
const GAP = 1

function makeDashedSections(filled: number, color: string) {
  const sections: { value: number; color: string }[] = []
  let pos = 0
  while (pos + DASH <= filled) {
    sections.push({ value: DASH, color })
    pos += DASH
    if (pos + GAP <= filled) {
      sections.push({
        value: GAP,
        color: 'transparent',
      })
      pos += GAP
    } else {
      break
    }
  }
  const leftover = filled - pos
  if (leftover > 0) {
    sections.push({ value: leftover, color })
  }
  return sections
}

export const RealtimePIGauge = ({
  value,
  isLoading,
  isNighttime,
  onClick,
}: {
  value: number | null
  isLoading: boolean
  isNighttime?: boolean
  onClick?: () => void
}) => {
  const cappedValue = value != null ? Math.min(100, value) : null
  const sectionValue = cappedValue ?? 0
  const color =
    cappedValue != null ? getRealtimeGaugeColor(cappedValue) : 'gray'
  const period = isNighttime ? 'last 24h' : 'last hour'

  const sections = isNighttime
    ? makeDashedSections(sectionValue, color)
    : [{ value: sectionValue, color }]

  return (
    <Tooltip
      label={'PV Performance Index' + ` (${period}): metered / expected energy`}
    >
      <RingProgress
        size={32}
        thickness={3}
        onClick={onClick}
        style={
          {
            '--rp-size': '32px',
            cursor: onClick ? 'pointer' : 'default',
          } as React.CSSProperties
        }
        label={<RealtimeGaugeValue value={cappedValue} isLoading={isLoading} />}
        sections={sections}
      />
    </Tooltip>
  )
}
