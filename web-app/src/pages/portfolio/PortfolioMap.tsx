import { useGetUserProjects } from '@/api/v1/admin/user_projects'
import {
  useGetFireOutlook,
  useGetHailForecastPolygons,
  useGetTornadoOutlook,
  useGetWindOutlook,
} from '@/api/v1/gis/noaa'
import {
  ProjectTypeId,
  useGetProjectTypes,
} from '@/api/v1/operational/project_types'
import { useGetProjects } from '@/api/v1/operational/projects'
import { NoData, PageError } from '@/components/Error'
import { MapSettings } from '@/components/GIS'
import { PageLoader } from '@/components/Loading'
import Attribution from '@/components/gis/Attribution'
import { GISContext } from '@/contexts/GISContext'
import * as gisUtils from '@/utils/GIS'
import { useAuth } from '@clerk/clerk-react'
import { Accordion } from '@mantine/core'
import {
  ActionIcon,
  Alert,
  Anchor,
  Box,
  Card,
  Group,
  HoverCard,
  Stack,
  Switch,
  Text,
  useComputedColorScheme,
} from '@mantine/core'
import { useLocalStorage } from '@mantine/hooks'
import {
  IconBattery4,
  IconExternalLink,
  IconInfoCircle,
  IconSolarElectricity,
  IconSolarPanel,
} from '@tabler/icons-react'
import { useContext, useEffect } from 'react'
import MapboxMap, { Layer, Marker, Source } from 'react-map-gl/mapbox'
import { Link } from 'react-router'

import styles from './PortfolioMap.module.css'

const DAY_1_OPACITY = 0.8
const DAY_2_OPACITY = 0.4
const FILL_OUTLINE_COLOR = '#000000'

const HAIL_COLOR = {
  5: '#C6A294',
  15: '#FFFF00',
  30: '#FF0000',
  45: '#FF00C5',
  60: '#A80084',
  default: '#000000',
}

const TORNADO_COLOR = {
  2: '#008B00',
  5: '#8B4513',
  10: '#FFC800',
  15: '#FF0000',
  30: '#FF00FF',
  45: '#912EFF',
  60: '#00C8FF',
  default: '#000000',
}

const WIND_COLOR = {
  5: '#C6A294',
  15: '#FFFF00',
  30: '#FF0000',
  45: '#FF00C5',
  60: '#A80084',
  default: '#000000',
}

const FIRE_COLOR = {
  5: '#FFC800',
  8: '#FF0000',
  10: '#FF00FF',
  default: '#000000',
}

const tileUrl = (tile: string): string => {
  const appid = import.meta.env.VITE_OPENWEATHERMAP_APP_ID
  return `https://tile.openweathermap.org/map/${tile}/{z}/{x}/{y}.png?appid=${appid}`
}

const PortfolioMap = () => {
  const computedColorScheme = useComputedColorScheme('dark')
  const context = useContext(GISContext)

  const [showClouds, setShowClouds] = useLocalStorage({
    key: 'show-clouds',
    defaultValue: true,
  })
  const [showPrecipitation, setShowPrecipitation] = useLocalStorage({
    key: 'show-precipitation',
    defaultValue: true,
  })
  const [showHail, setShowHail] = useLocalStorage({
    key: 'show-hail',
    defaultValue: false,
  })
  const [showHailDay2, setShowHailDay2] = useLocalStorage({
    key: 'show-hail-day2',
    defaultValue: false,
  })
  const [showTornado, setShowTornado] = useLocalStorage({
    key: 'show-tornado',
    defaultValue: false,
  })
  const [showWind, setShowWind] = useLocalStorage({
    key: 'show-wind',
    defaultValue: false,
  })
  const [showFire, setShowFire] = useLocalStorage({
    key: 'show-fire',
    defaultValue: false,
  })
  const [showFavorites, setShowFavorites] = useLocalStorage({
    key: 'show-favorites',
    defaultValue: false,
  })
  const [selectedProjectTypes, setSelectedProjectTypes] = useLocalStorage<
    ProjectTypeId[]
  >({
    key: 'selected-project-types',
    defaultValue: [ProjectTypeId.PV, ProjectTypeId.BESS, ProjectTypeId.PV_BESS],
  })

  const { userId } = useAuth()

  const { data, isLoading, error } = useGetProjects({
    queryParams: { deep: true },
  })
  const { data: projectTypes } = useGetProjectTypes()
  const { data: userProjects, isLoading: isUserProjectsLoading } =
    useGetUserProjects({
      pathParams: { userId: userId || '' },
      queryOptions: {
        enabled: !!userId,
      },
    })

  const { data: hailData } = useGetHailForecastPolygons({
    arcgis_layer_id: 5, // Day 1
    queryOptions: {
      enabled: showHail,
    },
  })

  const { data: hailDay2Data } = useGetHailForecastPolygons({
    arcgis_layer_id: 13, // Day 2
    queryOptions: {
      enabled: showHailDay2,
    },
  })

  const { data: tornadoData } = useGetTornadoOutlook({
    queryOptions: {
      enabled: showTornado,
    },
  })

  const { data: windData } = useGetWindOutlook({
    queryOptions: {
      enabled: showWind,
    },
  })

  const { data: fireData } = useGetFireOutlook({
    queryOptions: {
      enabled: showFire,
    },
  })

  useEffect(() => {
    if (projectTypes && selectedProjectTypes.length === 0) {
      const storedProjectTypes = localStorage.getItem('selected-project-types')
      if (!storedProjectTypes) {
        setSelectedProjectTypes(projectTypes.map((pt) => pt.project_type_id))
      }
    }
  }, [projectTypes, selectedProjectTypes, setSelectedProjectTypes])

  if (!context) {
    throw new Error('GISContext is not provided')
  }

  if (
    import.meta.env.VITE_ENVIRONMENT !== 'development' &&
    (isLoading || isUserProjectsLoading)
  ) {
    return <PageLoader />
  }

  if (error) {
    return <PageError error={error} />
  }

  if (!data) {
    return <NoData />
  }

  const cloudTileURL = tileUrl('clouds_new')
  const precipitationTileURL = tileUrl('precipitation_new')

  const icon_style = {
    width: '25px',
    height: '25px',
    color: 'var(--mantine-primary-color-filled)',
  }

  const { showSatellite } = context

  const filteredProjects = data
    .filter((project) => {
      if (showFavorites) {
        return userProjects?.some(
          (up) =>
            up.operational_project_id === project.project_id && up.is_favorited,
        )
      }
      return true
    })
    .filter((project) => {
      return selectedProjectTypes.includes(project.project_type_id)
    })

  const hasFavoritedProjects =
    userProjects?.some((up) => up.is_favorited) || false
  const showFavoritesWarning = showFavorites && !hasFavoritedProjects
  const showHailLegend = showHail || showHailDay2
  const showTornadoLegend = showTornado
  const showWindLegend = showWind
  const showFireLegend = showFire

  const hailLegendItems = [
    { value: 5, color: HAIL_COLOR[5], label: '5%' },
    { value: 15, color: HAIL_COLOR[15], label: '15%' },
    { value: 30, color: HAIL_COLOR[30], label: '30%' },
    { value: 45, color: HAIL_COLOR[45], label: '45%' },
    { value: 60, color: HAIL_COLOR[60], label: '60%' },
  ]

  const tornadoLegendItems = [
    { value: 2, color: TORNADO_COLOR[2], label: '2%' },
    { value: 5, color: TORNADO_COLOR[5], label: '5%' },
    { value: 10, color: TORNADO_COLOR[10], label: '10%' },
    { value: 15, color: TORNADO_COLOR[15], label: '15%' },
    { value: 30, color: TORNADO_COLOR[30], label: '30%' },
    { value: 45, color: TORNADO_COLOR[45], label: '45%' },
    { value: 60, color: TORNADO_COLOR[60], label: '60%' },
  ]

  const windLegendItems = [
    { value: 5, color: WIND_COLOR[5], label: '5%' },
    { value: 15, color: WIND_COLOR[15], label: '15%' },
    { value: 30, color: WIND_COLOR[30], label: '30%' },
    { value: 45, color: WIND_COLOR[45], label: '45%' },
    { value: 60, color: WIND_COLOR[60], label: '60%' },
  ]

  const fireLegendItems = [
    { value: 5, color: FIRE_COLOR[5], label: 'Elevated' },
    { value: 8, color: FIRE_COLOR[8], label: 'Critical' },
    { value: 10, color: FIRE_COLOR[10], label: 'Extreme' },
  ]

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      {showFavoritesWarning && (
        <div
          style={{
            position: 'absolute',
            top: 16,
            left: 16,
            zIndex: 2,
            maxWidth: '300px',
          }}
        >
          <Alert
            icon={<IconInfoCircle size="1rem" />}
            title="No Favorite Projects"
            // color="yellow"
            autoContrast={true}
            styles={{
              root: {
                // Adjust the rgba value for your desired color and opacity
                // Example: slightly more opaque than the previous
                backgroundColor: 'rgba(100, 90, 45, 0.9)', // Changed alpha from 0.8 to 0.9 for more opacity
                color: 'white', // You might need to explicitly set text color for contrast
              },
            }}
          >
            You have &quot;Favorites Only&quot; selected but haven&apos;t
            favorited any projects yet. You can favorite projects on the
            Portfolio Home screen.
          </Alert>
        </div>
      )}
      <MapboxMap
        initialViewState={{
          bounds: [-124.4, 24.54, -66.93, 49.38], // USA lower 48 bounds
          fitBoundsOptions: {
            padding: 50,
          },
        }}
        style={{
          borderBottomLeftRadius: 'inherit',
          borderBottomRightRadius: 'inherit',
        }}
        mapStyle={gisUtils.mapStyle({
          empty: false,
          satellite: showSatellite,
          theme: computedColorScheme,
        })}
        mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
      >
        {showClouds && (
          <Source
            id="weather-data"
            type="raster"
            tiles={[cloudTileURL]} // Use the template URL here
            tileSize={256} // Typically, slippy map tiles are 256x256
          >
            <Layer id="weather-layer" type="raster" source="weather-data" />
          </Source>
        )}
        {showPrecipitation && (
          <Source
            id="precipitation-data"
            type="raster"
            tiles={[precipitationTileURL]} // Use the template URL here
            tileSize={256} // Typically, slippy map tiles are 256x256
          >
            <Layer
              id="precipitation-layer"
              type="raster"
              source="precipitation-data"
            />
          </Source>
        )}
        {showHail && hailData && (
          <Source id="hail-data" type="geojson" data={hailData}>
            <Layer
              id="hail-layer"
              type="fill"
              source="hail-data"
              paint={{
                'fill-color': [
                  'match',
                  ['get', 'dn'],
                  5,
                  HAIL_COLOR[5],
                  15,
                  HAIL_COLOR[15],
                  30,
                  HAIL_COLOR[30],
                  45,
                  HAIL_COLOR[45],
                  60,
                  HAIL_COLOR[60],
                  HAIL_COLOR.default,
                ],
                'fill-opacity': DAY_1_OPACITY,
                'fill-outline-color': FILL_OUTLINE_COLOR,
              }}
            />
          </Source>
        )}
        {showHailDay2 && hailDay2Data && (
          <Source id="hail-day2-data" type="geojson" data={hailDay2Data}>
            <Layer
              id="hail-day2-layer"
              type="fill"
              source="hail-day2-data"
              paint={{
                'fill-color': [
                  'match',
                  ['get', 'dn'],
                  5,
                  HAIL_COLOR[5],
                  15,
                  HAIL_COLOR[15],
                  30,
                  HAIL_COLOR[30],
                  45,
                  HAIL_COLOR[45],
                  60,
                  HAIL_COLOR[60],
                  HAIL_COLOR.default,
                ],
                'fill-opacity': DAY_2_OPACITY,
                'fill-outline-color': FILL_OUTLINE_COLOR,
              }}
            />
          </Source>
        )}
        {showTornado && tornadoData && (
          <Source id="tornado-data" type="geojson" data={tornadoData}>
            <Layer
              id="tornado-layer"
              type="fill"
              source="tornado-data"
              paint={{
                'fill-color': [
                  'match',
                  ['get', 'dn'],
                  2,
                  TORNADO_COLOR[2],
                  5,
                  TORNADO_COLOR[5],
                  10,
                  TORNADO_COLOR[10],
                  15,
                  TORNADO_COLOR[15],
                  30,
                  TORNADO_COLOR[30],
                  45,
                  TORNADO_COLOR[45],
                  60,
                  TORNADO_COLOR[60],
                  TORNADO_COLOR.default,
                ],
                'fill-opacity': DAY_1_OPACITY,
                'fill-outline-color': FILL_OUTLINE_COLOR,
              }}
            />
          </Source>
        )}
        {showWind && windData && (
          <Source id="wind-data" type="geojson" data={windData}>
            <Layer
              id="wind-layer"
              type="fill"
              source="wind-data"
              paint={{
                'fill-color': [
                  'match',
                  ['get', 'dn'],
                  5,
                  WIND_COLOR[5],
                  15,
                  WIND_COLOR[15],
                  30,
                  WIND_COLOR[30],
                  45,
                  WIND_COLOR[45],
                  60,
                  WIND_COLOR[60],
                  WIND_COLOR.default,
                ],
                'fill-opacity': DAY_1_OPACITY,
                'fill-outline-color': FILL_OUTLINE_COLOR,
              }}
            />
          </Source>
        )}
        {showFire && fireData && (
          <Source id="fire-data" type="geojson" data={fireData}>
            <Layer
              id="fire-layer"
              type="fill"
              source="fire-data"
              paint={{
                'fill-color': [
                  'match',
                  ['get', 'dn'],
                  5,
                  FIRE_COLOR[5],
                  8,
                  FIRE_COLOR[8],
                  10,
                  FIRE_COLOR[10],
                  FIRE_COLOR.default,
                ],
                'fill-opacity': DAY_1_OPACITY,
                'fill-outline-color': FILL_OUTLINE_COLOR,
              }}
            />
          </Source>
        )}
        {filteredProjects.map((project) => (
          <Marker
            key={project.project_id}
            longitude={project.point.coordinates[0]}
            latitude={project.point.coordinates[1]}
          >
            <Link to={`/projects/${project.project_id}`}>
              <HoverCard shadow="md">
                <HoverCard.Target>
                  <div>
                    {(() => {
                      switch (project.project_type_id) {
                        case ProjectTypeId.PV:
                          return <IconSolarPanel style={icon_style} />
                        case ProjectTypeId.BESS:
                          return <IconBattery4 style={icon_style} />
                        case ProjectTypeId.PV_BESS:
                          return <IconSolarElectricity style={icon_style} />
                        default:
                          return <IconSolarPanel style={icon_style} />
                      }
                    })()}
                  </div>
                </HoverCard.Target>
                <HoverCard.Dropdown>
                  <Text>{project.name_long}</Text>
                </HoverCard.Dropdown>
              </HoverCard>
            </Link>
          </Marker>
        ))}
      </MapboxMap>
      <div
        style={{
          position: 'absolute',
          top: 16,
          right: 16,
          bottom: 16,
          zIndex: 1,
          display: 'flex',
          flexDirection: 'column',
          maxHeight: 'calc(100vh - 32px)',
          gap: 'var(--mantine-spacing-sm)',
        }}
      >
        <Accordion
          variant="contained"
          radius="md"
          classNames={{ panel: styles.panel, content: styles.content }}
        >
          <Accordion.Item value="photos" bg="var(--mantine-color-body)">
            <Accordion.Control>Environmental</Accordion.Control>
            <Accordion.Panel>
              <Stack gap="sm">
                <Switch
                  checked={showClouds}
                  onChange={(event) =>
                    setShowClouds(event.currentTarget.checked)
                  }
                  label="Cloud Overlay"
                />
                <Switch
                  checked={showPrecipitation}
                  onChange={(event) =>
                    setShowPrecipitation(event.currentTarget.checked)
                  }
                  label="Precipitation Overlay"
                />
                <Switch
                  checked={showHail}
                  onChange={(event) => setShowHail(event.currentTarget.checked)}
                  label="Hail Forecast (Day 1)"
                />
                <Switch
                  checked={showHailDay2}
                  onChange={(event) =>
                    setShowHailDay2(event.currentTarget.checked)
                  }
                  label="Hail Forecast (Day 2)"
                />
                <Switch
                  checked={showTornado}
                  onChange={(event) =>
                    setShowTornado(event.currentTarget.checked)
                  }
                  onClick={(e) => e.stopPropagation()}
                  label="Tornado Outlook"
                />
                <Switch
                  checked={showWind}
                  onChange={(event) => setShowWind(event.currentTarget.checked)}
                  onClick={(e) => e.stopPropagation()}
                  label="Wind Outlook"
                />

                <Switch
                  checked={showFire}
                  onChange={(event) => setShowFire(event.currentTarget.checked)}
                  onClick={(e) => e.stopPropagation()}
                  label="Fire Outlook"
                />
              </Stack>
            </Accordion.Panel>
          </Accordion.Item>
          <Accordion.Item value="print" bg="var(--mantine-color-body)">
            <Accordion.Control>Projects</Accordion.Control>
            <Accordion.Panel>
              <Stack gap="sm">
                <Switch
                  checked={showFavorites}
                  onChange={(event) =>
                    setShowFavorites(event.currentTarget.checked)
                  }
                  label="Favorites Only"
                />
                {projectTypes?.map((projectType) => (
                  <Switch
                    key={projectType.project_type_id}
                    checked={selectedProjectTypes.includes(
                      projectType.project_type_id,
                    )}
                    onChange={(event) => {
                      if (event.currentTarget.checked) {
                        setSelectedProjectTypes((prev) => [
                          ...prev,
                          projectType.project_type_id,
                        ])
                      } else {
                        setSelectedProjectTypes((prev) =>
                          prev.filter(
                            (id) => id !== projectType.project_type_id,
                          ),
                        )
                      }
                    }}
                    onClick={(e) => e.stopPropagation()}
                    label={projectType.name_long}
                  />
                ))}
              </Stack>
            </Accordion.Panel>
          </Accordion.Item>
        </Accordion>

        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            paddingRight: '4px',
            minHeight: 0,
          }}
        >
          <Stack gap="sm">
            {showHailLegend && (
              <Card withBorder shadow="sm" radius="md" px="sm">
                <Card.Section inheritPadding py="sm">
                  <Stack gap="xs">
                    <Group gap={2} align="center">
                      <Text size="sm" fw={500}>
                        Hail Forecast Probability
                      </Text>
                      <HoverCard shadow="md">
                        <HoverCard.Target>
                          <ActionIcon size="xs" variant="transparent">
                            <IconInfoCircle size={16} stroke={1.5} />
                          </ActionIcon>
                        </HoverCard.Target>
                        <HoverCard.Dropdown maw="300px">
                          <Stack gap="xs">
                            <Text size="sm">
                              Hail forecast probabilities are provided by
                              NOAA&apos;s Storm Prediction Center and represent
                              the likelihood of severe hail (≥1 inch diameter)
                              occurring within 25 miles of any point during the
                              forecast period.
                            </Text>
                            <Anchor
                              href="https://www.spc.noaa.gov/products/"
                              target="_blank"
                              rel="noopener noreferrer"
                              size="sm"
                            >
                              <Group gap="xs" align="center">
                                <Text>Learn more at NOAA SPC</Text>
                                <IconExternalLink size={14} />
                              </Group>
                            </Anchor>
                          </Stack>
                        </HoverCard.Dropdown>
                      </HoverCard>
                    </Group>
                    {hailLegendItems.map((item) => (
                      <Group key={item.value} gap="xs" align="center">
                        <div
                          style={{
                            width: '16px',
                            height: '16px',
                            backgroundColor: item.color,
                            border: '1px solid #000',
                            borderRadius: '2px',
                          }}
                        />
                        <Text size="xs">{item.label}</Text>
                      </Group>
                    ))}
                  </Stack>
                </Card.Section>
              </Card>
            )}
            {showTornadoLegend && (
              <Card withBorder shadow="sm" radius="md" px="sm">
                <Card.Section inheritPadding py="sm">
                  <Stack gap="xs">
                    <Group gap={2} align="center">
                      <Text size="sm" fw={500}>
                        Tornado Outlook
                      </Text>
                      <HoverCard shadow="md">
                        <HoverCard.Target>
                          <ActionIcon size="xs" variant="transparent">
                            <IconInfoCircle size={16} stroke={1.5} />
                          </ActionIcon>
                        </HoverCard.Target>
                        <HoverCard.Dropdown maw="300px">
                          <Stack gap="xs">
                            <Text size="sm">
                              Tornado outlook probabilities are provided by
                              NOAA&apos;s Storm Prediction Center and represent
                              the likelihood of a tornado occurring within 25
                              miles of any point during the forecast period.
                            </Text>
                            <Anchor
                              href="https://www.spc.noaa.gov/products/outlook/day1otlk.html"
                              target="_blank"
                              rel="noopener noreferrer"
                              size="sm"
                            >
                              <Group gap="xs" align="center">
                                <Text>Learn more at NOAA SPC</Text>
                                <IconExternalLink size={14} />
                              </Group>
                            </Anchor>
                          </Stack>
                        </HoverCard.Dropdown>
                      </HoverCard>
                    </Group>
                    {tornadoLegendItems.map((item) => (
                      <Group key={item.value} gap="xs" align="center">
                        <div
                          style={{
                            width: '16px',
                            height: '16px',
                            backgroundColor: item.color,
                            border: '1px solid #000',
                            borderRadius: '2px',
                          }}
                        />
                        <Text size="xs">{item.label}</Text>
                      </Group>
                    ))}
                  </Stack>
                </Card.Section>
              </Card>
            )}
            {showWindLegend && (
              <Card withBorder shadow="sm" radius="md" px="sm">
                <Card.Section inheritPadding py="sm">
                  <Stack gap="xs">
                    <Group gap={2} align="center">
                      <Text size="sm" fw={500}>
                        Wind Outlook
                      </Text>
                      <HoverCard shadow="md">
                        <HoverCard.Target>
                          <ActionIcon size="xs" variant="transparent">
                            <IconInfoCircle size={16} stroke={1.5} />
                          </ActionIcon>
                        </HoverCard.Target>
                        <HoverCard.Dropdown maw="300px">
                          <Stack gap="xs">
                            <Text size="sm">
                              Wind outlook probabilities are provided by
                              NOAA&apos;s Storm Prediction Center and represent
                              the likelihood of severe wind (≥58 mph) occurring
                              within 25 miles of any point during the forecast
                              period.
                            </Text>
                            <Anchor
                              href="https://www.spc.noaa.gov/products/outlook/day1otlk.html"
                              target="_blank"
                              rel="noopener noreferrer"
                              size="sm"
                            >
                              <Group gap="xs" align="center">
                                <Text>Learn more at NOAA SPC</Text>
                                <IconExternalLink size={14} />
                              </Group>
                            </Anchor>
                          </Stack>
                        </HoverCard.Dropdown>
                      </HoverCard>
                    </Group>
                    {windLegendItems.map((item) => (
                      <Group key={item.value} gap="xs" align="center">
                        <div
                          style={{
                            width: '16px',
                            height: '16px',
                            backgroundColor: item.color,
                            border: '1px solid #000',
                            borderRadius: '2px',
                          }}
                        />
                        <Text size="xs">{item.label}</Text>
                      </Group>
                    ))}
                  </Stack>
                </Card.Section>
              </Card>
            )}
            {showFireLegend && (
              <Card withBorder shadow="sm" radius="md" px="sm">
                <Card.Section inheritPadding py="sm">
                  <Stack gap="xs">
                    <Group gap={2} align="center">
                      <Text size="sm" fw={500}>
                        Fire Outlook
                      </Text>
                      <HoverCard shadow="md">
                        <HoverCard.Target>
                          <ActionIcon size="xs" variant="transparent">
                            <IconInfoCircle size={16} stroke={1.5} />
                          </ActionIcon>
                        </HoverCard.Target>
                        <HoverCard.Dropdown maw="300px">
                          <Stack gap="xs">
                            <Text size="sm">
                              Fire weather outlook categories are provided by
                              NOAA&apos;s Storm Prediction Center and indicate
                              areas where weather conditions could contribute to
                              dangerous fire behavior.
                            </Text>
                            <Anchor
                              href="https://www.spc.noaa.gov/products/fire_wx/"
                              target="_blank"
                              rel="noopener noreferrer"
                              size="sm"
                            >
                              <Group gap="xs" align="center">
                                <Text>Learn more at NOAA SPC</Text>
                                <IconExternalLink size={14} />
                              </Group>
                            </Anchor>
                          </Stack>
                        </HoverCard.Dropdown>
                      </HoverCard>
                    </Group>
                    {fireLegendItems.map((item) => (
                      <Group key={item.value} gap="xs" align="center">
                        <div
                          style={{
                            width: '16px',
                            height: '16px',
                            backgroundColor: item.color,
                            border: '1px solid #000',
                            borderRadius: '2px',
                          }}
                        />
                        <Text size="xs">{item.label}</Text>
                      </Group>
                    ))}
                  </Stack>
                </Card.Section>
              </Card>
            )}
          </Stack>
        </div>
      </div>
      <Box
        style={{ position: 'absolute', bottom: 0, left: 0, zIndex: 10 }}
        px="md"
        py="md"
      >
        <MapSettings disableLabels />
      </Box>
      <Attribution />
    </div>
  )
}

export default PortfolioMap
