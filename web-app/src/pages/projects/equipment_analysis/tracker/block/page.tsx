import { useGetBlockDropdown } from '@/api/ui'
import { useGetProject } from '@/api/v1/operational/projects'
import { useGetEquipmentAnalysisTrackerBlock } from '@/api/v1/protected/web-application/projects/equipment-analysis/tracker_block'
import BlockDropdown from '@/components/BlockDropdown'
import CustomCard from '@/components/CustomCard'
import { PageLoader } from '@/components/Loading'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useProjectDropdownToggle } from '@/hooks/custom'
import { Button, Group, Stack, Title } from '@mantine/core'
import { IconArrowBackUp } from '@tabler/icons-react'
import { Link, useParams, useSearchParams } from 'react-router'

const MAX_DAYS = 7

const Page = () => {
  const { projectId } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()

  useProjectDropdownToggle()

  const deviceId = searchParams.get('deviceId')
  const startURI = searchParams.get('start')
  const endURI = searchParams.get('end')

  const project = useGetProject({
    pathParams: { projectId: projectId || '-1' },
  })

  const { start, end } = useValidateDateRange({
    maxDays: MAX_DAYS,
  })

  let startRequest, endRequest
  if (project.data) {
    startRequest = start && start.tz(project.data.time_zone, true).toISOString()
    endRequest = end && end.tz(project.data.time_zone, true).toISOString()
  }

  const handleBlockDropdownChange = (value: string | null) => {
    if (value) {
      setSearchParams({
        deviceId: value,
        start: startURI || '',
        end: endURI || '',
      })
    }
  }

  const blockDropdown = useGetBlockDropdown({
    pathParams: { projectId: projectId || '-1' },
  })

  const data = useGetEquipmentAnalysisTrackerBlock({
    pathParams: { projectId: projectId || '-1', deviceId: deviceId || '-1' },
    queryParams: {
      start: startRequest,
      end: endRequest,
    },
  })

  if (blockDropdown.isLoading) {
    return <PageLoader />
  }

  return (
    <Stack p="md" h="100%">
      <Title order={1}>Tracker Current Day</Title>
      <Group>
        <BlockDropdown
          data={blockDropdown.data}
          value={deviceId}
          onChange={handleBlockDropdownChange}
          buttonPx={2}
        />
        <AdvancedDatePicker
          includeClearButton={false}
          defaultRange="today"
          includeTodayInDateRange
          limits={{
            day: 7,
            week: 1,
            month: 0,
            quarter: 0,
            year: 0,
          }}
          disableQuickActions={true}
          maxDays={MAX_DAYS}
        />
        <Link
          to={`/projects/${projectId}/equipment-analysis?tab=tracker&start=${startURI}&end=${endURI}`}
        >
          <Button variant="light" rightSection={<IconArrowBackUp size={14} />}>
            Back to Project
          </Button>
        </Link>
      </Group>
      <CustomCard title="Tracker Position" style={{ height: '50vh' }}>
        <PlotlyPlot
          data={Object.entries(data.data?.positions || {}).map(
            ([key, value]) => ({
              x: data.data?.times,
              y: value,
              type: 'scatter',
              mode: 'lines',
              name: key,
            }),
          )}
          layout={{
            yaxis: {
              title: { text: 'Angle (degrees)' },
            },
          }}
          isLoading={data.isLoading}
        />
      </CustomCard>
      <CustomCard title="Tracker Setpoint" style={{ height: '50vh' }}>
        <PlotlyPlot
          data={Object.entries(data.data?.setpoints || {}).map(
            ([key, value]) => ({
              x: data.data?.times,
              y: value,
              type: 'scatter',
              mode: 'lines',
              name: key,
            }),
          )}
          layout={{
            yaxis: {
              title: { text: 'Angle (degrees)' },
            },
          }}
          isLoading={data.isLoading}
        />
      </CustomCard>
    </Stack>
  )
}

export default Page
