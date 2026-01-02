import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

// Type definitions for dashboard components
interface GaugeDashboardConfig {
  measuredVariable: string
  maximumValue: string
}

interface KPIDashboardConfig {
  kpiTypeId: string
}

interface LineDashboardConfig {
  traces: Array<{
    id: string
    sensorTypeId: string | null
    aggregationMethod: string | null
  }>
}

interface ScatterDashboardConfig {
  xAxisSensorTypeId: string | null
  yAxisSensorTypeId: string | null
}

interface BarDashboardConfig {
  sensorTypeId: string | null
  aggregationMethod: string | null
}

interface RichTextDashboardConfig {
  content: string
}

type GISDashboardConfig = Record<string, unknown>

type DashboardComponentConfig =
  | GaugeDashboardConfig
  | KPIDashboardConfig
  | LineDashboardConfig
  | ScatterDashboardConfig
  | BarDashboardConfig
  | RichTextDashboardConfig
  | GISDashboardConfig

export interface DashboardComponent {
  component_id: string
  component_type:
    | 'gauge'
    | 'kpi'
    | 'gis'
    | 'bar'
    | 'line'
    | 'scatter'
    | 'rich_text'
  config: DashboardComponentConfig
  x: number
  y: number
  w: number
  h: number
}

interface DataCustomBar {
  x: string[]
  y: number[]
  sensor_type_id: number
  name: string
  unit: string
}

interface DataCustomGauge {
  value: number
  value_raw: number
  max: number
}

interface DataCustomLine {
  x: string[]
  y: number[]
  sensor_type_id: number
  name: string
  unit: string
  maximum?: number
  minimum?: number
}

interface DataCustomScatter {
  x: { values: number[]; name: string; unit: string }
  y: { values: number[]; name: string; unit: string }
}

interface UserDashboard {
  dashboard_id: string
  dashboard_name: string
  owner_user_id: string
}

interface Dashboard {
  dashboard_name: string
  default_time_range: string
  default_kpi_time_range: string
  components: DashboardComponent[]
  is_owner: boolean
}

export const useGetUserDashboards = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/custom-dash/user-dashboards`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<UserDashboard[]>({
    axiosConfig,
    queryName: 'getUserDashboards',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetSharedUserDashboards = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/custom-dash/shared-user-dashboards`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<UserDashboard[]>({
    axiosConfig,
    queryName: 'getSharedUserDashboards',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useAddUserDashboard = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      project_id,
      dashboard_name,
      default_time_range,
      default_kpi_time_range,
      components,
    }: {
      project_id: string
      dashboard_name: string
      default_time_range: number
      default_kpi_time_range: number
      components: DashboardComponent[]
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'post',
        url: `${baseURL}/v1/protected/web-application/projects/${project_id}/custom-dash/create-dashboard`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          dashboard_name,
          default_time_range,
          default_kpi_time_range,
          components,
        },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getUserDashboards'] })
    },
  })
}

export const useDuplicateUserDashboard = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      project_id,
      dashboard_id,
      target_project_ids,
    }: {
      project_id: string
      dashboard_id: string
      target_project_ids?: string[]
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'post',
        url: `${baseURL}/v1/protected/web-application/projects/${project_id}/custom-dash/duplicate/${dashboard_id}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: target_project_ids ? { target_project_ids } : undefined,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getUserDashboards'] })
      queryClient.invalidateQueries({ queryKey: ['getSharedUserDashboards'] })
    },
  })
}

export const useUpdateUserDashboard = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      project_id,
      dashboard_id,
      dashboard_name,
      default_time_range,
      default_kpi_time_range,
      components,
    }: {
      project_id: string
      dashboard_id: string
      dashboard_name: string
      default_time_range: number
      default_kpi_time_range: number
      components: DashboardComponent[]
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'put',
        url: `${baseURL}/v1/protected/web-application/projects/${project_id}/custom-dash/update-dashboard`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          dashboard_id,
          dashboard_name,
          default_time_range,
          default_kpi_time_range,
          components,
        },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getUserDashboards'] })
      queryClient.invalidateQueries({ queryKey: ['getDashboard'] })
    },
  })
}

export const useGetDashboard = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string; dashboardId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/custom-dash/${pathParams.dashboardId}`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<Dashboard>({
    axiosConfig,
    queryName: 'getDashboard',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetBarData = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: {
    sensor_type_id: number
    aggregation_type: string
    start: string
    end: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/custom-dash/bar`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<DataCustomBar>({
    axiosConfig,
    queryName: 'getBarData',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetGaugeData = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: {
    measured_variable: string
    maximum_value: string
    start: string
    end: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/custom-dash/gauge`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<DataCustomGauge>({
    axiosConfig,
    queryName: 'getGaugeData',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetLineData = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    sensor_type_ids?: number[]
    aggregation_types?: string[]
    tag_ids?: string[]
    maximum?: (number | null)[]
    minimum?: (number | null)[]
    start?: string
    end?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/custom-dash/line`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<DataCustomLine[]>({
    axiosConfig,
    queryName: 'getLineData',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetScatterData = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: {
    x_axis_sensor_type_id: number
    y_axis_sensor_type_id: number
    start: string
    end: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/custom-dash/scatter`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<DataCustomScatter>({
    axiosConfig,
    queryName: 'getScatterData',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetDashboardSharedUsers = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string; dashboardId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/custom-dash/share/${pathParams.dashboardId}/users`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<{ shared_user_ids: string[] }>({
    axiosConfig,
    queryName: 'getDashboardSharedUsers',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useShareUserDashboard = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      project_id,
      dashboard_id,
      shared_user_id,
    }: {
      project_id: string
      dashboard_id: string
      shared_user_id: string
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'post',
        url: `${baseURL}/v1/protected/web-application/projects/${project_id}/custom-dash/share/${dashboard_id}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          shared_user_id,
        },
      })
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['getUserDashboards'] })
      queryClient.invalidateQueries({ queryKey: ['getSharedUserDashboards'] })
      queryClient.invalidateQueries({
        queryKey: [
          'getDashboardSharedUsers',
          {
            projectId: variables.project_id,
            dashboardId: variables.dashboard_id,
          },
        ],
      })
    },
  })
}

export const useUnshareUserDashboard = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      project_id,
      dashboard_id,
      shared_user_id,
    }: {
      project_id: string
      dashboard_id: string
      shared_user_id: string
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'delete',
        url: `${baseURL}/v1/protected/web-application/projects/${project_id}/custom-dash/share/${dashboard_id}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          shared_user_id,
        },
      })
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['getUserDashboards'] })
      queryClient.invalidateQueries({ queryKey: ['getSharedUserDashboards'] })
      queryClient.invalidateQueries({
        queryKey: [
          'getDashboardSharedUsers',
          {
            projectId: variables.project_id,
            dashboardId: variables.dashboard_id,
          },
        ],
      })
    },
  })
}

export const useDeleteUserDashboard = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      project_id,
      dashboard_id,
    }: {
      project_id: string
      dashboard_id: string
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'delete',
        url: `${baseURL}/v1/protected/web-application/projects/${project_id}/custom-dash/${dashboard_id}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getUserDashboards'] })
    },
  })
}
