import { PVModule } from '@/api/v1/operational/pv_modules'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

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
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 1, // 1 minutes
  }

  return useCustomQuery<string[]>({
    axiosConfig,
    queryName: 'cec-pv-module-manufacturers',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
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
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 1, // 1 minutes
    enabled: !!queryParams?.manufacturer,
  }

  return useCustomQuery<string[]>({
    axiosConfig,
    queryName: `models-${queryParams.manufacturer}`,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
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
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 1, // 1 minutes
    enabled:
      manufacturers.length > 0 &&
      models.length > 0 &&
      manufacturers.length === models.length,
  }

  return useCustomQuery<(number | null)[]>({
    axiosConfig,
    queryName: 'cec-pv-module-ids-lookup',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
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
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 1, // 10 seconds
    enabled: !!cec_pv_module_id,
  }

  return useCustomQuery<PVModule>({
    axiosConfig,
    queryName: `cec-module-proximal-${cec_pv_module_id}`,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
