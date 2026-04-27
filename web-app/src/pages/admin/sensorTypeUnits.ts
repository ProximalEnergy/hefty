import type { SensorType } from '@/api/v1/operational/sensor_types'

type SensorTypeWithUnit = Pick<SensorType, 'unit'>

export const getUniqueUnits = (
  sensorTypes: SensorTypeWithUnit[] | undefined,
) => {
  if (!sensorTypes) {
    return []
  }

  const units = sensorTypes
    .map((sensorType) => sensorType.unit)
    .filter((unit): unit is string => unit !== null && unit !== '')

  return [...new Set(units)]
}
