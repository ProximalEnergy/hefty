import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useGetSunburstData } from '@/hooks/api'
import { PlotMouseEvent, PlotType } from 'plotly.js'
import { useRef } from 'react'
import { useParams } from 'react-router'

const DeviceSunburst = ({
  depth,
  style,
}: {
  depth: number
  style: PlotType
}) => {
  const { projectId } = useParams<{ projectId: string }>()

  const { data, isLoading } = useGetSunburstData({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  const clickedRef = useRef<string>('')
  const visibleRef = useRef<number[]>([])

  const handleDeviceSunburstPlotClick = (event: Readonly<PlotMouseEvent>) => {
    const points = event.points as unknown as Array<{
      label: string
      parent: string
    }>
    // event.points contains an array of clicked points
    if (points.length > 0) {
      const clickedPoint = points[0]

      const label = clickedPoint.label
      const parent = clickedPoint.parent
      let clickedId = data?.device_names[label] ?? -1
      let clickedChildren = data?.hierarchy[clickedId]

      if (clickedRef.current === label || clickedChildren === undefined) {
        clickedRef.current = parent
      } else {
        clickedRef.current = label
      }
      if (clickedRef.current === '') {
        clickedRef.current = label
      }
      clickedId = data?.device_names[clickedRef.current] ?? -1
      clickedChildren = data?.hierarchy[clickedId]
      visibleRef.current = clickedChildren ?? []

      // Perform any additional actions based on the clicked object
    }
  }

  return (
    <PlotlyPlot
      data={[
        {
          type: style,
          labels: data?.labels || [],
          parents: data?.parents || [],
          marker: {
            colors: data?.colors || [],
          },
          branchvalues: 'total',
          maxdepth: depth,
          sort: false,
        },
      ]}
      layout={{
        margin: { l: 0, r: 0, b: 0, t: 0, pad: 0 },
      }}
      onClick={handleDeviceSunburstPlotClick}
      isLoading={isLoading}
    />
  )
}

export default DeviceSunburst
