import { DeviceTypeEnum, ProjectTypeEnum } from '@/api/enumerations'

/** Device type IDs that belong to a PV project (warranty/claim scope). */
const PV_DEVICE_TYPE_IDS: number[] = [
  DeviceTypeEnum.PV_INVERTER,
  DeviceTypeEnum.PV_INVERTER_MODULE,
  DeviceTypeEnum.PV_BLOCK,
  DeviceTypeEnum.PV_DC_COMBINER,
  DeviceTypeEnum.PV_MVT,
  DeviceTypeEnum.PV_MV_COLLECTOR_CIRCUIT,
  DeviceTypeEnum.PV_FEEDER,
  DeviceTypeEnum.PV_MODULE,
]

/** Device type IDs that belong to a BESS project (warranty/claim scope). */
const BESS_DEVICE_TYPE_IDS: number[] = [
  DeviceTypeEnum.BESS_ENCLOSURE,
  DeviceTypeEnum.BESS_BLOCK,
  DeviceTypeEnum.BESS_PCS,
  DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT,
  DeviceTypeEnum.BESS_FEEDER,
  DeviceTypeEnum.BESS_MVT,
  DeviceTypeEnum.BESS_BANK,
  DeviceTypeEnum.BESS_STRING,
  DeviceTypeEnum.BESS_PCS_MODULE_GROUP,
  DeviceTypeEnum.BESS_PCS_MODULE,
  DeviceTypeEnum.BESS_MODULE,
  DeviceTypeEnum.BESS_DC_SKID,
]

/**
 * Device-type IDs in scope for the given project type. Hybrid (PVS) projects
 * fall through and get the union.
 */
export function deviceTypeIdsForProjectType(
  projectTypeId: number | null | undefined,
): number[] {
  if (projectTypeId === ProjectTypeEnum.PV) return PV_DEVICE_TYPE_IDS
  if (projectTypeId === ProjectTypeEnum.BESS) return BESS_DEVICE_TYPE_IDS
  return [...PV_DEVICE_TYPE_IDS, ...BESS_DEVICE_TYPE_IDS]
}
