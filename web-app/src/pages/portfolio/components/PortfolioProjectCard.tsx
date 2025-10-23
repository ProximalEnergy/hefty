import { useUpdateProjectFavorite } from '@/api/v1/admin/user_projects'
import { ProjectDataLastUpdated } from '@/api/v1/operational/project_data_last_updated'
import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useGetProject } from '@/api/v1/operational/projects'
import { useGetPortfolioHome } from '@/api/v1/protected/web-application/portfolio/home'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { projectDescription } from '@/utils/projectDescription'
import { useUser } from '@clerk/clerk-react'
import {
  ActionIcon,
  Box,
  Card,
  Center,
  Group,
  RingProgress,
  Stack,
  Text,
  Title,
  Tooltip,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import {
  IconBattery4,
  IconHeart,
  IconHeartFilled,
  IconInfoCircle,
  IconSolarPanel,
} from '@tabler/icons-react'
import { Link } from 'react-router-dom'

import DataStatus from '../../layout/header/DataStatus'
import styles from '../PortfolioHome.module.css'

export function PortfolioProjectCard({
  project,
  portfolioHomeProject,
  projectDataLastUpdated,
  isFavorited = false,
}: {
  project: NonNullable<ReturnType<typeof useGetProject>['data']>
  portfolioHomeProject:
    | NonNullable<ReturnType<typeof useGetPortfolioHome>['data']>[number]
    | undefined
  projectDataLastUpdated?: ProjectDataLastUpdated
  isFavorited?: boolean
}) {
  const theme = useMantineTheme()
  const computedColorScheme = useComputedColorScheme('dark')
  const { user } = useUser()
  const updateFavoriteMutation = useUpdateProjectFavorite()

  const description = projectDescription(project)

  const handleFavoriteToggle = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()

    if (!user?.id) return

    updateFavoriteMutation.mutate({
      userId: user.id,
      projectId: project.project_id,
      isFavorited: !isFavorited,
    })
  }

  // Define x-axis data based on real time data availability
  const x = project.has_real_time_data
    ? portfolioHomeProject?.times?.slice(-288)
    : portfolioHomeProject?.times?.slice(0, 288)

  // Define max power line based on project characteristics
  // NOTE: On some projects (Serrano) it appears that the BESS capacity is greater than the POI
  const maxPower = Math.max(project.poi, project.capacity_bess_power_ac || 0)

  // Define max power line
  const maxPowerLinePositive = Array(x?.length ?? 0).fill(maxPower)
  const maxPowerLineNegative = Array(x?.length ?? 0).fill(-maxPower)
  const maxPowerLineConfig = {
    color: computedColorScheme === 'dark' ? theme.colors.dark[0] : 'black',
    dash: 'dot' as const,
    width: 1,
  }

  return (
    <Link
      to={`/projects/${project.project_id}`}
      style={{ color: 'inherit', textDecoration: 'none' }}
    >
      <Card
        p="md"
        shadow="md"
        withBorder
        className={styles.root}
        style={{ position: 'relative' }}
      >
        <Card.Section withBorder>
          <Group gap="xs" p="md">
            <DataStatus
              data={projectDataLastUpdated}
              data_receive_schedule={project.data_receive_schedule}
              isLoading={false}
              isError={false}
            />
            <Group gap="xs" flex={1}>
              <Title order={5} lh={1}>
                {project.name_long}
              </Title>
              <Tooltip label={description}>
                <Group gap={0}>
                  {[ProjectTypeId.PV, ProjectTypeId.PV_BESS].includes(
                    project.project_type_id,
                  ) && <IconSolarPanel />}
                  {[ProjectTypeId.BESS, ProjectTypeId.PV_BESS].includes(
                    project.project_type_id,
                  ) && <IconBattery4 />}
                </Group>
              </Tooltip>
              {!project.has_real_time_data && (
                <Tooltip label="Real time data is not available for this project. Data shown is from yesterday.">
                  <ActionIcon variant="subtle" color="yellow" size="sm">
                    <IconInfoCircle size={16} />
                  </ActionIcon>
                </Tooltip>
              )}
            </Group>
            <ActionIcon
              variant="subtle"
              size="sm"
              onClick={handleFavoriteToggle}
            >
              {isFavorited ? (
                <IconHeartFilled size={16} color={theme.colors.red[6]} />
              ) : (
                <IconHeart size={16} />
              )}
            </ActionIcon>
          </Group>
        </Card.Section>
        <Group gap="sm" h={210} mt="md">
          <Box h="100%" flex={1}>
            {portfolioHomeProject?.times ? (
              <PlotlyPlot
                data={[
                  {
                    x,
                    y: maxPowerLinePositive,
                    type: 'scatter',
                    mode: 'lines',
                    line: maxPowerLineConfig,
                  },
                  project.project_type_id === ProjectTypeId.BESS ||
                  project.project_type_id === ProjectTypeId.PV_BESS
                    ? {
                        x,
                        y: maxPowerLineNegative,
                        type: 'scatter',
                        mode: 'lines',
                        line: maxPowerLineConfig,
                      }
                    : {},
                  portfolioHomeProject.meter_active_power
                    ? {
                        x,
                        y: project.has_real_time_data
                          ? portfolioHomeProject.meter_active_power.slice(-288)
                          : portfolioHomeProject.meter_active_power.slice(
                              0,
                              288,
                            ),
                        type: 'scatter',
                        mode: 'lines',
                        line: {
                          color: theme.colors.green[7],
                        },
                        fill: 'tozeroy',
                        fillcolor: theme.colors.green[7] + 'a0',
                      }
                    : {},
                  portfolioHomeProject.meter_soc_percent
                    ? {
                        x,
                        y: project.has_real_time_data
                          ? portfolioHomeProject.meter_soc_percent.slice(-288)
                          : portfolioHomeProject.meter_soc_percent.slice(
                              0,
                              288,
                            ),
                        type: 'scatter',
                        mode: 'lines',
                        line: {
                          color: theme.colors.blue[7],
                        },
                        fill: 'tozeroy',
                        fillcolor: theme.colors.blue[7] + '20',
                        yaxis: 'y2',
                      }
                    : {},
                ]}
                layout={{
                  xaxis: {
                    showticklabels: false,
                    gridcolor: 'transparent',
                  },
                  yaxis: {
                    title: {
                      text: 'Power (MW)',
                      font: {
                        color: theme.colors.green[7],
                      },
                    },
                    overlaying: 'y2',
                    // If solar only, set y-axis from 0 to positive POI
                    // If BESS included, set y-axis from negative POI to positive POI
                    // NOTE: Added check to see if project.capacity_bess_power_ac
                    // is greater than the POI.
                    range: [
                      project.project_type_id === ProjectTypeId.PV
                        ? 0
                        : maxPower * -1.1,
                      maxPower * 1.1,
                    ],
                    gridcolor: 'transparent',
                  },
                  yaxis2: portfolioHomeProject.meter_soc_percent
                    ? {
                        title: {
                          text: 'SOC',
                          font: {
                            color: theme.colors.blue[7],
                          },
                        },
                        range: [-0.1, 1.1],
                        side: 'right',
                        showgrid: false,
                        zeroline: false,
                        tickformat: ',.0%',
                      }
                    : undefined,
                  margin: {
                    l: 50,
                    r: 0,
                    t: 0,
                    b: 0,
                  },
                  showlegend: false,
                }}
                config={{
                  displayModeBar: false,
                  staticPlot: true,
                }}
              />
            ) : (
              <Center h="100%" w="100%">
                <Text fw={700} c="red">
                  NO DATA FOR PAST 24 HOURS
                </Text>
              </Center>
            )}
          </Box>
          {project.has_real_time_data && (
            <Stack h="100%" justify="center" gap={2}>
              <RingProgressStat
                project={project}
                type="power"
                value={portfolioHomeProject?.power}
              />
              {(project.project_type_id === ProjectTypeId.PV ||
                project.project_type_id === ProjectTypeId.PV_BESS) && (
                <RingProgressStat
                  project={project}
                  type="poa"
                  value={portfolioHomeProject?.poa}
                />
              )}
              {(project.project_type_id === ProjectTypeId.BESS ||
                project.project_type_id === ProjectTypeId.PV_BESS) && (
                <RingProgressStat
                  project={project}
                  type="soc"
                  value={portfolioHomeProject?.soc}
                />
              )}
            </Stack>
          )}
        </Group>
      </Card>
    </Link>
  )
}

const RingProgressStat = ({
  project,
  type,
  value,
}: {
  project: NonNullable<ReturnType<typeof useGetProject>['data']>
  type: 'power' | 'poa' | 'soc'
  value?: number
}) => {
  const powerLimit = Math.max(project.poi, project.capacity_bess_power_ac || 0)

  let tooltipLabel = ''
  let sectionValue = 0
  switch (type) {
    case 'power':
      tooltipLabel = 'Meter Power'
      sectionValue = value != null ? (Math.abs(value) / powerLimit) * 100 : 0
      break
    case 'poa':
      tooltipLabel = 'POA'
      if (value != null && value < 0) {
        sectionValue = 0
      } else {
        sectionValue = value != null ? (value / 1000) * 100 : 0
      }
      break
    case 'soc':
      tooltipLabel = 'SOC'
      sectionValue = value != null ? (value / 100) * 100 : 0
      break
  }
  return (
    <Tooltip
      label={value != null ? tooltipLabel : `No ${tooltipLabel} data available`}
    >
      <RingProgress
        size={65}
        thickness={4}
        style={{ '--rp-size': '65px' } as React.CSSProperties}
        label={
          <Stack gap={0} align="center">
            <Text
              size="lgfi"
              fw={700}
              ta="center"
              c={value != null ? 'inherit' : 'red'}
            >
              {value != null ? value.toFixed(0) : '?'}
            </Text>
            <Text size="xs" ta="center" c={value != null ? 'inherit' : 'red'}>
              {type === 'power' ? 'MW' : type === 'poa' ? 'W/m²' : '%'}
            </Text>
          </Stack>
        }
        sections={[
          {
            value: sectionValue,
            color: value != null && value >= 0 ? 'green' : 'red',
          },
        ]}
      />
    </Tooltip>
  )
}
