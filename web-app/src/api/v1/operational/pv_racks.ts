import type { components } from '@/api/schema'
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

/**
 * Interface for PV Rackings data
 */
export type PVRackings = components['schemas']['PVRackings']

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
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.ONE_MINUTE, // 1 minutes
  }

  return useCustomQuery<string[]>({
    axiosConfig,
    queryName: 'pvRackingManufacturers',
    queryParams,
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
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.ONE_MINUTE, // 1 minutes
    enabled: !!queryParams?.manufacturer,
  }

  return useCustomQuery<string[]>({
    axiosConfig,
    queryName: `modelsFor${queryParams.manufacturer}`,
    queryParams,
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
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.ONE_MINUTE, // 1 minutes
    enabled: manufacturers.length > 0 && models.length > 0,
  }

  return useCustomQuery<(number | null)[]>({
    axiosConfig,
    queryName: 'pvRackingIdsLookup',
    queryParams,
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
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.TEN_SECONDS, // 10 seconds
    enabled: racking_ids.length > 0,
  }

  return useCustomQuery<PVRackings[]>({
    axiosConfig,
    queryName: `rackDetailsFor${racking_ids.join('-')}`,
    queryParams,
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
