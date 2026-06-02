import { SensorTypeEnum } from '@/api/enumerations'

const CUSTOM_DASH_EXCLUDED_SENSOR_TYPE_IDS: ReadonlySet<number> = new Set([
  SensorTypeEnum.GHOST_UNKNOWN,
  SensorTypeEnum.BESS_CELL_VOLTAGE,
])

export function isCustomDashChartSensorType(sensorTypeId: number): boolean {
  return !CUSTOM_DASH_EXCLUDED_SENSOR_TYPE_IDS.has(sensorTypeId)
}
