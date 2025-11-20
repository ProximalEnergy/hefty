import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import { UseQueryOptions } from '@tanstack/react-query'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'

export interface DroneIntegration {
  drone_integration_id: number
  project_id: string
  drone_provider_id: number
  provider_project_id: string
}

export interface DroneProvider {
  drone_provider_id: number
  name_short: string
  name_long: string
}

export interface DronePermission {
  drone_integration_id: number
  company_id: string
  can_view: boolean
}

export interface DroneInspection {
  inspection_uuid: string
  inspection_time: string
  upload_time: string
  service_tier?: string
  total_power_loss_kw?: number
  total_power_loss_percent?: number
  total_affected_modules?: number
  report_summary?: string
}

export interface ProviderSite {
  site_name: string | null
  site_uuid: string
  site_id: number | null
}

export interface DroneAnomaly {
  anomaly_uuid: string
  inspection_uuid: string
  event_id?: number
  stack_id?: string
  ir_signal?: string
  rgb_signal?: string
  ir_image_url?: string
  rgb_image_url?: string
  subsystem?: string
  remediation_category?: string
  energy_loss_weighting?: number
  power_loss_kw?: number
  location_lat?: number
  location_lon?: number
  client_status_id?: number
}

export const useGetDroneIntegrations = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
} = {}) => {
  const axiosConfig = {
    url: 'v1/operational/drone-integrations',
  }
  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 60 * 6, // 6 hours
  }

  return useCustomQuery<DroneIntegration[]>({
    axiosConfig,
    queryName: 'getDroneIntegrations',
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetDroneProviders = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
} = {}) => {
  const axiosConfig = {
    url: 'v1/operational/drone-providers',
  }
  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 60 * 6, // 6 hours
  }

  return useCustomQuery<DroneProvider[]>({
    axiosConfig,
    queryName: 'getDroneProviders',
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useCreateDronePermission = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (newPermission: DronePermission) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/operational/drone-permissions`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: newPermission,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getDronePermissions'] })
    },
  })
}

export const useUpdateDronePermission = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (updatedPermission: DronePermission) => {
      const token = await getToken({ template: 'default' })
      const { drone_integration_id, company_id, ...rest } = updatedPermission
      const response = await axios({
        method: 'put',
        url: `${baseURL}/v1/operational/drone-permissions/${drone_integration_id}/${company_id}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: rest,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getDronePermissions'] })
    },
  })
}

export const useDeleteDronePermission = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (permission: DronePermission) => {
      const token = await getToken({ template: 'default' })
      const { drone_integration_id, company_id } = permission
      const response = await axios({
        method: 'delete',
        url: `${baseURL}/v1/operational/drone-permissions/${drone_integration_id}/${company_id}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getDronePermissions'] })
    },
  })
}

export const useGetDronePermissions = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
} = {}) => {
  const axiosConfig = {
    url: 'v1/operational/drone-permissions',
  }
  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 60 * 6, // 6 hours
  }

  return useCustomQuery<DronePermission[]>({
    axiosConfig,
    queryName: 'getDronePermissions',
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useCreateDroneIntegration = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (
      newIntegration: Omit<DroneIntegration, 'drone_integration_id'>,
    ) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/operational/drone-integrations`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: newIntegration,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getDroneIntegrations'] })
    },
  })
}

export const useUpdateDroneIntegration = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (updatedIntegration: DroneIntegration) => {
      const token = await getToken({ template: 'default' })
      const { drone_integration_id, ...rest } = updatedIntegration
      const response = await axios({
        method: 'put',
        url: `${baseURL}/v1/operational/drone-integrations/${drone_integration_id}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: rest,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getDroneIntegrations'] })
    },
  })
}

export const useQueryProviderSites = () => {
  const { getToken } = useAuth()

  return useMutation({
    mutationFn: async ({
      api_key,
      provider_id,
    }: {
      api_key: string
      provider_id: number
    }) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/operational/drone-integrations/query-provider-sites`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: { api_key, provider_id },
      })
      return response.data as ProviderSite[]
    },
  })
}

export const useDeleteDroneIntegration = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (drone_integration_id: number) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'delete',
        url: `${baseURL}/v1/operational/drone-integrations/${drone_integration_id}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getDroneIntegrations'] })
    },
  })
}

export const useCreateDroneProvider = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (
      newProvider: Omit<DroneProvider, 'drone_provider_id'>,
    ) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/operational/drone-providers`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: newProvider,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getDroneProviders'] })
    },
  })
}

export const useUpdateDroneProvider = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (updatedProvider: DroneProvider) => {
      const token = await getToken({ template: 'default' })
      const { drone_provider_id, ...rest } = updatedProvider
      const response = await axios({
        method: 'put',
        url: `${baseURL}/v1/operational/drone-providers/${drone_provider_id}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: rest,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getDroneProviders'] })
    },
  })
}

export const useDeleteDroneProvider = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (drone_provider_id: number) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'delete',
        url: `${baseURL}/v1/operational/drone-providers/${drone_provider_id}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getDroneProviders'] })
    },
  })
}

export const useGetDroneInspections = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `v1/operational/projects/${pathParams.projectId}/drone-inspections`,
  }
  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<DroneInspection[]>({
    axiosConfig,
    queryName: `getDroneInspections-${pathParams.projectId}`,
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useSyncZeitviewInspections = (
  projectId?: string,
  options = {},
) => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: async () => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'get',
        url: `${baseURL}/v1/operational/projects/${projectId}/drone-inspections/zeitview`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [`getDroneInspections-${projectId}`],
      })
    },
    ...options,
  })

  return {
    ...mutation,
    refetch: mutation.mutateAsync,
    isFetching: mutation.isPending,
  }
}

export const useGetDroneAnomalies = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string; inspectionId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `v1/operational/projects/${pathParams.projectId}/drone-inspections/${pathParams.inspectionId}/anomalies`,
  }
  const defaultQueryOptions: Partial<UseQueryOptions> = {}
  return useCustomQuery<DroneAnomaly[]>({
    axiosConfig,
    queryName: `getDroneAnomalies-${pathParams.projectId}-${pathParams.inspectionId}`,
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useSyncZeitviewAnomalies = (
  projectId?: string,
  inspectionId?: string,
  options = {},
) => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: async () => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/operational/projects/${projectId}/drone-inspections/${inspectionId}/anomalies/zeitview`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [`getDroneAnomalies-${projectId}-${inspectionId}`],
      })
    },
    ...options,
  })

  return {
    ...mutation,
    refetch: mutation.mutateAsync,
    isFetching: mutation.isPending,
  }
}

export interface DroneInspectionOrderRequest {
  project_id: string
  provider_email: string
  timing: string
}

export const useOrderDroneInspection = () => {
  const { getToken } = useAuth()

  return useMutation({
    mutationFn: async (request: DroneInspectionOrderRequest) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/operational/drone-integrations/order-inspection`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: request,
      })
      return response.data
    },
  })
}
