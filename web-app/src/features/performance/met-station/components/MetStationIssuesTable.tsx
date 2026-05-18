import { type ProjectIssue } from '@/api/v1/operational/project/issues'
import CustomCard from '@/components/CustomCard'
import { ScrollArea, Skeleton, Stack, Text } from '@mantine/core'
import dayjs from 'dayjs'

const formatStartedDate = (timeStart: string) =>
  `Started ${dayjs(timeStart).format('M/D/YY')}`

type MetStationIssuesTableProps = {
  title: string
  flex: number
  isLoading: boolean
  data: ProjectIssue[]
}

export function MetStationIssuesTable({
  title,
  flex,
  isLoading,
  data,
}: MetStationIssuesTableProps) {
  const issues = [...data].sort((left, right) => {
    return dayjs(right.time_start).valueOf() - dayjs(left.time_start).valueOf()
  })

  return (
    <CustomCard title={title} style={{ flex: flex }}>
      {isLoading ? (
        <Skeleton h="100%" />
      ) : (
        <ScrollArea h="100%">
          <Stack gap="xs">
            {issues.length === 0 ? (
              <Text c="dimmed" size="sm">
                No issues
              </Text>
            ) : (
              issues.map((issue) => (
                <Stack key={issue.issue_id} gap={0} style={{ minWidth: 0 }}>
                  <Text fw={500} size="sm" truncate>
                    {issue.tag_name_full ?? issue.device_name_full}
                  </Text>
                  <Text c="dimmed" size="xs" truncate>
                    {issue.issue_category}
                  </Text>
                  <Text c="dimmed" size="xs" truncate>
                    {formatStartedDate(issue.time_start)}
                  </Text>
                </Stack>
              ))
            )}
          </Stack>
        </ScrollArea>
      )}
    </CustomCard>
  )
}
