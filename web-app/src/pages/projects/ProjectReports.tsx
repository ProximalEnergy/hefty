import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { useGetProjectReportInstances } from '@/hooks/api'
import { Group, Paper, Stack, Text, Title } from '@mantine/core'
import { IconEyeOff } from '@tabler/icons-react'
import { Link, useParams } from 'react-router'

import styles from './ProjectReports.module.css'

const Page = () => {
  const { projectId } = useParams()

  const { data: reportData, isLoading: isReportDataLoading } =
    useGetProjectReportInstances({
      pathParams: { projectId: projectId || '' },
      queryParams: {
        deep: false,
      },
    })

  const reports = [
    ...(reportData?.find((report) => report.report_type_id === 2)
      ? [
          {
            name: 'DC Amperage Report',
            component: <DCAmperageReport />,
            link: `/projects/${projectId}/reports/dc-amperage`,
            is_visible: reportData?.find(
              (report) => report.report_type_id === 2,
            )?.is_visible,
          },
        ]
      : []),
    ...(reportData?.find((report) => report.report_type_id === 3)
      ? [
          {
            name: 'Module Degradation Report',
            component: <ModuleDegradationReport />,
            link: `/projects/${projectId}/reports/module-degradation`,
            is_visible: reportData?.find(
              (report) => report.report_type_id === 3,
            )?.is_visible,
          },
        ]
      : []),
    ...(reportData?.find((report) => report.report_type_id === 4)
      ? [
          {
            name: 'Tracker Availability: Position vs. Setpoint',
            component: <TrackerPositionVsSetpointReport />,
            link: `/projects/${projectId}/reports/tracker-availability?report_type_id=4`,
            is_visible: reportData?.find(
              (report) => report.report_type_id === 4,
            )?.is_visible,
          },
        ]
      : []),
    ...(reportData?.find((report) => report.report_type_id === 5)
      ? [
          {
            name: 'Tracker Availability: Position vs. Median Setpoint',
            component: <TrackerPositionVsMedianSetpointReport />,
            link: `/projects/${projectId}/reports/tracker-availability?report_type_id=5`,
            is_visible: reportData?.find(
              (report) => report.report_type_id === 5,
            )?.is_visible,
          },
        ]
      : []),
    ...(reportData?.find((report) => report.report_type_id === 6)
      ? [
          {
            name: 'Inverter Mechanical Availability',
            component: <InverterMechanicalAvailabilityReport />,
            link: `/projects/${projectId}/reports/inverter-availability`,
            is_visible: reportData?.find(
              (report) => report.report_type_id === 6,
            )?.is_visible,
          },
        ]
      : []),
    ...(reportData?.find((report) => report.report_type_id === 8)
      ? [
          {
            name: 'Inverter Apparent Power vs. Voltage',
            component: <PCSApparentPowerVsVoltageReport />,
            link: `/projects/${projectId}/reports/pcs-apparent-vs-voltage`,
            is_visible: reportData?.find(
              (report) => report.report_type_id === 8,
            )?.is_visible,
          },
        ]
      : []),
    ...(reportData?.find((report) => report.report_type_id === 9)
      ? [
          {
            name: 'PV Performance Daily Report',
            component: <DailyPerformanceReportPreview />,
            link: `/projects/${projectId}/reports/daily-performance`,
            is_visible: reportData?.find(
              (report) => report.report_type_id === 9,
            )?.is_visible,
          },
        ]
      : []),
  ]

  if (isReportDataLoading) return <PageLoader />

  return (
    <Stack p="md" h="100%">
      <PageTitle
        info={
          <Text>
            This page provides access to various project reports. Click on a
            report to view more details.
          </Text>
        }
      >
        Reports
      </PageTitle>
      <Group>
        {reports.map((report, index) => (
          <Link
            to={report.link}
            key={index}
            style={{ textDecoration: 'none', color: 'inherit' }}
          >
            <Paper
              withBorder
              key={index}
              p="md"
              radius="md"
              className={styles.element}
              style={{ cursor: 'pointer' }}
              w={297.5}
              h={385}
              shadow="md"
            >
              <Stack w="100%" h="100%" align="center">
                <Group gap={4}>
                  {!report.is_visible && <IconEyeOff size={16} />}
                  <Title order={4}>{report.name}</Title>
                </Group>
                {report.component}
              </Stack>
            </Paper>
          </Link>
        ))}
      </Group>
    </Stack>
  )
}

const DCAmperageReport = () => {
  return (
    <Stack h="100%" justify="space-between" flex={1}>
      <Text size="sm">
        This report is designed to characterize the normalized output current of
        combiners at a project. The analysis is generated with user input for
        clearsky data, then combiner current is normalized based on relative
        capacity and compared to both neighboring and project-wide combiner
        results.
      </Text>
      <Text size="sm">
        Data output is available for download in XLSX format.
      </Text>
    </Stack>
  )
}

const ModuleDegradationReport = () => {
  return (
    <Stack h="100%" justify="space-between" flex={1}>
      <Text size="sm">
        This report is designed to characterize the performance of the modules
        at the most granular level possible. The analysis is generated by
        heavily filtering data for clearsky, high-performance timestamps which
        guarantee that shortfalls can be attributed to module degradation or
        other DC performance issues.
      </Text>
      <Text size="sm">
        Data output is available for download in CSV format.
      </Text>
    </Stack>
  )
}

const TrackerPositionVsSetpointReport = () => {
  return (
    <Stack h="100%" justify="space-between" flex={1}>
      <Text size="sm">
        This report is designed to analyze the performance of trackers compared
        to their own setpoints. The downloadable Excel file allows the tuning of
        these parameters for more specific analysis.
      </Text>
      <Text size="sm">
        Data output is available for download in XLSX format.
      </Text>
    </Stack>
  )
}

const TrackerPositionVsMedianSetpointReport = () => {
  return (
    <Stack h="100%" justify="space-between" flex={1}>
      <Text size="sm">
        This report is designed to analyze the performance of trackers compared
        to the median setpoint of their associated NCU. The downloadable Excel
        file allows the tuning of these parameters for more specific analysis.
      </Text>
      <Text size="sm">
        Data output is available for download in XLSX format.
      </Text>
    </Stack>
  )
}

const InverterMechanicalAvailabilityReport = () => {
  return (
    <Stack h="100%" justify="space-between" flex={1}>
      <Text size="sm">
        This report is designed to analyze the mechanical availability of
        inverters and inverter modules. The report is user-tunable to allow for
        analysis of availability based on user-defined parameters.
      </Text>
      <Text size="sm">
        Data output is available for download in XLSX format.
      </Text>
    </Stack>
  )
}

const PCSApparentPowerVsVoltageReport = () => {
  return (
    <Stack h="100%" justify="space-between" flex={1}>
      <Text size="sm">
        This report visualizes the relationship between inverter apparent power
        output (in MVA) and terminal AC voltage. A theoretical envelope is
        included to illustrate expected voltage behavior under normal operating
        conditions.
      </Text>
      <Text size="sm">
        Data is available for visualization only; ideal limits are customizable
        in the report view.
      </Text>
    </Stack>
  )
}

const DailyPerformanceReportPreview = () => {
  return (
    <Stack h="100%" justify="space-between" flex={1}>
      <Text size="sm">
        This report provides a comprehensive daily performance overview,
        including project generation, performance ratio, PCS mechanical
        availability, and event tracking. It features a 30-day trailing energy
        analysis and DC combiner field health visualization.
      </Text>
      <Text size="sm">
        Data is displayed for a single selected date with interactive
        visualizations and metrics.
      </Text>
    </Stack>
  )
}

export default Page
