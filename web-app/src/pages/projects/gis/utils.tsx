import { HoverCard, List, SegmentedControl, Text } from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'
import { GeoJSONFeature } from 'mapbox-gl'
import { useSearchParams } from 'react-router-dom'
import { z } from 'zod'

export type HoverInfo = {
  feature: GeoJSONFeature | null
  x: number
  y: number
}

export const PositionSetpointHoverCard = () => {
  return (
    <HoverCard shadow="md" width="20%">
      <HoverCard.Target>
        <IconInfoCircle />
      </HoverCard.Target>
      <HoverCard.Dropdown>
        <List size="sm" pr="md">
          <List.Item>
            Position - Average position deviation from setpoint
          </List.Item>
          <List.Item>
            Setpoint - Average setpoint deviation from median setpoint
          </List.Item>
        </List>
      </HoverCard.Dropdown>
    </HoverCard>
  )
}

export const PositionSetpointSegmentedControl = () => {
  const [searchParams, setSearchParams] = useSearchParams()

  const QueryParamsSchema = z.object({
    data: z
      .string()
      .transform((val) => {
        if (['position', 'setpoint'].includes(val)) {
          return val
        }
        return 'position'
      })
      .optional()
      .default('position'),
  })

  const data = QueryParamsSchema.pick({ data: true }).parse(
    Object.fromEntries([...searchParams]),
  ).data

  const handleOnChange = (value: string) => {
    const newParams = new URLSearchParams(searchParams)
    newParams.set('data', value)
    setSearchParams(newParams)
  }

  const segmentedControlData = [
    { label: 'Position', value: 'position' },
    { label: 'Setpoint', value: 'setpoint' },
  ]

  return (
    <SegmentedControl
      size="xs"
      value={data}
      onChange={handleOnChange}
      data={segmentedControlData}
    />
  )
}

export const ZoomToBlockHoverCard = () => {
  return (
    <HoverCard shadow="md" width="20%">
      <HoverCard.Target>
        <IconInfoCircle />
      </HoverCard.Target>
      <HoverCard.Dropdown>
        <Text size="sm">
          Select a block from the dropdown or click on the map to zoom in and
          view its performance.
        </Text>
      </HoverCard.Dropdown>
    </HoverCard>
  )
}
