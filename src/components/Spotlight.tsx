import {
  KPIInstance,
  useGetKPIInstances,
} from '@/api/v1/operational/kpi_instances'
import { useGetProjects } from '@/api/v1/operational/projects'
// import { useGetProjectReportInstances } from '@/hooks/api'
import { isDisabled } from '@/pages/layout/header/ProjectDropdown'
import { useProjectDropdown } from '@/providers/ProjectDropdownProvider'
import {
  Spotlight,
  SpotlightActionData,
  createSpotlight,
} from '@mantine/spotlight'
import { useNavigate, useParams } from 'react-router-dom'

const [searchStore] = createSpotlight()
const [projectStore] = createSpotlight()

export function SpotlightSearch() {
  const navigate = useNavigate()

  const { projectId } = useParams<{ projectId: string }>()

  // const { data: reports, isLoading: reportsLoading } =
  //   useGetProjectReportInstances({
  //     pathParams: { projectId: projectId || '' },
  //     queryParams: {
  //       deep: true,
  //     },
  //     queryOptions: {
  //       enabled: !!projectId,
  //     },
  //   })

  const { data: kpis, isLoading: kpisLoading } = useGetKPIInstances({
    queryParams: {
      project_ids: [projectId || ''],
      deep: true,
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  const pages: SpotlightActionData[] = [
    {
      id: 'portfolio-home',
      label: 'Portfolio Home',
      description: 'Go to the portfolio homepage',
      onClick: () => navigate('/portfolio'),
    },
    {
      id: 'portfolio-list',
      label: 'Portfolio List',
      description: 'View a list of all projects',
      onClick: () => navigate('/portfolio/list'),
    },
    {
      id: 'portfolio-map',
      label: 'Portfolio Map',
      description: 'View all projects on a map',
      onClick: () => navigate('/portfolio/map'),
    },
    {
      id: 'portfolio-kpis',
      label: 'Portfolio KPIs',
      description: 'View portfolio-level KPIs',
      onClick: () => navigate('/portfolio/kpis'),
    },
    {
      id: 'portfolio-calendar',
      label: 'Portfolio Calendar',
      description: 'View the portfolio calendar',
      onClick: () => navigate('/portfolio/calendar'),
    },
    {
      id: 'portfolio-settings',
      label: 'Portfolio Settings',
      description: 'Manage portfolio settings',
      onClick: () => navigate('/portfolio/settings'),
    },
    {
      id: 'account-settings',
      label: 'Account Settings',
      description: 'Manage your account settings',
      onClick: () => navigate('/account-settings'),
    },
    {
      id: 'application-settings',
      label: 'Application Settings',
      description: 'Manage application settings',
      onClick: () => navigate('/application-settings'),
    },
  ]

  if (projectId) {
    pages.push(
      {
        id: 'project-home',
        label: 'Project Home',
        description: 'Go to the project homepage',
        onClick: () => navigate(`/projects/${projectId}`),
      },
      {
        id: 'project-reports',
        label: 'Project Reports',
        description: 'View project reports',
        onClick: () => navigate(`/projects/${projectId}/reports`),
      },
      {
        id: 'project-events',
        label: 'Project Events',
        description: 'View project events',
        onClick: () => navigate(`/projects/${projectId}/events`),
      },
      {
        id: 'project-settings',
        label: 'Project Settings',
        description: 'Manage project settings',
        onClick: () => navigate(`/projects/${projectId}/settings`),
      },
    )
  }

  // const reportActions: SpotlightActionData[] =
  //   !reportsLoading && reports
  //     ? reports.map((report) => ({
  //         id: `report-${report.report_instance_id || report.report_type_id}`,
  //         label:
  //           report.report_type?.name_long ||
  //           `Report Type ${report.report_type_id}`,
  //         description: `View the ${report.report_type?.name_long || 'report'}`,
  //         onClick: () =>
  //           navigate(
  //             `/projects/${projectId}/reports?report_id=${report.report_instance_id || report.report_type_id}`,
  //           ),
  //       }))
  //     : []

  const kpiActions: SpotlightActionData[] =
    !kpisLoading && kpis
      ? kpis.map((kpi: KPIInstance) => ({
          id: `kpi-${kpi.kpi_type_id}`,
          label: kpi.kpi_type?.name_long,
          description: `View the ${kpi.kpi_type?.name_long} KPI`,
          onClick: () =>
            navigate(`/projects/${projectId}/kpis/type/${kpi.kpi_type_id}`),
        }))
      : []

  const actions = [
    {
      group: 'Pages',
      actions: pages,
    },
    // {
    //   group: 'Reports',
    //   actions: reportActions,
    // },
    {
      group: 'KPIs',
      actions: kpiActions,
    },
  ]

  return (
    <Spotlight
      store={searchStore}
      actions={actions}
      nothingFound="Nothing found..."
      highlightQuery
      scrollable
      maxHeight={700}
      searchProps={{
        placeholder: 'Search...',
      }}
    />
  )
}

export function ProjectSpotlight() {
  const navigate = useNavigate()
  const { projectId } = useParams<{ projectId: string }>()
  const { isProjectDropdownEnabled, filterCriteria } = useProjectDropdown()

  const { data: projects, isLoading: projectsLoading } = useGetProjects({
    queryParams: {
      deep: true,
    },
  })

  const onClick = (newProjectId: string) => {
    if (!projectId) {
      navigate(`/projects/${newProjectId}`)
    } else {
      const updatedPath = location.pathname.replace(
        /projects\/[^/]+/,
        `projects/${newProjectId}`,
      )
      navigate(`${updatedPath}${location.search}`)
    }
  }

  if (!isProjectDropdownEnabled) {
    return null
  }

  const actions: SpotlightActionData[] =
    !projectsLoading && projects
      ? projects
          .filter(
            (project) => !isDisabled(projectId || '', filterCriteria, project),
          )
          .map((project) => ({
            id: `project-${project.project_id}`,
            label: project.name_long,
            onClick: () => onClick(project.project_id),
          }))
      : []

  return (
    <Spotlight
      shortcut="mod+O"
      store={projectStore}
      actions={actions}
      nothingFound="Nothing found..."
    />
  )
}
