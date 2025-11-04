import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import { UseMutationOptions, UseQueryOptions } from '@tanstack/react-query'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'

/**
 * Interface for PV Module data
 */
export interface PVModule {
  company_id: string | undefined
  pv_module_id: number | number[] | null
  manufacturer: string
  model: string
  technology: string
  bifaciality_factor: number
  pmax: number
  isc: number
  voc: number
  imp: number
  vmp: number
  gamma_pmax: number
  alpha_isc_relative: number | null | string
  beta_voc_relative: number | null | string
  alpha_isc: number | null | string
  beta_voc: number | null | string
  warranted_degradation_rate: number
  warranted_degradation_initial: number
  length: number
  width: number
  frame_overhang: number
  has_ar_coating: boolean
  cells_in_series: number
  cells_in_parallel: number
  photocurrent: number
  diode_saturation_current: number
  r_series: number
  r_shunt: number
  modified_ideality_factor: number
  eg: number
  degdt: number
  data_source: string
  family: string
  half_cut: boolean
}

// --- Manufacturers ---
export const useGetProximalPVModuleManufacturers = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/pv-modules/manufacturers`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 1, // 1 minutes
  }

  return useCustomQuery<string[]>({
    axiosConfig,
    queryName: 'pvModuleManufacturers',
    pathParams: {},
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

// --- Models ---
export const useGetProximalPVModuleModels = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: { manufacturer?: string | null }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/pv-modules/models`,
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

// --- Get Module IDs by Manufacturer and Model ---
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
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 1, // 1 minutes
    enabled: manufacturers.length > 0 && models.length > 0,
  }

  return useCustomQuery<(number | null)[]>({
    axiosConfig,
    queryName: 'pvModuleIdsLookup',
    pathParams: {},
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

// --- Module Details by ID ---
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
    method: 'GET',
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 1, // 1 seconds
    enabled: queryParams.pv_module_ids.length > 0,
  }

  return useCustomQuery<PVModule[]>({
    axiosConfig,
    queryName: `moduleDetailsFor${queryParams.pv_module_ids.join('-')}`,
    pathParams: {},
    queryParams: queryParams,
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

      // Clean up data - convert empty strings to null
      const cleanModule = { ...module }

      // Convert empty strings to null for temperature coefficients
      if (cleanModule.alpha_isc_relative === '')
        cleanModule.alpha_isc_relative = null
      if (cleanModule.beta_voc_relative === '')
        cleanModule.beta_voc_relative = null
      if (cleanModule.alpha_isc === '') cleanModule.alpha_isc = null
      if (cleanModule.beta_voc === '') cleanModule.beta_voc = null

      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/operational/pv-modules`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: cleanModule,
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
