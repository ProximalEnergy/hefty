import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useGetResource, useGetResourceNetPower } from '@/hooks/api'
import { Card, Checkbox, Group, Stack, Text } from '@mantine/core'
import { useState } from 'react'
import { useParams } from 'react-router-dom'

const NetPowerPlot = () => {
  const [showSPP, setShowSPP] = useState(false)

  const { resourceId } = useParams()

  const { data, isLoading, error } = useGetResourceNetPower({
    pathParams: { resourceId: resourceId || '-1' },
  })

  let filteredData
  if (showSPP) {
    filteredData = data
  } else {
    filteredData = data?.filter((d) => d.name === 'Net Power')
  }

  return (
    <>
      <CustomCard title="Resource Net Power" style={{ height: '100%' }}>
        <PlotlyPlot
          data={
            filteredData &&
            filteredData.map((d) => ({
              x: d.x,
              y: d.y,
              name: d.name,
              hoverlabel: {
                namelength: -1,
              },
              yaxis: d.yaxis,
              line: {
                shape: 'hv',
              },
              fill: d.name === 'Net Power' ? 'tozeroy' : null,
            }))
          }
          layout={{
            yaxis: {
              title: { text: 'Net Power (MW)' },
              range: filteredData && filteredData[0].y_range,
            },
            yaxis2: {
              title: { text: 'SPP ($/MWh)' },
              side: 'right',
              showgrid: false,
              overlaying: 'y',
            },
          }}
          isLoading={isLoading}
          error={error}
        />
      </CustomCard>
      <Checkbox
        label="Show SPPs"
        checked={showSPP}
        onChange={(event) => setShowSPP(event.currentTarget.checked)}
      />
    </>
  )
}

const ResourcePage = () => {
  const { resourceId } = useParams()

  const { data, isLoading } = useGetResource({
    pathParams: { resourceId: resourceId || '-1' },
    queryParams: { deep: true },
  })

  let content
  if (isLoading) {
    content = <Text>Loading Resource Information...</Text>
  } else {
    content = (
      <Group>
        <Text>
          {data?.name_long} ({data?.capacity_power} MW)
        </Text>
        <Text>QSE - {data?.qse?.name_long}</Text>
        <Text>DME - {data?.dme?.name_long}</Text>
        <Text>Settlement Point - {data?.settlement_point?.name}</Text>
      </Group>
    )
  }

  return (
    <Stack h="100%" p="md">
      <Card withBorder>{content}</Card>
      <NetPowerPlot />
    </Stack>
  )
}

export default ResourcePage
