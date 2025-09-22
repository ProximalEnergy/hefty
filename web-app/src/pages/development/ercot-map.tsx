import { NoData, PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import Attribution from '@/components/gis/Attribution'
import { useGetResources } from '@/hooks/api'
import {
  Badge,
  HoverCard,
  List,
  Text,
  useComputedColorScheme,
} from '@mantine/core'
import { Map, Marker } from 'react-map-gl'
import { Link } from 'react-router-dom'

import { countyCoordinates } from './county-data'

class SeededRandom {
  private seed: number

  constructor(seed: number) {
    this.seed = seed
  }

  next(): number {
    // Parameters for the generator, these are quite common values
    const a = 1664525
    const c = 1013904223
    const m = 4294967296 // 2^32

    // Update the seed
    this.seed = (a * this.seed + c) % m
    return this.seed / m
  }
}

const ERCOTMap = () => {
  const seed = 12345 // Example seed
  const rng = new SeededRandom(seed)

  const computedColorScheme = useComputedColorScheme('dark')

  const { data, isLoading, error } = useGetResources({
    queryParams: { deep: true },
  })

  if (isLoading) {
    return <PageLoader />
  }

  if (error) {
    return <PageError error={error} />
  }

  if (!data) {
    return <NoData />
  }

  return (
    <div style={{ height: '100%', width: '100%' }}>
      <Map
        initialViewState={{
          bounds: [-106.6, 25.8, -93.5, 36.5], //Texas bounds
          fitBoundsOptions: {
            padding: 50,
          },
        }}
        style={{
          borderBottomLeftRadius: 'inherit',
          borderBottomRightRadius: 'inherit',
        }}
        mapStyle={
          computedColorScheme === 'dark'
            ? 'mapbox://styles/mapbox/dark-v9'
            : 'mapbox://styles/mapbox/light-v9'
        }
        mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
      >
        {data.map((resource) => (
          <Marker
            key={resource.resource_id}
            longitude={
              countyCoordinates[resource.county].longitude +
              (rng.next() - 0.5) / 10
            }
            latitude={
              countyCoordinates[resource.county].latitude +
              (rng.next() - 0.5) / 10
            }
          >
            <Link to={`/development/resources/${resource.resource_id}`}>
              <HoverCard shadow="md">
                <HoverCard.Target>
                  <div
                    style={{
                      transform: 'translate(-50%, -50%)',
                      width: '8px',
                      height: '8px',
                      backgroundColor: 'var(--mantine-primary-color-filled)',
                      borderRadius: '100%',
                    }}
                  ></div>
                </HoverCard.Target>
                <HoverCard.Dropdown>
                  <Text size="sm" fw={800}>
                    {resource.name_long}
                  </Text>
                  <List size="sm" withPadding>
                    <List.Item>{resource.capacity_power} MW</List.Item>
                    {resource.settlement_point && (
                      <List.Item>
                        {resource.settlement_point.name}{' '}
                        <Badge variant="light" size="sm">
                          Resource Node
                        </Badge>
                      </List.Item>
                    )}
                    {resource.qse && (
                      <List.Item>
                        {resource.qse.name_long}{' '}
                        <Badge variant="light" size="sm">
                          QSE
                        </Badge>
                      </List.Item>
                    )}
                    {resource.dme && (
                      <List.Item>
                        {resource.dme.name_long}{' '}
                        <Badge variant="light" size="sm">
                          DME
                        </Badge>
                      </List.Item>
                    )}
                  </List>
                </HoverCard.Dropdown>
              </HoverCard>
            </Link>
          </Marker>
        ))}
      </Map>
      <Attribution />
    </div>
  )
}

export default ERCOTMap
