import { DeviceTypeEnum } from '@/api/enumerations'
import type { BessPcsStaticData } from '@/pages/projects/equipment_analysis/bess_pcs/use-bess-pcs-static-data'
import {
  getDeviceModelImagePublicUrl,
  getDeviceModelImageUrl,
} from '@/utils/cdn'
import { useMemo } from 'react'

type ChildDeviceSummary = {
  label: string
  total: number
  perPcs: number | null
}

type EquipmentSummary = {
  title: string
  countLabel?: string
  deviceCount: number
  totalMwac: number | null
  mwacPerDevice: number | null
  childDeviceSummary: ChildDeviceSummary[]
  moduleCount: number
  modulesPerModuleGroup: number | null
  imageSrc: string | null
  imageFallbackSrc: string | null
  imagePlaceholderSrc: string
  isPcsLoading: boolean
  hasPcsError: boolean
  isChildDevicesLoading: boolean
  hasChildDevicesError: boolean
  isDeviceModelsLoading: boolean
  hasDeviceModelsError: boolean
}

type UseEquipmentSummaryParams = {
  staticData: BessPcsStaticData
}

const FALLBACK_TITLE = 'BESS PCS'
const IMAGE_PLACEHOLDER_SRC = '/icon_bess_pcs.svg'

export function useEquipmentSummary({
  staticData,
}: UseEquipmentSummaryParams): EquipmentSummary {
  const { pcsDevices, childDevices, deviceModels } = staticData
  const deviceCount = pcsDevices?.length || 0

  const totalMwac = useMemo(() => {
    if (!pcsDevices?.length) {
      return null
    }

    const totalKwac = pcsDevices.reduce((sum, device) => {
      return sum + (device.capacity_ac || 0)
    }, 0)

    return totalKwac / 1000
  }, [pcsDevices])

  const mwacPerDevice = useMemo(() => {
    if (totalMwac === null || deviceCount === 0) {
      return null
    }

    return totalMwac / deviceCount
  }, [deviceCount, totalMwac])

  const childDeviceSummary = useMemo(() => {
    if (!pcsDevices || !childDevices) {
      return []
    }

    const pcsIds = new Set(pcsDevices.map((device) => device.device_id))
    const moduleGroups = childDevices.filter((child) => {
      return (
        child.device_type_id === DeviceTypeEnum.BESS_PCS_MODULE_GROUP &&
        child.parent_device_id !== null &&
        pcsIds.has(child.parent_device_id)
      )
    })
    const moduleGroupIds = new Set(
      moduleGroups.map((moduleGroup) => moduleGroup.device_id),
    )

    const moduleGroupsPerPcs = new Map<number, number>()
    moduleGroups.forEach((moduleGroup) => {
      const pcsId = moduleGroup.parent_device_id
      if (pcsId === null) {
        return
      }
      moduleGroupsPerPcs.set(pcsId, (moduleGroupsPerPcs.get(pcsId) || 0) + 1)
    })

    const modulesPerPcs = new Map<number, number>()
    const modules = childDevices.filter((child) => {
      if (child.device_type_id !== DeviceTypeEnum.BESS_PCS_MODULE) {
        return false
      }

      const parentId = child.parent_device_id
      if (parentId === null) {
        return false
      }

      if (moduleGroupIds.has(parentId)) {
        const parentModuleGroup = moduleGroups.find(
          (moduleGroup) => moduleGroup.device_id === parentId,
        )
        const pcsId = parentModuleGroup?.parent_device_id
        if (pcsId !== null && pcsId !== undefined) {
          modulesPerPcs.set(pcsId, (modulesPerPcs.get(pcsId) || 0) + 1)
          return true
        }
      }

      if (pcsIds.has(parentId)) {
        modulesPerPcs.set(parentId, (modulesPerPcs.get(parentId) || 0) + 1)
        return true
      }

      return false
    })

    const summarizePerParent = (countsByParent: Map<number, number>) => {
      const counts = Array.from(countsByParent.values())
      const allSame =
        counts.length > 0 && counts.every((count) => count === counts[0])

      return allSame ? counts[0] : null
    }

    return [
      {
        label: 'Module Groups',
        total: moduleGroups.length,
        perPcs: summarizePerParent(moduleGroupsPerPcs),
      },
      {
        label: 'Modules',
        total: modules.length,
        perPcs: summarizePerParent(modulesPerPcs),
      },
    ].filter((entry) => entry.total > 0)
  }, [childDevices, pcsDevices])

  const moduleCount = useMemo(() => {
    const modulesStat = childDeviceSummary.find(
      (item) => item.label === 'Modules',
    )
    return modulesStat?.total || 0
  }, [childDeviceSummary])

  const modulesPerModuleGroup = useMemo(() => {
    if (!childDevices) {
      return null
    }

    const moduleGroupIds = new Set(
      childDevices
        .filter((child) => {
          return child.device_type_id === DeviceTypeEnum.BESS_PCS_MODULE_GROUP
        })
        .map((child) => child.device_id),
    )

    if (moduleGroupIds.size === 0) {
      return null
    }

    const countsByGroup = new Map<number, number>()
    childDevices.forEach((child) => {
      if (
        child.device_type_id !== DeviceTypeEnum.BESS_PCS_MODULE ||
        child.parent_device_id === null ||
        !moduleGroupIds.has(child.parent_device_id)
      ) {
        return
      }

      countsByGroup.set(
        child.parent_device_id,
        (countsByGroup.get(child.parent_device_id) || 0) + 1,
      )
    })

    const counts = Array.from(countsByGroup.values())
    const allSame =
      counts.length > 0 && counts.every((count) => count === counts[0])

    return allSame ? counts[0] : null
  }, [childDevices])

  const resolvedModel = useMemo(() => {
    if (!pcsDevices || !deviceModels?.length) {
      return null
    }

    const counts = new Map<number, { count: number; title: string }>()

    pcsDevices.forEach((device) => {
      if (
        device.device_model_id === null ||
        device.device_model_id === undefined
      ) {
        return
      }

      const model = deviceModels.find(
        (deviceModel) => deviceModel.device_model_id === device.device_model_id,
      )
      if (!model) {
        return
      }

      const existing = counts.get(device.device_model_id)
      counts.set(device.device_model_id, {
        count: (existing?.count || 0) + 1,
        title: `${model.brand} ${model.model}`,
      })
    })

    let resolvedId: number | null = null
    let resolvedTitle: string | null = null
    let maxCount = 0

    counts.forEach((entry, modelId) => {
      if (entry.count > maxCount) {
        maxCount = entry.count
        resolvedId = modelId
        resolvedTitle = entry.title
      }
    })

    return {
      modelId: resolvedId,
      title: resolvedTitle,
    }
  }, [deviceModels, pcsDevices])

  const imageSrc = useMemo(() => {
    return getDeviceModelImageUrl(resolvedModel?.modelId || null)
  }, [resolvedModel?.modelId])

  const imageFallbackSrc = useMemo(() => {
    return getDeviceModelImagePublicUrl(resolvedModel?.modelId || null)
  }, [resolvedModel?.modelId])

  return {
    title: resolvedModel?.title || FALLBACK_TITLE,
    countLabel: deviceCount > 0 ? `x ${deviceCount}` : undefined,
    deviceCount,
    totalMwac,
    mwacPerDevice,
    childDeviceSummary,
    moduleCount,
    modulesPerModuleGroup,
    imageSrc,
    imageFallbackSrc,
    imagePlaceholderSrc: IMAGE_PLACEHOLDER_SRC,
    isPcsLoading: staticData.isPcsLoading,
    hasPcsError: staticData.hasPcsError,
    isChildDevicesLoading: staticData.isChildDevicesLoading,
    hasChildDevicesError: staticData.hasChildDevicesError,
    isDeviceModelsLoading: staticData.isDeviceModelsLoading,
    hasDeviceModelsError: staticData.hasDeviceModelsError,
  }
}
