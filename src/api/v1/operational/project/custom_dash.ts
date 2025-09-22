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
export interface DashboardComponent {
  component_id: string
  component_type: 'gauge' | 'kpi' | 'gis' | 'bar' | 'line' | 'scatter'
  config: any
  x: number
  y: number
  w: number
  h: number
}

export interface DataCustomBar {
  x: string[]
  y: number[]
  sensor_type_id: number
  name: string
  unit: string
}

export interface DataCustomGauge {
  value: number
  value_raw: number
  max: number
}

export interface DataCustomLine {
  x: string[]
  y: number[]
  sensor_type_id: number
  name: string
  unit: string
}

export interface DataCustomScatter {
  x: { values: number[]; name: string; unit: string }
  y: { values: number[]; name: string; unit: string }
}

export interface CustomDashCreate {
  dashboard_name: string
  default_time_range: number
  default_kpi_time_range: number
}

export interface UserDashboard {
  dashboard_id: string
  dashboard_name: string
  owner_user_id: string
}

export interface Dashboard {
  dashboard_name: string
  default_time_range: string
  default_kpi_time_range: string
  components: DashboardComponent[]
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

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<UserDashboard[]>({
    axiosConfig,
    queryName: 'getUserDashboards',
    pathParams,
    queryParams: {},
    queryOptions: queryOptions,
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

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<Dashboard>({
    axiosConfig,
    queryName: 'getDashboard',
    pathParams,
    queryParams: {},
    queryOptions: queryOptions,
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
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<DataCustomBar>({
    axiosConfig,
    queryName: 'getBarData',
    pathParams,
    queryParams,
    queryOptions: queryOptions,
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
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<DataCustomGauge>({
    axiosConfig,
    queryName: 'getGaugeData',
    pathParams,
    queryParams,
    queryOptions: queryOptions,
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
    start?: string
    end?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/custom-dash/line`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<DataCustomLine[]>({
    axiosConfig,
    queryName: 'getLineData',
    pathParams,
    queryParams,
    queryOptions: queryOptions,
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
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<DataCustomScatter>({
    axiosConfig,
    queryName: 'getScatterData',
    pathParams,
    queryParams,
    queryOptions: queryOptions,
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
