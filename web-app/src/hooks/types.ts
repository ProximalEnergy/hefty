import { DeviceType } from '@/api/v1/operational/device_types'
import { KPIType } from '@/api/v1/operational/kpi_types'
import { SensorType } from '@/api/v1/operational/sensor_types'
import { ReactNode } from 'react'

export const statisticOptions = [
  { value: 'sum', label: 'Sum' },
  { value: 'mean', label: 'Mean' },
  { value: 'std', label: 'Standard Deviation' },
  { value: 'min', label: 'Minimum' },
  { value: 'max', label: 'Maximum' },
  { value: 'median', label: 'Median' },
  { value: 'count', label: 'Count' },
  { value: 'range', label: 'Range' },
  { value: 'available_data', label: 'Available Data' },
] as const

export type StatisticType = (typeof statisticOptions)[number]['value']
export type StatisticIcon =
  | 'events'
  | 'pcs'
  | 'temp'
  | 'soc'
  | 'soh'
  | 'availability'
  | 'performance'
  | 'project'

export interface Statistic {
  title: string
  description?: ReactNode
  value: ReactNode
  diff?: number
  icon: StatisticIcon
}

export interface UserSubscription {
  user_id: string
  operational_project_id: string
  notifications: boolean
  reports: boolean
}

export interface FeedbackFormData {
  subject: string
  url: string
  comment: string
}

export interface Point {
  type: string
  coordinates: number[]
}

export interface MultiPolygon {
  type: string
  coordinates: number[][][][]
}

interface DataType {
  data_type_id: number
  name_short: string
}

export interface Device {
  device_id: number
  device_type_id: number
  device_model_id: number | null
  parent_device_id: number | null
  logical: boolean
  name_short: string | null
  name_long: string | null
  capacity_dc: number | null
  capacity_ac: number | null
  point: Point | null
  polygon: MultiPolygon | null
  device_type?: DeviceType
  name_full?: string
  cec_pv_module_id?: number
  pv_module_id?: number
  device_id_path?: string
}

export interface Tag {
  tag_id: number
  device: Device
  device_id: number | null
  sensor_type: SensorType | null
  data_type: DataType | null
  name_short: string | null
  name_long: string | null
  name_scada: string
  scada_id: number | null
  scada_type: string | null
  unit_scada: string | null
  unit_offset: number | null
  unit_scale: number | null
  point: Point | null
  polygon: MultiPolygon | null
  sensor_type_id: number | null
}

export interface Event {
  event_id: number
  event_type_id: number | null
  device_id: number
  device: Device
  device_name_full: string
  time_start: string
  time_end: string | null
  time_detected: string
  time_last_analyzed: string | null
  failure_mode_id: number | null
  failure_mode: FailureMode | null
  root_cause_id: number | null
  loss_total_financial: number | null
  loss_daily_financial: number | null
}

export interface EventDeviceInfo {
  unique_types: {
    device_type_id: number
    device_type_name: string
  }[]
  unique_devices: {
    device_id: number
    device_name_full: string
  }[]
}

export interface PaginatedEvent {
  event_id: number
  device_name_full: string
  time_start: string
  time_end: string
  loss_daily_power: number
  loss_today_power: number
  loss_total_power: number
  loss_daily_financial: number
  loss_today_financial: number
  loss_total_financial: number
  root_cause: string
}

export interface EventSummary {
  event_id: number
  device_type_name: string
  device_name_full: string
  time_start: string
  time_end: string | null
  failure_mode: string
  root_cause: string | null
  loss_total_financial: number | null
  loss_total_energy: number | null
  loss_daily_financial: number | null
  loss_daily_energy: number | null
}

export interface UptimeData {
  device_id: number
  device_type_id: number
  device_name_full: string
  downtime_hours: number
  downtime_percentage: number
  events: number
}

export interface FailureMode {
  failure_mode_id: number
  device_type_id: number
  name_short: string
  name_long: string
}

export interface RootCause {
  root_cause_id: number
  device_type_id: number
  name_short: string
  name_long: string
  name_full?: string
}

export interface DataHeatmap {
  x: string[]
  y: string[]
  z: number[][]
}

export interface DataTimeSeries {
  x: string[]
  y: number[]
  y_range: number[]
  yaxis: string
  name: string
  sensor_type_name: string
  device_name_long: string
  tag_name_scada: string
  tag_name_long: string
  device_id: number
  sensor_type_id: number
}

export interface DegradationPOA {
  data: DataTimeSeries[]
  valid_indexes: string[]
  valid_columns: string[]
}

interface SettlementPoint {
  settlement_point_id: number
  name: string
  settlement_point_type_id: number
  load_zone_id: number
  trading_hub_id: number
}

interface QSE {
  qse_id: number
  name_short: string
  name_long: string
}

interface DME {
  dme_id: number
  name_short: string
  name_long: string
}

export interface Resource {
  resource_id: number
  name_gen: string
  name_load: string
  name_long: string
  county: string
  in_service: number
  capacity_power: number
  qse_id: number
  dme_id: number
  settlement_point_id: number
  qse: QSE | null
  dme: DME | null
  settlement_point: SettlementPoint | null
}

export interface WeatherResponse {
  coord: {
    lon: number
    lat: number
  }
  weather: Array<{
    id: number
    main: string
    description: string
    icon: string
  }>
  base: string
  main: {
    temp: number
    feels_like: number
    temp_min: number
    temp_max: number
    pressure: number
    humidity: number
    sea_level: number
    grnd_level: number
  }
  visibility: number
  wind: {
    speed: number
    deg: number
    gust: number
  }
  clouds: {
    all: number
  }
  dt: number
  sys: {
    sunrise: number
    sunset: number
  }
  timezone: number
  id: number
  name: string
  cod: number
}

export interface ForecastResponse {
  cod: string
  message: number
  cnt: number
  list: {
    dt: number
    main: {
      temp: number
      feels_like: number
      temp_min: number
      temp_max: number
      pressure: number
      sea_level: number
      grnd_level: number
      humidity: number
      temp_kf: number
    }
    weather: {
      id: number
      main: string
      description: string
      icon: string
    }[]
    clouds: {
      all: number
    }
    wind: {
      speed: number
      deg: number
      gust: number
    }
    visibility: number
    pop: number
    sys: {
      pod: string
    }
    dt_txt: string
  }[]
  city: {
    id: number
    name: string
    coord: {
      lat: number
      lon: number
    }
    country: string
    population: number
    timezone: number
    sunrise: number
    sunset: number
  }
}

export interface EquipmentAnalysisCombiner {
  x: string[]
  y: number[]
  y_norm: number[]
}

type QualityLevel = 'good' | 'warning' | 'bad'
type QualityItem = {
  level: QualityLevel
  message: string
}

export interface Quality extends QualityItem {
  details: QualityItem[]
}

export interface MeterPowerAndExpected {
  data: DataTimeSeries[]
  quality: Quality
}

// GIS
export interface GISPCS {
  as_of: string | null
  data: {
    [key: string]: {
      power: number | null
      power_exp: number | null
      power_norm_exp: number | null
      energy: number | null
      red_outline: boolean
    }
  }
}

export interface KPIInstanceProps {
  name_short: string
  name_long: string
  unit: string
  kpi_type_id: number
  description?: string
  aggregation_method: string
  device_type_id: number
}

interface alertProps {
  alert_name: string
  comparison: string | null
  duration_value: string | null
  kpi_type_id: string | null
  statistic: StatisticType | null
  notify: boolean
  threshold_value: number | null | string
  triggered: boolean | null
}

export interface KPIAlertProps {
  kpi_alert_id: number
  user_id: string
  project_id: string
  kpi_type_id: string
  config: alertProps
}

export interface SunburstProps {
  labels: string[]
  parents: string[]
  colors: string[]
  device_names: Record<string, number>
  hierarchy: Record<number, number[]>
}

interface ContractKPI {
  contract_id: number
  kpi_type_id: number
  threshold: {
    values: {
      [key: string]: number
    }
  } | null
  liquidated_damages: {
    [key: string]: unknown
  } | null
  claim_howto: {
    [key: string]: unknown
  } | null
  provider_responsible: boolean | null
}

export interface KPITypeWithContracts extends KPIType {
  contracts: ContractWithCompany[]
  contract_kpis: ContractKPI[]
}
export interface ContractWithCompany {
  contract_id: number
  project_id: string
  document_id: string
  company_id_provider: string
  company_id_counter: string
  execution_date: string
  name_long: string
  name_short: string
  document_url?: string
  s3_key: string | null
  counter_company?: string
}
