import { useSelectProject } from '@/api/v1/operational/projects'
import { RingProgress, Stack, Text, Tooltip } from '@mantine/core'

export const RingProgressStat = ({
  project,
  type,
  value,
}: {
  project: NonNullable<ReturnType<typeof useSelectProject>['data']>
  type: 'power' | 'poa' | 'soc'
  value?: number
}) => {
  const powerLimit = Math.max(project.poi, project.capacity_bess_power_ac || 0)

  let tooltipLabel = ''
  let sectionValue = 0
  switch (type) {
    case 'power':
      tooltipLabel = 'Meter Power'
      sectionValue = value != null ? (Math.abs(value) / powerLimit) * 100 : 0
      break
    case 'poa':
      tooltipLabel = 'POA'
      if (value != null && value < 0) {
        sectionValue = 0
      } else {
        sectionValue = value != null ? (value / 1000) * 100 : 0
      }
      break
    case 'soc':
      tooltipLabel = 'SOC'
      sectionValue = value != null ? (value / 100) * 100 : 0
      break
  }
  return (
    <Tooltip
      label={value != null ? tooltipLabel : `No ${tooltipLabel} data available`}
    >
      <RingProgress
        size={65}
        thickness={4}
        style={{ '--rp-size': '65px' } as React.CSSProperties}
        label={
          <Stack gap={0} align="center">
            <Text
              size="lgfi"
              fw={700}
              ta="center"
              c={value != null ? 'inherit' : 'red'}
            >
              {value != null ? value.toFixed(0) : '?'}
            </Text>
            <Text size="xs" ta="center" c={value != null ? 'inherit' : 'red'}>
              {type === 'power' ? 'MW' : type === 'poa' ? 'W/m²' : '%'}
            </Text>
          </Stack>
        }
        sections={[
          {
            value: sectionValue,
            color: value != null && value >= 0 ? 'green' : 'red',
          },
        ]}
      />
    </Tooltip>
  )
}
