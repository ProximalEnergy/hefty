import { useGetUserType } from '@/api/admin'
import { ProjectTypeEnum } from '@/api/enumerations'
import { useGetUserProjects } from '@/api/v1/admin/user_projects'
import {
  getNWSWindspeedTileUrl,
  getTemperatureTileUrl,
  useGetFireOutlook,
  useGetHailForecastPolygons,
  useGetTornadoOutlook,
  useGetWindOutlook,
} from '@/api/v1/gis/noaa'
import { useGetProjectTypes } from '@/api/v1/operational/project_types'
import { Project, useGetProjects } from '@/api/v1/operational/projects'
import { NoData, PageError } from '@/components/Error'
import { MapSettings } from '@/components/GIS'
import { PageLoader } from '@/components/Loading'
import Attribution from '@/components/gis/Attribution'
import { WeatherHoverCard } from '@/components/portfolio/WeatherHoverCard'
import { GISContext } from '@/contexts/GISContext'
import * as gisUtils from '@/utils/GIS'
import { useAuth } from '@clerk/clerk-react'
import {
  Accordion,
  ActionIcon,
  Alert,
  Anchor,
  Box,
  Card,
  Divider,
  Group,
  HoverCard,
  SegmentedControl,
  Stack,
  Switch,
  Text,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { useLocalStorage } from '@mantine/hooks'
import {
  IconBattery4,
  IconExternalLink,
  IconInfoCircle,
  IconSolarElectricity,
  IconSolarPanel,
  IconTemperature,
  IconWind,
} from '@tabler/icons-react'
import { Feature } from 'geojson'
import {
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import MapboxMap, {
  Layer,
  MapMouseEvent,
  Marker,
  Source,
} from 'react-map-gl/mapbox'
import { Link } from 'react-router'

import styles from './PortfolioMap.module.css'

// Project Type Icon Component
const ProjectTypeIcon = ({
  project_type_id,
  icon_style,
}: {
  project_type_id: number
  icon_style: React.CSSProperties
}) => {
  switch (project_type_id) {
    case ProjectTypeEnum.PV:
      return <IconSolarPanel style={icon_style} />
    case ProjectTypeEnum.BESS:
      return <IconBattery4 style={icon_style} />
    case ProjectTypeEnum.PVS:
      return <IconSolarElectricity style={icon_style} />
    default:
      return <IconSolarPanel style={icon_style} />
  }
}

// Project Marker Component with Hover Card
const ProjectMarker = ({
  project,
  icon_style,
}: {
  project: Project
  icon_style: React.CSSProperties
}) => {
  const [isHoverCardOpen, setIsHoverCardOpen] = useState(false)

  return (
    <Marker
      key={project.project_id}
      longitude={project.point.coordinates[0]}
      latitude={project.point.coordinates[1]}
    >
      <HoverCard
        shadow="md"
        openDelay={200}
        closeDelay={100}
        width={450}
        onOpen={() => {
          queueMicrotask(() => setIsHoverCardOpen(true))
        }}
        onClose={() => {
          queueMicrotask(() => setIsHoverCardOpen(false))
        }}
      >
        <HoverCard.Target>
          <Link
            to={`/projects/${project.project_id}`}
            onClick={(e) => e.stopPropagation()}
          >
            <div>
              <ProjectTypeIcon
                project_type_id={project.project_type_id}
                icon_style={icon_style}
              />
            </div>
          </Link>
        </HoverCard.Target>
        {isHoverCardOpen && <WeatherHoverCard project={project} />}
      </HoverCard>
    </Marker>
  )
}

const DAY_1_OPACITY = 0.6
const DAY_2_OPACITY = 0.3
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

interface MapboxFeature extends Feature {
  layer?: {
    id: string
  }
  sourceLayer?: string
}

interface FeatureWithLayer {
  feature: Feature
  layerId: string
}

interface HoverInfo {
  features: FeatureWithLayer[]
  x: number
  y: number
}

// Helper function to get layer name from layer ID
const getLayerName = (layerId: string | null): string => {
  switch (layerId) {
    case 'hail-layer':
      return 'Hail Forecast (Day 1)'
    case 'hail-day2-layer':
      return 'Hail Forecast (Day 2)'
    case 'tornado-layer':
      return 'Tornado Outlook'
    case 'wind-layer':
      return 'Wind Outlook'
    case 'fire-layer':
      return 'Fire Outlook'
    default:
      return 'Unknown Layer'
  }
}

// Helper function to format the value based on layer type
const formatValue = (
  layerId: string | null,
  dn: number | undefined,
): string => {
  if (dn === undefined || dn === null) return 'N/A'

  switch (layerId) {
    case 'hail-layer':
    case 'hail-day2-layer':
    case 'tornado-layer':
    case 'wind-layer':
      return `${dn}%`
    case 'fire-layer':
      if (dn === 5) return 'Elevated'
      if (dn === 8) return 'Critical'
      if (dn === 10) return 'Extreme'
      return `${dn}`
    default:
      return `${dn}`
  }
}

const PortfolioMap = () => {
  const computedColorScheme = useComputedColorScheme('dark')
  const theme = useMantineTheme()
  const context = useContext(GISContext)

  const [hoverInfo, setHoverInfo] = useState<HoverInfo>({
    features: [],
    x: 0,
    y: 0,
  })

  const onHover = useCallback((event: MapMouseEvent) => {
    const {
      features,
      point: { x, y },
    } = event

    if (!features || features.length === 0) {
      setHoverInfo({ features: [], x, y })
      return
    }

    // Process all features and extract their layer IDs
    const featuresWithLayers: FeatureWithLayer[] = features
      .map((feature) => {
        // Try to get layer ID from the feature's layer property
        // In Mapbox GL JS, features from queryRenderedFeatures have a layer property
        const mapboxFeature = feature as MapboxFeature
        const layerId =
          mapboxFeature?.layer?.id || mapboxFeature?.sourceLayer || null

        if (layerId) {
          return {
            feature: feature as Feature,
            layerId: layerId,
          }
        }
        return null
      })
      .filter((item): item is FeatureWithLayer => item !== null)

    setHoverInfo({
      features: featuresWithLayers,
      x,
      y,
    })
  }, [])

  const onMouseLeave = useCallback(() => {
    setHoverInfo({ features: [], x: 0, y: 0 })
  }, [])

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
  const [showWindspeed, setShowWindspeed] = useLocalStorage({
    key: 'show-windspeed',
    defaultValue: false,
  })
  const [showTemperature, setShowTemperature] = useLocalStorage({
    key: 'show-temperature',
    defaultValue: false,
  })
  const [showDemo, _setShowDemo] = useLocalStorage({
    key: 'show-demo',
    defaultValue: false,
  })
  const [demoSeed, setDemoSeed] = useState(() => Date.now())

  // Wrapper for setShowDemo that resets seed when demo mode is enabled
  const setShowDemo = (value: boolean | ((prev: boolean) => boolean)) => {
    const willShow = typeof value === 'function' ? value(showDemo) : value
    if (willShow && !showDemo) {
      // Reset seed only when turning demo mode on
      setDemoSeed(Date.now())
    }
    _setShowDemo(willShow)
  }

  // One-time normalization on mount: enforce mutual exclusion if both persisted as true
  useEffect(() => {
    if (showWindspeed && showTemperature) {
      setShowTemperature(false)
    }
  }, []) // oxlint-disable-line react/exhaustive-deps

  // Type definition for demo markers
  type DemoMarker = {
    id: string
    longitude: number
    latitude: number
    project_type_id: number
  }

  // Generate 19 random demo markers with random locations and project types
  // Includes a couple in California and Texas, rest in continental USA interior
  const demoMarkers = useMemo(() => {
    if (!showDemo) return []

    // Use seed-based random number generator for deterministic but varied results
    let seed = demoSeed
    const random = () => {
      seed = (seed * 9301 + 49297) % 233280
      return seed / 233280
    }

    const markers: DemoMarker[] = []
    const projectTypes = [
      ProjectTypeEnum.PV,
      ProjectTypeEnum.BESS,
      ProjectTypeEnum.PVS,
    ]

    // Fixed locations in California (central California, avoiding coast)
    const californiaLocations = [
      { lng: -120.5, lat: 36.5 }, // Central Valley area
      { lng: -118.2, lat: 34.0 }, // Inland Southern California
    ]

    // Fixed locations in Texas (interior Texas)
    const texasLocations = [
      { lng: -98.5, lat: 32.8 }, // Central Texas
      { lng: -97.7, lat: 30.3 }, // South Central Texas
    ]

    // Add California markers
    californiaLocations.forEach((loc, idx) => {
      const projectTypeId =
        projectTypes[Math.floor(random() * projectTypes.length)]
      markers.push({
        id: `demo-ca-${idx}`,
        longitude: loc.lng,
        latitude: loc.lat,
        project_type_id: projectTypeId,
      })
    })

    // Add Texas markers
    texasLocations.forEach((loc, idx) => {
      const projectTypeId =
        projectTypes[Math.floor(random() * projectTypes.length)]
      markers.push({
        id: `demo-tx-${idx}`,
        longitude: loc.lng,
        latitude: loc.lat,
        project_type_id: projectTypeId,
      })
    })

    // Add remaining random markers in continental USA interior (avoiding coasts and major water bodies)
    // Longitude: -110 to -85 (central to eastern USA, avoiding Pacific coast)
    // Latitude: 32 to 45 (avoiding Gulf coast and northern border)
    const minLng = -110
    const maxLng = -85
    const minLat = 32
    const maxLat = 45
    const remainingCount = 19 - markers.length

    for (let i = 0; i < remainingCount; i++) {
      const lng = minLng + random() * (maxLng - minLng)
      const lat = minLat + random() * (maxLat - minLat)
      const projectTypeId =
        projectTypes[Math.floor(random() * projectTypes.length)]

      markers.push({
        id: `demo-${i}`,
        longitude: lng,
        latitude: lat,
        project_type_id: projectTypeId,
      })
    }

    return markers
  }, [showDemo, demoSeed])

  // Draggable position for overlay controls
  const [overlayPosition, setOverlayPosition] = useLocalStorage<{
    x: number
    y: number
  }>({
    key: 'overlay-controls-position',
    defaultValue: { x: 0, y: 16 },
  })
  const [isDragging, setIsDragging] = useState(false)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const overlayRef = useRef<HTMLDivElement>(null)

  // Handle dragging
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging) {
        const newX = e.clientX - dragOffset.x
        const newY = e.clientY - dragOffset.y
        setOverlayPosition({ x: newX, y: newY })
      }
    }

    const handleMouseUp = () => {
      setIsDragging(false)
    }

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      return () => {
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
      }
    }
  }, [isDragging, dragOffset, setOverlayPosition])

  const handleMouseDown = (e: React.MouseEvent) => {
    // Don't start dragging if clicking on interactive elements
    const target = e.target as HTMLElement
    if (
      target.closest('button') ||
      target.closest('input') ||
      target.closest('[role="tab"]') ||
      target.closest('[role="switch"]') ||
      target.closest('[data-segmented-control]') ||
      target.closest('label')
    ) {
      return
    }
    e.preventDefault() // Prevent text selection
    if (overlayRef.current) {
      const rect = overlayRef.current.getBoundingClientRect()
      setDragOffset({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      })
      setIsDragging(true)
    }
  }

  // Handle mutually exclusive selection for windspeed and temperature
  const handleWindspeedChange = (checked: boolean) => {
    if (checked) {
      setShowTemperature(false)
    }
    setShowWindspeed(checked)
  }

  const handleTemperatureChange = (checked: boolean) => {
    if (checked) {
      setShowWindspeed(false)
    }
    setShowTemperature(checked)
  }
  const [showFavorites, setShowFavorites] = useLocalStorage({
    key: 'show-favorites',
    defaultValue: false,
  })
  const [selectedProjectTypes, setSelectedProjectTypes] = useLocalStorage<
    number[]
  >({
    key: 'selected-project-types',
    defaultValue: [
      ProjectTypeEnum.PV,
      ProjectTypeEnum.BESS,
      ProjectTypeEnum.PVS,
    ],
  })

  const { userId } = useAuth()
  const { data: userType } = useGetUserType({})

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

  const isSuperadmin = userType?.name_short === 'superadmin'

  // Reset showDemo if user is not a superadmin
  useEffect(() => {
    if (!isSuperadmin && showDemo) {
      _setShowDemo(false)
    }
  }, [isSuperadmin, showDemo, _setShowDemo])

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
  const windspeedTileURL = getNWSWindspeedTileUrl()
  const temperatureTileURL = getTemperatureTileUrl()

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
  const showWindspeedLegend = showWindspeed
  const showTemperatureLegend = showTemperature

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

  // Temperature legend - OpenWeatherMap temp_new color stops (in °C)
  // Colors match OpenWeatherMap's official temp_new tile layer palette
  const temperatureLegendItems = [
    { value: -40, color: '#000080', label: '-40°C' },
    { value: -20, color: '#0000FF', label: '-20°C' },
    { value: 0, color: '#00FFFF', label: '0°C' },
    { value: 10, color: '#00FF00', label: '10°C' },
    { value: 20, color: '#FFFF00', label: '20°C' },
    { value: 30, color: '#FF8000', label: '30°C' },
    { value: 40, color: '#FF0000', label: '40°C' },
  ]

  // Wind speed legend - OpenWeatherMap wind_new color stops (in m/s)
  // Colors match OpenWeatherMap's official wind_new purple/indigo tile layer palette
  const windspeedLegendItems = [
    { value: 0, color: '#FFFFFF', label: '0 m/s' },
    { value: 5, color: '#E6E6FA', label: '5 m/s' },
    { value: 10, color: '#9370DB', label: '10 m/s' },
    { value: 15, color: '#8A2BE2', label: '15 m/s' },
    { value: 20, color: '#4B0082', label: '20 m/s' },
    { value: 25, color: '#191970', label: '25+ m/s' },
  ]

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      <div
        style={{
          position: 'absolute',
          top: 16,
          left: 16,
          zIndex: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--mantine-spacing-sm)',
          maxWidth: '300px',
        }}
      >
        {showFavoritesWarning && (
          <Alert
            icon={<IconInfoCircle size="1rem" />}
            title="No Favorite Projects"
            autoContrast={true}
            styles={{
              root: {
                backgroundColor: 'rgba(100, 90, 45, 0.9)',
                color: 'white',
              },
            }}
          >
            You have &quot;Favorites Only&quot; selected but haven&apos;t
            favorited any projects yet. You can favorite projects on the
            Portfolio Home screen.
          </Alert>
        )}
        {showTemperatureLegend && (
          <Card
            withBorder
            shadow="sm"
            radius="md"
            px="sm"
            bg="var(--mantine-color-body)"
          >
            <Card.Section inheritPadding py="sm">
              <Stack gap="xs">
                <Text size="sm" fw={500}>
                  Temperature
                </Text>
                {temperatureLegendItems.map((item) => (
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
        {showWindspeedLegend && (
          <Card
            withBorder
            shadow="sm"
            radius="md"
            px="sm"
            bg="var(--mantine-color-body)"
          >
            <Card.Section inheritPadding py="sm">
              <Stack gap="xs">
                <Text size="sm" fw={500}>
                  Wind Speed
                </Text>
                {windspeedLegendItems.map((item) => (
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
      </div>
      {/* Overlay Controls - Draggable */}
      <Box
        ref={overlayRef}
        onMouseDown={handleMouseDown}
        style={{
          position: 'absolute',
          top: overlayPosition.y,
          left: overlayPosition.x === 0 ? '50%' : overlayPosition.x,
          transform: overlayPosition.x === 0 ? 'translateX(-50%)' : 'none',
          zIndex: 2,
          cursor: isDragging ? 'grabbing' : 'grab',
          userSelect: 'none',
        }}
      >
        <Card
          withBorder
          shadow="sm"
          radius="md"
          p="xs"
          bg="var(--mantine-color-body)"
        >
          <Group gap="sm">
            <Switch
              checked={showClouds}
              onChange={(event) => setShowClouds(event.currentTarget.checked)}
              label="Clouds"
              size="sm"
              onMouseDown={(e) => e.stopPropagation()}
            />
            <Switch
              checked={showPrecipitation}
              onChange={(event) =>
                setShowPrecipitation(event.currentTarget.checked)
              }
              label="Precipitation"
              size="sm"
              onMouseDown={(e) => e.stopPropagation()}
            />
            <Divider orientation="vertical" />
            <Box
              onMouseDown={(e) => e.stopPropagation()}
              data-segmented-control
            >
              <SegmentedControl
                value={
                  showWindspeed
                    ? 'windspeed'
                    : showTemperature
                      ? 'temperature'
                      : ''
                }
                onChange={(value) => {
                  if (value === 'windspeed') {
                    handleWindspeedChange(true)
                  } else if (value === 'temperature') {
                    handleTemperatureChange(true)
                  }
                }}
                data={[
                  {
                    label: (
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '4px',
                          verticalAlign: 'middle',
                        }}
                      >
                        <IconWind
                          size={14}
                          stroke={1.5}
                          style={{ flexShrink: 0 }}
                        />
                        <span>Wind Speed</span>
                      </span>
                    ),
                    value: 'windspeed',
                  },
                  {
                    label: (
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '4px',
                          verticalAlign: 'middle',
                        }}
                      >
                        <IconTemperature
                          size={14}
                          stroke={1.5}
                          style={{ flexShrink: 0 }}
                        />
                        <span>Temperature</span>
                      </span>
                    ),
                    value: 'temperature',
                  },
                ]}
                size="sm"
                color={theme.primaryColor}
              />
            </Box>
          </Group>
        </Card>
      </Box>
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
        interactiveLayerIds={[
          ...(showHail ? ['hail-layer'] : []),
          ...(showHailDay2 ? ['hail-day2-layer'] : []),
          ...(showTornado ? ['tornado-layer'] : []),
          ...(showWind ? ['wind-layer'] : []),
          ...(showFire ? ['fire-layer'] : []),
        ]}
        onMouseMove={onHover}
        onMouseLeave={onMouseLeave}
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
        {showWindspeed && (
          <Source
            id="windspeed-data"
            type="raster"
            tiles={[windspeedTileURL]}
            tileSize={256}
          >
            <Layer
              id="windspeed-layer"
              type="raster"
              source="windspeed-data"
              paint={{ 'raster-opacity': 0.6 }}
            />
          </Source>
        )}
        {showTemperature && (
          <Source
            id="temperature-data"
            type="raster"
            tiles={[temperatureTileURL]}
            tileSize={256}
          >
            <Layer
              id="temperature-layer"
              type="raster"
              source="temperature-data"
              paint={{ 'raster-opacity': 0.6 }}
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
          <ProjectMarker
            key={project.project_id}
            project={project}
            icon_style={icon_style}
          />
        ))}
        {showDemo &&
          isSuperadmin &&
          demoMarkers.map((demoMarker: DemoMarker) => (
            <Marker
              key={demoMarker.id}
              longitude={demoMarker.longitude}
              latitude={demoMarker.latitude}
            >
              <div>
                <ProjectTypeIcon
                  project_type_id={demoMarker.project_type_id}
                  icon_style={icon_style}
                />
              </div>
            </Marker>
          ))}
      </MapboxMap>
      {/* Hover Tooltip for Polygon Layers */}
      {hoverInfo.features.length > 0 && (
        <div
          style={{
            position: 'absolute',
            left: hoverInfo.x + 10,
            top: hoverInfo.y - 10,
            backgroundColor:
              computedColorScheme === 'dark'
                ? 'rgba(37, 38, 43, 0.95)'
                : 'rgba(255, 255, 255, 0.95)',
            color: computedColorScheme === 'dark' ? 'white' : 'black',
            padding: '8px 12px',
            borderRadius: '6px',
            fontSize: '12px',
            pointerEvents: 'none',
            zIndex: 10,
            border: `1px solid ${
              computedColorScheme === 'dark' ? '#555' : '#ddd'
            }`,
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
            minWidth: '150px',
            maxWidth: '250px',
          }}
        >
          <Stack gap={6}>
            {hoverInfo.features.map((item, index) => (
              <Stack key={index} gap={2}>
                <Text size="sm" fw={600}>
                  {getLayerName(item.layerId)}
                </Text>
                <Text size="xs">
                  Value:{' '}
                  {formatValue(
                    item.layerId,
                    item.feature?.properties?.dn as number | undefined,
                  )}
                </Text>
                {index < hoverInfo.features.length - 1 && (
                  <Divider
                    size="xs"
                    color={computedColorScheme === 'dark' ? '#555' : '#ddd'}
                    mt={4}
                    mb={2}
                  />
                )}
              </Stack>
            ))}
          </Stack>
        </div>
      )}
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
          <Accordion.Item value="photos" bg="var(--mantine-color-body)">
            <Accordion.Control>Environmental</Accordion.Control>
            <Accordion.Panel>
              <Stack gap="sm">
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
        <MapSettings
          disableLabels
          showDemo={showDemo}
          onDemoChange={setShowDemo}
        />
      </Box>
      <Attribution />
    </div>
  )
}

export default PortfolioMap
