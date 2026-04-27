import { ReportTypeEnum } from '@/api/enumerations'
import { useGetSCADATelemetryLastReported } from '@/api/v1/protected/web-application/projects/reports/scada-telemetry-last-reported'
import { PageTitle } from '@/components/PageTitle'
import { useProjectFilter } from '@/hooks/custom'
import { Button, List, Stack, Text } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconDownload } from '@tabler/icons-react'
import { useParams } from 'react-router'

const SCADATelemetryLastReportedPage = () => {
  useProjectFilter({
    reportTypeId: ReportTypeEnum.SCADA_TELEMETRY_LAST_REPORTED,
  })

  const { projectId } = useParams<{ projectId: string }>()

  const report = useGetSCADATelemetryLastReported({
    pathParams: { project_id: projectId ?? '' },
  })

  const handleDownload = async () => {
    const result = await report.refetch()
    if (result.isError) {
      notifications.show({
        color: 'red',
        title: 'Download failed',
        message: 'Unable to generate report. Please try again.',
      })
      return
    }
    if (!result.data) return
    const filename =
      result.data.filename ?? 'scada_telemetry_last_reported.xlsx'
    const url = window.URL.createObjectURL(result.data.blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  }

  return (
    <Stack p="md">
      <PageTitle>SCADA Telemetry Last Reported</PageTitle>
      <Text>
        This report shows when each SCADA tag in the project last reported data
        and classifies it as Fresh, Stale (more than one hour old), or Never
        Reported. It also flags &quot;Ghost&quot; tags that do not represent
        physical sensors, which can explain why a tag has never reported.
      </Text>
      <Text>The Excel file contains two sheets:</Text>
      <List>
        <List.Item>
          <Text span fw={600}>
            Summary:
          </Text>{' '}
          Report timestamp, project name, then counts for non-ghost tags (total,
          Fresh, Stale, Never) and ghost tags (total, Fresh, Stale, Never).
        </List.Item>
        <List.Item>
          <Text span fw={600}>
            Data:
          </Text>{' '}
          All tags with their last reported time, ghost flag, and status (Fresh,
          Stale &gt; 1 hour, or Never Reported)
        </List.Item>
      </List>
      <Button
        leftSection={<IconDownload size={16} />}
        onClick={handleDownload}
        loading={report.isFetching}
        w="fit-content"
      >
        Download
      </Button>
    </Stack>
  )
}

export default SCADATelemetryLastReportedPage
