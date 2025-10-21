import { PlotRelayoutEvent } from 'plotly.js'
import { useCallback, useState } from 'react'

export interface SynchronizedLayout {
  xaxis: { range: number[] }
  yaxis: { range: number[] }
}

export const useSynchronizedCharts = () => {
  // Add synchronized layout state for charts
  const [synchronizedLayout, setSynchronizedLayout] =
    useState<SynchronizedLayout>({
      xaxis: { range: [] },
      yaxis: { range: [] },
    })

  // Add synchronized relayout handler
  const handleSynchronizedRelayout = useCallback(
    (relayoutData: PlotRelayoutEvent) => {
      // Check for axis range changes
      if (
        relayoutData['xaxis.range[0]'] !== undefined ||
        relayoutData['yaxis.range[0]'] !== undefined
      ) {
        setSynchronizedLayout((prevLayout) => ({
          ...prevLayout,
          xaxis: {
            range:
              relayoutData['xaxis.range[0]'] !== undefined
                ? [
                    relayoutData['xaxis.range[0]'] as number,
                    relayoutData['xaxis.range[1]'] as number,
                  ]
                : prevLayout.xaxis.range,
          },
          yaxis: {
            range:
              relayoutData['yaxis.range[0]'] !== undefined
                ? [
                    relayoutData['yaxis.range[0]'] as number,
                    relayoutData['yaxis.range[1]'] as number,
                  ]
                : prevLayout.yaxis.range,
          },
        }))
      } else if (
        relayoutData['xaxis.autorange'] ||
        relayoutData['yaxis.autorange']
      ) {
        // Handle double-click to reset view (autorange)
        setSynchronizedLayout({
          xaxis: { range: [] },
          yaxis: { range: [] },
        })
      }
    },
    [],
  )

  return {
    synchronizedLayout,
    handleSynchronizedRelayout,
  }
}
