import {
  KPIInstance,
  useGetKPIInstances,
} from '@/api/v1/operational/kpi_instances'
import { useGetProjects } from '@/api/v1/operational/projects'
import { useGetReportInstances } from '@/api/v1/operational/report_instances'
import { isDisabled } from '@/pages/layout/header/ProjectDropdown.utils'
import { useProjectDropdown } from '@/providers/ProjectDropdownContext'
import {
  Spotlight,
  SpotlightActionData,
  createSpotlight,
} from '@mantine/spotlight'
import { useNavigate, useParams } from 'react-router'

import { searchStore } from './Spotlight.search.store'

const [projectStore] = createSpotlight()

export function SpotlightSearch() {
  const navigate = useNavigate()

  const { projectId } = useParams<{ projectId: string }>()

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
        id: 'project-data-browsing',
        label: 'Project Data Browsing',
        description: 'View project data browsing',
        onClick: () => navigate(`/projects/${projectId}/data-browsing`),
      },
      {
        id: 'project-settings',
        label: 'Project Settings',
        description: 'Manage project settings',
        onClick: () => navigate(`/projects/${projectId}/settings`),
      },
    )
  }

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

  const projects = useGetProjects({
    queryParams: {
      deep: true,
    },
  })

  const reportInstances = useGetReportInstances({})

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

  const dataLoaded = projects.data && reportInstances.data

  const actions: SpotlightActionData[] = dataLoaded
    ? projects.data
        .filter(
          (project) =>
            !isDisabled(
              projectId || '',
              filterCriteria,
              project,
              reportInstances.data,
            ),
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
      scrollable
    />
  )
}
