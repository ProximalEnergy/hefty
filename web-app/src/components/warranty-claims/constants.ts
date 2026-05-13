import {
  ClaimSubmissionChannelEnum,
  ClaimUpdateTypeEnum,
  DeviceTypeEnum,
} from '@/api/enumerations'
import {
  IconClock,
  IconFileText,
  IconMessage,
  IconSettings,
} from '@tabler/icons-react'
import type { ReactNode } from 'react'
import { createElement } from 'react'

export const STATUS_COLORS: Record<string, string> = {
  draft: 'gray',
  submitted: 'blue',
  in_progress: 'orange',
  resolved: 'green',
  closed: 'dark',
}

export const STATUS_OPTIONS = [
  { value: 'draft', label: 'Draft' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'closed', label: 'Closed' },
]

/** Matches `ClaimStatus` lifecycle for sort (not label alphabetically). */
const CLAIM_STATUS_SORT_RANK: Record<string, number> = {
  draft: 0,
  submitted: 1,
  in_progress: 2,
  resolved: 3,
  closed: 4,
}

export function claimStatusSortRank(status: string): number {
  return CLAIM_STATUS_SORT_RANK[status] ?? 999
}

export const UPDATE_TYPE_OPTIONS = [
  { value: ClaimUpdateTypeEnum.STATUS_CHANGE, label: 'Status change' },
  { value: ClaimUpdateTypeEnum.SUBMISSION, label: 'Submission' },
  { value: ClaimUpdateTypeEnum.OEM_MESSAGE, label: 'OEM message' },
  { value: ClaimUpdateTypeEnum.NOTE, label: 'Note' },
  { value: ClaimUpdateTypeEnum.PARTS, label: 'Parts' },
  { value: ClaimUpdateTypeEnum.FIELD_VISIT, label: 'Field visit' },
]

export const UPDATE_ICONS: Record<string, ReactNode> = {
  [ClaimUpdateTypeEnum.STATUS_CHANGE]: createElement(IconSettings, {
    size: 14,
  }),
  [ClaimUpdateTypeEnum.SUBMISSION]: createElement(IconFileText, { size: 14 }),
  [ClaimUpdateTypeEnum.NOTE]: createElement(IconMessage, { size: 14 }),
  [ClaimUpdateTypeEnum.OEM_MESSAGE]: createElement(IconMessage, { size: 14 }),
  [ClaimUpdateTypeEnum.PARTS]: createElement(IconSettings, { size: 14 }),
  [ClaimUpdateTypeEnum.FIELD_VISIT]: createElement(IconClock, { size: 14 }),
}

export const CHANNEL_OPTIONS = [
  { value: ClaimSubmissionChannelEnum.EMAIL, label: 'Email' },
  { value: ClaimSubmissionChannelEnum.PORTAL, label: 'Portal' },
  { value: ClaimSubmissionChannelEnum.HYBRID, label: 'Hybrid' },
]

export function channelUsesPortalUrl(channel: string): boolean {
  return (
    channel === ClaimSubmissionChannelEnum.PORTAL ||
    channel === ClaimSubmissionChannelEnum.HYBRID
  )
}

/** Minimal device row for expanding OEM event matching device IDs. */
type WarrantyEventDeviceRow = {
  device_id: number
  device_type_id: number
  device_model_id: number | null
}

/**
 * Device IDs used to load candidate events for the warranty Events step.
 *
 * When the OEM supplies BESS PCS equipment, also include MVT, PCS module
 * group, and PCS module devices on the project. When the OEM supplies a
 * BESS DC enclosure, also include BESS string devices.
 */
export function expandOemDeviceIdsForEventMatching(
  oemDeviceModelIdSet: Set<number>,
  allProjectDevices: WarrantyEventDeviceRow[],
): number[] {
  const oemOwned = allProjectDevices.filter(
    (d) =>
      d.device_model_id != null && oemDeviceModelIdSet.has(d.device_model_id),
  )
  const ids = new Set(oemOwned.map((d) => d.device_id))

  const hasPcsOemDevice = oemOwned.some(
    (d) => d.device_type_id === DeviceTypeEnum.BESS_PCS,
  )
  const hasEnclosureOemDevice = oemOwned.some(
    (d) => d.device_type_id === DeviceTypeEnum.BESS_ENCLOSURE,
  )

  if (hasPcsOemDevice) {
    const pcsRelatedTypes = new Set<number>([
      DeviceTypeEnum.BESS_MVT,
      DeviceTypeEnum.BESS_PCS_MODULE_GROUP,
      DeviceTypeEnum.BESS_PCS_MODULE,
    ])
    for (const d of allProjectDevices) {
      if (pcsRelatedTypes.has(d.device_type_id)) ids.add(d.device_id)
    }
  }
  if (hasEnclosureOemDevice) {
    for (const d of allProjectDevices) {
      if (d.device_type_id === DeviceTypeEnum.BESS_STRING) {
        ids.add(d.device_id)
      }
    }
  }

  return Array.from(ids)
}
