import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import { UseQueryOptions } from '@tanstack/react-query'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'

/**
 * Interface for PV Rackings data
 */
export interface PVRackings {
  racking_id: number | null
  racking_type_id: number
  manufacturer: string
  model: string
  company_id?: string
  max_rotation_angle: number
  min_rotation_angle: number
  wind_stow_angle: number
  wind_stow_threshold: number
  hail_stow_angle: number
  snow_stow_angle: number
}

// --- Manufacturers ---
export const useGetProximalPVRackManufacturers = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: { company_id?: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/pv-rackings/manufacturers`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 1, // 1 minutes
  }

  return useCustomQuery<string[]>({
    axiosConfig,
    queryName: 'pvRackingManufacturers',
    pathParams: {},
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

// --- Models ---
export const useGetProximalPVRackModels = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: { manufacturer?: string | null; company_id?: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/pv-rackings/models`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 1, // 1 minutes
    enabled: !!queryParams?.manufacturer,
  }

  return useCustomQuery<string[]>({
    axiosConfig,
    queryName: `modelsFor${queryParams.manufacturer}`,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

// --- Get Racking IDs by Manufacturer and Model ---
export const useGetPVRackingIdsByManufacturerAndModel = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: {
    manufacturers?: string[]
    models?: string[]
    company_id?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const { manufacturers = [], models = [] } = queryParams

  const axiosConfig = {
    url: `/v1/operational/pv-rackings/lookup-ids`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 1, // 1 minutes
    enabled: manufacturers.length > 0 && models.length > 0,
  }

  return useCustomQuery<(number | null)[]>({
    axiosConfig,
    queryName: 'pvRackingIdsLookup',
    pathParams: {},
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

// --- Rack Details by ID ---
export const useGetProximalPVRackDetails = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: {
    racking_ids?: number[]
    company_id?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const { racking_ids = [] } = queryParams

  const axiosConfig = {
    url: `/v1/operational/pv-rackings`,
    method: 'GET',
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 10, // 10 seconds
    enabled: racking_ids.length > 0,
  }

  return useCustomQuery<PVRackings[]>({
    axiosConfig,
    queryName: `rackDetailsFor${racking_ids.join('-')}`,
    pathParams: {},
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

// --- Create or Update PV Racking using POST ---
export const useCreateOrUpdatePVRackingMutation = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (racking: PVRackings) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/operational/pv-rackings`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: racking,
      })
      return response.data as PVRackings
    },
    onSuccess: () => {
      // Invalidate relevant queries to refetch data
      queryClient.invalidateQueries({ queryKey: ['pvRackingManufacturers'] })
      queryClient.invalidateQueries({ queryKey: ['pvRackingIdsLookup'] })
      // Models queries are prefixed with manufacturer name, so we need to invalidate all of them
      queryClient.invalidateQueries({
        predicate: (query) =>
          typeof query.queryKey[0] === 'string' &&
          query.queryKey[0].startsWith('modelsFor'),
      })
    },
  })
}
