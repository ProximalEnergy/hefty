import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

const BESS_STRINGS_QUERY_NAME = 'bessStrings'

export interface BessStringSpec {
  bess_string_id: number
  company_id: string
  device_model_id: number

  configuration: string | null
  chemistry: string | null
  cells_in_series: number | null
  strings_in_parallel: number | null
  module_count: number | null

  nominal_energy_kwh: number | null
  nominal_power_kw: number | null
  charge_power_max_kw: number | null
  discharge_power_max_kw: number | null
  operating_voltage_min_v: number | null
  operating_voltage_max_v: number | null

  dimensions_width_mm: number | null
  dimensions_depth_mm: number | null
  dimensions_height_mm: number | null
  weight_kg: number | null

  bms_supply_voltage_vdc: number | null
  bms_cell_voltage_accuracy_mv: Record<string, unknown> | null
  bms_total_voltage_accuracy_pct: number | null
  bms_total_voltage_detection_min_v: number | null
  bms_total_voltage_detection_max_v: number | null
  bms_current_accuracy_pct: number | null
  bms_current_min_a: number | null
  bms_current_max_a: number | null
  bms_temperature_accuracy_c: Record<string, unknown> | null
  bms_soc_accuracy_pct: number | null
  bms_soc_accuracy_notes: string | null

  enclosure_rating_battery: string | null
  enclosure_rating_electrical: string | null
  anti_corrosion_rating: string | null

  operating_temp_min_c: number | null
  operating_temp_max_c: number | null
  storage_temp_min_c: number | null
  storage_temp_max_c: number | null
  relative_humidity_min_pct: number | null
  relative_humidity_max_pct: number | null
  altitude_max_m: number | null

  thermal_management_method: string | null
  auxiliary_power_phase: string | null
  auxiliary_power_ac_min_v: number | null
  auxiliary_power_ac_max_v: number | null
  auxiliary_power_frequency_hz: number[] | Record<string, unknown> | null

  charge_power_limit_map: Record<string, unknown> | null
  discharge_power_limit_map: Record<string, unknown> | null
  standards: string[] | Record<string, unknown> | null

  source_filename: string | null
  created_at: string | null
  updated_at: string | null
}

interface GetBessStringsParams {
  queryParams?: {
    bess_string_ids?: number[]
    device_model_ids?: number[]
  }
  queryOptions?: Partial<UseQueryOptions<BessStringSpec[]>>
}

export const useGetBessStrings = ({
  queryParams = {},
  queryOptions = {},
}: GetBessStringsParams = {}) => {
  const { bess_string_ids = [], device_model_ids = [] } = queryParams

  const axiosConfig = {
    url: `/v1/operational/bess-strings`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.ONE_MINUTE,
    enabled: bess_string_ids.length > 0 || device_model_ids.length > 0,
  }

  return useCustomQuery<BessStringSpec[]>({
    axiosConfig,
    queryName: BESS_STRINGS_QUERY_NAME,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
