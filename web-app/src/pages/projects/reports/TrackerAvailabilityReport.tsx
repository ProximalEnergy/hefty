import {
  useGetBucketListdir,
  useGetPresignedUrl,
} from '@/api/v1/operational/aws'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetReportType } from '@/api/v1/operational/report_types'
import { PageLoader } from '@/components/Loading'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { getQueryParamDateRange } from '@/components/datepicker/utils'
import { useProjectFilter } from '@/hooks/custom'
import { Button, Group, List, Stack, Text, Title, Tooltip } from '@mantine/core'
import { IconDownload, IconExternalLink } from '@tabler/icons-react'
import { UseQueryResult } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { useState } from 'react'
import { useParams, useSearchParams } from 'react-router'

const ICON_SIZE = 14

const handleTrackerAvailabilityDownload = async (
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
  const [searchParams] = useSearchParams()
  const reportTypeId = searchParams.get('report_type_id')

  useProjectFilter({
    reportTypeId: Number(reportTypeId) || 0,
  })

  const { projectId } = useParams<{ projectId: string }>()
  const reportDocUrl = 'kpi/trackers.html'

  const { startQuery, endQuery } = getQueryParamDateRange({
    searchParams,
  })
  const [isFetching, setIsFetching] = useState(false)

  const project = useSelectProject(projectId!)

  const reportType = useGetReportType({
    pathParams: {
      report_type_id: Number(reportTypeId) || 0,
    },
    queryOptions: { enabled: !!projectId && !!Number(reportTypeId) },
  })

  const fileName = `reports/persistent/${reportType?.data?.name_short}/${
    project.data?.name_short
  }_${startQuery}.xlsx`
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
      <DescriptionTextTrackerAvailabilityReport
        reportTypeId={reportTypeId || ''}
      />
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
              handleTrackerAvailabilityDownload(
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

const DescriptionTextTrackerAvailabilityReport = ({
  reportTypeId,
}: {
  reportTypeId: string
}) => {
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
