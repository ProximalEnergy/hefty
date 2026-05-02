import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { QUERY_TIME } from '@/utils/queryTiming'
import { useAuth } from '@clerk/react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

export type DroneIntegration =
  types.components['schemas']['DroneIntegrationInterface']
type DroneIntegrationCreate =
  types.components['schemas']['DroneIntegrationCreate']
type DroneIntegrationUpdate =
  types.components['schemas']['DroneIntegrationUpdate']
export type DroneProvider =
  types.components['schemas']['DroneProviderInterface']
type DroneProviderCreate = types.components['schemas']['DroneProviderCreate']
type DroneProviderUpdate = types.components['schemas']['DroneProviderUpdate']
export type DronePermission =
  types.components['schemas']['DronePermissionInterface']
type DronePermissionCreate =
  types.components['schemas']['DronePermissionCreate']
type DronePermissionUpdate =
  types.components['schemas']['DronePermissionUpdate']
export type DroneInspection =
  types.components['schemas']['DroneInspectionInterface']
export type DroneAnomaly = types.components['schemas']['DroneAnomalyInterface']
export type ProviderSite = types.components['schemas']['ProviderSite']
type QueryProviderSitesRequest =
  types.components['schemas']['QueryProviderSitesRequest']
export type DroneInspectionOrderRequest =
  types.components['schemas']['DroneInspectionOrderRequest']

type DronePermissionUpdateRequest = DronePermissionUpdate & {
  drone_integration_id: number
  company_id: string
}

type DroneIntegrationUpdateRequest = DroneIntegrationUpdate & {
  drone_integration_id: number
}

type DroneProviderUpdateRequest = DroneProviderUpdate & {
  drone_provider_id: number
}

export const useGetDroneIntegrations = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
} = {}) => {
  const axiosConfig = {
    url: '/v1/operational/drone-integrations',
  }
  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.SIX_HOURS, // 6 hours
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
    url: '/v1/operational/drone-providers',
  }
  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.SIX_HOURS, // 6 hours
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
    mutationFn: async (newPermission: DronePermissionCreate) => {
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
    mutationFn: async (updatedPermission: DronePermissionUpdateRequest) => {
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
    url: '/v1/operational/drone-permissions',
  }
  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.SIX_HOURS, // 6 hours
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
    mutationFn: async (newIntegration: DroneIntegrationCreate) => {
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
    mutationFn: async (updatedIntegration: DroneIntegrationUpdateRequest) => {
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
    mutationFn: async ({ api_key, provider_id }: QueryProviderSitesRequest) => {
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
      newProvider: Omit<DroneProviderCreate, 'drone_provider_id'>,
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
    mutationFn: async (updatedProvider: DroneProviderUpdateRequest) => {
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
  const defaultQueryOptions = {}

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
  const defaultQueryOptions = {}
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
