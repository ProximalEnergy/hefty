import type { operations } from '@/api/schema'
import { KPIType } from '@/api/v1/operational/kpi_types'
import type { Device } from '@/hooks/devices'
import type { Tag } from '@/hooks/projectTags'
import type {
  DataHeatmap,
  DataTimeSeries,
  DegradationPOA,
  Event,
  ForecastResponse,
  PaginatedEvent,
  Resource,
  RootCause,
  SunburstProps,
  UptimeData,
  UserSubscription,
  WeatherResponse,
} from '@/hooks/types'
import { baseURL } from '@/urlConfig'
import {
  QUERY_TIME,
  withDevRefetchInterval,
  withDevStaleTime,
} from '@/utils/queryTiming'
import { useAuth } from '@clerk/react'
import {
  UseQueryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { Table, tableFromIPC } from 'apache-arrow'
import axios, { AxiosHeaders, AxiosRequestConfig } from 'axios'
import { FeatureCollection } from 'geojson'
import qs from 'qs'

// Add request interceptor to include current page URL (backend only).
// Skip for third-party origins (e.g. NOAA) so CORS preflight succeeds.
axios.interceptors.request.use((config) => {
  if (typeof window === 'undefined') return config
  const url = String(config.url ?? '')
  if (url.includes('mapservices.weather.noaa.gov')) return config
  config.headers = AxiosHeaders.from(config.headers)
  config.headers.set('X-Client-Page-URL', window.location.href)
  return config
})

type PathParams = Record<string, string | number | boolean | null | undefined>
type GetProjectTagsParams =
  operations['get_project_tags_v1_operational_projects__project_id__tags__get']['parameters']['query']

function interpolatePath(url: string, pathParams: object): string {
  if (!pathParams || Object.keys(pathParams).length === 0) return url

  const params = pathParams as PathParams

  return url.replace(/{([^}]+)}/g, (_match, key) => {
    const value = params[key as keyof PathParams]
    if (value === undefined || value === null) {
      throw new Error(`Missing path param "${key}" for URL "${url}"`)
    }
    return encodeURIComponent(String(value))
  })
}

type AxiosRequestConfigWithoutParams = AxiosRequestConfig & { params?: never }

type QueryOptionsWithTiming = {
  staleTime?: unknown
  refetchInterval?: unknown
}

const applyDevQueryTimingFloor = <T extends object>(queryOptions: T): T => {
  const normalized = { ...queryOptions } as T & QueryOptionsWithTiming

  if (typeof normalized.staleTime === 'number') {
    normalized.staleTime = withDevStaleTime(normalized.staleTime)
  }

  if (
    typeof normalized.refetchInterval === 'number' ||
    normalized.refetchInterval === false
  ) {
    normalized.refetchInterval = withDevRefetchInterval(
      normalized.refetchInterval,
    )
  }

  return normalized
}

export const useCustomQuery = <T>({
  axiosConfig,
  queryName,
  pathParams = {},
  queryParams = {},
  queryOptions = {},
}: {
  axiosConfig: AxiosRequestConfigWithoutParams
  queryName: string
  pathParams?: object
  queryParams?: object
  queryOptions?: object
}) => {
  const { getToken } = useAuth()
  const normalizedQueryOptions = applyDevQueryTimingFloor(queryOptions)

  const queryKey: unknown[] = [queryName]

  // If pathParams is not empty, add it to queryKey
  if (Object.keys(pathParams).length !== 0) {
    queryKey.push(pathParams)
  }

  // If queryParams is not empty, add it to queryKey
  if (Object.keys(queryParams).length !== 0) {
    queryKey.push(queryParams)
  }

  const queryFn = async (): Promise<T> => {
    const token = await getToken({ template: 'default' })

    const url =
      axiosConfig.url != null
        ? interpolatePath(axiosConfig.url, pathParams)
        : undefined

    const response = await axios({
      ...axiosConfig,
      url,
      baseURL: baseURL,
      headers: {
        Authorization: `Bearer ${token}`,
      },
      params: queryParams, // Add this line to pass query parameters
      paramsSerializer: (params) => {
        return qs.stringify(params, { arrayFormat: 'repeat' })
      },
    })
    return response.data
  }

  return useQuery({
    queryKey: queryKey,
    queryFn: () => queryFn(),
    ...normalizedQueryOptions,
  })
}

export const useCustomQueryArrow = ({
  axiosConfig,
  queryName,
  pathParams = {},
  queryParams = {},
  queryOptions = {},
}: {
  axiosConfig: AxiosRequestConfig
  queryName: string
  pathParams?: object
  queryParams?: object
  queryOptions?: object
}) => {
  const { getToken } = useAuth()
  const normalizedQueryOptions = applyDevQueryTimingFloor(queryOptions)

  const queryKey: unknown[] = [queryName]

  if (Object.keys(pathParams).length !== 0) {
    queryKey.push(pathParams)
  }

  if (Object.keys(queryParams).length !== 0) {
    queryKey.push(queryParams)
  }

  const queryFn = async (): Promise<Table | null> => {
    const token = await getToken({ template: 'default' })
    const response = await axios({
      ...axiosConfig,
      baseURL: baseURL,
      headers: {
        Authorization: `Bearer ${token}`,
      },
      responseType: 'arraybuffer',
      params: queryParams,
      paramsSerializer: (params) => {
        return qs.stringify(params, { arrayFormat: 'repeat' })
      },
    })
    if (response.data.byteLength < 16) {
      return null
    }
    return tableFromIPC(response.data)
  }

  return useQuery({
    queryKey: queryKey,
    queryFn: () => queryFn(),
    ...normalizedQueryOptions,
  })
}

export const useCreateFeedbackMutation = () => {
  const { getToken } = useAuth()
  return useMutation({
    mutationFn: async (feedback: FormData) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'post',
        url: `${baseURL}/v1/feedback`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: feedback,
      })
    },
  })
}

export const useUpdateReportSubscription = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      project_id,
      subscribe,
    }: {
      project_id: string
      subscribe: boolean
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'put',
        url: `${baseURL}/v1/admin/subscriptions/reports/${project_id}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          subscribe,
        },
      })
    },
    onMutate: async (newSubscription) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['getSubscriptions'] })

      // Snapshot the previous value
      const previousSubscriptions = queryClient.getQueryData<
        UserSubscription[]
      >(['getSubscriptions'])

      // Optimistically update the new value
      queryClient.setQueryData(
        ['getSubscriptions'],
        (oldSubscriptions: UserSubscription[]) => {
          return oldSubscriptions?.map((subscription) => {
            if (
              subscription.operational_project_id === newSubscription.project_id
            ) {
              return {
                ...subscription,
                reports: newSubscription.subscribe,
              }
            }
            return subscription
          })
        },
      )

      // Return a context object with the snapshotted value
      return { previousSubscriptions }
    },
    onError: (_err, _newSubscription, context) => {
      queryClient.setQueryData(
        ['getSubscriptions'],
        context?.previousSubscriptions,
      )
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['getSubscriptions'] })
    },
  })
}

export const useGetDevice = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string; deviceId: string }
  queryParams?: { deep?: boolean }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url:
      `/v1/operational/projects/${pathParams.projectId}` +
      `/devices/${pathParams.deviceId}`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  return useCustomQuery<Device>({
    axiosConfig,
    queryName: 'getDevice',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

// V2 devices endpoint with POST support and pagination
export const useGetDevicesV2 = ({
  pathParams,
  filters,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  filters: {
    device_ids?: number[]
    device_type_ids?: number[]
    parent_device_ids?: (number | null)[]
    name_short?: string
    name_long?: string
    device_id_descendent_of?: number | null
    deep?: boolean
    with_tags?: boolean
    limit?: number | null
    offset?: number
    format?: string
    fields?: string[]
  }
  queryOptions?: Partial<UseQueryOptions<Device[]>>
}) => {
  const { getToken } = useAuth()

  const queryKey = ['getDevicesV2', pathParams, filters]

  const queryFn = async (): Promise<Device[]> => {
    const token = await getToken({ template: 'default' })
    const response = await axios({
      method: 'post',
      url: `${baseURL}/v1/operational/projects/${pathParams.projectId}/devices`,
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      data: filters,
    })
    return response.data
  }

  return useQuery({
    queryKey: queryKey,
    queryFn: queryFn,
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
    ...queryOptions,
  })
}

export const useUpdateDeviceSerialNumber = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      projectId,
      deviceId,
      serialNumber,
    }: {
      projectId: string
      deviceId: number
      serialNumber: string | null
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'patch',
        url: `${baseURL}/v1/operational/projects/${projectId}/devices/${deviceId}`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data: {
          serial_number: serialNumber,
        },
      })
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['getDevice'] })
      queryClient.invalidateQueries({ queryKey: ['getDevicesV2'] })
      queryClient.invalidateQueries({
        queryKey: [
          'getDevice',
          { projectId: variables.projectId, deviceId: variables.deviceId },
        ],
      })
    },
  })
}

export const useGetTags = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: GetProjectTagsParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/tags/`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  return useCustomQuery<Tag[]>({
    axiosConfig,
    queryName: 'getTags',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetEvents = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    device_ids?: number[]
    open?: boolean
    event_ids?: number[]
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/events`,
  }

  const defaultQueryOptions = {}

  return useCustomQuery<Event[]>({
    axiosConfig,
    queryName: 'getEvents',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetPaginatedEvents = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    page?: number
    page_size?: number
    open?: boolean
    sort_column?: string
    sort_direction?: string
    device_type_ids?: number[]
    device_ids?: number[]
    start?: string
    end?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/events/paginated-events`,
  }

  const defaultQueryOptions = {}

  return useCustomQuery<PaginatedEvent[]>({
    axiosConfig,
    queryName: 'getPaginatedEvents',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetUptimeTable = ({
  pathParams,
  queryParams = {
    start: '',
    end: '',
    project_id: '',
  },
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    start: string
    end: string
    project_id: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/events/uptime`,
  }

  const defaultQueryOptions = {}

  return useCustomQuery<UptimeData[]>({
    axiosConfig,
    queryName: 'getUptimeTable',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useUpdateRootCause = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      project_id,
      event_id,
      root_cause_id,
    }: {
      project_id: string
      event_id: number
      root_cause_id?: number
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'put',
        url:
          `${baseURL}/v1/operational/projects/` +
          `${project_id}/events/${event_id}/root-cause`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          root_cause_id: root_cause_id ?? -1,
        },
      })
    },
    onMutate: async (newRootCause) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['getRootCauses'] })
      await queryClient.cancelQueries({ queryKey: ['getEvents'] })

      // Snapshot the previous values
      const previousRootCauses = queryClient.getQueryData<RootCause[]>([
        'getRootCauses',
      ])
      const previousEvents = queryClient.getQueriesData({
        queryKey: ['getEvents'],
      })

      // Optimistically update the root causes
      queryClient.setQueryData(
        ['getRootCauses'],
        (oldRootCauses: RootCause[]) => {
          return oldRootCauses?.map((rootCause) => {
            if (rootCause.root_cause_id === newRootCause.root_cause_id) {
              return {
                ...rootCause,
                root_cause_id: newRootCause.root_cause_id,
              }
            }
            return rootCause
          })
        },
      )

      // Optimistically update the events data
      queryClient.setQueriesData(
        { queryKey: ['getEvents'] },
        (oldEvents: Event[] | undefined) => {
          if (!oldEvents) return oldEvents
          return oldEvents.map((event) => {
            if (event.event_id === newRootCause.event_id) {
              return {
                ...event,
                root_cause_id: newRootCause.root_cause_id,
              }
            }
            return event
          })
        },
      )

      return { previousRootCauses, previousEvents }
    },
    onError: (_err, _newRootCause, context) => {
      queryClient.setQueryData(['getRootCauses'], context?.previousRootCauses)
      // Restore previous events data
      if (context?.previousEvents) {
        context.previousEvents.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data)
        })
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['getRootCauses'] })
      queryClient.invalidateQueries({ queryKey: ['getEvents'] })
    },
  })
}

export const useGetWeather = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/gis/${pathParams.projectId}/project-weather`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.FIFTEEN_MINUTES, // 15 minutes
  }

  return useCustomQuery<WeatherResponse>({
    axiosConfig,
    queryName: 'getWeather',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetForecast = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/gis/${pathParams.projectId}/project-weather-forecast`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.FIFTEEN_MINUTES, // 15 minutes
  }

  return useCustomQuery<ForecastResponse>({
    axiosConfig,
    queryName: 'getForecast',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetHeatmap = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string; sensorTypeName: string }
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url:
      `/v1/protected/web-application/projects/${pathParams.projectId}` +
      `/equipment-analysis/heatmap/${pathParams.sensorTypeName}`,
  }

  const defaultQueryOptions = {}

  return useCustomQuery<DataHeatmap>({
    axiosConfig,
    queryName: 'getHeatmap',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetGISTrackerByBlock = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string; blockId: string }
  queryParams?: {
    start?: string
    end?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/gis/${pathParams.projectId}/tracker-by-block/${pathParams.blockId}`,
  }

  const defaultQueryOptions = {
    staleTime: QUERY_TIME.FIVE_MINUTES,
    refetchOnWindowFocus: false,
  }

  return useCustomQuery<FeatureCollection>({
    axiosConfig,
    queryName: 'getGISTrackerByBlock',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetGISBessEnclosure = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/gis/${pathParams.projectId}/bess-enclosure`,
  }

  const defaultQueryOptions = {}

  return useCustomQuery<FeatureCollection>({
    axiosConfig,
    queryName: 'getGISBessEnclosure',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetResources = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: '/v1/development/ercot/resources',
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  return useCustomQuery<Resource[]>({
    axiosConfig,
    queryName: 'getResources',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetResource = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { resourceId: string }
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/development/ercot/resources/${pathParams.resourceId}`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  return useCustomQuery<Resource>({
    axiosConfig,
    queryName: 'getResource',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetResourceNetPower = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { resourceId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/development/ercot/resources/${pathParams.resourceId}/net-power`,
  }

  const defaultQueryOptions = {}

  return useCustomQuery<DataTimeSeries[]>({
    axiosConfig,
    queryName: 'getResourceNetPower',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetKPIType = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { kpiTypeId: number }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/kpi-types/${pathParams.kpiTypeId}`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  return useCustomQuery<KPIType>({
    axiosConfig,
    queryName: 'getKPIType',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetSunburstData = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url:
      `/v1/protected/web-application/projects/${pathParams.projectId}` +
      '/equipment-analysis/sunburst-data',
  }

  const defaultQueryOptions = {
    staleTime: QUERY_TIME.FIVE_MINUTES,
  }

  return useCustomQuery<SunburstProps>({
    axiosConfig,
    queryName: 'getSunburstData',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetDegradationPOA = ({
  pathParams,
  queryOptions = {},
  queryParams = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
  queryParams?: {
    start?: string
    end?: string
  }
}) => {
  const axiosConfig = {
    url:
      `/v1/protected/web-application/projects/` +
      `${pathParams.projectId}/reports/degradation-poa`,
  }
  const defaultQueryOptions = {
    staleTime: QUERY_TIME.FIVE_MINUTES,
  }

  return useCustomQuery<DegradationPOA>({
    axiosConfig,
    queryName: 'getDegradationPOA',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useAnalyzeCombinerSwaps = () => {
  const { getToken } = useAuth()

  return useMutation({
    mutationFn: async ({
      projectId,
      analysisDate,
      blockNames,
    }: {
      projectId: string
      analysisDate?: string
      blockNames?: string[]
    }) => {
      const token = await getToken({ template: 'default' })

      // Convert parameters to query string
      const params = new URLSearchParams({
        ...(analysisDate && { analysis_date: analysisDate }),
        ...(blockNames?.length && { block_names: blockNames.join(',') }),
      })

      const response = await axios({
        method: 'GET',
        baseURL: baseURL,
        url:
          `/v1/protected/web-application/projects/${projectId}` +
          `/combiner-correlation-analysis?${params.toString()}`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      return response.data
    },
  })
}

export const useValidateCombinerData = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: {
    deviceIds?: number[]
    start?: string
    end?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  // Transform the parameters to match API expectations
  const transformedParams = {
    start: queryParams.start,
    end: queryParams.end,
    device_ids: queryParams.deviceIds,
  }

  const axiosConfig = {
    url: [
      '/v1/operational/projects',
      pathParams.projectId,
      'qc',
      'combiner-swaps',
      'validate-combiner-data',
    ].join('/'),
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
    // Only enable the query if we have all required parameters
    enabled: !!(
      queryParams.start &&
      queryParams.end &&
      queryParams.deviceIds &&
      queryParams.deviceIds.length > 0
    ),
  }

  return useCustomQuery<{ isValid: boolean; message?: string }>({
    axiosConfig,
    queryName: 'validateCombinerData',
    pathParams,
    queryParams: transformedParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
