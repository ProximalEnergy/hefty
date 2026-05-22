import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'

dayjs.extend(utc)
dayjs.extend(timezone)

export const parseIntervalMinutes = (value: string): number => {
  const match = value.match(/(\d+)/)
  if (!match) {
    return 5
  }
  return Number(match[1])
}

/** Map 5‑min (or other) loss samples onto each base trace timestep. */
export const alignLossSeries = (
  baseTimes: string[],
  lossTimes: string[],
  lossValues: number[],
  targetMinutes: number,
  timeZone: string,
  ffillLimit?: number,
): (number | null)[] => {
  if (baseTimes.length === 0 || lossTimes.length === 0) {
    return Array.from({ length: baseTimes.length }, () => null)
  }

  const baseMs = baseTimes.map((time) =>
    dayjs(time).tz(timeZone, true).valueOf(),
  )
  const losses = lossTimes
    .map((time, idx) => ({
      time: dayjs(time).tz(timeZone, true).valueOf(),
      value: lossValues[idx],
    }))
    .sort((a, b) => a.time - b.time)

  const result: (number | null)[] = Array.from(
    { length: baseTimes.length },
    () => null,
  )

  if (targetMinutes <= 1) {
    let lossIdx = 0
    let currentValue: number | null = null
    let ffilledPeriods = 0

    for (let i = 0; i < baseMs.length; i += 1) {
      const time = baseMs[i]
      let matchedLoss = false
      while (lossIdx < losses.length && time >= losses[lossIdx].time) {
        currentValue = losses[lossIdx].value
        lossIdx += 1
        ffilledPeriods = 0
        matchedLoss = true
      }

      if (currentValue === null || time < losses[0].time) {
        result[i] = null
      } else if (
        matchedLoss ||
        ffillLimit === undefined ||
        ffilledPeriods < ffillLimit
      ) {
        result[i] = currentValue
        if (!matchedLoss) {
          ffilledPeriods += 1
        }
      } else {
        result[i] = null
      }
    }

    return result
  }

  let pointer = 0
  let lastValue: number | null = null
  let ffilledPeriods = 0

  for (let i = 0; i < baseMs.length; i += 1) {
    const start = baseMs[i]
    const end =
      i < baseMs.length - 1 ? baseMs[i + 1] : start + targetMinutes * 60 * 1000

    while (pointer < losses.length && losses[pointer].time < start) {
      pointer += 1
    }

    let idx = pointer
    let sum = 0
    let count = 0

    while (idx < losses.length && losses[idx].time < end) {
      sum += losses[idx].value
      count += 1
      idx += 1
    }

    if (count > 0) {
      const average = sum / count
      result[i] = average
      lastValue = average
      ffilledPeriods = 0
      pointer = idx
    } else if (
      lastValue !== null &&
      (ffillLimit === undefined || ffilledPeriods < ffillLimit)
    ) {
      result[i] = lastValue
      ffilledPeriods += 1
    } else {
      result[i] = null
    }
  }

  return result
}
