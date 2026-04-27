import { useGetUserType } from '@/api/admin'
import { ProjectTypeEnum } from '@/api/enumerations'
import { useGetUserProjects } from '@/api/v1/admin/user_projects'
import {
  getNWSWindspeedTileUrl,
  getTemperatureTileUrl,
  parseNwsspcTimestamp,
  useGetFireOutlook,
  useGetHailForecastPolygons,
  useGetThunderstormOutlook,
  useGetTornadoOutlook,
  useGetWindOutlook,
  useSpcHailOutlookDayValidityPair,
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
import { useAuth } from '@clerk/react'
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
  Tooltip,
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

const FILL_OUTLINE_COLOR = '#000000'

const HAIL_BASE = '#1565C0'
const TORNADO_BASE = '#39FF14'
const WIND_BASE = '#7B1FA2'
const FIRE_BASE = '#D32F2F'
const THUNDERSTORM_BASE = '#FFB300'

type ForecastDay = 'today' | 'tomorrow'

const FORECAST_DAY_STORAGE_KEY = 'forecast-day-v2'
const FORECAST_DAY_LEGACY_STORAGE_KEY = 'forecast-day'

/** Prefer v2 key; else one-time read of legacy `forecast-day` (old semantics). */
const readForecastDayPreference = (): ForecastDay => {
  if (typeof localStorage === 'undefined') return 'today'
  const v2Raw = localStorage.getItem(FORECAST_DAY_STORAGE_KEY)
  if (v2Raw != null) {
    try {
      const parsed = JSON.parse(v2Raw) as unknown
      if (parsed === 'today' || parsed === 'tomorrow') return parsed
    } catch {
      /* invalid JSON */
    }
    return 'today'
  }
  const legacyRaw = localStorage.getItem(FORECAST_DAY_LEGACY_STORAGE_KEY)
  if (legacyRaw != null) {
    try {
      const p = JSON.parse(legacyRaw) as unknown
      if (p === 'day-after') return 'tomorrow'
      // Legacy "Tomorrow" was SPC Day 1 → new "today"
      if (p === 'tomorrow') return 'today'
      if (p === 'today') return 'today'
    } catch {
      /* ignore */
    }
  }
  return 'today'
}

const normalizeForecastDay = (v: ForecastDay | string): ForecastDay =>
  v === 'tomorrow' ? 'tomorrow' : 'today'

const LAYER_IDS: Record<
  ForecastDay,
  {
    hail: number
    tornado: number
    wind: number
    fire: number
    thunderstorm: number
  }
> = {
  today: {
    hail: 5,
    tornado: 3,
    wind: 7,
    fire: 1,
    thunderstorm: 1,
  },
  tomorrow: {
    hail: 13,
    tornado: 11,
    wind: 15,
    fire: 4,
    thunderstorm: 9,
  },
}

const HAIL_OPACITY: Record<number, number> = {
  5: 0.25,
  15: 0.4,
  30: 0.55,
  45: 0.7,
  60: 0.9,
}

const TORNADO_OPACITY: Record<number, number> = {
  2: 0.2,
  5: 0.3,
  10: 0.45,
  15: 0.55,
  30: 0.7,
  45: 0.8,
  60: 0.95,
}

const WIND_OPACITY: Record<number, number> = {
  5: 0.25,
  15: 0.4,
  30: 0.55,
  45: 0.7,
  60: 0.9,
}

const FIRE_OPACITY: Record<number, number> = {
  5: 0.35,
  8: 0.6,
  10: 0.9,
}

const THUNDERSTORM_OPACITY: Record<number, number> = {
  2: 0.2,
  3: 0.35,
  4: 0.5,
  5: 0.65,
  6: 0.8,
  8: 0.95,
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
      return 'Hail Forecast'
    case 'tornado-layer':
      return 'Tornado Outlook'
    case 'wind-layer':
      return 'Wind Outlook'
    case 'fire-layer':
      return 'Fire Outlook'
    case 'thunderstorm-layer':
      return 'Thunderstorm Outlook'
    default:
      return 'Unknown Layer'
  }
}

// Helper function to format the value based on layer type
const formatWeatherLayerValue = (
  layerId: string | null,
  dn: number | undefined,
): string => {
  if (dn === undefined || dn === null) return 'N/A'

  switch (layerId) {
    case 'hail-layer':
    case 'tornado-layer':
    case 'wind-layer':
      return `${dn}%`
    case 'fire-layer':
      if (dn === 5) return 'Elevated'
      if (dn === 8) return 'Critical'
      if (dn === 10) return 'Extreme'
      return `${dn}`
    case 'thunderstorm-layer':
      if (dn === 2) return 'TSTM'
      if (dn === 3) return 'Marginal'
      if (dn === 4) return 'Slight'
      if (dn === 5) return 'Enhanced'
      if (dn === 6) return 'Moderate'
      if (dn === 8) return 'High'
      return `${dn}`
    default:
      return `${dn}`
  }
}

const startOfLocalDay = (d: Date) =>
  new Date(d.getFullYear(), d.getMonth(), d.getDate())

const startOfLocalTomorrow = (now: Date) => {
  const s = startOfLocalDay(now)
  s.setDate(s.getDate() + 1)
  return s
}

const sameLocalCalendarDay = (a: Date, b: Date) =>
  startOfLocalDay(a).getTime() === startOfLocalDay(b).getTime()

const formatLocalTimeHm = (d: Date) =>
  d.toLocaleTimeString(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })

/** Day 1 (Today) segment: hours/minutes left until MapServer `expire`. */
const todayOutlookTooltip = (expireRaw: string) => {
  const expire = parseNwsspcTimestamp(expireRaw)
  if (!expire) return 'Outlook end time unavailable.'
  const ms = expire.getTime() - Date.now()
  if (ms <= 0) return 'This outlook period has ended.'
  const hours = ms / 3_600_000
  if (hours < 1) {
    const m = Math.max(1, Math.round(ms / 60_000))
    return `Valid for the next ${m} minutes.`
  }
  const h = Math.max(1, Math.round(hours))
  return `Valid for the next ${h} hours.`
}

/** Day 2 (Tomorrow) segment: local-time range from `valid` through `expire`. */
const day2OutlookTooltip = (validRaw: string, expireRaw: string) => {
  const valid = parseNwsspcTimestamp(validRaw)
  const expire = parseNwsspcTimestamp(expireRaw)
  if (!valid || !expire) return 'Outlook window unavailable.'

  const now = new Date()
  const validStartsTomorrowLocal =
    startOfLocalDay(valid).getTime() === startOfLocalTomorrow(now).getTime()

  const startPhrase = validStartsTomorrowLocal
    ? 'tomorrow'
    : valid.toLocaleDateString(undefined, {
        weekday: 'long',
        month: 'short',
        day: 'numeric',
      })

  const t0 = formatLocalTimeHm(valid)
  const t1 = formatLocalTimeHm(expire)

  if (sameLocalCalendarDay(valid, expire)) {
    return `Valid from ${startPhrase}, ${t0} – ${t1}.`
  }
  const endDay = expire.toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
  })
  return `Valid from ${startPhrase}, ${t0} – ${endDay}, ${t1}.`
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

    const byLayer = new Map<string, FeatureWithLayer>()
    for (const feature of features) {
      const f = feature as MapboxFeature
      const layerId = f?.layer?.id || f?.sourceLayer || null
      if (!layerId) continue

      const dn = (feature.properties?.dn as number) ?? -Infinity
      const existing = byLayer.get(layerId)
      const existingDn =
        (existing?.feature.properties?.dn as number) ?? -Infinity

      if (!existing || dn > existingDn) {
        byLayer.set(layerId, {
          feature: feature as Feature,
          layerId,
        })
      }
    }

    setHoverInfo({
      features: Array.from(byLayer.values()),
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
  const [forecastDayRaw, setForecastDay] = useLocalStorage<ForecastDay>({
    key: FORECAST_DAY_STORAGE_KEY,
    defaultValue: readForecastDayPreference(),
  })
  const forecastDay = normalizeForecastDay(forecastDayRaw)

  useEffect(() => {
    if (forecastDayRaw !== forecastDay) {
      setForecastDay(forecastDay)
    }
  }, [forecastDay, forecastDayRaw, setForecastDay])

  // Drop legacy `forecast-day` once v2 is stored (mapping lives in
  // readForecastDayPreference).
  useEffect(() => {
    try {
      if (localStorage.getItem(FORECAST_DAY_STORAGE_KEY) == null) {
        return
      }
      if (localStorage.getItem(FORECAST_DAY_LEGACY_STORAGE_KEY) != null) {
        localStorage.removeItem(FORECAST_DAY_LEGACY_STORAGE_KEY)
      }
    } catch {
      /* ignore */
    }
  }, [])

  const [showHail, setShowHail] = useLocalStorage({
    key: 'show-hail',
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
  const [showThunderstorm, setShowThunderstorm] = useLocalStorage({
    key: 'show-thunderstorm',
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

  const hailOutlookValidity = useSpcHailOutlookDayValidityPair(
    LAYER_IDS.today.hail,
    LAYER_IDS.tomorrow.hail,
  )

  const forecastDayTooltips = useMemo((): Record<ForecastDay, string> => {
    if (hailOutlookValidity.isPending) {
      return {
        today: 'Loading outlook times…',
        tomorrow: 'Loading outlook times…',
      }
    }
    if (hailOutlookValidity.isError) {
      return {
        today: 'Could not load outlook times.',
        tomorrow: 'Could not load outlook times.',
      }
    }
    const d1 = hailOutlookValidity.data?.day1
    const d2 = hailOutlookValidity.data?.day2
    return {
      today: d1?.expire
        ? todayOutlookTooltip(d1.expire)
        : 'Outlook end time unavailable.',
      tomorrow:
        d2?.valid && d2?.expire
          ? day2OutlookTooltip(d2.valid, d2.expire)
          : 'Outlook window unavailable.',
    }
  }, [
    hailOutlookValidity.data,
    hailOutlookValidity.isError,
    hailOutlookValidity.isPending,
  ])

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

  const layerIds = LAYER_IDS[forecastDay]

  const { data: hailData } = useGetHailForecastPolygons({
    arcgis_layer_id: layerIds.hail,
    queryOptions: {
      enabled: showHail,
    },
  })

  const { data: tornadoData } = useGetTornadoOutlook({
    arcgis_layer_id: layerIds.tornado,
    queryOptions: {
      enabled: showTornado,
    },
  })

  const { data: windData } = useGetWindOutlook({
    arcgis_layer_id: layerIds.wind,
    queryOptions: {
      enabled: showWind,
    },
  })

  const { data: fireData } = useGetFireOutlook({
    arcgis_layer_id: layerIds.fire,
    queryOptions: {
      enabled: showFire,
    },
  })

  const { data: thunderstormData } = useGetThunderstormOutlook({
    arcgis_layer_id: layerIds.thunderstorm,
    queryOptions: {
      enabled: showThunderstorm,
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
  const showHailLegend = showHail
  const showTornadoLegend = showTornado
  const showWindLegend = showWind
  const showFireLegend = showFire
  const showThunderstormLegend = showThunderstorm
  const showWindspeedLegend = showWindspeed
  const showTemperatureLegend = showTemperature

  const hailLegendItems = [
    { label: '5%', opacity: HAIL_OPACITY[5] },
    { label: '15%', opacity: HAIL_OPACITY[15] },
    { label: '30%', opacity: HAIL_OPACITY[30] },
    { label: '45%', opacity: HAIL_OPACITY[45] },
    { label: '60%', opacity: HAIL_OPACITY[60] },
  ]

  const tornadoLegendItems = [
    { label: '2%', opacity: TORNADO_OPACITY[2] },
    { label: '5%', opacity: TORNADO_OPACITY[5] },
    { label: '10%', opacity: TORNADO_OPACITY[10] },
    { label: '15%', opacity: TORNADO_OPACITY[15] },
    { label: '30%', opacity: TORNADO_OPACITY[30] },
    { label: '45%', opacity: TORNADO_OPACITY[45] },
    { label: '60%', opacity: TORNADO_OPACITY[60] },
  ]

  const windLegendItems = [
    { label: '5%', opacity: WIND_OPACITY[5] },
    { label: '15%', opacity: WIND_OPACITY[15] },
    { label: '30%', opacity: WIND_OPACITY[30] },
    { label: '45%', opacity: WIND_OPACITY[45] },
    { label: '60%', opacity: WIND_OPACITY[60] },
  ]

  const fireLegendItems = [
    { label: 'Elevated', opacity: FIRE_OPACITY[5] },
    { label: 'Critical', opacity: FIRE_OPACITY[8] },
    { label: 'Extreme', opacity: FIRE_OPACITY[10] },
  ]

  const thunderstormLegendItems = [
    { label: 'TSTM', opacity: THUNDERSTORM_OPACITY[2] },
    { label: 'Marginal', opacity: THUNDERSTORM_OPACITY[3] },
    { label: 'Slight', opacity: THUNDERSTORM_OPACITY[4] },
    { label: 'Enhanced', opacity: THUNDERSTORM_OPACITY[5] },
    { label: 'Moderate', opacity: THUNDERSTORM_OPACITY[6] },
    { label: 'High', opacity: THUNDERSTORM_OPACITY[8] },
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
          ...(showTornado ? ['tornado-layer'] : []),
          ...(showWind ? ['wind-layer'] : []),
          ...(showFire ? ['fire-layer'] : []),
          ...(showThunderstorm ? ['thunderstorm-layer'] : []),
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
        {showThunderstorm && thunderstormData && (
          <Source id="thunderstorm-data" type="geojson" data={thunderstormData}>
            <Layer
              id="thunderstorm-layer"
              type="fill"
              source="thunderstorm-data"
              paint={{
                'fill-color': THUNDERSTORM_BASE,
                'fill-opacity': [
                  'match',
                  ['get', 'dn'],
                  2,
                  0.2,
                  3,
                  0.35,
                  4,
                  0.5,
                  5,
                  0.65,
                  6,
                  0.8,
                  8,
                  0.95,
                  0.2,
                ],
                'fill-outline-color': FILL_OUTLINE_COLOR,
              }}
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
                'fill-color': HAIL_BASE,
                'fill-opacity': [
                  'match',
                  ['get', 'dn'],
                  5,
                  0.25,
                  15,
                  0.4,
                  30,
                  0.55,
                  45,
                  0.7,
                  60,
                  0.9,
                  0.25,
                ],
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
                'fill-color': WIND_BASE,
                'fill-opacity': [
                  'match',
                  ['get', 'dn'],
                  5,
                  0.25,
                  15,
                  0.4,
                  30,
                  0.55,
                  45,
                  0.7,
                  60,
                  0.9,
                  0.25,
                ],
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
                'fill-color': TORNADO_BASE,
                'fill-opacity': [
                  'match',
                  ['get', 'dn'],
                  2,
                  0.2,
                  5,
                  0.3,
                  10,
                  0.45,
                  15,
                  0.55,
                  30,
                  0.7,
                  45,
                  0.8,
                  60,
                  0.95,
                  0.2,
                ],
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
                'fill-color': FIRE_BASE,
                'fill-opacity': [
                  'match',
                  ['get', 'dn'],
                  5,
                  0.35,
                  8,
                  0.6,
                  10,
                  0.9,
                  0.35,
                ],
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
                  {formatWeatherLayerValue(
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
                  label="Hail Forecast"
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
                <Switch
                  checked={showThunderstorm}
                  onChange={(event) =>
                    setShowThunderstorm(event.currentTarget.checked)
                  }
                  onClick={(e) => e.stopPropagation()}
                  label="Thunderstorm Outlook"
                />
              </Stack>
            </Accordion.Panel>
          </Accordion.Item>
        </Accordion>

        <Box onMouseDown={(e) => e.stopPropagation()} data-segmented-control>
          <SegmentedControl
            value={forecastDay}
            onChange={(v) => setForecastDay(v as ForecastDay)}
            data={[
              {
                value: 'today',
                label: (
                  <Tooltip
                    label={forecastDayTooltips.today}
                    multiline
                    maw={320}
                    position="bottom"
                    withArrow
                    events={{ hover: true, focus: true, touch: true }}
                  >
                    <span
                      style={{
                        display: 'block',
                        width: '100%',
                        textAlign: 'center',
                      }}
                    >
                      Today
                    </span>
                  </Tooltip>
                ),
              },
              {
                value: 'tomorrow',
                label: (
                  <Tooltip
                    label={forecastDayTooltips.tomorrow}
                    multiline
                    maw={320}
                    position="bottom"
                    withArrow
                    events={{ hover: true, focus: true, touch: true }}
                  >
                    <span
                      style={{
                        display: 'block',
                        width: '100%',
                        textAlign: 'center',
                      }}
                    >
                      Tomorrow
                    </span>
                  </Tooltip>
                ),
              },
            ]}
            size="xs"
            fullWidth
            color={theme.primaryColor}
          />
        </Box>

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
                        Hail Probability
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
                      <Group key={item.label} gap="xs" align="center">
                        <div
                          style={{
                            width: '16px',
                            height: '16px',
                            backgroundColor: HAIL_BASE,
                            opacity: item.opacity,
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
                      <Group key={item.label} gap="xs" align="center">
                        <div
                          style={{
                            width: '16px',
                            height: '16px',
                            backgroundColor: TORNADO_BASE,
                            opacity: item.opacity,
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
                      <Group key={item.label} gap="xs" align="center">
                        <div
                          style={{
                            width: '16px',
                            height: '16px',
                            backgroundColor: WIND_BASE,
                            opacity: item.opacity,
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
                      <Group key={item.label} gap="xs" align="center">
                        <div
                          style={{
                            width: '16px',
                            height: '16px',
                            backgroundColor: FIRE_BASE,
                            opacity: item.opacity,
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
            {showThunderstormLegend && (
              <Card withBorder shadow="sm" radius="md" px="sm">
                <Card.Section inheritPadding py="sm">
                  <Stack gap="xs">
                    <Group gap={2} align="center">
                      <Text size="sm" fw={500}>
                        Thunderstorm Outlook
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
                              Categorical outlook risk levels are provided by
                              NOAA&apos;s Storm Prediction Center and indicate
                              the overall severe weather threat level for the
                              forecast period.
                            </Text>
                            <Anchor
                              href="https://www.spc.noaa.gov/products/outlook/"
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
                    {thunderstormLegendItems.map((item) => (
                      <Group key={item.label} gap="xs" align="center">
                        <div
                          style={{
                            width: '16px',
                            height: '16px',
                            backgroundColor: THUNDERSTORM_BASE,
                            opacity: item.opacity,
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
