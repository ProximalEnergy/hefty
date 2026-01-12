import { useGetUserType } from '@/api/admin'
import { GISContext } from '@/contexts/GISContext'
import {
  ActionIcon,
  Paper,
  Popover,
  Stack,
  Switch,
  Text,
  TextProps,
  rem,
} from '@mantine/core'
import { IconSettings } from '@tabler/icons-react'
import { useContext } from 'react'

export function ColorBar({
  gradient,
  lowLabel,
  middleLabel,
  highLabel,
}: {
  gradient: string
  highLabel: string | number
  middleLabel?: string | number
  lowLabel: string | number
}) {
  const textProps: TextProps = {
    size: 'md',
    fw: 500,
    c: 'black',
    style: {
      writingMode: 'vertical-rl',
      textAlign: 'center',
      borderRadius: '3px',
    },
    bg: 'rgba(255, 255, 255, 0.75)',
    py: 'xs',
    px: 3,
    lh: 0,
  }

  return (
    <Paper h="100%" p={0} bg={gradient} withBorder>
      <Stack
        h="100%"
        p={8}
        align="center"
        justify="space-between"
        ff="monospace"
        pos="relative"
      >
        <Text {...textProps}>{highLabel}</Text>
        {middleLabel && <Text {...textProps}>{middleLabel}</Text>}
        <Text {...textProps}>{lowLabel}</Text>
      </Stack>
    </Paper>
  )
}

export function MapSettings({
  disableLabels = false,
  disableSatellite = false,
  showDemo,
  onDemoChange,
}: {
  disableLabels?: boolean
  disableSatellite?: boolean
  showDemo?: boolean
  onDemoChange?: (checked: boolean) => void
}) {
  const context = useContext(GISContext)
  const { data: userType } = useGetUserType({})

  if (!context) {
    throw new Error('GISContext is not provided')
  }

  const { showLabels, setShowLabels, showSatellite, setShowSatellite } = context

  // If all settings are disabled, don't render anything
  if (disableLabels && disableSatellite) {
    return null
  }

  const switchSize = 'xs'
  const isSuperadmin = userType?.name_short === 'superadmin'

  return (
    <Popover position="top-start">
      <Popover.Target>
        <ActionIcon size={30}>
          <IconSettings style={{ width: rem(18), height: rem(18) }} />
        </ActionIcon>
      </Popover.Target>
      <Popover.Dropdown>
        <Stack gap="xs">
          {isSuperadmin && showDemo !== undefined && onDemoChange && (
            <Switch
              label="Demo"
              size={switchSize}
              checked={showDemo}
              onChange={(event) => onDemoChange(event.currentTarget.checked)}
            />
          )}
          {!disableSatellite && (
            <Switch
              label="Satellite"
              size={switchSize}
              checked={showSatellite}
              onChange={(event) =>
                setShowSatellite(event.currentTarget.checked)
              }
            />
          )}
          {!disableLabels && (
            <Switch
              label="Labels"
              size={switchSize}
              checked={showLabels}
              onChange={(event) => setShowLabels(event.currentTarget.checked)}
            />
          )}
        </Stack>
      </Popover.Dropdown>
    </Popover>
  )
}
