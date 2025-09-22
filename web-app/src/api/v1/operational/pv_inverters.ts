import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  UseMutationOptions,
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

// Query Names
export const INVERTERS_QUERY_NAME = 'inverters'
export const INVERTER_MANUFACTURERS_QUERY_NAME = 'inverterManufacturers'
export const INVERTER_MODELS_QUERY_NAME = 'inverterModels'
export const INVERTER_IDS_QUERY_NAME = 'inverterIdsLookup'

// Interfaces
export interface Inverter {
  inverter_id: number | null
  company_id: string
  manufacturer: string
  model: string

  // Operating window parameters
  voltage_mpp_min: number
  voltage_mpp_max: number
  voltage_start_up: number
  voltage_min: number
  voltage_max: number
  current_max: number

  // Temperature-dependent power characteristics
  power_max_at_reference_temp: number[]
  reference_temp: number[]

  // Inverter efficiency reference parameters
  voltage_nominal_efficiency: number[]
  efficiency_at_low_voltage: number[][]
  efficiency_at_mid_voltage: number[][]
  efficiency_at_high_voltage: number[][]

  // Inverter efficiency parameters
  power_start_up: number
  power_ac_nominal: number
  power_dc_nominal: number
  voltage_dc_nominal: number
  c0: number
  c1: number
  c2: number
  c3: number
  night_tare: number
}

// Hook parameters
interface GetInvertersParams {
  queryParams?: {
    inverter_ids?: number[]
  }
  queryOptions?: Partial<UseQueryOptions>
}

interface GetInverterIdsByManufacturerAndModelParams {
  queryParams?: {
    manufacturers?: string[]
    models?: string[]
  }
  queryOptions?: Partial<UseQueryOptions>
}

// API Hooks
export const useGetInverters = ({
  queryParams = {},
  queryOptions = {},
}: GetInvertersParams) => {
  const { inverter_ids = [] } = queryParams

  const axiosConfig = {
    url: `/v1/operational/pv-inverters`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 1, // 1 minute
    enabled: inverter_ids.length > 0,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<Inverter[]>({
    axiosConfig,
    queryName: `${INVERTERS_QUERY_NAME}For${inverter_ids.join('-')}`,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}

export const useGetInverterIdsByManufacturerAndModel = ({
  queryParams = {},
  queryOptions = {},
}: GetInverterIdsByManufacturerAndModelParams) => {
  const { manufacturers = [], models = [] } = queryParams

  const axiosConfig = {
    url: `/v1/operational/pv-inverters/lookup-ids`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 1, // 1 minute
    enabled: manufacturers.length > 0 && models.length > 0,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<(number | null)[]>({
    axiosConfig,
    queryName: INVERTER_IDS_QUERY_NAME,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}

export const useGetProximalInverterManufacturers = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: { company_id?: string }
  queryOptions?: Partial<UseQueryOptions>
} = {}) => {
  const { company_id } = queryParams

  const axiosConfig = {
    url: `/v1/operational/pv-inverters/manufacturers`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 1, // 1 minute
    enabled: !!company_id,
  }

  queryOptions = {
    ...defaultQueryOptions,
    ...queryOptions,
    enabled: !!company_id && queryOptions.enabled !== false,
  }

  return useCustomQuery<string[]>({
    axiosConfig,
    queryName: `${INVERTER_MANUFACTURERS_QUERY_NAME}For${company_id || 'none'}`,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}

export const useGetProximalInverterModels = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: { manufacturer?: string | null; company_id?: string }
  queryOptions?: Partial<UseQueryOptions>
} = {}) => {
  const { manufacturer, company_id } = queryParams

  const axiosConfig = {
    url: `/v1/operational/pv-inverters/models`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 1, // 1 minute
    enabled: !!manufacturer && !!company_id,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<string[]>({
    axiosConfig,
    queryName: `${INVERTER_MODELS_QUERY_NAME}For${manufacturer || 'all'}Company${company_id || 'all'}`,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}

export const useCreateInverterMutation = (
  options?: UseMutationOptions<Inverter, Error, Inverter>,
) => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (inverter: Inverter) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        url: `${baseURL}/v1/operational/pv-inverters`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: inverter,
      })

      return response.data as Inverter
    },
    onSuccess: () => {
      // Invalidate relevant queries to refresh data
      queryClient.invalidateQueries({ queryKey: [INVERTERS_QUERY_NAME] })
      queryClient.invalidateQueries({ queryKey: [INVERTER_IDS_QUERY_NAME] })
      queryClient.invalidateQueries({
        queryKey: [INVERTER_MANUFACTURERS_QUERY_NAME],
      })
      // Models queries are prefixed with model name, so we need to invalidate all of them
      queryClient.invalidateQueries({
        predicate: (query) =>
          typeof query.queryKey[0] === 'string' &&
          query.queryKey[0].startsWith(INVERTER_MODELS_QUERY_NAME),
      })
    },
    ...options,
  })
}

export const useParseOndFileMutation = (
  options?: UseMutationOptions<Inverter, Error, File>,
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
        url: `${baseURL}/v1/operational/pv-inverters/parse-ond`,
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
