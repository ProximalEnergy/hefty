import Plotly from 'plotly.js/dist/plotly-custom.min.js'
import { type RefObject, useEffect } from 'react'

type UseResizePlotlyChartsOptions = {
  containerRef: RefObject<HTMLElement | null>
  enabled: boolean
  delayMs?: number
  dependency?: unknown
}

export const useResizePlotlyCharts = ({
  containerRef,
  enabled,
  delayMs = 150,
  dependency,
}: UseResizePlotlyChartsOptions) => {
  useEffect(() => {
    const container = containerRef.current

    if (!enabled || !container) {
      return
    }

    let timeoutId: number | undefined

    const resizeCharts = () => {
      const plotElements = container.querySelectorAll(
        '.js-plotly-plot',
      ) as NodeListOf<HTMLElement>

      if (plotElements.length === 0) {
        return
      }

      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId)
      }

      timeoutId = window.setTimeout(() => {
        plotElements.forEach((plotElement) => {
          const rect = plotElement.getBoundingClientRect()
          if (rect.width > 0 && rect.height > 0) {
            Plotly.Plots.resize(plotElement)
          }
        })
      }, delayMs)
    }

    resizeCharts()

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && entry.intersectionRatio > 0) {
            resizeCharts()
          }
        })
      },
      { threshold: 0.01 },
    )

    observer.observe(container)

    return () => {
      observer.disconnect()
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId)
      }
    }
  }, [containerRef, delayMs, enabled, dependency])
}
