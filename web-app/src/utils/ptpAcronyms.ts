// Slimmed-down PTP acronym metadata for LongTermTab.
// Based on a subset of ERCOT settlement charge fields currently used in the UI.
// NOTE: If you add new fields to LongTermTab, update this mapping accordingly.

export interface PTPAcronymMetadata {
  elementDefinition: string
  granularityMinutes: number | null
  sequence: string
  dimensions: string
  description: string
  endpoint: string
  unit: string | null
  uiGroup: string | null
  uiSubgroup: string | null
}

interface PTPAcronymData {
  [keyname: string]: { [endpoint: string]: PTPAcronymMetadata }
}

const PTP_ACRONYM_DATA: PTPAcronymData = {
  DAEPAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'The Settlement-Quality Day-Ahead Energy Charge Daily Total',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Energy',
      uiSubgroup: 'Day-Ahead',
    },
  },
  DAESAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'The Settlement-Quality Day-Ahead Energy Payment Daily Total',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Energy',
      uiSubgroup: 'Day-Ahead',
    },
  },
  RTEIAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Energy Imbalance Payment/(Charge)',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Energy',
      uiSubgroup: 'Real-Time',
    },
  },
  DAPCECROAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'The Settlement-Quality Day-Ahead Procured Capacity for ERCOT Contingency Reserve',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'ECRS',
    },
  },
  DAPCNSOAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'The Settlement-Quality Day-Ahead Procured Capacity for Non-Spin Reserve',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'Non-Spin Reserve',
    },
  },
  DAPCRDOAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'The Settlement-Quality Day-Ahead Procured Capacity for Regulation Down',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'RegDown',
    },
  },
  DAPCRUOAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'The Settlement-Quality Day-Ahead Procured Capacity for Regulation Up',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'RegUp',
    },
  },
  DARTPCECRAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'Day-Ahead Updated Real-Time Procured Capacity for ERCOT Contingency Reserve',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'ECRS',
    },
  },
  DARTPCNSAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'Day-Ahead Updated Real-Time Procured Capacity for Non-Spin Reserve',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'Non-Spin Reserve',
    },
  },
  DARTPCRDAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'Day-Ahead Updated Real-Time Procured Capacity for Regulation Down',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'RegDown',
    },
  },
  DARTPCRUAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'Day-Ahead Updated Real-Time Procured Capacity for Regulation Up',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'RegUp',
    },
  },
  LARTDASAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Load-Allocated Real-Time Derated Ancillary Services Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: null,
    },
  },
  LARTECRAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'Load-Allocated Real-Time ERCOT Contingency Reserve Service Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'ECRS',
    },
  },
  LARTNSAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Load-Allocated Real-Time Non-Spin Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'Non-Spin Reserve',
    },
  },
  LARTRDAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Load-Allocated Real-Time Regulation Down Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'RegDown',
    },
  },
  LARTRRAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Load-Allocated Real-Time Responsive Reserve Service Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: null,
    },
  },
  LARTRUAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Load-Allocated Real-Time Regulation Up Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'RegUp',
    },
  },
  RTDASAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Real-Time Derated Ancillary Service Settlement Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: null,
    },
  },
  LASPDAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Load-Allocated Set Point Deviation Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Deviations & Imbalance',
      uiSubgroup: null,
    },
  },
  RTECRIMBAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'Real-Time ERCOT Contingency Reserve Service Imbalance Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'ECRS',
    },
  },
  RTECROAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'Real-Time ERCOT Contingency Reserve Service Only Offer Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'ECRS',
    },
  },
  RTECRTOAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'Real-Time ERCOT Contingency Reserve Service Trade Overage Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'ECRS',
    },
  },
  RTNSIMBAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Real-Time Non-Spin Imbalance Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'Non-Spin Reserve',
    },
  },
  RTNSOAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Real-Time Non-Spin Only Offer Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'Non-Spin Reserve',
    },
  },
  RTNSTOAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Real-Time Non-Spin Trade Overage Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'Non-Spin Reserve',
    },
  },
  RTRDIMBAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'Real-Time Regulation Down Ancillary Service Imbalance Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'RegDown',
    },
  },
  RTRDOAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Real-Time Regulation Down Only Offer Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'RegDown',
    },
  },
  RTRDTOAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Real-Time Regulation-Down Trade Overage Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'RegDown',
    },
  },
  RTRRIMBAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'Real-Time Responsive Reserve Service Ancillary Service Imbalance Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: null,
    },
  },
  RTRROAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Real-Time Responsive Reserve Only Offer Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: null,
    },
  },
  RTRRTOAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Real-Time Responsive Reserve Service Trade Overage Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: null,
    },
  },
  RTRUIMBAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Real-Time Regulation Up Ancillary Service Imbalance Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'RegUp',
    },
  },
  RTRUOAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Real-Time Regulation Up Only Offer Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'RegUp',
    },
  },
  RTRUTOAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Real-Time Regulation-Up Trade Overage Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'RegUp',
    },
  },
  SPDAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Set Point Deviation Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Deviations & Imbalance',
      uiSubgroup: null,
    },
  },
  DAMWAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'The Settlement-Quality Day-Ahead Make-Whole Payment Daily Total',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'RUC & Uplift / Make-Whole',
      uiSubgroup: 'Make-Whole',
    },
  },
  DAPCRROAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'The Settlement-Quality Day-Ahead Procured Capacity for Responsive Reserve',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: null,
    },
  },
  DARTOBLLOAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'Day-Ahead Real-Time Obligation with Links to an Option Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Other / Unclassified',
      uiSubgroup: null,
    },
  },
  DARTPCRRAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'Day-Ahead Updated Real-Time Procured Capacity for Responsive Reserve',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: null,
    },
  },
  LACMRNZAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Load-Allocated CRR Monthly Revenue Non-Zonal Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Congestion & CRR/PTP',
      uiSubgroup: null,
    },
  },
  LACMRZAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Load-Allocated CRR Monthly Revenue Zonal Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Congestion & CRR/PTP',
      uiSubgroup: null,
    },
  },
  LACRRAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Load-Allocated CRR Surplus Allocation',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Congestion & CRR/PTP',
      uiSubgroup: null,
    },
  },
  LAERSAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Load-Allocated Emergency Response Service Charge',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Other / Unclassified',
      uiSubgroup: null,
    },
  },
  LAFFSSAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Load-Allocated Firm Fuel Supply Service Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Other / Unclassified',
      uiSubgroup: null,
    },
  },
  LASUCAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Load-Allocated Securitization Default Uplift Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Other / Unclassified',
      uiSubgroup: null,
    },
  },
  QNSAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Non-Spinning Reserve Amount (Quarterly)',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'Ancillary Services',
      uiSubgroup: 'Non-Spin Reserve',
    },
  },
  RMRAAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Reliability Must Run Adjustment Charge',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'RUC & Uplift / Make-Whole',
      uiSubgroup: null,
    },
  },
  RMRNPAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description:
        'Reliability Must-Run Charge for Unexcused Misconduct Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'RUC & Uplift / Make-Whole',
      uiSubgroup: null,
    },
  },
  RMRSBAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Reliability Must-Run Standby Payment',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'RUC & Uplift / Make-Whole',
      uiSubgroup: null,
    },
  },
  RUCCSAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Reliability Unit Commitment Capacity-Short Charge',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'RUC & Uplift / Make-Whole',
      uiSubgroup: null,
    },
  },
  SWMWAMT: {
    'Settlement-Charges': {
      elementDefinition: 'Entity',
      granularityMinutes: 1440,
      sequence: '',
      dimensions: '',
      description: 'Switchable Generation Resource Make-Whole Amount',
      endpoint: 'Settlement-Charges',
      unit: 'Amount ($)',
      uiGroup: 'RUC & Uplift / Make-Whole',
      uiSubgroup: 'Make-Whole',
    },
  },
}

/**
 * Get metadata for a given acronym key and optional endpoint.
 *
 * If endpoint is provided, we try to match it exactly, then fall back to
 * composite keys (e.g. endpoint_granularity) and finally to any metadata
 * entry with a matching endpoint inside the key's map.
 *
 * If endpoint is omitted, we return the first available metadata for that key.
 */
export function getAcronymMetadata(
  keyname: string,
  endpoint?: string,
): PTPAcronymMetadata | null {
  const acronymData = PTP_ACRONYM_DATA[keyname]
  if (!acronymData) return null

  // If no endpoint specified, return first available metadata
  if (!endpoint) {
    const firstKey = Object.keys(acronymData)[0]
    return firstKey ? acronymData[firstKey] : null
  }

  // Try exact key match first
  const metadata = acronymData[endpoint]
  if (metadata) return metadata

  // Try composite key match (endpoint_granularity)
  for (const key of Object.keys(acronymData)) {
    if (key.startsWith(endpoint + '_')) {
      return acronymData[key]
    }
  }

  // Fallback: find by endpoint value
  for (const value of Object.values(acronymData)) {
    if (value.endpoint === endpoint) {
      return value
    }
  }

  return null
}
