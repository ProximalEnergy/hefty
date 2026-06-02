import { useGetUserType } from '@/api/admin'
import { DeviceTypeEnum, UserTypeEnum } from '@/api/enumerations'
import { useGetBessStrings } from '@/api/v1/operational/bess_strings'
import { useGetDeviceModels } from '@/api/v1/operational/device_models'
import { useGetOMContractorScopes } from '@/api/v1/operational/project/om_contractors'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetDevicesV2 } from '@/hooks/api'
import type { Device } from '@/hooks/devices'
import {
  getDeviceModelImagePublicUrl,
  getDeviceModelImageUrl,
} from '@/utils/cdn'
import { QUERY_TIME } from '@/utils/queryTiming'
import { useMemo } from 'react'

const BESS_STRING_DEVICE_TYPE_ID = DeviceTypeEnum.BESS_STRING

const DC_SIDE_MODEL_DEVICE_TYPE_IDS = [
  DeviceTypeEnum.BESS_ENCLOSURE,
  DeviceTypeEnum.BESS_DC_SKID,
]

type UseBessStringContextProps = {
  projectId: string | undefined
}

export function useBessStringContext({ projectId }: UseBessStringContextProps) {
  const userType = useGetUserType({})
  const isSuperadmin = userType.data?.user_type_id === UserTypeEnum.SUPERADMIN
  const isAdmin =
    userType.data?.user_type_id === UserTypeEnum.ADMIN || isSuperadmin

  const projectQuery = useSelectProject(projectId ?? '')
  const devices = useGetDevicesV2({
    pathParams: {
      projectId: projectId ?? '-1',
    },
    filters: {
      device_type_ids: [BESS_STRING_DEVICE_TYPE_ID],
    },
    queryOptions: {
      enabled: projectId != null,
      staleTime: QUERY_TIME.NEVER,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
    },
  })

  const dcSideDevices = useGetDevicesV2({
    pathParams: {
      projectId: projectId ?? '-1',
    },
    filters: {
      device_type_ids: [...DC_SIDE_MODEL_DEVICE_TYPE_IDS],
    },
    queryOptions: {
      enabled: projectId != null,
      staleTime: QUERY_TIME.NEVER,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
    },
  })

  const stringDevices = useMemo(() => devices.data ?? [], [devices.data])
  const dcSideHardware = useMemo(
    () => dcSideDevices.data ?? [],
    [dcSideDevices.data],
  )

  const deviceModelIds = useMemo(() => {
    const modelIds = new Set<number>()
    const addModelIds = (devs: Device[]) => {
      devs.forEach((device) => {
        if (device.device_model_id != null) {
          modelIds.add(device.device_model_id)
        }
      })
    }

    addModelIds(stringDevices)
    addModelIds(dcSideHardware)
    return Array.from(modelIds).sort((a, b) => a - b)
  }, [stringDevices, dcSideHardware])

  const deviceModels = useGetDeviceModels({
    queryParams: {
      device_model_ids: deviceModelIds,
    },
    queryOptions: {
      enabled: deviceModelIds.length > 0,
      staleTime: QUERY_TIME.NEVER,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
    },
  })

  const omContractorScopes = useGetOMContractorScopes({
    pathParams: {
      projectId: projectId ?? '-1',
    },
    queryOptions: {
      enabled: projectId != null,
      staleTime: QUERY_TIME.NEVER,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
    },
  })

  const stringContractors = useMemo(() => {
    if (!omContractorScopes.data) return []
    return omContractorScopes.data.filter((scope) =>
      scope.scope_json?.device_type_ids?.includes(BESS_STRING_DEVICE_TYPE_ID),
    )
  }, [omContractorScopes.data])

  const omContractor = stringContractors[0] ?? null
  const epcContractor = stringContractors[1] ?? null

  const headerModelDevices = useMemo(() => {
    const stringsHaveModel = stringDevices.some(
      (device) => device.device_model_id != null,
    )
    return stringsHaveModel ? stringDevices : dcSideHardware
  }, [stringDevices, dcSideHardware])

  const headerModelLoading =
    devices.isLoading ||
    dcSideDevices.isLoading ||
    (deviceModelIds.length > 0 && deviceModels.isLoading)

  const stringBrandModel = useMemo(() => {
    if (!deviceModels.data || deviceModels.data.length === 0) {
      return null
    }

    const counts = new Map<string, number>()
    headerModelDevices.forEach((device) => {
      if (device.device_model_id == null) return
      const deviceModel = deviceModels.data?.find(
        (model) => model.device_model_id === device.device_model_id,
      )
      if (!deviceModel) return

      const key = `${deviceModel.brand}|${deviceModel.model}`
      counts.set(key, (counts.get(key) ?? 0) + 1)
    })

    if (counts.size === 0) return null

    let mostCommon = ''
    let maxCount = 0
    counts.forEach((count, key) => {
      if (count > maxCount) {
        maxCount = count
        mostCommon = key
      }
    })

    if (!mostCommon) return null
    const [brand, model] = mostCommon.split('|')
    return `${brand} ${model}`
  }, [headerModelDevices, deviceModels.data])

  const mostCommonDeviceModelId = useMemo(() => {
    if (headerModelDevices.length === 0) {
      return null
    }

    const counts = new Map<number, number>()
    headerModelDevices.forEach((device) => {
      if (device.device_model_id == null) return
      counts.set(
        device.device_model_id,
        (counts.get(device.device_model_id) ?? 0) + 1,
      )
    })

    if (counts.size === 0) return null

    let id: number | null = null
    let maxCount = 0
    counts.forEach((count, modelId) => {
      if (count > maxCount) {
        maxCount = count
        id = modelId
      }
    })
    return id
  }, [headerModelDevices])

  const headerDeviceModel = useMemo(() => {
    if (!deviceModels.data || mostCommonDeviceModelId === null) {
      return null
    }
    return deviceModels.data.find(
      (deviceModel) => deviceModel.device_model_id === mostCommonDeviceModelId,
    )
  }, [deviceModels.data, mostCommonDeviceModelId])

  const bessStrings = useGetBessStrings({
    queryParams: {
      device_model_ids: mostCommonDeviceModelId
        ? [mostCommonDeviceModelId]
        : [],
    },
    queryOptions: {
      enabled: mostCommonDeviceModelId !== null,
      staleTime: QUERY_TIME.NEVER,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
    },
  })

  const bessStringSpec =
    bessStrings.data && bessStrings.data.length > 0 ? bessStrings.data[0] : null

  const nameplatePowerKW = bessStringSpec?.nominal_power_kw ?? null

  const deviceModelImageUrl = useMemo(
    () => getDeviceModelImageUrl(mostCommonDeviceModelId),
    [mostCommonDeviceModelId],
  )

  const deviceModelImageFallbackUrl = useMemo(
    () => getDeviceModelImagePublicUrl(mostCommonDeviceModelId),
    [mostCommonDeviceModelId],
  )

  const deviceCount = stringDevices.length

  const fallbackTotalKWdc = useMemo(() => {
    if (stringDevices.length === 0) {
      return null
    }
    return stringDevices.reduce(
      (sum, device) => sum + (device.capacity_dc ?? device.capacity_ac ?? 0),
      0,
    )
  }, [stringDevices])

  const totalKWdc = useMemo(() => {
    if (nameplatePowerKW !== null && deviceCount > 0) {
      return nameplatePowerKW * deviceCount
    }
    return fallbackTotalKWdc
  }, [fallbackTotalKWdc, nameplatePowerKW, deviceCount])

  const totalMWdc = useMemo(() => {
    return totalKWdc !== null ? totalKWdc / 1000 : null
  }, [totalKWdc])

  const kwdcPerDevice = useMemo(() => {
    if (nameplatePowerKW !== null) {
      return nameplatePowerKW
    }

    if (fallbackTotalKWdc === null || deviceCount === 0) {
      return null
    }
    return fallbackTotalKWdc / deviceCount
  }, [fallbackTotalKWdc, nameplatePowerKW, deviceCount])

  const mwdcPerDevice = useMemo(() => {
    return kwdcPerDevice !== null ? kwdcPerDevice / 1000 : null
  }, [kwdcPerDevice])

  const kwhdcPerDevice = bessStringSpec?.nominal_energy_kwh ?? null
  const nameplateLoading =
    headerModelLoading ||
    (mostCommonDeviceModelId !== null && bessStrings.isLoading)

  const totalMWhdc = useMemo(() => {
    if (kwhdcPerDevice === null || deviceCount === 0) {
      return null
    }
    return (kwhdcPerDevice * deviceCount) / 1000
  }, [kwhdcPerDevice, deviceCount])

  return {
    projectId: projectId ?? '',
    project: projectQuery.data,
    projectQuery,
    userType,
    isSuperadmin,
    isAdmin,
    devices,
    dcSideDevices,
    stringDevices,
    deviceModels,
    deviceModelIds,
    omContractorScopes,
    omContractor,
    epcContractor,
    headerModelLoading,
    stringBrandModel,
    mostCommonDeviceModelId,
    headerDeviceModel,
    bessStrings,
    bessStringSpec,
    deviceModelImageUrl,
    deviceModelImageFallbackUrl,
    deviceModelIconUrl: '/icon_bess_string.svg',
    deviceCount,
    totalMWdc,
    kwdcPerDevice,
    mwdcPerDevice,
    kwhdcPerDevice,
    totalMWhdc,
    nameplateLoading,
    isLoading: projectQuery.isLoading,
    error: projectQuery.error ?? null,
  }
}

export type BessStringContext = ReturnType<typeof useBessStringContext>
