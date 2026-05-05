import { DeviceTypeEnum } from '@/api/enumerations'
import { useLocalStorage } from '@mantine/hooks'

/** Project performance map vs Events page embedded map — separate prefs per project. */
type MapEventDeviceSurface = 'home' | 'events'

const LEGACY_GLOBAL_DC = 'proximal-gis-show-dc-field-events'

const legacyPerProjectDcKey = (
  projectId: string,
  surface: MapEventDeviceSurface,
): string => `proximal-gis-dc-field-events:${projectId}:${surface}`

const storageKey = (
  projectId: string,
  surface: MapEventDeviceSurface,
): string =>
  `proximal-gis-map-hidden-event-device-types:${projectId}:${surface}`

/** Seed from legacy DC-only toggles when the new key is absent. */
function readInitialHidden(
  projectId: string,
  surface: MapEventDeviceSurface,
): number[] {
  if (typeof window === 'undefined') {
    return []
  }
  try {
    const k = storageKey(projectId, surface)
    if (localStorage.getItem(k) !== null) {
      return JSON.parse(localStorage.getItem(k) as string) as number[]
    }
    const perProject = localStorage.getItem(
      legacyPerProjectDcKey(projectId, surface),
    )
    if (perProject !== null && JSON.parse(perProject) === false) {
      return [DeviceTypeEnum.DC_FIELD]
    }
    if (surface === 'home' && projectId !== '__invalid__') {
      const g = localStorage.getItem(LEGACY_GLOBAL_DC)
      if (g !== null && JSON.parse(g) === false) {
        return [DeviceTypeEnum.DC_FIELD]
      }
    }
  } catch {
    /* ignore */
  }
  return []
}

export function usePerProjectHiddenMapEventDeviceTypes(
  projectId: string | undefined,
  surface: MapEventDeviceSurface,
) {
  const id = projectId ?? '__invalid__'
  return useLocalStorage<number[]>({
    key: storageKey(id, surface),
    defaultValue: readInitialHidden(id, surface),
  })
}
