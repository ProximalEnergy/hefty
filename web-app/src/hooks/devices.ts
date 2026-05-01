import { DeviceType } from '@/api/v1/operational/device_types'

export interface Point {
  type: string
  coordinates: number[]
}

export interface MultiPolygon {
  type: string
  coordinates: number[][][][]
}

export interface Device {
  device_id: number
  device_type_id: number
  device_model_id: number | null
  parent_device_id: number | null
  logical: boolean
  name_short: string | null
  name_long: string | null
  capacity_dc: number | null
  capacity_ac: number | null
  point: Point | null
  polygon: MultiPolygon | null
  serial_number?: string | null
  device_type?: DeviceType
  name_full?: string
  cec_pv_module_id?: number
  pv_module_id?: number
  device_id_path?: string
}
