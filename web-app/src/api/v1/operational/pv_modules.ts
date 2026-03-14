import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/react'
import {
  UseMutationOptions,
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

const _COMPONENT_NAME = 'PVModule'
const URL = '/v1/operational/pv-modules'

export type PVModule = types.components['schemas'][typeof _COMPONENT_NAME]
type get = types.paths[typeof URL]['get']
type getQueryParams = get['parameters']['query']

export const useGetPvModules = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: getQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<PVModule[]>({
    axiosConfig,
    queryName: 'getPvModules',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetProximalPVModuleManufacturers = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/pv-modules/manufacturers`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 1, // 1 minutes
  }

  return useCustomQuery<string[]>({
    axiosConfig,
    queryName: 'pvModuleManufacturers',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetProximalPVModuleModels = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: { manufacturer?: string | null }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/pv-modules/models`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 1, // 1 minutes
    enabled: !!queryParams?.manufacturer,
  }

  return useCustomQuery<string[]>({
    axiosConfig,
    queryName: `modelsFor${queryParams.manufacturer}`,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetPVModuleIdsByManufacturerAndModel = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: {
    manufacturers?: string[]
    models?: string[]
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const { manufacturers = [], models = [] } = queryParams

  const axiosConfig = {
    url: `/v1/operational/pv-modules/lookup-ids`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 1, // 1 minutes
    enabled: manufacturers.length > 0 && models.length > 0,
  }

  return useCustomQuery<(number | null)[]>({
    axiosConfig,
    queryName: 'pvModuleIdsLookup',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetPVModuleDetails = ({
  queryParams = { pv_module_ids: [] },
  queryOptions = {},
}: {
  queryParams: {
    pv_module_ids: number[]
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/pv-modules`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 1, // 1 seconds
    enabled: queryParams.pv_module_ids.length > 0,
  }

  return useCustomQuery<PVModule[]>({
    axiosConfig,
    queryName: `moduleDetailsFor${queryParams.pv_module_ids.join('-')}`,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

// --- Create or Update PV Module using POST ---
export const useCreateOrUpdatePVModuleMutation = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (module: PVModule) => {
      const token = await getToken({ template: 'default' })

      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/operational/pv-modules`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: module,
      })

      return response.data as PVModule
    },
    onSuccess: () => {
      // Invalidate relevant queries to refetch data
      queryClient.invalidateQueries({ queryKey: ['pvModuleManufacturers'] })
      queryClient.invalidateQueries({ queryKey: ['pvModuleIdsLookup'] })
      // Models queries are prefixed with manufacturer name, so we need to invalidate all of them
      queryClient.invalidateQueries({
        predicate: (query) =>
          typeof query.queryKey[0] === 'string' &&
          query.queryKey[0].startsWith('modelsFor'),
      })
    },
  })
}

export interface PVModuleFromPAN {
  manufacturer: string
  model: string
  technology: string
  bifaciality_factor: number | null
  pmax: number
  isc: number
  voc: number
  imp: number
  vmp: number
  cells_in_series: number
  cells_in_parallel: number
  r_series: number
  r_shunt: number
  gamma_pmax: number
  alpha_isc: number
  beta_voc: number
  width: number
  length: number
  eg: number
  degdt: number
  photocurrent: number
  diode_saturation_current: number
  modified_ideality_factor: number
}

export const useParsePANfileMutation = (
  options?: UseMutationOptions<PVModuleFromPAN, Error, File>,
) => {
  const { getToken } = useAuth()

  return useMutation({
    mutationFn: async (file: File) => {
      const token = await getToken({ template: 'default' })

      // Form Data
      const formData = new FormData()
      formData.append('file', file)

      // Response
      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/operational/pv-modules/parse-pan`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
        data: formData,
        withCredentials: true, // Add credentials for CORS
      })

      return response.data
    },
    ...options,
  })
}
