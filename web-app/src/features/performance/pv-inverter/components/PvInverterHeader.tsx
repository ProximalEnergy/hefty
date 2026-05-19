import PlotlyPlot from '@/components/plots/PlotlyPlot'
import type { PvInverterContext } from '@/features/performance/pv-inverter/hooks/use-pv-inverter-context'
import { useResizePlotlyCharts } from '@/hooks/useResizePlotlyCharts'
import {
  ActionIcon,
  Box,
  Group,
  Image,
  Modal,
  SimpleGrid,
  Skeleton,
  Stack,
  Tabs,
  Text,
  useComputedColorScheme,
} from '@mantine/core'
import {
  IconEdit,
  IconInfoCircle,
  IconMail,
  IconPhone,
} from '@tabler/icons-react'
import dayjs from 'dayjs'
import type { PlotType } from 'plotly.js'
import type { SyntheticEvent } from 'react'
import { useRef, useState } from 'react'
import { Link } from 'react-router'

const deviceModelIconUrl = '/icon_pv_pcs.svg'

type PvInverterHeaderProps = {
  context: PvInverterContext
}

export function PvInverterHeader({ context }: PvInverterHeaderProps) {
  const colorScheme = useComputedColorScheme()
  const [imageModalOpened, setImageModalOpened] = useState(false)
  const [modalActiveTab, setModalActiveTab] = useState('overview')
  const modalContentRef = useRef<HTMLDivElement>(null)

  useResizePlotlyCharts({
    containerRef: modalContentRef,
    enabled: imageModalOpened,
    dependency: modalActiveTab,
  })

  const matchesAssetUrl = (currentUrl: string, expectedUrl: string) => {
    if (!expectedUrl) {
      return false
    }
    return currentUrl === expectedUrl || currentUrl.endsWith(expectedUrl)
  }

  const handleDeviceModelImageError = (
    event: SyntheticEvent<HTMLImageElement>,
  ) => {
    const target = event.currentTarget
    const fallback = context.deviceModelImageFallbackUrl
    const shouldTryFallback =
      fallback &&
      !matchesAssetUrl(target.src, fallback) &&
      !matchesAssetUrl(target.src, deviceModelIconUrl)

    if (shouldTryFallback) {
      target.src = fallback
      return
    }

    if (!matchesAssetUrl(target.src, deviceModelIconUrl)) {
      target.src = deviceModelIconUrl
    }
  }

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-start">
        <Group gap="md" align="flex-start">
          {context.mostCommonDeviceModelId !== null ? (
            <>
              <Box
                w={100}
                h={100}
                style={{
                  flexShrink: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Image
                  src={context.deviceModelImageUrl}
                  alt={context.pcsBrandModel || 'Device Model'}
                  w="100%"
                  h="100%"
                  fit="contain"
                  radius="md"
                  style={{
                    objectFit: 'contain',
                    cursor: 'pointer',
                  }}
                  onClick={() => setImageModalOpened(true)}
                  onError={handleDeviceModelImageError}
                />
              </Box>
              <Modal
                opened={imageModalOpened}
                onClose={() => setImageModalOpened(false)}
                title={context.pcsBrandModel || 'Device Model'}
                size="xl"
                centered
              >
                <div ref={modalContentRef}>
                  {context.inverters.isLoading ? (
                    <Skeleton height={400} />
                  ) : context.inverter ? (
                    <Tabs
                      value={modalActiveTab}
                      onChange={(value) =>
                        setModalActiveTab(value || 'overview')
                      }
                      defaultValue="overview"
                      variant="outline"
                    >
                      <Tabs.List>
                        <Tabs.Tab value="overview">Overview</Tabs.Tab>
                        <Tabs.Tab value="power-temp">
                          Power & Temperature
                        </Tabs.Tab>
                        <Tabs.Tab value="efficiency">Efficiency</Tabs.Tab>
                        <Tabs.Tab value="sandia">Sandia Parameters</Tabs.Tab>
                      </Tabs.List>
                      <Tabs.Panel value="overview" pt="md">
                        <Stack gap="md">
                          <Image
                            src={context.deviceModelImageUrl}
                            alt={context.pcsBrandModel || 'Device Model'}
                            style={{
                              filter:
                                colorScheme === 'dark'
                                  ? 'invert(1) brightness(0.7)'
                                  : 'none',
                            }}
                            maw={280}
                            mah={280}
                            fit="contain"
                            radius="md"
                            mx="auto"
                            onError={handleDeviceModelImageError}
                          />
                          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                            <Text size="sm" c="dimmed">
                              Manufacturer:{' '}
                              <Text component="span" fw={500}>
                                {context.inverter.manufacturer}
                              </Text>
                            </Text>
                            <Text size="sm" c="dimmed">
                              Model:{' '}
                              <Text component="span" fw={500}>
                                {context.inverter.model}
                              </Text>
                            </Text>
                            <Text size="sm" c="dimmed">
                              Rated AC power:{' '}
                              <Text component="span" fw={500}>
                                {context.inverter.power_ac_nominal
                                  ? `${(
                                      context.inverter.power_ac_nominal /
                                      1000000
                                    ).toFixed(2)} MWac`
                                  : 'N/A'}
                              </Text>
                            </Text>
                            <Text size="sm" c="dimmed">
                              Rated DC power:{' '}
                              <Text component="span" fw={500}>
                                {context.inverter.power_dc_nominal
                                  ? `${(
                                      context.inverter.power_dc_nominal /
                                      1000000
                                    ).toFixed(2)} MWdc`
                                  : 'N/A'}
                              </Text>
                            </Text>
                          </SimpleGrid>
                        </Stack>
                      </Tabs.Panel>
                      <Tabs.Panel value="power-temp" pt="md">
                        <Stack gap="md">
                          <Text size="sm" c="dimmed">
                            Power vs Temperature Characteristics
                          </Text>
                          {context.inverter.power_max_at_reference_temp &&
                          context.inverter.reference_temp &&
                          context.inverter.power_max_at_reference_temp.length >
                            0 &&
                          context.inverter.reference_temp.length > 0 ? (
                            <Box
                              w="100%"
                              maw="100%"
                              mx="auto"
                              style={{ overflow: 'hidden' }}
                            >
                              <PlotlyPlot
                                data={[
                                  (() => {
                                    const powerValues =
                                      context.inverter.power_max_at_reference_temp.map(
                                        (power) => (power / 1000000) * 1000,
                                      )
                                    const temperatures = [
                                      ...context.inverter.reference_temp,
                                    ]
                                    if (
                                      temperatures.length > 0 &&
                                      powerValues.length > 0
                                    ) {
                                      temperatures.unshift(0)
                                      powerValues.unshift(powerValues[0])
                                    }
                                    return {
                                      x: temperatures,
                                      y: powerValues,
                                      type: 'scatter' as PlotType,
                                      mode: 'lines+markers' as const,
                                      name: 'Max Power',
                                      line: { color: '#228be6' },
                                      marker: { size: 8 },
                                    }
                                  })(),
                                ]}
                                layout={{
                                  title: {
                                    text: 'Maximum Power vs Temperature',
                                    font: { size: 12 },
                                  },
                                  xaxis: {
                                    title: { text: 'Temperature (°C)' },
                                    range: [0, undefined],
                                  },
                                  yaxis: {
                                    title: { text: 'Power (MW)' },
                                    range: [0, undefined],
                                  },
                                  height: 300,
                                  margin: { l: 55, r: 40, t: 40, b: 45 },
                                  autosize: true,
                                }}
                                config={{
                                  displayModeBar: true,
                                  responsive: true,
                                }}
                              />
                            </Box>
                          ) : (
                            <Text
                              size="sm"
                              c="dimmed"
                              style={{ fontStyle: 'italic' }}
                            >
                              No power vs temperature data available
                            </Text>
                          )}
                        </Stack>
                      </Tabs.Panel>
                      <Tabs.Panel value="efficiency" pt="md">
                        <Text size="sm" c="dimmed">
                          Efficiency Characteristics
                        </Text>
                      </Tabs.Panel>
                      <Tabs.Panel value="sandia" pt="md">
                        <Text size="sm" c="dimmed">
                          Sandia Inverter Model Parameters
                        </Text>
                      </Tabs.Panel>
                    </Tabs>
                  ) : (
                    <Stack gap="md">
                      <Image
                        src={context.deviceModelImageUrl}
                        alt={context.pcsBrandModel || 'Device Model'}
                        style={{
                          filter:
                            colorScheme === 'dark'
                              ? 'invert(1) brightness(0.7)'
                              : 'none',
                        }}
                        maw={280}
                        mah={280}
                        fit="contain"
                        radius="md"
                        mx="auto"
                        onError={handleDeviceModelImageError}
                      />
                      <Text
                        size="sm"
                        c="dimmed"
                        style={{ fontStyle: 'italic' }}
                        ta="center"
                      >
                        No technical information available
                      </Text>
                    </Stack>
                  )}
                </div>
              </Modal>
            </>
          ) : context.deviceModels.isLoading ? (
            <Skeleton w={100} h={100} radius="md" />
          ) : (
            <Box
              w={100}
              h={100}
              style={{
                flexShrink: 0,
                padding: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Image
                src={deviceModelIconUrl}
                alt="Device Type Icon"
                w="100%"
                h="100%"
                fit="contain"
                radius="md"
                style={{
                  objectFit: 'contain',
                  filter:
                    colorScheme === 'dark'
                      ? 'invert(1) brightness(0.7)'
                      : 'none',
                }}
              />
            </Box>
          )}
          <Stack gap="xs">
            <Group gap="md">
              <Text
                fw={600}
                size="lg"
                style={{ cursor: 'pointer' }}
                onClick={() => setImageModalOpened(true)}
              >
                {context.deviceModels.isLoading ? (
                  'Loading...'
                ) : context.pcsBrandModel ? (
                  <>
                    {context.pcsBrandModel}
                    <Text component="span" c="dimmed" fw={400} ml="xs" mr="xs">
                      (x {context.deviceCount})
                    </Text>
                    <ActionIcon
                      variant="transparent"
                      size="sm"
                      onClick={(event) => {
                        event.stopPropagation()
                        setImageModalOpened(true)
                      }}
                      style={{
                        display: 'inline-flex',
                        verticalAlign: 'middle',
                        cursor: 'pointer',
                      }}
                    >
                      <IconInfoCircle size={18} />
                    </ActionIcon>
                  </>
                ) : null}
              </Text>
            </Group>
            <Group gap="lg">
              <Text size="sm" c="dimmed">
                MWac per device:{' '}
                <Text component="span" fw={500}>
                  {context.mwacPerDevice !== null
                    ? context.mwacPerDevice.toFixed(2)
                    : 'N/A'}
                </Text>
              </Text>
              <Text size="sm" c="dimmed">
                Total MWac:{' '}
                <Text component="span" fw={500}>
                  {context.totalMWac !== null
                    ? context.totalMWac.toFixed(2)
                    : 'N/A'}
                </Text>
                {context.project?.poi && (
                  <>
                    {' '}
                    <Text component="span" c="dimmed" size="xs">
                      (POI limit: {context.project.poi.toFixed(2)} MWac)
                    </Text>
                  </>
                )}
              </Text>
            </Group>
          </Stack>
        </Group>
        <Group gap="xl" align="flex-start">
          <Stack gap="xs" align="flex-start">
            <Text size="md" fw={500}>
              Installed:
            </Text>
            <Group gap="xs" align="center">
              <Text size="sm" c="dimmed">
                Placed in Service:{' '}
                {context.projectQuery.isLoading ? (
                  <Text component="span" fw={500}>
                    Loading...
                  </Text>
                ) : context.project?.placed_in_service_date ? (
                  <Text component="span" fw={500}>
                    {dayjs(context.project.placed_in_service_date).format(
                      'MMM D, YYYY',
                    )}
                  </Text>
                ) : context.isAdmin ? (
                  <Link
                    to={`/projects/${context.projectId}/settings?tab=project-info`}
                    style={{ textDecoration: 'none', color: 'inherit' }}
                  >
                    <Text
                      component="span"
                      fw={500}
                      style={{ cursor: 'pointer' }}
                    >
                      Set
                    </Text>
                  </Link>
                ) : (
                  <Text component="span" fw={500}>
                    Not set
                  </Text>
                )}
              </Text>
              {context.isAdmin && (
                <ActionIcon
                  variant="transparent"
                  size="sm"
                  component={Link}
                  to={`/projects/${context.projectId}/settings?tab=project-info`}
                  style={{ cursor: 'pointer' }}
                >
                  <IconEdit size={16} />
                </ActionIcon>
              )}
            </Group>
          </Stack>
          <Stack gap="xs" align="flex-start">
            <Group gap="xs" align="center">
              <Text size="md" fw={500}>
                Service by:
              </Text>
              {context.isAdmin && (
                <ActionIcon
                  variant="transparent"
                  size="sm"
                  component={Link}
                  to={`/projects/${context.projectId}/settings?tab=om-contractors`}
                  style={{ cursor: 'pointer' }}
                >
                  <IconEdit size={16} />
                </ActionIcon>
              )}
            </Group>
            {context.omContractor?.contractor_addressee ? (
              <>
                <Text size="sm" c="dimmed">
                  Name:{' '}
                  <Text component="span" fw={500}>
                    {context.omContractor.contractor_addressee}
                  </Text>
                </Text>
                {(context.omContractor.contractor_phone ||
                  context.omContractor.contractor_email) && (
                  <Group gap="xs" align="center">
                    <Text size="sm" c="dimmed">
                      Contact:
                    </Text>
                    {context.omContractor.contractor_phone && (
                      <Group gap={4} align="center">
                        <IconPhone size={14} />
                        <Text size="sm" fw={500}>
                          {context.omContractor.contractor_phone}
                        </Text>
                      </Group>
                    )}
                    {context.omContractor.contractor_email && (
                      <Group gap={4} align="center">
                        <IconMail size={14} />
                        <Text size="sm" fw={500}>
                          {context.omContractor.contractor_email}
                        </Text>
                      </Group>
                    )}
                  </Group>
                )}
              </>
            ) : (
              <Group gap="xs" align="center">
                <Text size="sm" c="dimmed" style={{ fontStyle: 'italic' }}>
                  O&M provider scope not set
                </Text>
              </Group>
            )}
          </Stack>
        </Group>
      </Group>
    </Stack>
  )
}
