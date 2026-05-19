import { ProjectTypeEnum, ReportTypeEnum } from '@/api/enumerations'
import {
  type ReportInstance,
  useGetProjectReportInstances,
} from '@/api/v1/operational/project/report_instances'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetReportTypes } from '@/api/v1/operational/report_types'
import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import RequiresUserType from '@/components/admin/RequiresUserType'
import { ReportInstancesConfigModal } from '@/components/modals/ReportInstancesConfigModal'
import styles from '@/pages/projects/ProjectReports.module.css'
import {
  Badge,
  Button,
  Divider,
  Group,
  Paper,
  SimpleGrid,
  Space,
  Stack,
  Text,
  Tooltip,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import {
  Icon,
  IconAccessPoint,
  IconActivity,
  IconBatteryCharging,
  IconCalendarEvent,
  IconCalendarWeek,
  IconCircuitAmmeter,
  IconClockHour2,
  IconEyeOff,
  IconFileText,
  IconFileTypeCsv,
  IconFileTypePdf,
  IconFileTypeXls,
  IconGraph,
  IconSettings,
  IconTrendingDown,
} from '@tabler/icons-react'
import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router'

// Report metadata configuration
// NOTE: In the future some of this information could be moved to the database
const REPORT_CONFIG: {
  // The link to the report page
  link: Record<number, string>
  // Whether the report has a selectable date
  selectable_date: Record<number, boolean>
  // Whether the report has a selectable date range
  selectable_date_range: Record<number, boolean>
  // Whether the report has a downloadable Excel file
  downloadable_excel: Record<number, boolean>
  // Whether the report has a downloadable CSV file
  downloadable_csv: Record<number, boolean>
  // Whether the report has a downloadable PDF file
  downloadable_pdf: Record<number, boolean>
} = {
  link: {
    [ReportTypeEnum.DC_AMPERAGE]: 'dc-amperage',
    [ReportTypeEnum.MODULE_DEGRADATION]: 'module-degradation',
    [ReportTypeEnum.MONTHLY_PERFORMANCE]: 'monthly-performance',
    [ReportTypeEnum.TRACKER_ROW_AVAILABILITY_POSITION_VS_SETPOINT]:
      'tracker-availability?report_type_id=' +
      ReportTypeEnum.TRACKER_ROW_AVAILABILITY_POSITION_VS_SETPOINT,
    [ReportTypeEnum.TRACKER_ROW_AVAILABILITY_POSITION_VS_MEDIAN_SETPOINT]:
      'tracker-availability?report_type_id=' +
      ReportTypeEnum.TRACKER_ROW_AVAILABILITY_POSITION_VS_MEDIAN_SETPOINT,
    [ReportTypeEnum.INVERTER_MECHANICAL_AVAILABILITY]: 'inverter-availability',
    [ReportTypeEnum.PV_INVERTER_APPARENT_POWER_VS_AC_VOLTAGE]:
      'pcs-apparent-vs-voltage',
    [ReportTypeEnum.PV_PERFORMANCE_DAILY]: 'daily-performance',
    [ReportTypeEnum.PV_PERFORMANCE_WEEKLY]: 'weekly-performance',
    [ReportTypeEnum.EEC_BESS_MONTHLY_REPORT]: 'eec-bess-monthly-report',
    [ReportTypeEnum.SCADA_TELEMETRY_LAST_REPORTED]:
      'scada-telemetry-last-reported',
  },
  selectable_date: {
    [ReportTypeEnum.DC_AMPERAGE]: true,
    [ReportTypeEnum.MONTHLY_PERFORMANCE]: true,
    [ReportTypeEnum.TRACKER_ROW_AVAILABILITY_POSITION_VS_SETPOINT]: true,
    [ReportTypeEnum.TRACKER_ROW_AVAILABILITY_POSITION_VS_MEDIAN_SETPOINT]: true,
    [ReportTypeEnum.INVERTER_MECHANICAL_AVAILABILITY]: true,
    [ReportTypeEnum.PV_PERFORMANCE_DAILY]: true,
  },
  selectable_date_range: {
    [ReportTypeEnum.PV_PERFORMANCE_WEEKLY]: true,
    [ReportTypeEnum.MODULE_DEGRADATION]: true,
    [ReportTypeEnum.PV_INVERTER_APPARENT_POWER_VS_AC_VOLTAGE]: true,
    [ReportTypeEnum.EEC_BESS_MONTHLY_REPORT]: true,
  },
  downloadable_excel: {
    [ReportTypeEnum.DC_AMPERAGE]: true,
    [ReportTypeEnum.TRACKER_ROW_AVAILABILITY_POSITION_VS_SETPOINT]: true,
    [ReportTypeEnum.TRACKER_ROW_AVAILABILITY_POSITION_VS_MEDIAN_SETPOINT]: true,
    [ReportTypeEnum.INVERTER_MECHANICAL_AVAILABILITY]: true,
    [ReportTypeEnum.SCADA_TELEMETRY_LAST_REPORTED]: true,
  },
  downloadable_csv: {
    [ReportTypeEnum.MODULE_DEGRADATION]: true,
  },
  downloadable_pdf: {
    [ReportTypeEnum.MONTHLY_PERFORMANCE]: true,
    [ReportTypeEnum.PV_PERFORMANCE_DAILY]: true,
    [ReportTypeEnum.PV_PERFORMANCE_WEEKLY]: true,
    [ReportTypeEnum.EEC_BESS_MONTHLY_REPORT]: true,
  },
}

const reportTypeIcons: Partial<Record<number, Icon>> = {
  [ReportTypeEnum.DC_AMPERAGE]: IconCircuitAmmeter,
  [ReportTypeEnum.TRACKER_ROW_AVAILABILITY_POSITION_VS_SETPOINT]:
    IconClockHour2,
  [ReportTypeEnum.TRACKER_ROW_AVAILABILITY_POSITION_VS_MEDIAN_SETPOINT]:
    IconClockHour2,
  [ReportTypeEnum.INVERTER_MECHANICAL_AVAILABILITY]: IconClockHour2,
  [ReportTypeEnum.PV_PERFORMANCE_DAILY]: IconGraph,
  [ReportTypeEnum.PV_PERFORMANCE_WEEKLY]: IconCalendarWeek,
  [ReportTypeEnum.MONTHLY_PERFORMANCE]: IconGraph,
  [ReportTypeEnum.MODULE_DEGRADATION]: IconTrendingDown,
  [ReportTypeEnum.PV_INVERTER_APPARENT_POWER_VS_AC_VOLTAGE]: IconActivity,
  [ReportTypeEnum.EEC_BESS_MONTHLY_REPORT]: IconBatteryCharging,
  [ReportTypeEnum.SCADA_TELEMETRY_LAST_REPORTED]: IconAccessPoint,
}

const reportsPageInfo =
  'This page provides access to various project reports. Click on a report ' +
  'to view more details.'

const ProjectReportsPage = () => {
  // Get the project ID from the URL
  const { projectId } = useParams<{ projectId: string }>()
  const [configModalOpened, setConfigModalOpened] = useState(false)

  // Get project data to determine project type
  const project = useSelectProject(projectId || '')

  // Get report instances for the project
  const reportInstances = useGetProjectReportInstances({
    pathParams: { project_id: projectId || '' },
    queryParams: {
      deep: true,
    },
  })
  const reportTypes = useGetReportTypes({})

  const reportTypeLookup = useMemo(() => {
    if (!reportTypes.data) {
      return {}
    }

    return Object.fromEntries(
      reportTypes.data.map((reportType) => [
        reportType.report_type_id,
        reportType,
      ]),
    ) as Record<number, NonNullable<ReportInstance['report_type']>>
  }, [reportTypes.data])

  // Create example report instances when there are no real instances
  const exampleReports = useMemo(() => {
    if (reportInstances.data && reportInstances.data.length > 0) {
      return null
    }

    const projectTypeId = project.data?.project_type_id

    // For PV projects, show Daily Performance Report
    if (projectTypeId === ProjectTypeEnum.PV) {
      const dailyType = reportTypeLookup[ReportTypeEnum.PV_PERFORMANCE_DAILY]
      const weeklyType = reportTypeLookup[ReportTypeEnum.PV_PERFORMANCE_WEEKLY]
      return [
        {
          project_id: projectId || '',
          report_type_id: ReportTypeEnum.PV_PERFORMANCE_DAILY,
          is_visible: true,
          report_type: {
            report_type_id: ReportTypeEnum.PV_PERFORMANCE_DAILY,
            name_short: dailyType?.name_short ?? 'Daily Performance',
            name_long: dailyType?.name_long ?? 'PV Daily Performance Report',
            doc_url: dailyType?.doc_url ?? '',
            description: dailyType?.description ?? null,
          },
        } as ReportInstance,
        {
          project_id: projectId || '',
          report_type_id: ReportTypeEnum.PV_PERFORMANCE_WEEKLY,
          is_visible: true,
          report_type: {
            report_type_id: ReportTypeEnum.PV_PERFORMANCE_WEEKLY,
            name_short: weeklyType?.name_short ?? 'Weekly Performance',
            name_long: weeklyType?.name_long ?? 'PV Weekly Performance Report',
            doc_url: weeklyType?.doc_url ?? '',
            description: weeklyType?.description ?? null,
          },
        } as ReportInstance,
      ]
    }

    // For BESS projects, show PCS Mechanical Availability Report
    if (projectTypeId === ProjectTypeEnum.BESS) {
      const reportType =
        reportTypeLookup[ReportTypeEnum.INVERTER_MECHANICAL_AVAILABILITY]
      return [
        {
          project_id: projectId || '',
          report_type_id: ReportTypeEnum.INVERTER_MECHANICAL_AVAILABILITY,
          is_visible: true,
          report_type: {
            report_type_id: ReportTypeEnum.INVERTER_MECHANICAL_AVAILABILITY,
            name_short: reportType?.name_short ?? 'PCS Availability',
            name_long:
              reportType?.name_long ??
              'BESS PCS Mechanical Availability Report',
            doc_url: reportType?.doc_url ?? '',
            description: reportType?.description ?? null,
          },
        } as ReportInstance,
      ]
    }

    // For PVS (PV + BESS) projects, show both example reports
    if (projectTypeId === ProjectTypeEnum.PVS) {
      const pvReportType = reportTypeLookup[ReportTypeEnum.PV_PERFORMANCE_DAILY]
      const pvWeeklyType =
        reportTypeLookup[ReportTypeEnum.PV_PERFORMANCE_WEEKLY]
      const bessReportType =
        reportTypeLookup[ReportTypeEnum.INVERTER_MECHANICAL_AVAILABILITY]
      return [
        {
          project_id: projectId || '',
          report_type_id: ReportTypeEnum.PV_PERFORMANCE_DAILY,
          is_visible: true,
          report_type: {
            report_type_id: ReportTypeEnum.PV_PERFORMANCE_DAILY,
            name_short: pvReportType?.name_short ?? 'Daily Performance',
            name_long: pvReportType?.name_long ?? 'PV Daily Performance Report',
            doc_url: pvReportType?.doc_url ?? '',
            description: pvReportType?.description ?? null,
          },
        } as ReportInstance,
        {
          project_id: projectId || '',
          report_type_id: ReportTypeEnum.PV_PERFORMANCE_WEEKLY,
          is_visible: true,
          report_type: {
            report_type_id: ReportTypeEnum.PV_PERFORMANCE_WEEKLY,
            name_short: pvWeeklyType?.name_short ?? 'Weekly Performance',
            name_long:
              pvWeeklyType?.name_long ?? 'PV Weekly Performance Report',
            doc_url: pvWeeklyType?.doc_url ?? '',
            description: pvWeeklyType?.description ?? null,
          },
        } as ReportInstance,
        {
          project_id: projectId || '',
          report_type_id: ReportTypeEnum.INVERTER_MECHANICAL_AVAILABILITY,
          is_visible: true,
          report_type: {
            report_type_id: ReportTypeEnum.INVERTER_MECHANICAL_AVAILABILITY,
            name_short: bessReportType?.name_short ?? 'PCS Availability',
            name_long:
              bessReportType?.name_long ??
              'BESS PCS Mechanical Availability Report',
            doc_url: bessReportType?.doc_url ?? '',
            description: bessReportType?.description ?? null,
          },
        } as ReportInstance,
      ]
    }

    return null
  }, [
    reportInstances.data,
    project.data?.project_type_id,
    projectId,
    reportTypeLookup,
  ])

  // Use example reports if no real instances exist
  const displayReports = reportInstances.data?.length
    ? reportInstances.data
    : exampleReports
  const reportsWithLinks = useMemo(
    () =>
      (displayReports ?? [])
        .filter(
          (reportInstance) =>
            reportInstance.report_type_id in REPORT_CONFIG.link,
        )
        .sort((left, right) =>
          (left.report_type?.name_long ?? '').localeCompare(
            right.report_type?.name_long ?? '',
          ),
        ),
    [displayReports],
  )

  // Early return for loading and error states
  if (reportInstances.isLoading || project.isLoading) return <PageLoader />
  if (reportInstances.error) return <PageError error={reportInstances.error} />

  return (
    <Stack p="md" h="100%">
      <Group justify="space-between" align="center">
        <PageTitle info={reportsPageInfo}>Reports</PageTitle>
        <RequiresUserType requiredUserType="superadmin" silent>
          <Button
            leftSection={<IconSettings size={16} />}
            onClick={() => setConfigModalOpened(true)}
          >
            Configure Reports
          </Button>
        </RequiresUserType>
      </Group>

      {exampleReports !== null && (
        <Paper
          p="md"
          withBorder
          style={{
            backgroundColor: 'var(--mantine-color-blue-0)',
            borderColor: 'var(--mantine-color-blue-2)',
          }}
        >
          <Text size="sm" c="dimmed">
            No reports are configured for this project yet. The example report
            below shows what reports will look like once configured. To request
            reports for this project, please reach out via the{' '}
            <Text component="span" fw={500} c="blue">
              Feedback
            </Text>{' '}
            button in the navigation menu.
          </Text>
        </Paper>
      )}

      {!displayReports || displayReports.length === 0 ? (
        // If no reports are available, show a message
        <Text c="dimmed">No reports available for this project.</Text>
      ) : (
        // Otherwise, show report instance cards in a single grid
        <SimpleGrid cols={{ base: 1, sm: 2, md: 4, lg: 5, xl: 6 }}>
          {reportsWithLinks.map((reportInstance) => (
            <ReportInstanceCard
              key={reportInstance.report_type_id}
              reportInstance={reportInstance}
              isExample={exampleReports !== null}
            />
          ))}
        </SimpleGrid>
      )}

      <ReportInstancesConfigModal
        opened={configModalOpened}
        onClose={() => setConfigModalOpened(false)}
        projectId={projectId || ''}
      />
    </Stack>
  )
}

const ReportCardTypeIcon = ({ reportTypeId }: { reportTypeId: number }) => {
  const IconComponent = reportTypeIcons[reportTypeId] ?? IconFileText

  return <IconComponent size={24} stroke={1.5} />
}

const ReportInstanceCard = ({
  reportInstance,
  isExample = false,
}: {
  reportInstance: ReportInstance
  isExample?: boolean
}) => {
  const theme = useMantineTheme()
  const computedColorScheme = useComputedColorScheme('dark')
  const iconSize = 14
  const excelGreen = '#0F7C41'
  const pdfRed = '#EB1F00'
  const reportIconColor =
    computedColorScheme === 'dark' ? theme.colors.gray[0] : theme.colors.dark[8]

  const link = REPORT_CONFIG.link[reportInstance.report_type_id]
  const description = reportInstance.report_type?.description

  const cardContent = (
    <Paper
      withBorder
      p="md"
      radius="md"
      className={styles.element}
      style={{
        cursor: isExample ? 'default' : 'pointer',
        opacity: isExample ? 0.8 : 1,
      }}
      shadow="md"
      h={360}
    >
      <Stack h="100%">
        <Group justify="center" c={reportIconColor}>
          <ReportCardTypeIcon reportTypeId={reportInstance.report_type_id} />
        </Group>

        {/* Report title */}
        <Stack gap="xs" justify="center" align="center" mih={64}>
          {isExample && (
            <Badge color="orange" variant="light" size="sm">
              Example
            </Badge>
          )}
          <Text fw={700} ta="center">
            {reportInstance.report_type?.name_long}
          </Text>
        </Stack>

        {/* Description and description */}
        <Divider />
        {description && <Text size="sm">{description}</Text>}
        <Space flex={1} />

        {/* Information icons */}
        <Group justify="end">
          {REPORT_CONFIG.selectable_date[reportInstance.report_type_id] && (
            <Tooltip label="Selectable date">
              <IconCalendarEvent size={iconSize} />
            </Tooltip>
          )}
          {REPORT_CONFIG.selectable_date_range[
            reportInstance.report_type_id
          ] && (
            <Tooltip label="Selectable date range">
              <IconCalendarWeek size={iconSize} />
            </Tooltip>
          )}
          {REPORT_CONFIG.downloadable_excel[reportInstance.report_type_id] && (
            <Tooltip label="Excel download available">
              <IconFileTypeXls size={iconSize} color={excelGreen} />
            </Tooltip>
          )}
          {REPORT_CONFIG.downloadable_csv[reportInstance.report_type_id] && (
            <Tooltip label="CSV download available">
              <IconFileTypeCsv size={iconSize} color={excelGreen} />
            </Tooltip>
          )}
          {REPORT_CONFIG.downloadable_pdf[reportInstance.report_type_id] && (
            <Tooltip label="PDF download available">
              <IconFileTypePdf size={iconSize} color={pdfRed} />
            </Tooltip>
          )}
          {!reportInstance.is_visible && (
            <Tooltip label="Hidden report">
              <IconEyeOff size={iconSize} color="red" />
            </Tooltip>
          )}
        </Group>
      </Stack>
    </Paper>
  )

  if (isExample) {
    return cardContent
  }

  return (
    <Link to={link} style={{ textDecoration: 'none', color: 'inherit' }}>
      {cardContent}
    </Link>
  )
}

export default ProjectReportsPage
