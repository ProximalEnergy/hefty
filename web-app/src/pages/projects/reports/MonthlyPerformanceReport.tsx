import { ReportTypeEnum } from '@/api/enumerations'
import { PageTitle } from '@/components/PageTitle'
import { useProjectFilter } from '@/hooks/custom'
import { Button, Card, Stack, Text } from '@mantine/core'
import { MonthPickerInput } from '@mantine/dates'
import { IconDownload } from '@tabler/icons-react'
import dayjs from 'dayjs'
import { useState } from 'react'

const ICON_SIZE = 14

const MonthlyPerformanceReport = () => {
  useProjectFilter({
    reportTypeId: ReportTypeEnum.MONTHLY_PERFORMANCE,
  })

  const previousMonth = dayjs().subtract(1, 'month').startOf('month').toDate()
  const [selectedMonth, setSelectedMonth] = useState<Date>(previousMonth)

  return (
    <Stack p="md" h="100%">
      <PageTitle>Monthly Performance Report</PageTitle>

      <Card withBorder p="md" radius="md">
        <Stack>
          <Text c="dimmed">
            Summarizes monthly project performance, highlighting key production,
            availability, and operational trends for the selected month.
          </Text>

          <MonthPickerInput
            label="Select Month"
            placeholder="Pick a month"
            value={selectedMonth}
            onChange={(value) => setSelectedMonth(value || previousMonth)}
            clearable={false}
          />

          <Button rightSection={<IconDownload size={ICON_SIZE} />}>
            Download
          </Button>
        </Stack>
      </Card>
    </Stack>
  )
}

export default MonthlyPerformanceReport
