import { useGetERCOTPrices, useGetERCOTSettlementPoints } from '@/api/ercot'
import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { Button, Group, Select, Stack } from '@mantine/core'
import { DatePickerInput, DatesProvider } from '@mantine/dates'
import { useState } from 'react'

const Prices = () => {
  const [dateRange, setDateRange] = useState<[Date | null, Date | null]>([
    null,
    null,
  ])
  const [settlementPoint, setSettlementPoint] = useState<string | null>('')
  // const [includeASPrices, setIncludeASPrices] = useState(false);
  const [queryState, setQueryState] = useState({
    enabled: false,
    settlement_point_id: 0,
    start: '',
    end: '',
  })

  const { data: settlementPoints } = useGetERCOTSettlementPoints({})
  const { data: priceData, isLoading: priceDataIsLoading } = useGetERCOTPrices({
    queryParams: {
      ...queryState,
    },
    queryOptions: {
      enabled: queryState.enabled,
    },
  })

  // Sort settlement points by name
  if (settlementPoints) {
    settlementPoints.sort((a, b) => {
      return a.name.localeCompare(b.name)
    })
  }

  const settlementPointsSorted = settlementPoints?.map((item) => {
    return {
      value: String(item.settlement_point_id),
      label: item.name,
    }
  })

  return (
    <Stack h="100%" p="md">
      <Group w="100%">
        <DatesProvider settings={{ timezone: 'America/Chicago' }}>
          <DatePickerInput
            type="range"
            allowSingleDateInRange
            maxDate={new Date()}
            placeholder="Pick date"
            value={dateRange}
            onChange={setDateRange}
            flex={1}
          ></DatePickerInput>
        </DatesProvider>
        <Select
          placeholder="Pick settlement point"
          data={settlementPointsSorted}
          value={settlementPoint}
          onChange={setSettlementPoint}
          searchable
          flex={1}
        />
        {/* <Checkbox
          label="Include Ancillary Service Prices"
          checked={includeASPrices}
          onChange={(event) => setIncludeASPrices(event.currentTarget.checked)}
        /> */}
        <Button
          disabled={
            dateRange[0] === null || dateRange[1] === null || !settlementPoint
          }
          flex={1}
          onClick={() => {
            if (dateRange[0] && dateRange[1]) {
              // Check that both dates are not null
              const end = new Date(dateRange[1])
              end.setDate(end.getDate() + 1)

              setQueryState({
                enabled: true,
                settlement_point_id: Number(settlementPoint),
                start: dateRange[0].toISOString(),
                end: end.toISOString(),
              })
            }
          }}
        >
          Plot
        </Button>
      </Group>
      <CustomCard title="ERCOT Market Prices" style={{ flex: 1 }}>
        <PlotlyPlot
          data={priceData?.map((d) => ({
            x: d.x,
            y: d.y,
            name: d.name,
            hoverlabel: {
              namelength: -1,
            },
            line: {
              shape: 'hv',
            },
          }))}
          layout={{
            yaxis: {
              title: { text: 'Price ($/MWh)' },
            },
          }}
          isLoading={priceDataIsLoading}
        />
      </CustomCard>
    </Stack>
  )
}

export default Prices
