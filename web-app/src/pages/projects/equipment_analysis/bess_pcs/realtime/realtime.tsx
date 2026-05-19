import { ErrorBoundary } from '@/ErrorBoundary'
import { StatusAndAlarmCodes } from '@/components/bess-pcs/StatusAndAlarmCodes'
import { ACVoltageChartBessPcsRealtime } from '@/pages/projects/equipment_analysis/bess_pcs/realtime/ac-voltage/ac-voltage-chart'
import { ActivePowerChartBessPcsRealtime } from '@/pages/projects/equipment_analysis/bess_pcs/realtime/active-power/active-power-chart'
import { DCVoltageChartBessPcsRealtime } from '@/pages/projects/equipment_analysis/bess_pcs/realtime/dc-voltage/dc-voltage-chart'
import { IGBTTemperatureChartBessPcsRealtime } from '@/pages/projects/equipment_analysis/bess_pcs/realtime/igbt-temperature/igbt-temperature-chart'
import { BessPcsRealtimeReactivePowerChart } from '@/pages/projects/equipment_analysis/bess_pcs/realtime/reactive-power/reactive-power-chart'
import { RealtimeStats } from '@/pages/projects/equipment_analysis/bess_pcs/realtime/stats/realtime-stats'
import { useRealtimeSources } from '@/pages/projects/equipment_analysis/bess_pcs/realtime/use-realtime-sources'
import { useBessPcsStaticData } from '@/pages/projects/equipment_analysis/bess_pcs/use-bess-pcs-static-data'
import { Stack } from '@mantine/core'
import { useMemo } from 'react'
import { useParams } from 'react-router'

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

      <ActivePowerChartBessPcsRealtime
        realtimeData={sources.pcsRealtime}
        maxCapacityMWac={maxCapacityMwac}
      />

      <BessPcsRealtimeReactivePowerChart
        realtimeData={sources.pcsRealtime}
        maxCapacityMWac={maxCapacityMwac}
      />

      <ACVoltageChartBessPcsRealtime />

      <DCVoltageChartBessPcsRealtime realtimeData={sources.pcsRealtime} />

      <IGBTTemperatureChartBessPcsRealtime maxCapacityMWac={maxCapacityMwac} />

      <ErrorBoundary>
        <StatusAndAlarmCodes projectId={projectId || '-1'} />
      </ErrorBoundary>
    </Stack>
  )
}
