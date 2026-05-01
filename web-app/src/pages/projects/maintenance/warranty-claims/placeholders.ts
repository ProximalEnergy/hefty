import type { ClaimListItem } from '@/api/v1/operational/claims'

export const PV_PLACEHOLDERS: ClaimListItem[] = [
  {
    claim_id: -1,
    claim_config_id: 0,
    status: 'submitted',
    summary: 'String inverter failure — INV-14',
    external_reference: 'WC-2026-001',
    counterparty_name: 'Sungrow',
    created_at: '2026-01-12T10:00:00Z',
    updated_at: '2026-01-28T14:00:00Z',
    device_count: 1,
  },
  {
    claim_id: -2,
    claim_config_id: 0,
    status: 'in_progress',
    summary: 'PV module hot-spot degradation — Block A rows 12-18',
    external_reference: 'WC-2026-002',
    counterparty_name: 'LONGi',
    created_at: '2026-01-20T08:00:00Z',
    updated_at: '2026-02-15T09:30:00Z',
    device_count: 42,
  },
  {
    claim_id: -3,
    claim_config_id: 0,
    status: 'resolved',
    summary: 'Tracker motor seized — Zone C',
    external_reference: 'WC-2025-018',
    counterparty_name: 'NEXTracker',
    created_at: '2025-11-05T12:00:00Z',
    updated_at: '2026-01-10T16:00:00Z',
    device_count: 3,
  },
  {
    claim_id: -4,
    claim_config_id: 0,
    status: 'submitted',
    summary: 'DC combiner box arc fault damage',
    external_reference: 'WC-2026-003',
    counterparty_name: 'SMA',
    created_at: '2026-02-01T09:00:00Z',
    updated_at: '2026-02-05T11:00:00Z',
    device_count: 2,
  },
  {
    claim_id: -5,
    claim_config_id: 0,
    status: 'closed',
    summary: 'PPC firmware defect causing curtailment',
    external_reference: 'WC-2025-012',
    counterparty_name: 'Power Electronics',
    created_at: '2025-09-15T07:00:00Z',
    updated_at: '2025-12-20T10:00:00Z',
    device_count: 1,
  },
  {
    claim_id: -6,
    claim_config_id: 0,
    status: 'draft',
    summary: 'Module PID — Block D south-facing strings',
    external_reference: null,
    counterparty_name: 'Canadian Solar',
    created_at: '2026-03-28T14:00:00Z',
    updated_at: '2026-03-28T14:00:00Z',
    device_count: 0,
  },
  {
    claim_id: -7,
    claim_config_id: 0,
    status: 'in_progress',
    summary: 'Inverter AC contactor failure — central INV-03',
    external_reference: 'WC-2026-005',
    counterparty_name: 'Sungrow',
    created_at: '2026-02-20T11:00:00Z',
    updated_at: '2026-03-15T08:00:00Z',
    device_count: 1,
  },
  {
    claim_id: -8,
    claim_config_id: 0,
    status: 'submitted',
    summary: 'MV transformer oil leak — MVT-02',
    external_reference: 'WC-2026-006',
    counterparty_name: 'ABB',
    created_at: '2026-03-01T10:00:00Z',
    updated_at: '2026-03-10T12:00:00Z',
    device_count: 1,
  },
  {
    claim_id: -9,
    claim_config_id: 0,
    status: 'resolved',
    summary: 'Module delamination — Block B rows 1-5',
    external_reference: 'WC-2025-021',
    counterparty_name: 'JA Solar',
    created_at: '2025-10-10T08:00:00Z',
    updated_at: '2026-01-05T09:00:00Z',
    device_count: 60,
  },
  {
    claim_id: -10,
    claim_config_id: 0,
    status: 'submitted',
    summary: 'Tracker row stuck in stow — wind event damage',
    external_reference: 'WC-2026-007',
    counterparty_name: 'Array Technologies',
    created_at: '2026-03-20T07:00:00Z',
    updated_at: '2026-03-25T15:00:00Z',
    device_count: 8,
  },
]

export const BESS_PLACEHOLDERS: ClaimListItem[] = [
  {
    claim_id: -11,
    claim_config_id: 0,
    status: 'submitted',
    summary: 'Battery module thermal runaway — Enclosure E-04',
    external_reference: 'WC-2026-010',
    counterparty_name: 'CATL',
    created_at: '2026-01-15T09:00:00Z',
    updated_at: '2026-02-01T11:00:00Z',
    device_count: 4,
  },
  {
    claim_id: -12,
    claim_config_id: 0,
    status: 'in_progress',
    summary: 'PCS inverter IGBT failure — PCS-02',
    external_reference: 'WC-2026-011',
    counterparty_name: 'Sungrow',
    created_at: '2026-02-05T10:00:00Z',
    updated_at: '2026-03-12T08:00:00Z',
    device_count: 1,
  },
  {
    claim_id: -13,
    claim_config_id: 0,
    status: 'resolved',
    summary: 'Battery string SOH below guarantee — strings S-12 to S-15',
    external_reference: 'WC-2025-030',
    counterparty_name: 'BYD',
    created_at: '2025-10-20T08:00:00Z',
    updated_at: '2026-01-18T14:00:00Z',
    device_count: 4,
  },
  {
    claim_id: -14,
    claim_config_id: 0,
    status: 'submitted',
    summary: 'HVAC unit failure causing enclosure overtemp',
    external_reference: 'WC-2026-012',
    counterparty_name: 'Sungrow',
    created_at: '2026-02-28T12:00:00Z',
    updated_at: '2026-03-05T09:00:00Z',
    device_count: 2,
  },
  {
    claim_id: -15,
    claim_config_id: 0,
    status: 'closed',
    summary: 'PPC communication loss — repeated grid code violations',
    external_reference: 'WC-2025-025',
    counterparty_name: 'ABB',
    created_at: '2025-08-10T07:00:00Z',
    updated_at: '2025-11-30T16:00:00Z',
    device_count: 1,
  },
  {
    claim_id: -16,
    claim_config_id: 0,
    status: 'draft',
    summary: 'DC-DC converter efficiency degradation — Block B',
    external_reference: null,
    counterparty_name: 'Sungrow',
    created_at: '2026-03-25T14:00:00Z',
    updated_at: '2026-03-25T14:00:00Z',
    device_count: 0,
  },
  {
    claim_id: -17,
    claim_config_id: 0,
    status: 'in_progress',
    summary: 'Battery bank capacity test failure — Bank B-03',
    external_reference: 'WC-2026-014',
    counterparty_name: 'Samsung SDI',
    created_at: '2026-03-01T08:00:00Z',
    updated_at: '2026-03-20T10:00:00Z',
    device_count: 1,
  },
  {
    claim_id: -18,
    claim_config_id: 0,
    status: 'submitted',
    summary: 'PCS module fan bearing failure — PCS-M-07',
    external_reference: 'WC-2026-015',
    counterparty_name: 'Sungrow',
    created_at: '2026-03-10T11:00:00Z',
    updated_at: '2026-03-18T09:00:00Z',
    device_count: 1,
  },
  {
    claim_id: -19,
    claim_config_id: 0,
    status: 'resolved',
    summary: 'MV circuit breaker trip — false protection fault',
    external_reference: 'WC-2025-028',
    counterparty_name: 'Eaton',
    created_at: '2025-11-15T09:00:00Z',
    updated_at: '2026-02-10T12:00:00Z',
    device_count: 1,
  },
  {
    claim_id: -20,
    claim_config_id: 0,
    status: 'submitted',
    summary: 'Battery string voltage imbalance — rack R-22',
    external_reference: 'WC-2026-016',
    counterparty_name: 'CATL',
    created_at: '2026-03-22T08:00:00Z',
    updated_at: '2026-03-28T10:00:00Z',
    device_count: 2,
  },
]

type FakeUpdate = {
  type: string
  status: string | null
  message: string
  user: string
  date: string
}

const FAKE_UPDATES: Record<number, FakeUpdate[]> = {
  [-1]: [
    {
      type: 'status_change',
      status: 'draft',
      message: 'Claim created',
      user: 'Sarah Chen',
      date: '2026-01-12T10:00:00Z',
    },
    {
      type: 'note',
      status: null,
      message:
        'Inverter INV-14 showing E-031 fault. Output dropped to 0 kW. Site crew confirmed unit not responding.',
      user: 'Sarah Chen',
      date: '2026-01-12T10:30:00Z',
    },
    {
      type: 'submission',
      status: 'submitted',
      message: 'Claim submitted to Sungrow via email',
      user: 'Sarah Chen',
      date: '2026-01-14T09:00:00Z',
    },
    {
      type: 'oem_message',
      status: null,
      message:
        'Sungrow acknowledged receipt. Requesting serial number photo and event logs.',
      user: 'Mike Torres',
      date: '2026-01-18T14:00:00Z',
    },
    {
      type: 'note',
      status: null,
      message: 'Uploaded inverter serial plate photo and SCADA event export.',
      user: 'Sarah Chen',
      date: '2026-01-20T11:00:00Z',
    },
  ],
  [-2]: [
    {
      type: 'status_change',
      status: 'draft',
      message: 'Claim created',
      user: 'James Park',
      date: '2026-01-20T08:00:00Z',
    },
    {
      type: 'note',
      status: null,
      message:
        'Drone inspection identified 42 modules with hot-spot defects in Block A, rows 12-18. EL imaging confirms cell cracking.',
      user: 'James Park',
      date: '2026-01-20T08:30:00Z',
    },
    {
      type: 'submission',
      status: 'submitted',
      message: 'Claim submitted with drone report and EL images',
      user: 'James Park',
      date: '2026-01-22T09:00:00Z',
    },
    {
      type: 'oem_message',
      status: null,
      message:
        'LONGi reviewing images. Requested shipping 3 sample modules for lab analysis.',
      user: 'LONGi Support',
      date: '2026-02-01T10:00:00Z',
    },
    {
      type: 'status_change',
      status: 'in_progress',
      message:
        'LONGi confirmed manufacturing defect in batch. Replacement modules being shipped.',
      user: 'James Park',
      date: '2026-02-15T09:30:00Z',
    },
  ],
  [-3]: [
    {
      type: 'status_change',
      status: 'draft',
      message: 'Claim created',
      user: 'Emily Rodriguez',
      date: '2025-11-05T12:00:00Z',
    },
    {
      type: 'submission',
      status: 'submitted',
      message:
        'Submitted to NEXTracker — 3 tracker motors in Zone C seized after rain event',
      user: 'Emily Rodriguez',
      date: '2025-11-06T09:00:00Z',
    },
    {
      type: 'field_visit',
      status: null,
      message:
        'NEXTracker technician inspected on-site. Confirmed bearing failure due to seal defect.',
      user: 'NEXTracker Field Eng',
      date: '2025-11-20T14:00:00Z',
    },
    {
      type: 'parts',
      status: null,
      message: '3 replacement motors shipped. ETA Dec 5.',
      user: 'Emily Rodriguez',
      date: '2025-11-28T10:00:00Z',
    },
    {
      type: 'status_change',
      status: 'resolved',
      message: 'Motors replaced and tested. All 3 rows tracking normally.',
      user: 'Emily Rodriguez',
      date: '2026-01-10T16:00:00Z',
    },
  ],
  [-11]: [
    {
      type: 'status_change',
      status: 'draft',
      message: 'Claim created',
      user: 'David Kim',
      date: '2026-01-15T09:00:00Z',
    },
    {
      type: 'note',
      status: null,
      message:
        'Enclosure E-04 fire suppression triggered. 4 battery modules show thermal damage. Enclosure isolated.',
      user: 'David Kim',
      date: '2026-01-15T09:30:00Z',
    },
    {
      type: 'submission',
      status: 'submitted',
      message:
        'Emergency claim submitted to CATL with incident report and BMS logs',
      user: 'David Kim',
      date: '2026-01-16T08:00:00Z',
    },
    {
      type: 'oem_message',
      status: null,
      message:
        'CATL dispatching investigation team. Requested full BMS data export and thermal camera footage.',
      user: 'CATL Engineering',
      date: '2026-01-18T10:00:00Z',
    },
    {
      type: 'field_visit',
      status: null,
      message:
        'CATL team completed on-site investigation. Root cause: cell manufacturing defect in batch QC-2025-L04.',
      user: 'David Kim',
      date: '2026-02-01T11:00:00Z',
    },
  ],
  [-12]: [
    {
      type: 'status_change',
      status: 'draft',
      message: 'Claim created',
      user: 'Lisa Wang',
      date: '2026-02-05T10:00:00Z',
    },
    {
      type: 'note',
      status: null,
      message:
        'PCS-02 tripped on IGBT overcurrent fault. Unit shows F-107 alarm. Cannot restart.',
      user: 'Lisa Wang',
      date: '2026-02-05T10:15:00Z',
    },
    {
      type: 'submission',
      status: 'submitted',
      message: 'Submitted to Sungrow with fault logs and photos',
      user: 'Lisa Wang',
      date: '2026-02-06T09:00:00Z',
    },
    {
      type: 'parts',
      status: null,
      message: 'Sungrow shipping replacement IGBT module. Lead time 4-6 weeks.',
      user: 'Sungrow Support',
      date: '2026-02-20T14:00:00Z',
    },
    {
      type: 'status_change',
      status: 'in_progress',
      message: 'IGBT module received. Scheduling installation with site crew.',
      user: 'Lisa Wang',
      date: '2026-03-12T08:00:00Z',
    },
  ],
  [-13]: [
    {
      type: 'status_change',
      status: 'draft',
      message: 'Claim created',
      user: 'Tom Bradley',
      date: '2025-10-20T08:00:00Z',
    },
    {
      type: 'note',
      status: null,
      message:
        'Strings S-12 to S-15 showing SOH at 82-84%, below 88% guarantee threshold at 1.5 years.',
      user: 'Tom Bradley',
      date: '2025-10-20T08:30:00Z',
    },
    {
      type: 'submission',
      status: 'submitted',
      message: 'Submitted with KPI data export and capacity test results',
      user: 'Tom Bradley',
      date: '2025-10-22T09:00:00Z',
    },
    {
      type: 'oem_message',
      status: null,
      message:
        'BYD requesting independent capacity test per warranty protocol section 4.2',
      user: 'BYD Warranty Dept',
      date: '2025-11-05T10:00:00Z',
    },
    {
      type: 'field_visit',
      status: null,
      message: 'Independent test completed. Confirmed SOH below threshold.',
      user: 'Tom Bradley',
      date: '2025-12-10T14:00:00Z',
    },
    {
      type: 'status_change',
      status: 'resolved',
      message: 'BYD approved replacement of 4 battery strings under warranty.',
      user: 'Tom Bradley',
      date: '2026-01-18T14:00:00Z',
    },
  ],
}

export function getFakeUpdates(claimId: number): FakeUpdate[] {
  if (FAKE_UPDATES[claimId]) return FAKE_UPDATES[claimId]
  const all = [...PV_PLACEHOLDERS, ...BESS_PLACEHOLDERS]
  const c = all.find((p) => p.claim_id === claimId)
  if (!c) return []
  return [
    {
      type: 'status_change',
      status: 'draft',
      message: 'Claim created',
      user: 'System',
      date: c.created_at ?? '',
    },
    {
      type: 'submission',
      status: 'submitted',
      message: `Claim submitted to ${c.counterparty_name}`,
      user: 'System',
      date: c.created_at ?? '',
    },
    ...(c.status === 'in_progress' ||
    c.status === 'resolved' ||
    c.status === 'closed'
      ? [
          {
            type: 'status_change',
            status: c.status,
            message: `Status changed to ${c.status.replace('_', ' ')}`,
            user: 'System',
            date: c.updated_at ?? '',
          },
        ]
      : []),
  ]
}
