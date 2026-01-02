import { ProjectStatusTypeId } from '@/api/v1/operational/project_status_types'
import { ProjectType } from '@/api/v1/operational/project_types'
import { useCustomQuery } from '@/hooks/api'
import { MultiPolygon, Point } from '@/hooks/types'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import { readLocalStorageValue } from '@mantine/hooks'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

// Interface for creating a project based on backend ProjectCreate interface
export interface ProjectCreate {
  project_type_id: number
  name_long: string
  address?: string | null
  elevation: number
  time_zone: string
  poi: number // Point of Interconnection limit in MW
  capacity_dc?: number | null
  capacity_ac?: number | null
  capacity_bess_power_ac?: number | null
  capacity_bess_energy_bol_dc?: number | null
  ppa?: {
    rate?: number // flat rate for now
  } | null
  cod?: string | null // Commercial Operation Date (ISO date string)
  latitude: number
  longitude: number
}

interface ProjectSpec {
  used_device_type_ids?: number[]
  used_sensor_type_ids?: number[]
  device_types_with_all_points?: number[]
  device_types_all_with_polygons?: number[]
}

export interface Project {
  project_id: string
  project_type_id: ProjectType['project_type_id']
  project_status_type_id: ProjectStatusTypeId
  name_short: string
  name_long: string
  data_interval: string
  data_receive_schedule?: string
  address: string | null
  image_url: string | null
  point: Point
  polygon?: MultiPolygon
  elevation: number
  time_zone: string
  poi: number
  capacity_dc: number | null
  capacity_ac: number | null
  capacity_bess_power_ac: number | null
  capacity_bess_energy_bol_dc: number | null
  cod?: string | null // Commercial Operation Date
  commencement_of_construction_date?: string | null
  financial_close_date?: string | null
  notice_to_proceed_date?: string | null
  mechanical_completion_date?: string | null
  substantial_completion_date?: string | null
  interconnection_approval_date?: string | null
  performance_test_completion_date?: string | null
  placed_in_service_date?: string | null
  first_realtime_data_received_date?: string | null
  first_data_backfilled_date?: string | null
  has_event_integration: boolean
  has_expected_energy_integration: boolean
  has_report_integration: boolean
  has_quality_integration: boolean
  has_block_layout: boolean
  has_pv_pcs_layout: boolean
  has_tracker_layout: boolean
  has_pv_dc_combiner_layout: boolean
  has_met_stations: boolean
  has_pv_pcs_modules: boolean
  has_pv_dc_combiners: boolean
  has_trackers: boolean
  has_bess_blocks: boolean
  has_bess_pcss: boolean
  has_bess_enclosures: boolean
  has_bess_banks: boolean
  has_bess_strings: boolean
  has_real_time_data: boolean
  ppa?: { rate?: number; type?: string } | null
  interconnecting_utility?: string | null
  interconnecting_substation?: string | null
  interconnecting_voltage?: number | null
  interconnecting_iso?: string | null
  interconnecting_node_code?: string | null
  spec: ProjectSpec

  project_type: ProjectType | null
}

export interface ProjectUpdate {
  name_long?: string
  address?: string
  elevation?: number
  time_zone?: string
  poi?: number
  capacity_dc?: number
  capacity_ac?: number
  capacity_bess_power_ac?: number
  capacity_bess_energy_bol_dc?: number
  cod?: string | Date
  commencement_of_construction_date?: string | Date
  financial_close_date?: string | Date
  notice_to_proceed_date?: string | Date
  mechanical_completion_date?: string | Date
  substantial_completion_date?: string | Date
  interconnection_approval_date?: string | Date
  performance_test_completion_date?: string | Date
  placed_in_service_date?: string | Date
  first_realtime_data_received_date?: string | Date
  first_data_backfilled_date?: string | Date
  ppa?: { rate?: number; type?: string }
  interconnecting_utility?: string
  interconnecting_substation?: string
  interconnecting_voltage?: number
  interconnecting_iso?: string
  interconnecting_node_code?: string
}

export const useCreateProject = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation<Project, Error, ProjectCreate>({
    mutationFn: async (projectData: ProjectCreate) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/operational/projects`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data: projectData,
      })
      return response.data
    },
    onSuccess: () => {
      // Invalidate and refetch projects list
      queryClient.invalidateQueries({ queryKey: ['getProjects'] })
      queryClient.invalidateQueries({ queryKey: ['getProjectsPersonal'] })
    },
  })
}

export const useUpdateProject = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation<
    Project,
    Error,
    { projectId: string; projectData: ProjectUpdate }
  >({
    mutationFn: async ({ projectId, projectData }) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'put',
        url: `${baseURL}/v1/operational/projects/${projectId}`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data: projectData,
      })
      return response.data
    },
    onSuccess: () => {
      // Invalidate and refetch project data
      queryClient.invalidateQueries({ queryKey: ['getProject'] })
      queryClient.invalidateQueries({ queryKey: ['getProjects'] })
      queryClient.invalidateQueries({ queryKey: ['getProjectsPersonal'] })
    },
  })
}

export const useGetProjects = ({
  queryParams = {},
  queryOptions = {},
  personalPortfolio = true,
}: {
  queryParams?: {
    [key: string]: string | number | boolean | Array<string | number | boolean>
  }
  queryOptions?: Partial<UseQueryOptions>
  personalPortfolio?: boolean
}) => {
  let queryName: string
  if (personalPortfolio) {
    queryName = 'getProjectsPersonal'
  } else {
    queryName = 'getProjects'
  }

  const excludedProjectIds = readLocalStorageValue<string[]>({
    key: 'proximal-personal-portfolio-excluded-project-ids',
    defaultValue: [],
  })

  const paramsWithExclusions = personalPortfolio
    ? {
        ...queryParams,
        project_ids_excluded: excludedProjectIds,
      }
    : queryParams

  const axiosConfig = {
    url: '/v1/operational/projects',
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  const mergedQueryOptions = {
    ...defaultQueryOptions,
    ...queryOptions,
    enabled: queryOptions.enabled !== false && excludedProjectIds !== undefined,
  }

  return useCustomQuery<Project[]>({
    axiosConfig,
    queryName: queryName,
    queryParams: paramsWithExclusions,
    queryOptions: mergedQueryOptions,
  })
}

export const useSelectProject = (projectId: string) => {
  const { data: projects, ...rest } = useGetProjects({
    queryParams: {},
    queryOptions: { enabled: !!projectId },
  })

  const project = projects?.find((p) => p.project_id === projectId)

  return { data: project, ...rest }
}
