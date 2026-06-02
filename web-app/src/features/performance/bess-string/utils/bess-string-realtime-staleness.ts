import { formatRelativeTime } from '@/utils/relativeTime'

/** Chart bars stay full opacity when telemetry is newer than this. */
const BESS_STRING_CHART_FRESH_MS = 10 * 60 * 1000

/** Between fresh and stale — bars render at reduced opacity (10–60 min). */
const BESS_STRING_CHART_DELAYED_MS = 60 * 60 * 1000

/** Data Status card: device treated as not reporting beyond this age. */
const BESS_STRING_NOT_REPORTING_MS = 60 * 60 * 1000

export type DataFreshnessTier = 'fresh' | 'delayed' | 'stale' | 'missing'

const TIER_RANK: Record<DataFreshnessTier, number> = {
  fresh: 0,
  delayed: 1,
  stale: 2,
  missing: 3,
}

function getDataFreshnessTier(
  time: string | null | undefined,
  nowMs: number = Date.now(),
): DataFreshnessTier {
  if (!time) {
    return 'missing'
  }
  const ts = new Date(time).getTime()
  if (Number.isNaN(ts)) {
    return 'missing'
  }
  const ageMs = nowMs - ts
  if (ageMs <= BESS_STRING_CHART_FRESH_MS) {
    return 'fresh'
  }
  if (ageMs <= BESS_STRING_CHART_DELAYED_MS) {
    return 'delayed'
  }
  return 'stale'
}

export function getWorstFreshnessTier(
  times: (string | null | undefined)[],
  nowMs: number = Date.now(),
): DataFreshnessTier {
  return times.reduce<DataFreshnessTier>((worst, time) => {
    const tier = getDataFreshnessTier(time, nowMs)
    return TIER_RANK[tier] > TIER_RANK[worst] ? tier : worst
  }, 'fresh')
}

export function isDeviceNotReporting(
  time: string | null | undefined,
  nowMs: number = Date.now(),
): boolean {
  if (!time) {
    return true
  }
  const ts = new Date(time).getTime()
  if (Number.isNaN(ts)) {
    return true
  }
  return nowMs - ts >= BESS_STRING_NOT_REPORTING_MS
}

export function barOpacityForTier(tier: DataFreshnessTier): number {
  switch (tier) {
    case 'fresh':
      return 1
    case 'delayed':
      return 0.45
    case 'stale':
    case 'missing':
      return 0.3
  }
}

export function freshnessLabel(tier: DataFreshnessTier): string {
  switch (tier) {
    case 'fresh':
      return 'Fresh'
    case 'delayed':
      return 'Delayed'
    case 'stale':
      return 'Stale'
    case 'missing':
      return 'No timestamp'
  }
}

export function formatUpdatedHover(
  time: string | null | undefined,
  nowMs: number = Date.now(),
): { relative: string; freshness: string; tier: DataFreshnessTier } {
  const tier = getDataFreshnessTier(time, nowMs)
  return {
    relative: time ? formatRelativeTime(time).relative : 'N/A',
    freshness: freshnessLabel(tier),
    tier,
  }
}

export function oldestTimestamp(
  times: (string | null | undefined)[],
): string | null | undefined {
  let oldest: string | null | undefined = null
  let oldestTs = Infinity

  for (const time of times) {
    if (!time) {
      continue
    }
    const ts = new Date(time).getTime()
    if (Number.isNaN(ts)) {
      continue
    }
    if (ts < oldestTs) {
      oldestTs = ts
      oldest = time
    }
  }

  if (oldest !== null) {
    return oldest
  }

  return times.find((time) => time != null)
}

export function barMarkerWithFreshness(
  baseColor: string,
  times: (string | null | undefined)[],
  nowMs: number = Date.now(),
): { color: string; opacity: number | number[] } {
  const tiers = times.map((time) => getDataFreshnessTier(time, nowMs))
  const opacities = tiers.map(barOpacityForTier)
  const allFresh = tiers.every((tier) => tier === 'fresh')
  return {
    color: baseColor,
    opacity: allFresh ? 1 : opacities,
  }
}
