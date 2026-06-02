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

const DEVICE_ANCESTOR_MAX_HOPS = 64

/**
 * Walk from `startDeviceId` upward (including that device) using `deviceById`
 * until `device_type_id === targetTypeId`. Returns that device's id, or null.
 *
 * To match “parents only” (exclude the start node), pass
 * `parent_device_id` of the start device as `startDeviceId`.
 */
export function findAncestorDeviceIdByType(
  startDeviceId: number,
  targetTypeId: number,
  deviceById: Map<number, Device>,
): number | null {
  let cur: Device | undefined = deviceById.get(startDeviceId)
  for (let h = 0; h < DEVICE_ANCESTOR_MAX_HOPS; h++) {
    if (!cur) return null
    if (cur.device_type_id === targetTypeId) return cur.device_id
    const pid = cur.parent_device_id
    if (pid == null) return null
    cur = deviceById.get(pid)
  }
  return null
}
