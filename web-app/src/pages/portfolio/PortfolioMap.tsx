import { useGetUserProjects } from '@/api/v1/admin/user_projects'
import { useGetHailForecastPolygons } from '@/api/v1/gis/noaa'
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
import Map, { Layer, Marker, Source } from 'react-map-gl'
import { Link } from 'react-router-dom'

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

  if (isLoading || isUserProjectsLoading) {
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

  const hailLegendItems = [
    { value: 5, color: HAIL_COLOR[5], label: '5%' },
    { value: 15, color: HAIL_COLOR[15], label: '15%' },
    { value: 30, color: HAIL_COLOR[30], label: '30%' },
    { value: 45, color: HAIL_COLOR[45], label: '45%' },
    { value: 60, color: HAIL_COLOR[60], label: '60%' },
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
            You have "Favorites Only" selected but haven't favorited any
            projects yet. You can favorite projects on the Portfolio Home
            screen.
          </Alert>
        </div>
      )}
      <Map
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
      </Map>
      <div style={{ position: 'absolute', top: 16, right: 16, zIndex: 1 }}>
        <Stack gap="sm">
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
                    onChange={(event) =>
                      setShowHail(event.currentTarget.checked)
                    }
                    label="Hail Forecast (Day 1)"
                  />
                  <Switch
                    checked={showHailDay2}
                    onChange={(event) =>
                      setShowHailDay2(event.currentTarget.checked)
                    }
                    label="Hail Forecast (Day 2)"
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
                      onChange={() => {
                        setSelectedProjectTypes((prev) =>
                          prev.includes(projectType.project_type_id)
                            ? prev.filter(
                                (id) => id !== projectType.project_type_id,
                              )
                            : [...prev, projectType.project_type_id],
                        )
                      }}
                      label={projectType.name_long}
                    />
                  ))}
                </Stack>
              </Accordion.Panel>
            </Accordion.Item>
          </Accordion>

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
                            Hail forecast probabilities are provided by NOAA's
                            Storm Prediction Center and represent the likelihood
                            of severe hail (≥1 inch diameter) occurring within
                            25 miles of any point during the forecast period.
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
        </Stack>
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
