const DEV_MIN_QUERY_INTERVAL_MS = 5 * 60 * 1000

const DEV_ENVIRONMENT_NAMES = new Set(['DEV', 'DEVELOPMENT', 'LOCAL'])
const viteEnvironment = (import.meta.env?.VITE_ENVIRONMENT ?? '').toUpperCase()

const isDevEnvironment =
  import.meta.env?.DEV || DEV_ENVIRONMENT_NAMES.has(viteEnvironment)

export const QUERY_TIME = {
  ZERO: 0,
  ONE_SECOND: 1 * 1000,
  FIVE_SECONDS: 5 * 1000,
  TEN_SECONDS: 10 * 1000,
  FIFTEEN_SECONDS: 15 * 1000,
  TWENTY_FIVE_SECONDS: 25 * 1000,
  THIRTY_SECONDS: 30 * 1000,
  ONE_MINUTE: 60 * 1000,
  FIVE_MINUTES: 5 * 60 * 1000,
  TEN_MINUTES: 10 * 60 * 1000,
  FOURTEEN_MINUTES: 14 * 60 * 1000,
  FIFTEEN_MINUTES: 15 * 60 * 1000,
  THIRTY_MINUTES: 30 * 60 * 1000,
  ONE_HOUR: 60 * 60 * 1000,
  SIX_HOURS: 6 * 60 * 60 * 1000,
  TWENTY_FOUR_HOURS: 24 * 60 * 60 * 1000,
  NEVER: Infinity,
} as const

type QueryRefetchInterval = number | false | undefined

const enforceDevMinimum = (value: number): number => {
  if (!isDevEnvironment || value === Infinity) {
    return value
  }
  return Math.max(value, DEV_MIN_QUERY_INTERVAL_MS)
}

export const withDevStaleTime = (value: number): number => {
  return enforceDevMinimum(value)
}

export const withDevRefetchInterval = (
  value: QueryRefetchInterval,
): QueryRefetchInterval => {
  if (value === false || value == null) {
    return value
  }
  return enforceDevMinimum(value)
}
