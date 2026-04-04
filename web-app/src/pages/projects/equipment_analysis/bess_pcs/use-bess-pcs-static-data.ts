import { DeviceTypeEnum } from '@/api/enumerations'
import type { components } from '@/api/schema'
import { useGetDeviceModels } from '@/api/v1/operational/device_models'
import { useGetDevicesV2 } from '@/hooks/api'
import type { Device } from '@/hooks/types'
import { useMemo } from 'react'

type DeviceModel = components['schemas']['DeviceModel']

type UseBessPcsStaticDataParams = {
  projectId?: string
}

export type BessPcsStaticData = {
  pcsDevices: Device[] | undefined
  childDevices: Device[] | undefined
  deviceModels: DeviceModel[] | undefined
  isPcsLoading: boolean
  hasPcsError: boolean
  isChildDevicesLoading: boolean
  hasChildDevicesError: boolean
  isDeviceModelsLoading: boolean
  hasDeviceModelsError: boolean
}

const queryOptions = {
  staleTime: Infinity,
  refetchOnWindowFocus: false,
  refetchOnMount: false,
  refetchOnReconnect: false,
}

export function useBessPcsStaticData({
  projectId,
}: UseBessPcsStaticDataParams): BessPcsStaticData {
  const enabled = !!projectId

  const pcsDevices = useGetDevicesV2({
    pathParams: {
      projectId: projectId || '-1',
    },
    filters: {
      device_type_ids: [DeviceTypeEnum.BESS_PCS],
    },
    queryOptions: {
      enabled,
      ...queryOptions,
    },
  })

  const childDevices = useGetDevicesV2({
    pathParams: {
      projectId: projectId || '-1',
    },
    filters: {
      device_type_ids: [
        DeviceTypeEnum.BESS_PCS_MODULE,
        DeviceTypeEnum.BESS_PCS_MODULE_GROUP,
      ],
    },
    queryOptions: {
      enabled,
      ...queryOptions,
    },
  })

  const deviceModelIds = useMemo(() => {
    if (!pcsDevices.data?.length) {
      return []
    }

    const modelIds = new Set<number>()

    pcsDevices.data.forEach((device) => {
      if (
        device.device_model_id !== null &&
        device.device_model_id !== undefined
      ) {
        modelIds.add(device.device_model_id)
      }
    })

    return Array.from(modelIds).sort((a, b) => a - b)
  }, [pcsDevices.data])

  const deviceModels = useGetDeviceModels({
    queryParams: {
      device_model_ids: deviceModelIds,
    },
    queryOptions: {
      enabled: deviceModelIds.length > 0,
      ...queryOptions,
    },
  })

  return {
    pcsDevices: pcsDevices.data,
    childDevices: childDevices.data,
    deviceModels: deviceModels.data,
    isPcsLoading: pcsDevices.isLoading,
    hasPcsError: pcsDevices.isError,
    isChildDevicesLoading: childDevices.isLoading,
    hasChildDevicesError: childDevices.isError,
    isDeviceModelsLoading: deviceModels.isLoading,
    hasDeviceModelsError: deviceModels.isError,
  }
}
