import { ErrorBoundary } from '@/ErrorBoundary'
import { Stack } from '@mantine/core'
import { useState } from 'react'

import { BessStringRealtimeCharts } from '@/features/performance/bess-string/components/BessStringRealtimeCharts'
import { StatsGrid } from '@/features/performance/bess-string/components/StatsGrid'
import { StatusCodesCard } from '@/features/performance/bess-string/components/StatusCodesCard'
import type { BessStringContext } from '@/features/performance/bess-string/hooks/use-bess-string-context'
import { useBessStringRealtimeViewModel } from '@/features/performance/bess-string/hooks/use-bess-string-realtime-view-model'

type BessStringRealtimeViewProps = {
  context: BessStringContext
}

const EMPTY_HIGHLIGHTED_DEVICE_IDS: number[] = []

export function BessStringRealtimeView({
  context,
}: BessStringRealtimeViewProps) {
  const viewModel = useBessStringRealtimeViewModel({ context })
  const [isDataStatusHovered, setIsDataStatusHovered] = useState(false)
  const highlightedNotReportingDeviceIds = isDataStatusHovered
    ? viewModel.statsGridProps.stats.staleDeviceIds
    : EMPTY_HIGHLIGHTED_DEVICE_IDS

  return (
    <Stack gap="md" pb="md">
      <StatsGrid
        {...viewModel.statsGridProps}
        onDataStatusHoverChange={setIsDataStatusHovered}
      />

      <ErrorBoundary>
        <BessStringRealtimeCharts
          {...viewModel.chartProps}
          highlightedNotReportingDeviceIds={highlightedNotReportingDeviceIds}
        />
      </ErrorBoundary>

      <ErrorBoundary>
        <StatusCodesCard projectId={viewModel.statusCodesProjectId} />
      </ErrorBoundary>
    </Stack>
  )
}
