import { ProjectTypeEnum, ReportTypeEnum } from '@/api/enumerations'
import {
  useGetBucketListdir,
  useGetPresignedUrl,
} from '@/api/v1/operational/aws'
import {
  type GenerateBESSMonthlyReportPayload,
  type SmartBidderMetricPayload,
  useGenerateEECBESSMonthlyReport,
} from '@/api/v1/operational/project/project_reports'
import { useGetProjects, useSelectProject } from '@/api/v1/operational/projects'
import { useGetUserProjectLabels } from '@/api/v1/operational/user_project_labels'
import { PageTitle } from '@/components/PageTitle'
import { useProjectFilter } from '@/hooks/custom'
import {
  ActionIcon,
  Button,
  Checkbox,
  Group,
  NumberInput,
  Paper,
  ScrollArea,
  Select,
  Skeleton,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Tooltip,
} from '@mantine/core'
import { MonthPickerInput } from '@mantine/dates'
import { useLocalStorage } from '@mantine/hooks'
import { notifications } from '@mantine/notifications'
import { IconDownload, IconMinus, IconPlus } from '@tabler/icons-react'
import { UseQueryResult } from '@tanstack/react-query'
import { AxiosError, isAxiosError } from 'axios'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useParams } from 'react-router'

const ICON_SIZE = 14

type SmartBidderRowValues = { actual: number | ''; expected: number | '' }

const getGenerateReportErrorMessage = (error: unknown): string => {
  const fallback =
    'Failed to generate the BESS monthly report. Please try again.'
  if (!isAxiosError(error)) {
    return fallback
  }

  const responseData = error.response?.data
  if (typeof responseData === 'string' && responseData.trim().length > 0) {
    return responseData
  }

  if (responseData && typeof responseData === 'object') {
    const maybeDetail = (responseData as { detail?: unknown }).detail
    if (typeof maybeDetail === 'string' && maybeDetail.trim().length > 0) {
      return maybeDetail
    }
  }

  if (error.message.trim().length > 0) {
    return error.message
  }
  return fallback
}

const SMART_BIDDER_ROWS = [
  'Energy Capacity (MWh)',
  'RT Energy VOM ($/MWh)',
  'RT AS VOM ($/MWh)',
  'DA VOM - Energy & AS ($/MWh)',
  'Max Charge Power (MW)',
  'Max Discharge Power (MW)',
] as const

const createSmartBidderDefaults = (
  rows: string[],
): Record<string, SmartBidderRowValues> =>
  Object.fromEntries(
    rows.map((label) => [label, { actual: '', expected: '' }]),
  ) as Record<string, SmartBidderRowValues>

const handleDownload = async (
  presignedUrl: UseQueryResult<string, AxiosError>,
  selectedReport: string | null,
  reportKeys: string[] | undefined,
  setIsFetching: (isFetching: boolean) => void,
) => {
  if (!selectedReport || !reportKeys?.includes(selectedReport)) {
    throw new Error('Selected report is not available for download.')
  }
  setIsFetching(true)

  // refetch() resolves to the latest query result
  const { data } = await presignedUrl.refetch()

  if (data) {
    window.open(data, '_blank')
  }
  setIsFetching(false)
}

const BESSMonthlyReport = () => {
  useProjectFilter({
    reportTypeId: ReportTypeEnum.EEC_BESS_MONTHLY_REPORT,
  })

  const { projectId } = useParams()
  const generateReport = useGenerateEECBESSMonthlyReport()

  // Default to the previous full month (the month that just completed)
  const previousMonth = dayjs().subtract(1, 'month').startOf('month').toDate()
  const [selectedMonth, setSelectedMonth] = useState<Date>(previousMonth)
  const [operationalCommentary, setOperationalCommentary] = useState<string>('')
  const [selectedReport, setSelectedReport] = useState<string | null>(null)
  const [isFetching, setIsFetching] = useState(false)
  const [includedProjects, setIncludedProjects] = useState<string[]>([])
  const [quickSelectLabelName, setQuickSelectLabelName] = useState<
    string | null
  >(null)

  const project = useSelectProject(projectId!)
  const projects = useGetProjects({
    queryParams: { deep: false },
    personalPortfolio: true,
  })
  const batteryProjects = projects.data?.filter(
    (p) =>
      p.project_type_id === ProjectTypeEnum.BESS ||
      p.project_type_id === ProjectTypeEnum.PVS,
  )
  const userProjectLabels = useGetUserProjectLabels()

  const handleQuickSelectChange = (value: string | null) => {
    setQuickSelectLabelName(value)

    if (!value) {
      setIncludedProjects([])
      return
    }

    const label = userProjectLabels.data?.find((l) => l.name === value)
    const labelProjectIds = label?.project_ids?.map((id) => String(id)) ?? []

    // Selecting a label clears any prior manual selections.
    setIncludedProjects(labelProjectIds)
  }

  const bucketList = useGetBucketListdir({
    queryParams: {
      bucket_name: 'proximal-am-documents',
      path: `reports/persistent/bess_monthly_reports`,
      project_prefix: project.data?.name_short,
    },
    queryOptions: { enabled: !!project.data },
  })

  const reportKeys = bucketList.data
    ?.map((item) => item.Key.split('/').pop())
    .filter((key): key is string => key !== undefined)

  const filePath = selectedReport
    ? `reports/persistent/bess_monthly_reports/${selectedReport}`
    : ''

  const presignedUrl = useGetPresignedUrl({
    queryParams: {
      bucket_name: 'proximal-am-documents',
      file_path: filePath,
    },
    queryOptions: { enabled: false },
  })

  const initialRows = [
    'Active Strategy',
    'Perfect Foresight',
    'Selected Strategy',
    'Alternate Strategy',
    'Alternate Strategy II',
    'DA-RT Only Strategy',
    'Revenue Floor Strategy',
    'Real Time Energy Only',
    'South Hub',
  ]
  // State to store row names
  const [rowNames, setRowNames] = useState<string[]>(initialRows)

  // State to store input values: [rowIndex][columnIndex] = value
  const [tableData, setTableData] = useState<
    Record<string, Record<string, number | ''>>
  >(() => {
    const initial: Record<string, Record<string, number | ''>> = {}
    initialRows.forEach((_, rowIndex) => {
      initial[rowIndex] = {
        month: '',
        ytd: '',
      }
    })
    return initial
  })

  const smartBidderStorageKey = projectId
    ? `bess-smartbidder-${projectId}`
    : 'bess-smartbidder-default'
  const [smartBidderData, setSmartBidderData] = useLocalStorage<
    Record<string, SmartBidderRowValues>
  >({
    key: smartBidderStorageKey,
    defaultValue: createSmartBidderDefaults([...SMART_BIDDER_ROWS]),
  })

  useEffect(() => {
    setSmartBidderData((prev) => {
      const defaults = createSmartBidderDefaults([...SMART_BIDDER_ROWS])
      let changed = false
      const merged: Record<string, SmartBidderRowValues> = { ...prev }
      Object.entries(defaults).forEach(([label, defaultsVal]) => {
        if (!merged[label]) {
          merged[label] = defaultsVal
          changed = true
        }
      })
      return changed ? merged : prev
    })
  }, [setSmartBidderData])

  const handleInputChange = (
    rowIndex: number,
    columnKey: string,
    value: number | '',
  ) => {
    setTableData((prev) => ({
      ...prev,
      [rowIndex]: {
        ...prev[rowIndex],
        [columnKey]: value,
      },
    }))
  }

  const handleRowNameChange = (rowIndex: number, value: string) => {
    setRowNames((prev) => {
      const updated = [...prev]
      updated[rowIndex] = value
      return updated
    })
  }

  const handleSmartBidderChange = (
    label: string,
    key: 'actual' | 'expected',
    value: number | '',
  ) => {
    setSmartBidderData((prev) => ({
      ...prev,
      [label]: {
        ...(prev[label] ?? { actual: '', expected: '' }),
        [key]: value,
      },
    }))
  }

  const handleAddRow = () => {
    const newIndex = rowNames.length
    setRowNames((prev) => [...prev, 'New Strategy'])
    setTableData((prev) => ({
      ...prev,
      [newIndex]: {
        month: '',
        ytd: '',
      },
    }))
  }

  const handleRemoveRow = (rowIndex: number) => {
    setRowNames((prev) => prev.filter((_, index) => index !== rowIndex))
    setTableData((prev) => {
      const updated: Record<string, Record<string, number | ''>> = {}
      // Reindex all rows, skipping the removed one
      let newIndex = 0
      Object.keys(prev)
        .map(Number)
        .sort((a, b) => a - b)
        .forEach((oldIndex) => {
          if (oldIndex !== rowIndex) {
            updated[newIndex] = prev[oldIndex]
            newIndex++
          }
        })
      return updated
    })
  }

  const handleGenerateReport = async () => {
    if (!projectId) return

    // Format the strategies data
    const strategies = rowNames.map((name, index) => ({
      name,
      month_value:
        typeof tableData[index]?.month === 'number'
          ? tableData[index].month
          : null,
      ytd_value:
        typeof tableData[index]?.ytd === 'number' ? tableData[index].ytd : null,
    }))

    const smartBidderMetrics: Record<string, SmartBidderMetricPayload> =
      Object.fromEntries(
        [...SMART_BIDDER_ROWS].map((label) => {
          const metric = smartBidderData[label] ?? {
            actual: '',
            expected: '',
          }
          return [
            label,
            {
              actual: typeof metric.actual === 'number' ? metric.actual : null,
              expected:
                typeof metric.expected === 'number' ? metric.expected : null,
            },
          ]
        }),
      ) as Record<string, SmartBidderMetricPayload>

    // Format the month as YYYY-MM-DD (first day of the month)
    const monthDate = dayjs(selectedMonth).startOf('month').format('YYYY-MM-DD')

    const payload: GenerateBESSMonthlyReportPayload = {
      month: monthDate,
      strategies,
      operational_commentary:
        operationalCommentary.trim().length > 0
          ? operationalCommentary.trim()
          : null,
      smart_bidder_metrics: smartBidderMetrics,
      included_projects: includedProjects,
    }

    try {
      await generateReport.mutateAsync({
        projectId,
        data: payload,
      })

      await bucketList.refetch()

      notifications.show({
        title: 'Report ready',
        message: 'The BESS monthly report generated successfully.',
        color: 'teal',
        autoClose: false,
      })
    } catch (error) {
      notifications.show({
        title: 'Report generation failed',
        message: getGenerateReportErrorMessage(error),
        color: 'red',
        autoClose: false,
      })
    }
  }

  const trimmedRowNames = rowNames.map((name) => name.trim())
  const disableReasons: string[] = []

  if (!projectId) {
    disableReasons.push('Select a project to continue.')
  }

  if (!trimmedRowNames.some((name) => name === 'Perfect Foresight')) {
    disableReasons.push('Add the "Perfect Foresight" strategy row.')
  }

  if (trimmedRowNames.some((name) => name.length === 0)) {
    disableReasons.push('Fill every strategy name.')
  }

  const hasBlankSmartBidderMetric = SMART_BIDDER_ROWS.some((label) => {
    const metric = smartBidderData[label]
    const actual = metric?.actual ?? ''
    const expected = metric?.expected ?? ''
    return actual === '' || expected === ''
  })

  if (hasBlankSmartBidderMetric) {
    disableReasons.push('Fill every SmartBidder metric.')
  }

  const isGenerateDisabled = disableReasons.length > 0
  const disabledTooltip = disableReasons.join(' • ')

  return (
    <Stack p="md" h="100%">
      <Group>
        <PageTitle>BESS Monthly Report</PageTitle>
      </Group>
      <Group align="flex-end">
        <MonthPickerInput
          label="Select Month"
          placeholder="Pick a month"
          value={selectedMonth}
          onChange={(value) => setSelectedMonth(value || previousMonth)}
          clearable={false}
          flex={1}
        />
        {bucketList.isPending || bucketList.isRefetching ? (
          <Stack flex={1} gap={0}>
            <Text size="sm" fw={500}>
              Select Report
            </Text>
            <Skeleton height={37} />
          </Stack>
        ) : (
          <Select
            label="Select Report"
            placeholder="Select report"
            data={reportKeys}
            value={selectedReport}
            onChange={setSelectedReport}
            flex={1}
          />
        )}
        <Button
          rightSection={<IconDownload size={ICON_SIZE} />}
          disabled={!selectedReport || !reportKeys?.includes(selectedReport)}
          onClick={() =>
            handleDownload(
              presignedUrl,
              selectedReport,
              reportKeys,
              setIsFetching,
            )
          }
          loading={isFetching}
          style={{ marginTop: 'auto' }}
        >
          Download
        </Button>
      </Group>

      <Group align="stretch" flex={1} mih={0}>
        <ScrollArea flex={2} mih={0}>
          <Table withTableBorder withColumnBorders>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>
                  <Group w="100%" justify="space-between">
                    <Text size="sm" fw={1000}>
                      Strategy Performance Comparison
                    </Text>
                    <Tooltip label="Add row" withArrow>
                      <ActionIcon
                        size="xs"
                        variant="subtle"
                        color="gray"
                        onClick={handleAddRow}
                      >
                        <IconPlus />
                      </ActionIcon>
                    </Tooltip>
                  </Group>
                </Table.Th>
                <Table.Th>{dayjs(selectedMonth).format('MMM-YY')}</Table.Th>
                <Table.Th>Year-to-Date</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {rowNames.map((rowLabel, rowIndex) => (
                <Table.Tr key={rowIndex}>
                  <Table.Td>
                    <Group justify="space-between" gap="xs">
                      <TextInput
                        value={rowLabel}
                        onChange={(e) =>
                          handleRowNameChange(rowIndex, e.currentTarget.value)
                        }
                        placeholder="Enter strategy name"
                        size="xs"
                        flex={1}
                      />
                      <Tooltip label="Remove row" withArrow>
                        <ActionIcon
                          size="xs"
                          variant="subtle"
                          color="gray"
                          onClick={() => handleRemoveRow(rowIndex)}
                        >
                          <IconMinus />
                        </ActionIcon>
                      </Tooltip>
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    <NumberInput
                      value={tableData[rowIndex]?.month ?? ''}
                      onChange={(value) =>
                        handleInputChange(
                          rowIndex,
                          'month',
                          typeof value === 'number' ? value : '',
                        )
                      }
                      placeholder="Enter value"
                      prefix="$"
                      decimalScale={2}
                      thousandSeparator=","
                    />
                  </Table.Td>
                  <Table.Td>
                    <NumberInput
                      value={tableData[rowIndex]?.ytd ?? ''}
                      onChange={(value) =>
                        handleInputChange(
                          rowIndex,
                          'ytd',
                          typeof value === 'number' ? value : '',
                        )
                      }
                      placeholder="Enter value"
                      prefix="$"
                      decimalScale={2}
                      thousandSeparator=","
                    />
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </ScrollArea>
        <Stack flex={2} mih={0}>
          <Textarea
            label="Operational Commentary"
            placeholder="Enter operational commentary"
            value={operationalCommentary}
            onChange={(e) => setOperationalCommentary(e.currentTarget.value)}
            minRows={6}
            maxRows={6}
            autosize
          />
          <Table withTableBorder withColumnBorders>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>BESS SmartBidder Metrics</Table.Th>
                <Table.Th>Actual</Table.Th>
                <Table.Th>Expected</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {[...SMART_BIDDER_ROWS].map((label) => (
                <Table.Tr key={label}>
                  <Table.Td>{label}</Table.Td>
                  <Table.Td>
                    <NumberInput
                      value={smartBidderData[label]?.actual ?? ''}
                      onChange={(value) =>
                        handleSmartBidderChange(
                          label,
                          'actual',
                          typeof value === 'number' ? value : '',
                        )
                      }
                      placeholder="Enter value"
                      decimalScale={3}
                      thousandSeparator=","
                    />
                  </Table.Td>
                  <Table.Td>
                    <NumberInput
                      value={smartBidderData[label]?.expected ?? ''}
                      onChange={(value) =>
                        handleSmartBidderChange(
                          label,
                          'expected',
                          typeof value === 'number' ? value : '',
                        )
                      }
                      placeholder="Enter value"
                      decimalScale={3}
                      thousandSeparator=","
                    />
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Stack>
        <Stack flex={1} mih={0} h="100%">
          <Paper withBorder p="md" radius="md" mih={0} h="100%">
            <Stack h="100%">
              <Text size="sm" fw={1000}>
                Included Projects
              </Text>
              {projects.isLoading && <Skeleton height="100%" />}
              {userProjectLabels.data && userProjectLabels.data.length > 0 && (
                <Group>
                  <Text size="sm" fw={1000}>
                    Quick Select:
                  </Text>
                  <Select
                    data={
                      userProjectLabels.data?.map((label) => label.name) || []
                    }
                    flex={1}
                    clearable
                    value={quickSelectLabelName}
                    onChange={handleQuickSelectChange}
                  />
                </Group>
              )}
              <ScrollArea flex={1} mih={0}>
                {batteryProjects?.map((project) => {
                  const projectIdString = project.project_id.toString()

                  return (
                    <Group key={project.project_id}>
                      <Checkbox
                        checked={includedProjects.includes(projectIdString)}
                        onChange={(event) => {
                          setQuickSelectLabelName(null)
                          const { checked } = event.currentTarget

                          setIncludedProjects((prev) => {
                            if (checked) {
                              return prev.includes(projectIdString)
                                ? prev
                                : [...prev, projectIdString]
                            }

                            return prev.filter((id) => id !== projectIdString)
                          })
                        }}
                      />
                      <Text>{project.name_long}</Text>
                    </Group>
                  )
                })}
              </ScrollArea>
              <Group p="xs" grow>
                <Button
                  size="compact-xs"
                  onClick={() => {
                    setQuickSelectLabelName(null)
                    setIncludedProjects(
                      batteryProjects?.map((p) => p.project_id.toString()) ||
                        [],
                    )
                  }}
                >
                  Include All
                </Button>
                <Button
                  size="compact-xs"
                  onClick={() => {
                    setQuickSelectLabelName(null)
                    setIncludedProjects([])
                  }}
                >
                  Clear All
                </Button>
              </Group>
            </Stack>
          </Paper>
        </Stack>
      </Group>
      <Group grow>
        <Tooltip
          label={disabledTooltip}
          disabled={!isGenerateDisabled}
          withArrow
          withinPortal
          position="top"
        >
          <Button
            onClick={handleGenerateReport}
            loading={generateReport.isPending}
            disabled={isGenerateDisabled}
          >
            Generate Report
          </Button>
        </Tooltip>
      </Group>
    </Stack>
  )
}

export default BESSMonthlyReport
