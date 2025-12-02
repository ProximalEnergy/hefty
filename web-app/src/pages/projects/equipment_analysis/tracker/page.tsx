import { useGetBlockDropdown } from '@/api/ui'
import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useGetTrackerEquipmentAnalysis } from '@/api/v1/protected/web-application/projects/equipment-analysis/tracker'
import BlockDropdown from '@/components/BlockDropdown'
import CustomCard from '@/components/CustomCard'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useProjectFilter } from '@/hooks/custom'
import {
  Alert,
  Group,
  List,
  SegmentedControl,
  Stack,
  Text,
} from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'
import { Data } from 'plotly.js'
import { useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router'

const MAX_DAYS = 7

const ProjectEquipmentAnalysisTracker = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeId.PV, ProjectTypeId.PV_BESS],
  })

  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [view, setView] = useState<'block' | 'row'>('block')

  const [searchParams] = useSearchParams()
  const selectedBlockId = searchParams.get('deviceId')
  // const startURI = searchParams.get("start");
  // const endURI = searchParams.get("end");

  // const devices = useGetDevices({
  //   pathParams: { projectId: projectId || "-1" },
  //   queryParams: { device_type_ids: [6, 10, 2] },
  // });

  const blockDropdown = useGetBlockDropdown({
    pathParams: { projectId: projectId || '-1' },
  })

  const handleBlockDropdownChange = (value: string | null) => {
    if (value) {
      const newSearchParams = new URLSearchParams(searchParams)
      newSearchParams.set('deviceId', value)
      newSearchParams.set('tab', 'tracker')
      navigate(
        `/projects/${projectId}/equipment-analysis/tracker/block?${newSearchParams.toString()}`,
      )
    }
  }

  const { start, end } = useValidateDateRange({
    maxDays: MAX_DAYS,
  })

  const data = useGetTrackerEquipmentAnalysis({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: start?.format('YYYY-MM-DD'),
      end: end?.format('YYYY-MM-DD'),
    },
    queryOptions: {
      enabled: !!start && !!end,
    },
  })

  const positionData = data.data?.position_from_setpoint
  const setpointData = data.data?.setpoint_from_median

  const PositionData = () => {
    return view === 'block'
      ? [
          {
            x: Object.keys(positionData?.by_block || {})
              .sort()
              .map((key) => key), // Extract block identifiers as strings
            y: Object.values(positionData?.by_block || {}), // Extract corresponding values
            type: 'bar',
          },
        ]
      : Object.entries(positionData?.by_row || {})
          .sort((a, b) => a[0].localeCompare(b[0]))
          .map(([blockId, values]) => ({
            x: Object.keys(values).sort(), // Extract row keys as strings
            y: Object.values(values), // Extract corresponding values
            type: 'bar', // Specify the type as bar
            name: `${blockId}`, // Optional: Name for the legend
          }))
  }

  const SetpointData = () => {
    return view === 'block'
      ? [
          {
            x: Object.keys(setpointData?.by_block || {})
              .sort()
              .map((key) => key), // Extract block identifiers as strings
            y: Object.values(setpointData?.by_block || {}), // Extract corresponding values
            type: 'bar',
          },
        ]
      : Object.entries(setpointData?.by_row || {})
          .sort((a, b) => a[0].localeCompare(b[0]))
          .map(([blockId, values]) => ({
            x: Object.keys(values).sort(), // Extract row keys as strings
            y: Object.values(values), // Extract corresponding values
            type: 'bar', // Specify the type as bar
            name: `${blockId}`, // Optional: Name for the legend
          }))
  }

  return (
    <Stack p="md" h="100%">
      <Group>
        <BlockDropdown
          data={blockDropdown.data}
          value={selectedBlockId}
          onChange={handleBlockDropdownChange}
          includeNextPrevious={false}
          includeFirstLast={false}
        />
        <AdvancedDatePicker
          includeClearButton={false}
          defaultRange="today"
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
        <SegmentedControl
          value={view}
          onChange={(value) => setView(value as 'block' | 'row')}
          data={[
            { label: 'PV Block', value: 'block' },
            { label: 'Tracker Row', value: 'row' },
          ]}
        />
      </Group>
      <Alert
        icon={<IconInfoCircle size={16} />}
        title="Information"
        color="blue"
      >
        Select a block above to view detailed tracker analysis for that specific
        block.
      </Alert>
      <CustomCard
        title="Position Deviating From Setpoint"
        info={
          <Stack gap="xs">
            <Text fw={600}>Understanding Position Deviation</Text>
            <Text size="sm">
              This chart shows how much each tracker&apos;s actual position
              deviates from its setpoint.
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Lower values:
              </Text>{' '}
              Trackers are closely following their setpoints (good performance)
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Higher values:
              </Text>{' '}
              Trackers are significantly off from their setpoints (potential
              issues)
            </Text>
            <List size="sm" spacing="xs">
              <List.Item>
                <Text component="span" fw={500}>
                  0-1°:
                </Text>{' '}
                Excellent tracking performance
              </List.Item>
              <List.Item>
                <Text component="span" fw={500}>
                  1-3°:
                </Text>{' '}
                Acceptable performance, monitor for trends
              </List.Item>
              <List.Item>
                <Text component="span" fw={500}>
                  3°+:
                </Text>{' '}
                Investigate tracker or controller issues
              </List.Item>
            </List>
            <Text size="sm">
              <Text component="span" fw={500}>
                Note:
              </Text>{' '}
              Values are averaged over the selected time period.
            </Text>
          </Stack>
        }
        style={{ height: '50vh' }}
      >
        <PlotlyPlot
          isLoading={data.isLoading || data.isPending}
          error={data.error}
          data={PositionData() as Data[]}
          layout={{
            xaxis: {
              title: { text: view === 'block' ? 'PV Block' : 'Tracker Row' },
            },
            yaxis: {
              title: { text: 'Degrees' },
              range: view === 'row' ? [0, 5] : undefined,
            },
            showlegend: false,
          }}
          // onClick={(event) => {
          //   const xValue = event.points[0]?.x;
          //   if (xValue) {
          //     const deviceId =
          //       view === "row"
          //         ? tagMap[xValue as string] // Use tagMap if positionView is "row"
          //         : deviceMap[xValue as string]; // Use deviceMap otherwise
          //     navigate(
          //       `/projects/${projectId}/equipment-analysis/tracker/block?deviceId=${deviceId}&start=${startURI}&end=${endURI}`
          //     );
          //   }
          // }}
        />
      </CustomCard>
      <CustomCard
        title="Setpoint Deviating From Median"
        info={
          <Stack gap="xs">
            <Text fw={600}>Understanding Setpoint Deviation from Median</Text>
            <Text size="sm">
              This chart shows how much each tracker&apos;s setpoint deviates
              from the median setpoint of all trackers in the same group.
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                What is the median?
              </Text>{' '}
              The median is the middle value when all tracker setpoints are
              sorted from lowest to highest. It represents the
              &quot;typical&quot; setpoint that most trackers should be
              following.
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Lower values:
              </Text>{' '}
              This tracker&apos;s setpoint is close to the typical setpoint
              (good alignment)
            </Text>
            <Text size="sm">
              <Text component="span" fw={500}>
                Higher values:
              </Text>{' '}
              This tracker&apos;s setpoint is significantly different from the
              typical setpoint (potential controller issue)
            </Text>
            <List size="sm" spacing="xs">
              <List.Item>
                <Text component="span" fw={500}>
                  0-1°:
                </Text>{' '}
                Excellent setpoint alignment
              </List.Item>
              <List.Item>
                <Text component="span" fw={500}>
                  1-3°:
                </Text>{' '}
                Acceptable alignment, monitor for trends
              </List.Item>
              <List.Item>
                <Text component="span" fw={500}>
                  3°+:
                </Text>{' '}
                Investigate tracker controller or network issues
              </List.Item>
            </List>
            <Text size="sm">
              <Text component="span" fw={500}>
                Note:
              </Text>{' '}
              Values are averaged over the selected time period. The median is
              calculated daily across all trackers in the same group (block or
              row view).
            </Text>
          </Stack>
        }
        style={{ height: '50vh' }}
      >
        <PlotlyPlot
          isLoading={data.isLoading || data.isPending}
          error={data.error}
          data={SetpointData() as Data[]}
          layout={{
            xaxis: {
              title: { text: view === 'block' ? 'PV Block' : 'Tracker Row' }, // Change label based on view
            },
            yaxis: {
              title: { text: 'Degrees' },
              range: view === 'row' ? [0, 5] : undefined,
            },
            showlegend: false,
          }}
          // onClick={(event) => {
          //   const xValue = event.points[0]?.x;
          //   if (xValue) {
          //     const deviceId =
          //       view === "row"
          //         ? tagMap[xValue as string] // Use tagMap if positionView is "row"
          //         : deviceMap[xValue as string]; // Use deviceMap otherwise
          //     navigate(
          //       `/projects/${projectId}/equipment-analysis/tracker/block?deviceId=${deviceId}&start=${startURI}&end=${endURI}`
          //     );
          //   }
          // }}
        />
      </CustomCard>
    </Stack>
  )
}

export default ProjectEquipmentAnalysisTracker
