import type { CandidateEvent } from '@/api/v1/ai/historical_claim_extract'

/** Compact yyyy-mm-dd → yyyy-mm-dd range; ongoing if no end. */
function formatEventRange(
  startIso: string,
  endIso: string | null | undefined,
): string {
  const start = new Date(startIso)
  if (Number.isNaN(start.getTime())) return startIso
  const end = endIso ? new Date(endIso) : null
  const startYmd = start.toISOString().slice(0, 10)
  if (!end || Number.isNaN(end.getTime())) {
    return `${startYmd} → ongoing`
  }
  const endYmd = end.toISOString().slice(0, 10)
  if (startYmd === endYmd) return startYmd
  if (startYmd.slice(0, 4) === endYmd.slice(0, 4)) {
    return `${startYmd} → ${endYmd.slice(5)}`
  }
  return `${startYmd} → ${endYmd}`
}

/** "#id · range · failure_mode" label for an AI-suggested candidate event. */
export function formatEventOption(c: CandidateEvent): string {
  const range = formatEventRange(c.time_start, c.time_end)
  const fm = c.failure_mode ? ` · ${c.failure_mode}` : ''
  return `#${c.event_id} · ${range}${fm}`
}
