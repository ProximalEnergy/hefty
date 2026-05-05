import { useGetUserType } from '@/api/admin'
import { GISContext } from '@/contexts/GISContext'
import {
  ActionIcon,
  Paper,
  Popover,
  ScrollArea,
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
  disableEvents = false,
  showEvents,
  onShowEventsChange,
  mapEventDeviceTypes,
  showDemo,
  onDemoChange,
}: {
  disableLabels?: boolean
  disableSatellite?: boolean
  disableEvents?: boolean
  showEvents?: boolean
  onShowEventsChange?: (checked: boolean) => void
  /** Per device type: which event types appear as markers (from current data). */
  mapEventDeviceTypes?: {
    options: { deviceTypeId: number; label: string }[]
    hiddenIds: number[]
    onVisibilityChange: (deviceTypeId: number, visible: boolean) => void
  }
  showDemo?: boolean
  onDemoChange?: (checked: boolean) => void
}) {
  const context = useContext(GISContext)
  const { data: userType } = useGetUserType({})

  if (!context) {
    throw new Error('GISContext is not provided')
  }

  const { showLabels, setShowLabels, showSatellite, setShowSatellite } = context

  const shouldShowEventsToggle =
    showEvents !== undefined && onShowEventsChange !== undefined

  // If all settings are disabled, don't render anything
  if (disableLabels && disableSatellite && !shouldShowEventsToggle) {
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
      <Popover.Dropdown maw={320}>
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
          {shouldShowEventsToggle && (
            <Switch
              label="Events"
              size={switchSize}
              checked={showEvents}
              disabled={disableEvents}
              onChange={(event) =>
                onShowEventsChange(event.currentTarget.checked)
              }
            />
          )}
          {mapEventDeviceTypes != null &&
            mapEventDeviceTypes.options.length > 0 &&
            shouldShowEventsToggle && (
              <>
                <Text size="xs" c="dimmed" fw={600}>
                  Event types on map
                </Text>
                <ScrollArea.Autosize mah={280} type="auto" offsetScrollbars>
                  <Stack gap={6}>
                    {mapEventDeviceTypes.options.map(
                      ({ deviceTypeId, label }) => (
                        <Switch
                          key={deviceTypeId}
                          size={switchSize}
                          label={label}
                          checked={
                            !mapEventDeviceTypes.hiddenIds.includes(
                              deviceTypeId,
                            )
                          }
                          disabled={!showEvents}
                          onChange={(event) =>
                            mapEventDeviceTypes.onVisibilityChange(
                              deviceTypeId,
                              event.currentTarget.checked,
                            )
                          }
                        />
                      ),
                    )}
                  </Stack>
                </ScrollArea.Autosize>
              </>
            )}
        </Stack>
      </Popover.Dropdown>
    </Popover>
  )
}
