import { DeviceTypeEnum } from '@/api/enumerations'
import { Group, HoverCard, Table, Text } from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'

export type EventLossesValue = {
  title: string
  value: string | number
  unit: string
  info?: string
}

export type EventLossesData = Record<
  'financial' | 'energetic' | 'capacity',
  EventLossesValue
>

const CAPACITY_VARIES_CURTAILMENT_INFO =
  'Curtailment is not always a consistent reduction in capacity. ' +
  'Operating limits can change with grid conditions, dispatch, and other ' +
  'factors, so a single capacity loss value may not reflect the event ' +
  'evenly over time.'

const CAPACITY_VARIES_TRACKER_INFO =
  "Trackers don't have a fixed capacity loss when offline because they " +
  'remain stuck at a single tilt angle rather than following the sun. When ' +
  "the tracker's fixed position happens to align well with the optimal angle, " +
  "production is nearly normal; when it doesn't, the loss increases " +
  'proportionally with the misalignment.'

type EventLossesCapacityValueProps = {
  deviceTypeId: number
  value: string | number
  unit: string
}

function EventLossesCapacityValue({
  deviceTypeId,
  value,
  unit,
}: EventLossesCapacityValueProps) {
  const isTracker =
    deviceTypeId === DeviceTypeEnum.TRACKER_ROW ||
    deviceTypeId === DeviceTypeEnum.TRACKER_ZONE
  const isProject = deviceTypeId === DeviceTypeEnum.PROJECT

  if (!isTracker && !isProject) {
    return (
      <Text>
        {Number(value).toLocaleString()} {unit}
      </Text>
    )
  }

  const hoverText = isProject
    ? CAPACITY_VARIES_CURTAILMENT_INFO
    : CAPACITY_VARIES_TRACKER_INFO

  return (
    <Group gap={2} align="center">
      <Text>Varies</Text>
      <HoverCard>
        <HoverCard.Target>
          <IconInfoCircle size={16} />
        </HoverCard.Target>
        <HoverCard.Dropdown w="33%">
          <Text>{hoverText}</Text>
        </HoverCard.Dropdown>
      </HoverCard>
    </Group>
  )
}

type EventLossesProps = {
  losses: EventLossesData
  deviceTypeId: number
  capacityOnly?: boolean
}

export function EventLosses({
  losses,
  deviceTypeId,
  capacityOnly = false,
}: EventLossesProps) {
  if (capacityOnly) {
    return (
      <Group gap={4} align="center">
        <Text fw={500}>{losses.capacity.title}:</Text>
        <EventLossesCapacityValue
          deviceTypeId={deviceTypeId}
          value={losses.capacity.value}
          unit={losses.capacity.unit}
        />
      </Group>
    )
  }

  return (
    <Table w="100%">
      <Table.Thead>
        <Table.Tr>
          <Table.Td>
            {losses.financial.title}
            {losses.financial.info && (
              <HoverCard>
                <HoverCard.Target>
                  <IconInfoCircle size={10} />
                </HoverCard.Target>
                <HoverCard.Dropdown w="50%">
                  <Text>{losses.financial.info}</Text>
                </HoverCard.Dropdown>
              </HoverCard>
            )}
          </Table.Td>
          <Table.Td>{losses.energetic.title}</Table.Td>
          <Table.Td>{losses.capacity.title}</Table.Td>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        <Table.Tr>
          <Table.Td>
            <Text>
              {losses.financial.unit}
              {Number(losses.financial.value).toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </Text>
          </Table.Td>
          <Table.Td>
            <Text>
              {Number(losses.energetic.value).toLocaleString()}{' '}
              {losses.energetic.unit}
            </Text>
          </Table.Td>
          <Table.Td>
            <EventLossesCapacityValue
              deviceTypeId={deviceTypeId}
              value={losses.capacity.value}
              unit={losses.capacity.unit}
            />
          </Table.Td>
        </Table.Tr>
      </Table.Tbody>
    </Table>
  )
}
