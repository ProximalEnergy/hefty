export interface DeviceEntry {
  device_id: number
  device_name: string
  device_model_id: number | null
  device_serial_number: string | null
  oem_serial_number: string
  oem_part_number: string
  notes: string
  event_id: number | null
}

/**
 * Extra columns on POST /projects/{id}/devices JSON (Polars/SQL join).
 * OpenAPI `Device` omits these; they are always present on that endpoint.
 */
interface DeviceAssistApiRow {
  name_full?: string | null
  /** Device type `name_long` from join (see api project_devices). */
  name_long_1?: string | null
  device_type?: {
    name_long?: string | null
    name_short?: string | null
  } | null
}

/** Device label for warranty PDF assist (device type + instance name). */
export function deviceNameForWarrantyAssist(
  deviceId: number,
  storedName: string,
  detail: (DeviceAssistApiRow & { device_id?: number }) | undefined,
): string {
  const row = detail
  const combined = row?.name_full?.trim()
  if (combined) {
    return combined
  }
  const typeName =
    row?.name_long_1?.trim() ||
    row?.device_type?.name_long?.trim() ||
    row?.device_type?.name_short?.trim() ||
    ''
  const base = storedName.trim() || `Device ${deviceId}`
  return typeName ? `${typeName} ${base}`.trim() : base
}
