import { RingProgress, Text, Tooltip } from '@mantine/core'

const getColor = (pct: number) => {
  if (pct >= 90) return 'green'
  if (pct >= 70) return 'yellow'
  return 'red'
}

export const RealtimePowerAvailabilityGauge = ({
  value,
  availablePowerMw,
  ratedCapacityMw,
  numPcsUnits,
  maxPcsCapacityMw,
  isLoading,
  onClick,
}: {
  value: number | null
  availablePowerMw: number | null
  ratedCapacityMw: number | null
  numPcsUnits: number | null
  maxPcsCapacityMw: number | null
  isLoading: boolean
  onClick?: () => void
}) => {
  const sectionValue = value != null ? Math.min(100, value) : 0
  const color = value != null ? getColor(value) : 'gray'

  const pwrLabel =
    availablePowerMw != null ? `${availablePowerMw.toFixed(1)} MW` : '—'
  const capLabel =
    ratedCapacityMw != null ? `${ratedCapacityMw.toFixed(1)} MW` : '—'

  let pcsLabel = ''
  if (numPcsUnits != null && numPcsUnits > 0 && maxPcsCapacityMw != null) {
    const perUnit = maxPcsCapacityMw / numPcsUnits
    pcsLabel =
      ` (PCS cumulative: ${numPcsUnits}x ` +
      `${perUnit.toFixed(1)} MW = ` +
      `${maxPcsCapacityMw.toFixed(1)} MW)`
  }

  return (
    <Tooltip
      label={
        <div>
          <div>
            {`Storage Power Availability:`}
            {` ${pwrLabel} / ${capLabel}`}
            {` POI capacity${pcsLabel}.`}
          </div>
          <div>
            Based on max of cumulative PCS available charge and discharge power.
          </div>
        </div>
      }
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
        label={
          <Text
            size="11px"
            fw={600}
            ta="center"
            c={value != null ? 'inherit' : 'dimmed'}
            style={{ lineHeight: 1, fontSize: 11 }}
          >
            {isLoading ? '…' : value != null ? `${value.toFixed(0)}` : '—'}
          </Text>
        }
        sections={[{ value: sectionValue, color }]}
      />
    </Tooltip>
  )
}
