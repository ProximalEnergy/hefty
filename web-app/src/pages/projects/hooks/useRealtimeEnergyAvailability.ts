import { DeviceTypeEnum, ProjectTypeEnum } from '@/api/enumerations'
import { useGetDevicesV2, useGetEvents } from '@/hooks/api'
import { useMemo } from 'react'

/**
 * Returns energy availability for storage projects
 * as available_strings / total_strings. A string is
 * unavailable if it, or any device in its ancestry,
 * has an open event directly assigned to it. For
 * BESS PCS module events, strings under the same
 * BESS PCS module group are also unavailable.
 */
export function useRealtimeEnergyAvailability(
  projectId: string | undefined,
  projectTypeId: number | undefined,
) {
  const hasStorage =
    projectTypeId === ProjectTypeEnum.BESS ||
    projectTypeId === ProjectTypeEnum.PVS
  const isEnabled = !!projectId && hasStorage

  const allDevices = useGetDevicesV2({
    pathParams: {
      projectId: projectId || '-1',
    },
    filters: {
      device_type_ids: [
        DeviceTypeEnum.BESS_PCS,
        DeviceTypeEnum.BESS_PCS_MODULE_GROUP,
        DeviceTypeEnum.BESS_PCS_MODULE,
        DeviceTypeEnum.BESS_ENCLOSURE,
        DeviceTypeEnum.BESS_BANK,
        DeviceTypeEnum.BESS_STRING,
      ],
    },
    queryOptions: {
      enabled: isEnabled,
      staleTime: 5 * 60 * 1000,
    },
  })

  const openEvents = useGetEvents({
    pathParams: {
      projectId: projectId || '-1',
    },
    queryParams: { open: true },
    queryOptions: {
      enabled: isEnabled,
      refetchInterval: 60 * 1000,
      staleTime: 30 * 1000,
    },
  })

  return useMemo(() => {
    if (!allDevices.data || !openEvents.data) {
      return {
        energyAvailabilityPct: null,
        availableStrings: null,
        totalStrings: null,
        isLoading: allDevices.isLoading || openEvents.isLoading,
      }
    }

    const deviceMap = new Map(allDevices.data.map((d) => [d.device_id, d]))
    const childDevicesMap = new Map<number, typeof allDevices.data>()
    allDevices.data.forEach((device) => {
      if (device.parent_device_id == null) {
        return
      }

      const siblings = childDevicesMap.get(device.parent_device_id) ?? []
      siblings.push(device)
      childDevicesMap.set(device.parent_device_id, siblings)
    })

    const strings = allDevices.data.filter(
      (d) => d.device_type_id === DeviceTypeEnum.BESS_STRING,
    )
    const totalStrings = strings.length

    if (totalStrings === 0) {
      return {
        energyAvailabilityPct: null,
        availableStrings: 0,
        totalStrings: 0,
        isLoading: false,
      }
    }

    const stringDescendantsByDeviceId = new Map<number, number[]>()
    const getStringDescendantIds = (deviceId: number): number[] => {
      const cached = stringDescendantsByDeviceId.get(deviceId)
      if (cached) {
        return cached
      }

      const descendantStringIds: number[] = []
      const childDevices = childDevicesMap.get(deviceId) ?? []

      childDevices.forEach((childDevice) => {
        if (childDevice.device_type_id === DeviceTypeEnum.BESS_STRING) {
          descendantStringIds.push(childDevice.device_id)
        }

        descendantStringIds.push(
          ...getStringDescendantIds(childDevice.device_id),
        )
      })

      stringDescendantsByDeviceId.set(deviceId, descendantStringIds)
      return descendantStringIds
    }

    const unavailableStringIds = new Set<number>()
    openEvents.data.forEach((event) => {
      const eventDevice = deviceMap.get(event.device_id) ?? event.device
      if (!eventDevice) {
        return
      }

      if (eventDevice.device_type_id === DeviceTypeEnum.BESS_STRING) {
        unavailableStringIds.add(eventDevice.device_id)
        return
      }

      getStringDescendantIds(eventDevice.device_id).forEach((stringId) => {
        unavailableStringIds.add(stringId)
      })

      if (
        eventDevice.device_type_id === DeviceTypeEnum.BESS_PCS_MODULE &&
        eventDevice.parent_device_id != null &&
        deviceMap.get(eventDevice.parent_device_id)?.device_type_id ===
          DeviceTypeEnum.BESS_PCS_MODULE_GROUP
      ) {
        getStringDescendantIds(eventDevice.parent_device_id).forEach(
          (stringId) => {
            unavailableStringIds.add(stringId)
          },
        )
      }
    })

    const availableStrings = strings.filter((s) => {
      return !unavailableStringIds.has(s.device_id)
    }).length

    const pct = (availableStrings / totalStrings) * 100

    return {
      energyAvailabilityPct: pct,
      availableStrings,
      totalStrings,
      isLoading: allDevices.isLoading || openEvents.isLoading,
    }
  }, [
    allDevices.data,
    allDevices.isLoading,
    openEvents.data,
    openEvents.isLoading,
  ])
}
