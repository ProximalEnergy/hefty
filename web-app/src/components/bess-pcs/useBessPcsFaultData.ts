import { DeviceTypeEnum, SensorTypeEnum } from '@/api/enumerations'
import { useGetLastKnownStatuses } from '@/api/v1/operational/project/project_status'
import { useGetRealTimeByDeviceTypeID } from '@/api/v1/protected/web-application/projects/real_time'
import { useGetDevicesV2 } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import dayjs from 'dayjs'
import { useMemo } from 'react'
import { useParams } from 'react-router'

const formatStatusTime = (time: string) =>
  dayjs(time).format('MMM D, YYYY HH:mm')

const STATUS_DEVICE_TYPES = [
  DeviceTypeEnum.BESS_PCS,
  DeviceTypeEnum.BESS_PCS_MODULE_GROUP,
  DeviceTypeEnum.BESS_PCS_MODULE,
]

const STATUS_SENSOR_TYPES = [
  SensorTypeEnum.BESS_PCS_MODULE_STATUS,
  SensorTypeEnum.BESS_BANK_STATUS,
  SensorTypeEnum.BESS_PCS_MODULE_ALARM,
]

const isAbnormalStatus = (statusType?: string | null) =>
  statusType === 'alert' || statusType === 'warning'

const highlightAbnormalTerms = (code: string) =>
  code.replace(/\b(Fault|Warning|Alarm|Error)\b/gi, (match) => {
    const color = match.toLowerCase() === 'warning' ? '#f08c00' : '#fa5252'
    return `<span style="color:${color}">${match}</span>`
  })

type FaultData = {
  faultSet: Set<string>
  hoverMap: Map<string, string>
}

export const useBessPcsFaultData = (realtimeOverrides?: {
  pcs?: { data?: { device_ids?: number[]; device_names?: (string | null)[] } }
  module?: {
    data?: { device_ids?: number[]; device_names?: (string | null)[] }
  }
  moduleGroup?: {
    data?: { device_ids?: number[]; device_names?: (string | null)[] }
  }
}) => {
  const { projectId } = useParams<{ projectId: string }>()

  const devices = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: { device_type_ids: STATUS_DEVICE_TYPES },
    queryOptions: { enabled: !!projectId, staleTime: QUERY_TIME.ONE_MINUTE },
  })

  const childStatuses = useGetLastKnownStatuses({
    pathParams: { project_id: projectId || '-1' },
    queryParams: {
      device_type_ids: STATUS_DEVICE_TYPES,
      sensor_type_ids: STATUS_SENSOR_TYPES,
      alert_only: false,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.THIRTY_SECONDS,
      staleTime: QUERY_TIME.FIFTEEN_SECONDS,
    },
  })

  const pcsRealtime = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DeviceTypeEnum.BESS_PCS,
    },
    queryParams: { sensor_type_ids: [SensorTypeEnum.BESS_PCS_AC_POWER] },
    queryOptions: {
      enabled: !!projectId && !realtimeOverrides?.pcs?.data,
    },
  })

  const moduleRealtime = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DeviceTypeEnum.BESS_PCS_MODULE,
    },
    queryParams: { sensor_type_ids: STATUS_SENSOR_TYPES },
    queryOptions: {
      enabled: !!projectId && !realtimeOverrides?.module?.data,
    },
  })

  const groupRealtime = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DeviceTypeEnum.BESS_PCS_MODULE_GROUP,
    },
    queryParams: { sensor_type_ids: STATUS_SENSOR_TYPES },
    queryOptions: {
      enabled: !!projectId && !realtimeOverrides?.moduleGroup?.data,
    },
  })

  const pcsData = realtimeOverrides?.pcs?.data ?? pcsRealtime.data
  const moduleData = realtimeOverrides?.module?.data ?? moduleRealtime.data
  const groupData = realtimeOverrides?.moduleGroup?.data ?? groupRealtime.data

  return useMemo(() => {
    const empty: FaultData = { faultSet: new Set(), hoverMap: new Map() }

    if (!Array.isArray(devices.data) || !Array.isArray(childStatuses.data)) {
      return { pcs: empty, module: empty, moduleGroup: empty }
    }

    const deviceById = new Map(devices.data.map((d) => [d.device_id, d]))
    const pcsIds = new Set(pcsData?.device_ids || [])
    const pcsNameById = new Map<number, string>()
    ;(pcsData?.device_ids || []).forEach((id, idx) => {
      const name = pcsData?.device_names?.[idx]
      if (name) pcsNameById.set(id, name)
    })

    const moduleNameById = new Map<number, string>()
    ;(moduleData?.device_ids || []).forEach((id, idx) => {
      const name = moduleData?.device_names?.[idx]
      if (name) moduleNameById.set(id, name)
    })

    const groupNameById = new Map<number, string>()
    ;(groupData?.device_ids || []).forEach((id, idx) => {
      const name = groupData?.device_names?.[idx]
      if (name) groupNameById.set(id, name)
    })

    const getAncestorPcsId = (deviceId: number): number | null => {
      const path = deviceById.get(deviceId)?.device_id_path
      if (!path) return null
      const pathIds = path
        .split('.')
        .map((v) => Number(v))
        .filter((v) => Number.isFinite(v))
      for (let i = pathIds.length - 1; i >= 0; i -= 1) {
        if (pcsIds.has(pathIds[i])) return pathIds[i]
      }
      return null
    }

    const pcsWithFaultsIds = new Set<number>()
    const moduleGroupCodesByPcs = new Map<number, Map<string, string>>()
    const moduleCodesByPcs = new Map<number, Map<string, string>>()
    const moduleWithFaultsIds = new Set<number>()
    const moduleGroupWithFaultsIds = new Set<number>()
    const moduleCodesByModule = new Map<number, Map<string, string>>()
    const moduleGroupCodesByGroup = new Map<number, Map<string, string>>()

    const upsertCodeTime = (
      map: Map<number, Map<string, string>>,
      key: number,
      code: string,
      time: string,
    ) => {
      if (!map.has(key)) map.set(key, new Map())
      const codeMap = map.get(key)!
      const existing = codeMap.get(code)
      if (!existing || time > existing) codeMap.set(code, time)
    }

    childStatuses.data!.forEach((deviceStatus) => {
      const childId = deviceStatus.device_id
      if (childId === null || childId === undefined) return
      const childDevice = deviceById.get(childId)
      if (!childDevice) return
      const isModuleGroup =
        childDevice.device_type_id === DeviceTypeEnum.BESS_PCS_MODULE_GROUP
      const isModule =
        childDevice.device_type_id === DeviceTypeEnum.BESS_PCS_MODULE
      if (!isModuleGroup && !isModule) return

      const abnormalStatuses = (deviceStatus.statuses || []).filter((status) =>
        isAbnormalStatus(status?.status_type),
      )
      const hasFaultOrWarning = abnormalStatuses.length > 0

      const parentPcsId = getAncestorPcsId(childId)

      abnormalStatuses.forEach((s) => {
        const code = s?.status
        const time = s?.time
        if (!code || !time) return

        if (isModuleGroup) {
          if (hasFaultOrWarning) moduleGroupWithFaultsIds.add(childId)
          if (parentPcsId) {
            if (hasFaultOrWarning) pcsWithFaultsIds.add(parentPcsId)
            upsertCodeTime(moduleGroupCodesByPcs, parentPcsId, code, time)
          }
          upsertCodeTime(moduleGroupCodesByGroup, childId, code, time)
        } else if (isModule) {
          if (hasFaultOrWarning) moduleWithFaultsIds.add(childId)
          if (parentPcsId) {
            if (hasFaultOrWarning) pcsWithFaultsIds.add(parentPcsId)
            upsertCodeTime(moduleCodesByPcs, parentPcsId, code, time)
          }
          upsertCodeTime(moduleCodesByModule, childId, code, time)
        }
      })
    })

    const formatCodeWithTime = (code: string, time: string) =>
      `${highlightAbnormalTerms(code)} (last: ${formatStatusTime(time)})`

    const formatHoverSection = (
      title: string,
      codeMap: Map<string, string> | undefined,
    ) => {
      const lines = Array.from((codeMap || new Map()).entries())
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([code, time]) => formatCodeWithTime(code, time))

      return `<b>${title}</b><br>${lines.length ? lines.join('<br>') : 'None'}`
    }

    const pcsHoverMap = new Map<string, string>()
    const pcsFaultSet = new Set<string>()
    pcsNameById.forEach((name, id) => {
      const gMap = moduleGroupCodesByPcs.get(id) || new Map()
      const mMap = moduleCodesByPcs.get(id) || new Map()
      pcsHoverMap.set(
        name,
        `${formatHoverSection('Module Group Faults/Errors/Warnings', gMap)}<br><br>` +
          `${formatHoverSection('Module Faults/Errors/Warnings', mMap)}`,
      )
      if (pcsWithFaultsIds.has(id)) pcsFaultSet.add(name)
    })

    const moduleHoverMap = new Map<string, string>()
    const moduleFaultSet = new Set<string>()
    moduleNameById.forEach((name, id) => {
      const codeMap = moduleCodesByModule.get(id) || new Map()
      moduleHoverMap.set(
        name,
        formatHoverSection('Module Faults/Errors/Warnings', codeMap),
      )
      if (moduleWithFaultsIds.has(id)) moduleFaultSet.add(name)
    })

    const moduleGroupHoverMap = new Map<string, string>()
    const moduleGroupFaultSet = new Set<string>()
    groupNameById.forEach((name, id) => {
      const codeMap = moduleGroupCodesByGroup.get(id) || new Map()
      moduleGroupHoverMap.set(
        name,
        formatHoverSection('Module Group Faults/Errors/Warnings', codeMap),
      )
      if (moduleGroupWithFaultsIds.has(id)) moduleGroupFaultSet.add(name)
    })

    return {
      pcs: { faultSet: pcsFaultSet, hoverMap: pcsHoverMap },
      module: { faultSet: moduleFaultSet, hoverMap: moduleHoverMap },
      moduleGroup: {
        faultSet: moduleGroupFaultSet,
        hoverMap: moduleGroupHoverMap,
      },
    }
  }, [devices.data, childStatuses.data, pcsData, moduleData, groupData])
}
