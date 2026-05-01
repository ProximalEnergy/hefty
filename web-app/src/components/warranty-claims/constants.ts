import {
  ClaimSubmissionChannelEnum,
  ClaimUpdateTypeEnum,
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
