import { Tag } from '@/hooks/projectTags'
import { createColumnHelper } from '@tanstack/react-table'

const columnHelper = createColumnHelper<Tag>()

export const columns = [
  columnHelper.accessor('tag_id', {
    header: 'Tag ID',
    aggregationFn: 'uniqueCount',
  }),
  columnHelper.accessor('device_id', {
    header: 'Device ID',
    filterFn: 'equalsString',
  }),
  columnHelper.accessor('sensor_type_id', {
    header: 'Sensor Type ID',
    enableSorting: false,
    filterFn: 'equalsString',
    aggregationFn: 'uniqueCount',
  }),
  columnHelper.accessor('name_scada', {
    header: 'Name',
    aggregationFn: 'uniqueCount',
  }),
]
