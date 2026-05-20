import { useGetUserType } from '@/api/admin'
import { DeviceTypeEnum, UserTypeEnum } from '@/api/enumerations'
import { useGetDeviceModels } from '@/api/v1/operational/device_models'
import { useGetOMContractorScopes } from '@/api/v1/operational/project/om_contractors'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetInverters } from '@/api/v1/operational/pv_inverters'
import { useGetDevicesV2 } from '@/hooks/api'
import type { Device } from '@/hooks/devices'
import {
  getDeviceModelImagePublicUrl,
  getDeviceModelImageUrl,
} from '@/utils/cdn'
import { QUERY_TIME } from '@/utils/queryTiming'
import { useMemo } from 'react'

type UsePvInverterContextProps = {
  projectId: string | undefined
}

export function usePvInverterContext({ projectId }: UsePvInverterContextProps) {
  const userType = useGetUserType({})
  const isSuperadmin = userType.data?.user_type_id === UserTypeEnum.SUPERADMIN
  const isAdmin =
    userType.data?.user_type_id === UserTypeEnum.ADMIN || isSuperadmin

  const projectQuery = useSelectProject(projectId ?? '')
  const devices = useGetDevicesV2({
    pathParams: { projectId: projectId ?? '-1' },
    filters: {
      device_type_ids: [DeviceTypeEnum.PV_INVERTER],
    },
    queryOptions: {
      enabled: projectId != null,
      staleTime: QUERY_TIME.NEVER,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
    },
  })

  const deviceModelIds = useMemo(() => {
    if (!devices.data || devices.data.length === 0) {
      return []
    }

    const modelIds = new Set<number>()
    devices.data.forEach((device: Device) => {
      if (device.device_model_id != null) {
        modelIds.add(device.device_model_id)
      }
    })

    return Array.from(modelIds).sort()
  }, [devices.data])

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
    pathParams: { projectId: projectId ?? '-1' },
    queryOptions: {
      enabled: projectId != null,
      staleTime: QUERY_TIME.NEVER,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
    },
  })

  const pcsContractors = useMemo(() => {
    if (!omContractorScopes.data) {
      return []
    }

    return omContractorScopes.data.filter((scope) =>
      scope.scope_json?.device_type_ids?.includes(DeviceTypeEnum.PV_INVERTER),
    )
  }, [omContractorScopes.data])

  const omContractor = pcsContractors[0] ?? null
  const epcContractor = pcsContractors[1] ?? null

  const pcsBrandModel = useMemo(() => {
    if (!deviceModels.data || deviceModels.data.length === 0) {
      return null
    }

    const brandModelCounts = new Map<string, number>()
    devices.data?.forEach((device: Device) => {
      if (device.device_model_id) {
        const deviceModel = deviceModels.data?.find(
          (model) => model.device_model_id === device.device_model_id,
        )
        if (deviceModel) {
          const key = `${deviceModel.brand}|${deviceModel.model}`
          brandModelCounts.set(key, (brandModelCounts.get(key) ?? 0) + 1)
        }
      }
    })

    if (brandModelCounts.size === 0) {
      return null
    }

    let mostCommon = ''
    let maxCount = 0
    brandModelCounts.forEach((count, key) => {
      if (count > maxCount) {
        maxCount = count
        mostCommon = key
      }
    })

    if (!mostCommon) {
      return null
    }

    const [brand, model] = mostCommon.split('|')
    return `${brand} ${model}`
  }, [devices.data, deviceModels.data])

  const mostCommonDeviceModelId = useMemo(() => {
    if (!devices.data || devices.data.length === 0) {
      return null
    }

    const modelIdCounts = new Map<number, number>()
    devices.data.forEach((device: Device) => {
      if (device.device_model_id != null) {
        modelIdCounts.set(
          device.device_model_id,
          (modelIdCounts.get(device.device_model_id) ?? 0) + 1,
        )
      }
    })

    if (modelIdCounts.size === 0) {
      return null
    }

    let mostCommonId: number | null = null
    let maxCount = 0
    modelIdCounts.forEach((count, id) => {
      if (count > maxCount) {
        maxCount = count
        mostCommonId = id
      }
    })

    return mostCommonId
  }, [devices.data])

  const deviceModelImageUrl = useMemo(
    () => getDeviceModelImageUrl(mostCommonDeviceModelId),
    [mostCommonDeviceModelId],
  )

  const deviceModelImageFallbackUrl = useMemo(
    () => getDeviceModelImagePublicUrl(mostCommonDeviceModelId),
    [mostCommonDeviceModelId],
  )

  const inverters = useGetInverters({
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

  const inverter =
    inverters.data && inverters.data.length > 0 ? inverters.data[0] : null
  const deviceCount = devices.data?.length ?? 0

  const totalMWac = useMemo(() => {
    if (!devices.data || devices.data.length === 0) {
      return null
    }

    const totalKWac = devices.data.reduce((sum, device) => {
      return sum + (device.capacity_ac ?? 0)
    }, 0)

    return totalKWac / 1000
  }, [devices.data])

  const mwacPerDevice = useMemo(() => {
    if (!totalMWac || deviceCount === 0) {
      return null
    }

    return totalMWac / deviceCount
  }, [totalMWac, deviceCount])

  return {
    projectId: projectId ?? '',
    project: projectQuery.data,
    projectQuery,
    devices,
    deviceModels,
    omContractorScopes,
    omContractor,
    epcContractor,
    pcsBrandModel,
    mostCommonDeviceModelId,
    deviceModelImageUrl,
    deviceModelImageFallbackUrl,
    inverter,
    inverters,
    isSuperadmin,
    isAdmin,
    userType,
    deviceCount,
    totalMWac,
    mwacPerDevice,
    isLoading: projectQuery.isLoading,
    error: projectQuery.error ?? null,
  }
}

export type PvInverterContext = ReturnType<typeof usePvInverterContext>
