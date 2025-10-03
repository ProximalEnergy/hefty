import { PVModule } from '@/api/v1/operational/pv_modules'
import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import { UseQueryOptions } from '@tanstack/react-query'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'

// --- Manufacturers ---
export const useGetCECPVModuleManufacturers = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/cec-pv-modules/manufacturers`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 1, // 1 minutes
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<string[]>({
    axiosConfig,
    queryName: 'cec-pv-module-manufacturers',
    pathParams: {},
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}

// --- Models ---
export const useGetCECPVModuleModels = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: { manufacturer?: string | null }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/cec-pv-modules/models`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 1, // 1 minutes
    enabled: !!queryParams?.manufacturer,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<string[]>({
    axiosConfig,
    queryName: `models-${queryParams.manufacturer}`,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}

// --- Get CEC Module IDs by Manufacturer and Model ---
export const useGetCECPVModuleIdsByManufacturerAndModel = ({
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
    url: `/v1/operational/cec-pv-modules/lookup-ids`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 1, // 1 minutes
    enabled:
      manufacturers.length > 0 &&
      models.length > 0 &&
      manufacturers.length === models.length,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<(number | null)[]>({
    axiosConfig,
    queryName: 'cec-pv-module-ids-lookup',
    pathParams: {},
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}

// --- Get CEC PV Module in Proximal Format ---
export const useGetCECPVModuleInProximalFormat = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: {
    cec_pv_module_id?: number | null
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const { cec_pv_module_id } = queryParams

  const axiosConfig = {
    url: `/v1/operational/cec-pv-modules/proximal-format`,
    method: 'GET',
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 1, // 10 seconds
    enabled: !!cec_pv_module_id,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<PVModule>({
    axiosConfig,
    queryName: `cec-module-proximal-${cec_pv_module_id}`,
    pathParams: {},
    queryParams: queryParams,
    queryOptions: queryOptions,
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
        url: `${baseURL}/v1/operational/cec-pv-modules`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: cleanModule,
      })
      return response.data as PVModule
    },
    onSuccess: () => {
      // Invalidate relevant queries to refetch data
      queryClient.invalidateQueries({
        queryKey: ['cec-pv-module-manufacturers'],
      })
      queryClient.invalidateQueries({ queryKey: ['cec-pv-module-ids-lookup'] })
      // Models queries are prefixed with manufacturer name, so we need to invalidate all of them
      queryClient.invalidateQueries({
        predicate: (query) =>
          typeof query.queryKey[0] === 'string' &&
          query.queryKey[0].startsWith('models-'),
      })
    },
  })
}
