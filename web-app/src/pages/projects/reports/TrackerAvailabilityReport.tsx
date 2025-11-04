import {
  useGetBucketListdir,
  useGetPresignedUrl,
} from '@/api/v1/operational/aws'
import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetReportType } from '@/api/v1/operational/report_types'
import { PageLoader } from '@/components/Loading'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import { useProjectFilter } from '@/hooks/custom'
import { Button, Group, List, Text, Title, Tooltip } from '@mantine/core'
import { Stack } from '@mantine/core'
import { IconDownload } from '@tabler/icons-react'
import { IconExternalLink } from '@tabler/icons-react'
import { UseQueryResult } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { useState } from 'react'
import { useParams, useSearchParams } from 'react-router'

const ICON_SIZE = 14

const handleDownload = async (
  presignedUrl: UseQueryResult<string, AxiosError>,
  startQuery: string | undefined,
  validDates: string[] | undefined,
  setIsFetching: (isFetching: boolean) => void,
) => {
  if (!startQuery || !validDates?.includes(startQuery)) {
    throw new Error('Selected date is not available for download.')
  }
  setIsFetching(true)

  // refetch() resolves to the latest query result
  const { data } = await presignedUrl.refetch()

  if (data) {
    window.open(data, '_blank')
  }
  setIsFetching(false)
}

const Page: React.FC = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeId.PV, ProjectTypeId.PV_BESS],
  })

  const { projectId } = useParams<{ projectId: string }>()
  const [searchParams] = useSearchParams()
  const reportTypeId = searchParams.get('report_type_id')
  const reportDocUrl = 'kpi/trackers.html'

  const { start, end } = useValidateDateRange()
  const startQuery = start?.format('YYYY-MM-DD')
  const endQuery = end?.add(1, 'day').format('YYYY-MM-DD')
  const [isFetching, setIsFetching] = useState(false)

  const project = useSelectProject(projectId!)

  const reportType = useGetReportType({
    pathParams: {
      projectId: projectId || '',
      reportTypeId: reportTypeId || '',
    },
    queryOptions: { enabled: !!projectId },
  })

  const fileName = `reports/persistent/${reportType?.data?.name_short}/${
    project.data?.name_short
  }_${start?.format('YYYY-MM-DD')}.xlsx`
  const presignedUrl = useGetPresignedUrl({
    queryParams: {
      bucket_name: 'proximal-am-documents',
      file_path: fileName,
    },
    queryOptions: { enabled: false },
  })

  const bucketList = useGetBucketListdir({
    queryParams: {
      bucket_name: 'proximal-am-documents',
      path: `reports/persistent/${reportType?.data?.name_short}`,
    },
    queryOptions: { enabled: !!reportType?.data?.name_short },
  })

  const isLoading =
    project.isLoading || reportType.isLoading || bucketList.isLoading

  const projectBucketList = bucketList.data?.filter((item) => {
    return item.Key.includes(`${project.data?.name_short}_`)
  })
  const validDates = projectBucketList?.map((item) => {
    return item.Key.split(`${project.data?.name_short}_`)[1].split('.')[0]
  })

  const invalidDateWarning = !validDates?.includes(startQuery || '')

  if (isLoading) return <PageLoader />

  return (
    <Stack p="md" h="100%">
      <Title>{reportType.data?.name_long}</Title>
      <DescriptionText reportTypeId={reportTypeId || ''} />
      <Stack align="center">
        <AdvancedDatePicker
          includeClearButton={false}
          defaultRange="today"
          maxDays={1}
          includeTodayInDateRange={false}
        />
        {invalidDateWarning && (
          <Stack align="center">
            <Text color="red">
              Selected date is unavailable. Please reach out to the Proximal
              team for backfill support.
            </Text>
          </Stack>
        )}
        <Group>
          <Tooltip
            label="Documentation for this report coming soon!"
            disabled={!!reportDocUrl}
          >
            <Button
              variant="default"
              rightSection={<IconExternalLink size={ICON_SIZE} />}
              onClick={() =>
                window.open(
                  `https://docs.proximal.energy/${reportDocUrl}`,
                  '_blank',
                )
              }
              disabled={!reportDocUrl}
            >
              Documentation
            </Button>
          </Tooltip>

          <Button
            rightSection={<IconDownload size={ICON_SIZE} />}
            disabled={
              !reportTypeId ||
              !startQuery ||
              !endQuery ||
              !projectId ||
              invalidDateWarning
            }
            onClick={() =>
              handleDownload(
                presignedUrl,
                startQuery,
                validDates,
                setIsFetching,
              )
            }
            loading={isFetching}
          >
            Download
          </Button>
        </Group>
      </Stack>
    </Stack>
  )
}

export default Page

const DescriptionText = ({ reportTypeId }: { reportTypeId: string }) => {
  return (
    <Stack>
      <Text>
        This downloadable report is a tunable analysis of tracker availability.
        Select a time range to download a .zip file containing an Excel file
        with the following:
      </Text>
      <List withPadding>
        <List.Item>
          Tunable parameters including minimum irradiance, maximum deviation,
          and more
        </List.Item>
        <List.Item>
          Daily calculated availability, responsive to user-defined parameters
        </List.Item>
        <List.Item>
          Raw 5-minute data for each tracker&apos;s position
          {reportTypeId === '4'
            ? ', setpoint, and stow command'
            : ' and stow command'}
        </List.Item>
        {reportTypeId === '5' && (
          <List.Item>
            Calculated 5-minute data for the median setpoint of each tracker
            zone
          </List.Item>
        )}
        <List.Item>
          Raw 5-minute data for each met station&apos;s POA sensor and
          calculated mean irradiance across all sensors
        </List.Item>
      </List>
    </Stack>
  )
}
