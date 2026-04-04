import { ErrorBoundary } from '@/ErrorBoundary'
import { Stack } from '@mantine/core'
import { useMemo } from 'react'
import { useParams } from 'react-router'

import { useBessPcsStaticData } from '../use-bess-pcs-static-data'
import { ACVoltageChart } from './ac-voltage/ac-voltage-chart'
import { ActivePowerChart } from './active-power/active-power-chart'
import { DCVoltageChart } from './dc-voltage/dc-voltage-chart'
import { IGBTTemperatureChart } from './igbt-temperature/igbt-temperature-chart'
import { ReactivePowerChart } from './reactive-power/reactive-power-chart'
import { RealtimeStats } from './stats/realtime-stats'
import { StatusAndAlarmCodes } from './status-and-alarm-codes/status-and-alarm-codes'
import { useRealtimeSources } from './use-realtime-sources'

export function Realtime() {
  const { projectId } = useParams<{ projectId: string }>()
  const staticData = useBessPcsStaticData({ projectId })
  const sources = useRealtimeSources({ projectId })

  const maxCapacityMwac = useMemo(() => {
    if (!staticData.pcsDevices?.length) {
      return null
    }

    const maxKwac = Math.max(
      ...staticData.pcsDevices.map((device) => device.capacity_ac || 0),
    )

    return maxKwac / 1000
  }, [staticData.pcsDevices])

  return (
    <Stack gap="md" pb="md">
      <RealtimeStats pcsDevices={staticData.pcsDevices} sources={sources} />

      <ActivePowerChart
        realtimeData={sources.pcsRealtime}
        maxCapacityMWac={maxCapacityMwac}
      />

      <ReactivePowerChart
        realtimeData={sources.pcsRealtime}
        maxCapacityMWac={maxCapacityMwac}
      />

      <ACVoltageChart />

      <DCVoltageChart realtimeData={sources.pcsRealtime} />

      <IGBTTemperatureChart maxCapacityMWac={maxCapacityMwac} />

      <ErrorBoundary>
        <StatusAndAlarmCodes projectId={projectId || '-1'} />
      </ErrorBoundary>
    </Stack>
  )
}
