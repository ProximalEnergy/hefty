import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { AxiosError } from 'axios'
import type { Data, Layout } from 'plotly.js'

type EventTracesProps = {
  data: unknown[]
  error: unknown
  isLoading: boolean
  layout: Partial<Layout>
  xAxisTimeZone: string
}

export function EventTraces({
  data,
  error,
  isLoading,
  layout,
  xAxisTimeZone,
}: EventTracesProps) {
  return (
    <PlotlyPlot
      isLoading={isLoading}
      xAxisTimeZone={xAxisTimeZone}
      data={data as Data[]}
      layout={layout}
      error={error as AxiosError<{ detail: string }> | null}
    />
  )
}
