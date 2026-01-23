import { SensorType } from '@/api/v1/operational/sensor_types'

import { Device, MultiPolygon, Point } from './devices'

interface DataType {
  data_type_id: number
  name_short: string
}

export interface Tag {
  tag_id: number
  in_tsdb?: boolean
  device_id: number | null
  sensor_type_id: number | null
  pg_data_type_id?: number
  data_type_id?: number | null
  name_short: string | null
  name_long: string | null
  name_scada: string
  scada_id: number | null
  scada_type: string | null
  unit_scada: string | null
  unit_offset: number | null
  unit_scale: number | null
  point: Point | null
  polygon: MultiPolygon | null
  status_lookup_id?: number | null

  // Nested structure (v1 compatible)
  device?: Device | null
  sensor_type?: SensorType | null
  data_type?: DataType | null

  // Flat structure (v2)
  device_device_id?: number | null
  device_device_id_path?: string | null
  device_device_type_id?: number | null
  device_device_model_id?: number | null
  device_parent_device_id?: number | null
  device_logical?: boolean | null
  device_name_short?: string | null
  device_name_long?: string | null
  device_capacity_dc?: number | null
  device_capacity_ac?: number | null
  device_point?: Point | null
  device_polygon?: MultiPolygon | null

  device_type_device_type_id?: number | null
  device_type_name_short?: string | null
  device_type_name_long?: string | null
  device_type_description?: string | null

  sensor_type_sensor_type_id?: number | null
  sensor_type_device_type_id?: number | null
  sensor_type_name_short?: string | null
  sensor_type_name_long?: string | null
  sensor_type_name_metric?: string | null
  sensor_type_unit?: string | null
  sensor_type_description?: string | null

  data_type_data_type_id?: number | null
  data_type_name_short?: string | null

  // Dynamic fields
  [key: string]: unknown
}
