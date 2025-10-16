import { useGetPCSApparentVsVoltage } from '@/api/v1/operational/project/project_reports'
import { useGetProject } from '@/api/v1/operational/projects'
import CustomCard from '@/components/CustomCard'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { Group, NumberInput, Stack, Title } from '@mantine/core'
import { useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'

const MAX_DAYS = 3

const Page: React.FC = () => {
  const { projectId } = useParams()
  const { start, end } = useValidateDateRange({
    maxDays: MAX_DAYS,
  })

  const [V_nom, setVNom] = useState(630) // volts
  const [S_rated, setSRated] = useState(3600) // kVA
  const [V_min_pu, setVMinPU] = useState(0.9)
  const [V_max_pu, setVMaxPU] = useState(1.1)

  let startQuery: string | undefined = undefined
  let endQuery: string | undefined = undefined

  const project = useGetProject({
    pathParams: { projectId: projectId || '' },
    queryOptions: { enabled: !!projectId },
  })

  if (project.data) {
    if (start) {
      startQuery = start.tz(project.data.time_zone, true).toISOString()
    }
    if (end) {
      endQuery = end.tz(project.data.time_zone, true).toISOString()
    }
  }

  const data = useGetPCSApparentVsVoltage({
    pathParams: { projectId: projectId! },
    queryParams: {
      start: startQuery || '',
      end: endQuery || '',
    },
    queryOptions: { enabled: !!project.data && !!startQuery && !!endQuery },
  })

  const idealCurve = useMemo(() => {
    const V_min = V_nom * V_min_pu
    const V_max = V_nom * V_max_pu
    const S_mva = S_rated / 1000

    return {
      x: [0, V_min_pu * S_mva, S_mva, S_mva, 0],
      y: [V_min, V_min, V_nom, V_max, V_max],
    }
  }, [V_nom, S_rated, V_min_pu, V_max_pu])

  return (
    <Stack p="md" h="100%">
      <Title>PCS Apparent Power vs. Voltage</Title>
      <Group w="100%" gap="md" align="flex-end">
        <AdvancedDatePicker
          includeClearButton={false}
          defaultRange="today"
          includeTodayInDateRange
          maxDays={MAX_DAYS}
          disableQuickActions
        />
        <NumberInput
          label="Nominal Voltage (V)"
          value={V_nom}
          onChange={(val) => setVNom(Number(val) || 0)}
          step={10}
          min={0}
        />
        <NumberInput
          label="Rated Apparent Power (kVA)"
          value={S_rated}
          onChange={(val) => setSRated(Number(val) || 0)}
          step={100}
          min={0}
        />
        <NumberInput
          label="Min Voltage (p.u.)"
          value={V_min_pu}
          onChange={(val) => setVMinPU(Number(val) || 0)}
          step={0.01}
          min={0.5}
          max={1}
        />
        <NumberInput
          label="Max Voltage (p.u.)"
          value={V_max_pu}
          onChange={(val) => setVMaxPU(Number(val) || 0)}
          step={0.01}
          min={1}
          max={1.5}
        />
      </Group>
      <CustomCard header={false} style={{ height: '100%' }}>
        <PlotlyPlot
          data={[
            ...(data.data ?? []).map(
              (item) =>
                ({
                  x: item.x,
                  y: item.y,
                  type: 'scatter' as const,
                  name: item.device_name,
                  mode: 'markers' as const,
                }) as Partial<Plotly.Data>,
            ),
            {
              x: idealCurve.x,
              y: idealCurve.y,
              type: 'scatter' as const,
              mode: 'lines' as const,
              line: {
                color: 'red',
                dash: 'dash',
              },
              name: 'Ideal',
              showlegend: false,
              hoverinfo: 'none',
            } as Partial<Plotly.Data>,
          ]}
          isLoading={data.isPending}
          layout={{
            xaxis: {
              title: { text: 'Apparent Power (MVA)' },
            },
            yaxis: {
              title: { text: 'Voltage (V)' },
            },
            hovermode: 'closest',
          }}
        />
      </CustomCard>
    </Stack>
  )
}

export default Page
