import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import React from 'react'

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

export interface SiteInfo {
  site_uuid: string
  site_id: number
  site_name: string
  site_capacity_mw: number
}

export interface Grade {
  site_impact_category: string
  grade: string
  power_loss_kw: number
  power_loss_percent: number
  affected_modules: number
  affected_modules_percent: number
}

export interface ZeitviewObservation {
  description: string
}

export interface ZeitviewInspection {
  inspection_uuid: string
  inspection_date: string
  upload_date: string
  site: SiteInfo
  service_tier?: string
  total_power_loss_kw?: number
  total_power_loss_percent?: number
  total_affected_modules?: number
  grades: Grade[]
  observations: ZeitviewObservation[]
  report_summary?: string
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

export const useGetDroneIntegrations = () => {
  const axiosConfig = {
    url: 'v1/operational/drone-integrations',
  }

  return useCustomQuery<DroneIntegration[]>({
    axiosConfig,
    queryName: 'getDroneIntegrations',
  })
}

export const useGetDroneProviders = () => {
  const axiosConfig = {
    url: 'v1/operational/drone-providers',
  }

  return useCustomQuery<DroneProvider[]>({
    axiosConfig,
    queryName: 'getDroneProviders',
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

export const useGetDronePermissions = () => {
  const axiosConfig = {
    url: 'v1/operational/drone-permissions',
  }

  return useCustomQuery<DronePermission[]>({
    axiosConfig,
    queryName: 'getDronePermissions',
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

export const useGetDroneInspections = (projectId?: string) => {
  const axiosConfig = {
    url: `v1/operational/projects/${projectId}/drone-inspections`,
  }
  return useCustomQuery<DroneInspection[]>({
    axiosConfig,
    queryName: `getDroneInspections-${projectId}`,
    queryOptions: {
      enabled: !!projectId,
    },
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

export const useGetDroneAnomalies = (
  projectId?: string,
  inspectionId?: string,
) => {
  const axiosConfig = {
    url: `v1/operational/projects/${projectId}/drone-inspections/${inspectionId}/anomalies`,
  }
  return useCustomQuery<DroneAnomaly[]>({
    axiosConfig,
    queryName: `getDroneAnomalies-${inspectionId}`,
    queryOptions: {
      enabled: !!projectId && !!inspectionId,
    },
  })
}

export const useGetDroneAnomaliesWithBounds = (
  projectId?: string,
  inspectionId?: string,
  bounds?: {
    minLat: number
    maxLat: number
    minLon: number
    maxLon: number
  },
) => {
  const axiosConfig = {
    url: `v1/operational/projects/${projectId}/drone-inspections/${inspectionId}/anomalies`,
  }

  const queryParams = bounds
    ? {
        min_lat: bounds.minLat,
        max_lat: bounds.maxLat,
        min_lon: bounds.minLon,
        max_lon: bounds.maxLon,
      }
    : {}

  const queryResult = useCustomQuery<DroneAnomaly[]>({
    axiosConfig,
    queryName: `getDroneAnomaliesWithBounds-${inspectionId}-${JSON.stringify(bounds)}`,
    queryParams: queryParams,
    queryOptions: {
      enabled: !!projectId && !!inspectionId,
    },
  })

  // Add timing debug for the API call
  React.useEffect(() => {
    if (queryResult.data) {
    }
  }, [queryResult.data, bounds])

  return queryResult
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
        queryKey: [`getDroneAnomalies-${inspectionId}`],
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
